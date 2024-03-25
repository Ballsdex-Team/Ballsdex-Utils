import discord
import asyncio
import enum
import re
import json
from email.message import EmailMessage

import aiosmtplib

from typing import Optional, Union, cast
from logging import getLogger

from discord.ui import Button, Modal, TextInput, View

from redbot.core import commands, app_commands, Config, modlog
from redbot.core.bot import Red

from ballsdex.core.models import (
    Ball,
    BallInstance,
    Player,
    GuildConfig,
    BlacklistedID,
    Special,
    balls,
)

from ballsdex.core.utils.transformers import BallEnabledTransform

from discord.ext import tasks

ID_REGEX = re.compile("\d{17,20}")
ROLE_IDS = {
    "ticket": 1059622470677704754,
    "boss": 1054624927879266404,
    "forum": 1055747502726447184,
    "reactions": 1052727000369995938,
    "ads": 1059931415069863976,
    "art": 1068426860964347904,
}

logger = getLogger("red.bdtools")


class BlacklistChoices(enum.Enum):
    ticket = 0
    boss = 1
    forum = 2
    reactions = 3
    ads = 4
    art = 5



class BDTools(commands.Cog):
    """Tools used within the Ballsdex server"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=104911, force_registration=True)
        self.config.register_guild(
            log_channel=None,
            email=None,
            password=None,
            appeals={},
            blacklised_appeals={},
            max=5000,
            min=250,
            pinned_thread=None,
            ignore_collector=[],
            ignore_diamond=[],
            diamond_max=60,
            diamond_min=10,
            submissions={},
        )
        self.config.register_user(collector_balls={})
        self.bot.add_view(UnbanView(None, bot, self))
        asyncio.create_task(self.check_collectors())

    async def check_collectors(self):
        # members = await self.config.all_users()
        to_delete = {}
        special_ignore = await self.config.guild_from_id(1049118743101452329).ignore_collector()
        maxi = await self.config.guild_from_id(1049118743101452329).max()
        mini = await self.config.guild_from_id(1049118743101452329).min()
        balls = await BallInstance.filter(special__id=13).prefetch_related("player", "ball")
        for ball in balls:
            if [ball.player.discord_id, ball.ball.id] in special_ignore:
                continue
            user = self.bot.get_user(ball.player.discord_id)
            rarity = ball.ball.rarity

            needed_count = self.interpolate_value(maxi, mini, rarity)
            needed_count = self.round_to_50(needed_count)
            count = await BallInstance.filter(
                ball=ball.ball, player__discord_id=ball.player.discord_id
            ).count()
            if count >= needed_count:
                continue
            await ball.delete()
            if user:
                await user.send(
                    f"Your {ball.ball.country} collector ball has been deleted because you no longer have enough balls to maintain it."
                )
            # to_delete[member].append(ball)
        # for member in to_delete:
        #     async with self.config.user_from_id(
        #         member
        #     ).collector_balls() as collector_balls:
        #         for ball in to_delete[member]:
        #             del collector_balls[str(ball)]
        diamond_balls = await BallInstance.filter(special__id=19).prefetch_related("player", "ball")
        special_ignore = await self.config.guild_from_id(1049118743101452329).ignore_diamond()
        diamond_max = await self.config.guild_from_id(1049118743101452329).diamond_max()
        diamond_min = await self.config.guild_from_id(1049118743101452329).diamond_min()
        for ball in diamond_balls:
            if [ball.player.discord_id, ball.ball.id] in special_ignore:
                continue
            user = self.bot.get_user(ball.player.discord_id)
            rarity = ball.ball.rarity
            needed_count = self.interpolate_value(diamond_max, diamond_min, rarity)
            needed_count = self.round_to_5(needed_count)
            count = await BallInstance.filter(
                ball=ball.ball, player__discord_id=ball.player.discord_id, shiny=True
            ).count()
            if count >= needed_count:
                continue
            await ball.delete()
            if user:
                await user.send(
                    f"Your {ball.ball.country} diamond ball has been deleted because you no longer have enough shiny balls to maintain it."
                )

        await asyncio.sleep(21600)

    async def on_load(self):
        balls.clear()
        for ball in await Ball.all():
            balls[ball.pk] = ball

    async def maybe_send_logs(
        self,
        guild: discord.Guild,
        mod: Union[discord.User, discord.Member],
        event: str,
        message: str,
    ) -> None:
        """Sends a message to the log channel if it exists."""
        log_channel_id = await self.config.guild(guild).log_channel()
        if log_channel_id is None:
            return
        log_channel = guild.get_channel(log_channel_id)
        if log_channel is None:
            return
        embed = discord.Embed(
            title=f"{event}",
            description=f"{message}",
        )
        embed.set_author(name=str(mod), icon_url=mod.avatar.url)
        await log_channel.send(embed=embed)

    # --- Set Commands ---
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(name="bdset")
    async def bdset_group(self, ctx):
        pass

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @bdset_group.command(name="logchannel")
    async def bdset_logchannel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        """Set the log channel for the server."""
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(f"Log channel has been set to {channel.mention}.")

    # --- Text Commands ---
    #    @commands.mod()
    #    @commands.command()
    #    async def slowmode(self, ctx: commands.Context, time: int):
    #        """Set the slowmode for the channel."""
    #        if time < 0 or time > 60:
    #            await ctx.send(
    #                "The time your have provided is out of bounds. It should be between 0 and 60."
    #            )
    #            return
    #        await ctx.channel.edit(
    #            slowmode_delay=time, reason=f"Requested by {str(ctx.author)}"
    #        )
    #        await ctx.send(f"Slowmode has been set to {time} seconds.")
    #        await self.maybe_send_logs(
    #            guild=ctx.guild,
    #            mod=ctx.author,
    #            event="Slowmode set",
    #            message=f"Slowmode has been set to {time} seconds on {ctx.channel.mention}."
    #        )

    @commands.mod()
    @commands.group(name="thread")
    async def thread_group(self, ctx):
        pass

    @commands.mod()
    @thread_group.command()
    async def close(self, ctx: commands.Context, *, reason: Optional[str] = None):
        """Close a thread/forum post."""
        if isinstance(ctx.channel, discord.Thread):
            if ctx.channel.parent_id == 1059224729019498546:
                return await ctx.send(
                    "You cannot close a thread in the tickets with this command.\nPlease use `-close` instead."
                )
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send("This channel is not a thread or forum post.")
            return
        await ctx.send("Topic has been closed.")
        if reason is not None:
            await ctx.channel.edit(
                locked=True,
                archived=True,
                reason=f"Requested by {str(ctx.author)} | {reason}",
            )
            await self.maybe_send_logs(
                guild=ctx.guild,
                mod=ctx.author,
                event="Thread closed",
                message=f"{ctx.channel.mention} has been closed.\nReason: {reason}",
            )
        else:
            await ctx.channel.edit(
                locked=True, archived=True, reason=f"Requested by {str(ctx.author)}"
            )
            await self.maybe_send_logs(
                guild=ctx.guild,
                mod=ctx.author,
                event="Thread closed",
                message=f"{ctx.channel.mention} has been closed.",
            )

    @commands.mod()
    @thread_group.command()
    async def lock(self, ctx: commands.Context, *, reason: Optional[str] = None):
        """Lock a forum/thread."""
        if isinstance(ctx.channel, discord.Thread):
            if ctx.channel.parent_id == 1059224729019498546:
                return await ctx.send(
                    "You cannot lock a thread in the tickets with this command.\nPlease use `-close` instead."
                )
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send("This channel is not a thread or forum post.")
            return
        await ctx.send("Topic has been locked.")
        if reason is not None:
            await ctx.channel.edit(
                locked=True, reason=f"Requested by {str(ctx.author)} | {reason}"
            )
            await self.maybe_send_logs(
                guild=ctx.guild,
                mod=ctx.author,
                event="Thread locked",
                message=f"{ctx.channel.mention} has been locked.\nReason: {reason}",
            )
        else:
            await ctx.channel.edit(
                locked=True, reason=f"Requested by {str(ctx.author)}"
            )
            await self.maybe_send_logs(
                guild=ctx.guild,
                mod=ctx.author,
                event="Thread locked",
                message=f"{ctx.channel.mention} has been locked.",
            )

    # @commands.is_owner()
    # @commands.command()
    # async def accept(self, ctx, *, reason: str):
    #     """Accept a suggestion"""
        
    #     if type(ctx.channel) is not discord.Tread:
    #         return await ctx.send("This is not a suggestion thread.")

    # --- Slash Commands ---
    @app_commands.command(name="clear-marketplace")
    @app_commands.guilds(discord.Object(id=1049118743101452329))
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_clear_marketplace(
        self,
        interaction: discord.Interaction,
        you_sure: bool = False,
    ) -> None:
        """Lock, archive, and clean the marketplace.

        Parameters
        -----------
        you_sure: bool
            Whether or not you are sure you want to clear the marketplace.
        """
        if you_sure is False:
            return await interaction.response.send_message(
                "You must be sure you want to clear the marketplace.",
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True, ephemeral=True)
        pinned_thread_conf = await self.config.guild(interaction.guild).pinned_thread()
        if pinned_thread_conf is not None:
            channel = interaction.guild.get_channel(1092534995605782678)
            pinned_thread_obj = channel.get_thread(pinned_thread_conf)
            if pinned_thread_obj is not None:
                await pinned_thread_obj.edit(locked=True, archived=True)
        # This better not take 15 minutes!
        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = False
        overwrite.send_messages_in_threads = False
        overwrite.add_reactions = False

        marketplace = discord.utils.get(
            interaction.guild.channels, id=1092534995605782678
        )
        if marketplace is None:
            return await interaction.followup.send(
                "The marketplace channel could not be found.",
                ephemeral=True,
            )
        await marketplace.set_permissions(
            interaction.guild.default_role, overwrite=overwrite
        )
        thread_list = (
            marketplace.threads
        )  # Store a local copy so we don't close our maintain message
        tag = discord.utils.get(marketplace.available_tags, name="Meta")

        try:
            pinned_thread = await marketplace.create_thread(
                name="Marketplace Maintenance 🧹",
                content="The marketplace is currently being cleaned. Please check back later.",
                applied_tags=[tag],
            )
            await pinned_thread.thread.edit(locked=True, pinned=True)
        except discord.HTTPException:
            return await interaction.followup.send(
                "The marketplace could not be cleaned due to max pinned threads being reached.",
                ephemeral=True,
            )
        for thread in thread_list:
            await thread.edit(locked=True, archived=True)
        # Undo the permissions
        overwrite.send_messages = None
        overwrite.send_messages_in_threads = None
        await pinned_thread.thread.edit(locked=True, archived=True)
        await marketplace.set_permissions(
            interaction.guild.default_role, overwrite=overwrite
        )
        trade = await marketplace.create_thread(
            name="Ask for Trade", content="Post your trades below.", applied_tags=[tag]
        )
        await trade.thread.edit(pinned=True)
        await self.config.guild(interaction.guild).pinned_thread.set(trade.thread.id)
        await marketplace.create_thread(
            name="Ask for Ball",
            content="Ask for balls below, any duplicate threads will be deleted..",
            applied_tags=[tag],
        )
        await interaction.followup.send("All done!")

    @app_commands.command(name="submit-artwork")
    @app_commands.guilds(discord.Object(id=1049118743101452329))
    @app_commands.choices(
        submission_type=[
            app_commands.Choice(name="Boss", value="boss"),
        ]
    )
    @app_commands.guild_only()
    async def slash_submit_art(
        self,
        interaction: discord.Interaction,
        submission_type: str,
        artwork: discord.Attachment,
    ):
        """Submit artwork to the server.

        Parameters
        -----------
        submission_type: str
            The type of submission.
        artwork: discord.Attachment
            The artwork to submit.
        """
        if submission_type == "boss":
            channel = interaction.guild.get_channel(1221794533088559174)
            async with self.config.guild(interaction.guild).submissions() as submissions:
                if submission_type not in submissions:
                    submissions[submission_type] = {}
                if str(interaction.user.id) in submissions[submission_type]:
                    return await interaction.response.send_message(
                        "You have already submitted an artwork.", ephemeral=True
                    )
                message = await channel.send(
                    file=await artwork.to_file(),
                )
                submissions[submission_type][str(interaction.user.id)] = {
                    "message": message.id,
                    "attachment": artwork.url,
                }
                await message.add_reaction("👍")
            await interaction.response.send_message(
                "Your artwork has been submitted.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Invalid submission type.", ephemeral=True
            )

    @commands.is_owner()
    @commands.command()
    async def accept(self, ctx):
        """Accept a suggestion"""
        
        if type(ctx.channel) is not discord.Thread:
            return await ctx.send("This is not a suggestion thread.")
        if ctx.channel.parent_id != 1049164568066281472:
            return await ctx.send("This is not in suggestions.")
        channel = ctx.guild.get_channel(1049164568066281472)
        tag = discord.utils.get(channel.available_tags, name="accepted")
        await ctx.channel.edit(locked=True, applied_tags=[tag] + ctx.channel.applied_tags)

    @commands.is_owner()
    @commands.command()
    async def deny(self, ctx, *, reason: str):
        """Deny a suggestion"""
        
        if type(ctx.channel) is not discord.Thread:
            return await ctx.send("This is not a suggestion thread.")
        if ctx.channel.parent_id != 1049164568066281472:
            return await ctx.send("This is not in suggestions.")
        await ctx.send(f"Denied for the following reason: {reason}")
        channel = ctx.guild.get_channel(1049164568066281472)
        tag = discord.utils.get(channel.available_tags, name="denied")
        await ctx.channel.edit(locked=True, applied_tags=[tag] + ctx.channel.applied_tags, archived=True)

    @commands.is_owner()
    @commands.command()
    async def implemented(self, ctx):
        """Mark a suggestion as implemented"""
        
        if type(ctx.channel) is not discord.Thread:
            return await ctx.send("This is not a suggestion thread.")
        if ctx.channel.parent_id != 1049164568066281472:
            return await ctx.send("This is not in suggestions.")
        channel = ctx.guild.get_channel(1049164568066281472)
        await ctx.send("Marked as implemented.")
        tag = discord.utils.get(channel.available_tags, name="implemented")
        tags = ctx.channel.applied_tags
        # remove accepted tag
        if discord.utils.get(tags, name="accepted"):
            tags.remove(discord.utils.get(tags, name="accepted"))
        await ctx.channel.edit(locked=True, applied_tags=[tag] + tags, archived=True)


    def round_to_50(self, x):
        return int(round(x / 50.0)) * 50
    
    def round_to_5(self, x):
        return int(round(x / 5.0)) * 5

    def interpolate_value(self, maximum, minimum, x):
        x1, y1 = 0.05, minimum
        x2, y2 = 0.8, maximum

        # formula :DDDDDDDDDDDDDDDD
        result = min(maximum, max(minimum, y1 + (x - x1) * (y2 - y1) / (x2 - x1)))
        return result

    @app_commands.command(name="collector")
    @app_commands.guilds(discord.Object(id=1049118743101452329))
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 600, key=lambda i: i.user.id)
    async def slash_collector(
        self,
        interaction: discord.Interaction,
        ball: BallEnabledTransform,
    ):
        """Create a collector ball.

        Parameters
        -----------
        ball: Ball
            The ball to create.
        """
        if not ball:
            return await interaction.response.send_message(
                "Ball not found.", ephemeral=True
            )
        if not ball.enabled:
            return await interaction.response.send_message(
                "Cannot use this ball", ephemeral=True
            )
        already_exists = await BallInstance.filter(
            ball=ball, player__discord_id=interaction.user.id, special__name="Collector"
        ).exists()
        if already_exists:
            return await interaction.response.send_message(
                f"You already have a {ball.country} collector ball.",
                ephemeral=True,
            )
        count = await BallInstance.filter(
            ball=ball, player__discord_id=interaction.user.id
        ).count()
        maxi = await self.config.guild(interaction.guild).max()
        mini = await self.config.guild(interaction.guild).min()
        needed_count = self.interpolate_value(maxi, mini, ball.rarity)
        needed_count = self.round_to_50(needed_count)
        if count < needed_count:
            return await interaction.response.send_message(
                f"You need {needed_count} {ball.country} to create a collector ball. You currently have {count}.",
                ephemeral=True,
            )

        async with self.config.user(
            interaction.user
        ).collector_balls() as collector_balls:
            if ball.country in collector_balls:
                return await interaction.response.send_message(
                    f"You already have a {ball.country} collector ball.",
                    ephemeral=True,
                )
            await interaction.response.send_message(
                f"Successfully created a {ball.country} collector ball.",
                ephemeral=True,
            )
            ball_obj = await BallInstance.create(
                ball=ball,
                player=await Player.get(discord_id=interaction.user.id),
                special=await Special.get(name="Collector"),
            )
            collector_balls[ball.country] = ball_obj.pk

    @app_commands.command(name="diamond")
    @app_commands.guilds(discord.Object(id=1049118743101452329))
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 600, key=lambda i: i.user.id)
    async def slash_diamond(
        self,
        interaction: discord.Interaction,
        ball: BallEnabledTransform,
    ):
        """Create a diamond ball."""
        if not ball:
            return await interaction.response.send_message(
                "Ball not found.", ephemeral=True
            )
        if not ball.enabled:
            return await interaction.response.send_message(
                "Cannot use this ball", ephemeral=True
            )
        already_exists = await BallInstance.filter(
            ball=ball, player__discord_id=interaction.user.id, special__name="Diamond"
        ).exists()
        if already_exists:
            return await interaction.response.send_message(
                f"You already have a diamond {ball.country} ball.", ephemeral=True
            )
        count = await BallInstance.filter(
            ball=ball, player__discord_id=interaction.user.id, shiny=True
        ).count()
        maxi = await self.config.guild(interaction.guild).diamond_max()
        mini = await self.config.guild(interaction.guild).diamond_min()
        needed_count = self.interpolate_value(maxi, mini, ball.rarity)
        needed_count = self.round_to_5(needed_count)
        if count < needed_count:
            return await interaction.response.send_message(
                f"You need {needed_count} shiny {ball.country} to create a diamond ball. You currently have {count}.",
                ephemeral=True,
            )
        ball_obj = await BallInstance.create(
            ball=ball,
            player=await Player.get(discord_id=interaction.user.id),
            special=await Special.get(name="Diamond"),
        )
        await interaction.response.send_message(
            f"Successfully created a diamond {ball.country} ball.", ephemeral=True
        )

    blacklist_group = app_commands.Group(
        name="blacklist",
        description="Blacklist a member from various parts of the server.",
        guild_only=True,
        guild_ids=[1049118743101452329],
        default_permissions=discord.Permissions(permissions=8),
    )

    @blacklist_group.command(
        name="add",
        description="Add a member to a blacklist.",
    )
    async def slash_blacklist_add(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        blacklist_type: BlacklistChoices,
        reason: str,
    ) -> None:
        """Blacklist a member from various parts of the server.

        Parameters
        -----------
        member: discord.Member
            A member to blacklist.
        blacklist_type: BlacklistChoices
            The type of blacklist to add a member to.
        reason: str
            The reason for blacklisting the member.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Security checks
        if member.bot is True:
            return await interaction.followup.send(
                "You're not allowed to blacklist bots."
            )
        if any(role.id in ROLE_IDS.values() for role in member.roles):
            return await interaction.followup.send("Member is already blacklisted.")
        if any(
            role.id in [1049119786988212296, 1073776116898218036, 1073775485840003102]
            for role in member.roles
        ):
            return await interaction.followup.send(
                "You're not allowed to blacklist a moderator or administrator."
            )

        role = interaction.guild.get_role(ROLE_IDS[blacklist_type.name])
        if type(role) is None:
            return await interaction.followup.send(
                "Role not found. Please notify the proper people."
            )
        await member.add_roles(role, reason=f"Requested by {str(interaction.user)}")
        await interaction.followup.send(
            f"Successfully blacklisted `{member.display_name}` from `{blacklist_type.name}`"
        )
        await self.maybe_send_logs(
            guild=interaction.guild,
            mod=interaction.user,
            event="Member server blacklisted",
            message=(
                f"{member.mention} has been blacklisted from {blacklist_type.name}.\n"
                f"Reason: {reason}"
            ),
        )

    @blacklist_group.command(
        name="remove",
        description="Remove a member from a blacklist.",
    )
    async def slash_blacklist_remove(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        blacklist_type: BlacklistChoices,
        reason: str,
    ) -> None:
        """De-blacklist a member from various parts of the server.

        Parameters
        -----------
        member: discord.Member
            A member to blacklist.
        blacklist_type: BlacklistChoices
            The type of blacklist to remove a member from.
        reason: str
            The reason for de-blacklisting the member.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Security checks
        if member.bot is True:
            return await interaction.followup.send(
                "You're not allowed to blacklist bots."
            )
        if any(
            role.id in [1049119786988212296, 1073776116898218036, 1073775485840003102]
            for role in member.roles
        ):
            return await interaction.followup.send(
                "You're not allowed to blacklist a moderator or administrator."
            )

        role = interaction.guild.get_role(ROLE_IDS[blacklist_type.name])
        if type(role) is None:
            return await interaction.followup.send(
                "Role not found. Please notify the proper people."
            )
        await member.remove_roles(role, reason=f"Requested by {str(interaction.user)}")
        await interaction.followup.send(
            f"Successfully de-blacklisted `{member.display_name}` from `{blacklist_type.name}`"
        )
        await self.maybe_send_logs(
            guild=interaction.guild,
            mod=interaction.user,
            event="Member server de-blacklisted",
            message=(
                f"{member.mention} has been de-blacklisted from {blacklist_type.name}.\n"
                f"Reason: {reason}"
            ),
        )

    @blacklist_group.command(
        name="appeal",
        description="Blacklist a member from appealing.",
    )
    async def slash_blacklist_appeal(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: str,
    ) -> None:
        """
        Blacklist a member from appealing."""
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.followup.send(
                "Invalid user ID. Please try again.", ephemeral=True
            )
        await interaction.followup.send(
            f"Successfully blacklisted `{user_id}` from appealing."
        )
        await self.maybe_send_logs(
            guild=interaction.guild,
            mod=interaction.user,
            event="Member appeal blacklisted",
            message=(
                f"{user_id} has been blacklisted from appealing.\n" f"Reason: {reason}"
            ),
        )
        async with self.config.guild(
            interaction.guild
        ).blacklised_appeals() as blacklised_appeals:
            blacklised_appeals[str(user_id)] = reason

    # thread_group = app_commands.Group(
    #     name="thread",
    #     description="Various thread actions.",
    #     guild_only=True,
    #     guild_ids=[1049118743101452329],
    # )

    # @thread_group.command(
    #     name="remove",
    #     description="Remove a user from a thread.",
    # )
    # async def slash_thread_remove(
    #     self,
    #     interaction: discord.Interaction,
    #     member: discord.Member,
    # ) -> None:
    #     """Remove a user from a thread.

    #     Parameters
    #     -----------
    #     member: discord.Member
    #         A member to remove from a thread.
    #     """
    #     await interaction.response.defer(thinking=True, ephemeral=True)
    #     thread = interaction.channel
    #     if not isinstance(thread, discord.Thread):
    #         return await interaction.followup.send(
    #             "This channel is not a thread or forum post."
    #         )
    #     if member not in thread.recipient:
    #         return await interaction.followup.send(
    #             "This member is not in this thread."
    #         )
    #     if interaction.user != thread.owner or interaction.guild.get_role(1049119446372986921) not in interaction.user.roles or interaction.guild.get_role(1100043591625232404) not in interaction.user.roles:
    #         return await interaction.followup.send(
    #             "You are not allowed to remove members from threads."
    #         )
    #     await thread.remove_recipient(member)
    #     await interaction.followup.send(
    #         f"Successfully removed `{member.display_name}` from `{thread.name}`"
    #     )
    #     await self.maybe_send_logs(
    #         guild=interaction.guild,
    #         mod=interaction.user,
    #         event="Member removed from thread",
    #         message=(
    #             f"{member.mention} has been removed from {thread.name}.\n"
    #         ),
    #     )

    async def handle_req(self, message):
        guild = message.guild
        ban_appeal_channel = guild.get_channel(1184091996932022292)
        ban_appeal = {}
        if (
            message.content
            == "{{Email Address}},{{Discord ID}},{{Discord Name}},{{Banning Admin}},{{Reason for ban}},{{Why should we unban you?}}"
        ):
            return
        try:
            split = message.content.split(",")
            ban_appeal["email"] = split[0]
            ban_appeal["id"] = split[1]
            ban_appeal["name"] = split[2]
            ban_appeal["admin"] = split[3]
            ban_appeal["reason"] = split[4]
            ban_appeal["msg"] = ",".join(split[5:])
        except Exception as e:
            user = guild.get_member(95932766180343808)
            await user.send(
                f"<@95932766180343808> cannot decode for ban appeal\n\n{message.content}"
            )
            logger.error(f"Cannot decode text for ban appeal\n\n{message.content}")
            return
        # check if user is banned
        # if not, return
        # if so, send message to ban-appeals channel
        try:
            ban_entry = await guild.fetch_ban(discord.Object(ban_appeal["id"]))
        except discord.NotFound:
            contents = "The user you are appealing for is not banned. Please appeal for a user that is banned.\n\nThanks,\nBallsdex Staff\n\nThis is an automated message, please do not reply to this email."
            await send_email(ban_appeal["email"], contents, self, guild)
            return
        blacklisted_app = await self.config.guild(guild).blacklised_appeals()
        if ban_appeal["id"] in blacklisted_app:
            contents = f"You have been blacklisted from appealing for the following reason(s): {blacklisted_app[ban_appeal['id']]}\n\nThanks,\nBallsdex Staff\n\nThis is an automated message, please do not reply to this email."
            await send_email(ban_appeal["email"], contents, self, guild)
            await ban_appeal_channel.send(
                f"{ban_appeal['name']}-{ban_appeal['id']} (Reason: {ban_entry.reason}) has appealed but is blacklisted from appealing for the following reason(s): {blacklisted_app[ban_appeal['id']]}"
            )
            return
        embed = discord.Embed(
            title=f"Ban Appeal for {ban_appeal['name']}",
            description=f"**Name**: {ban_appeal['name']}-{ban_appeal['id']}\n**Ban Reason**: {ban_entry.reason}\n**Ban Reason Supplied**: {ban_appeal['reason']}\n**Appeal Message**: {ban_appeal['msg'] if len(ban_appeal['msg']) < 750 else ban_appeal['msg'][:750] + '...'}\n**Banning Admin**: {ban_appeal['admin']}",
        )
        content = ""
        admin_search = ID_REGEX.findall(ban_entry.reason)
        if admin_search:
            admin = message.guild.get_member(int(admin_search[0]))
            content = admin.mention
        else:
            content = "<@&1049119786988212296> <@&1049119446372986921>"
        allowed_mentions = discord.AllowedMentions(
            everyone=False, roles=True, users=True
        )
        msg = await ban_appeal_channel.send(
            content,
            embed=embed,
            view=UnbanView(message, self.bot, self),
            allowed_mentions=allowed_mentions,
        )
        async with self.config.guild(guild).appeals() as appeals:
            appeals[str(msg.id)] = ban_appeal

    @commands.is_owner()
    @commands.command()
    async def bancheck(self, ctx, amount: int = 100):
        """Check for ban appeals."""
        ban_appeal_channel = ctx.guild.get_channel(1184084842405707828)
        async for message in ban_appeal_channel.history(limit=amount):
            await self.handle_req(message)

    # --- Events ---
    @commands.Cog.listener()
    async def on_message(self, message):
        """Add a reaction to messages with attachments or links for art contest."""
        if message.channel.id == 1184084842405707828:
            await self.handle_req(message)
            return

        if message.channel.id != 1210632184747135028:  # Art channel.
            return
        if any(
            # bots, ballsdexteam and staff.
            role.id in [1049188813508980806, 1049119446372986921, 1100043591625232404]
            for role in message.author.roles
        ):
            return
        await message.add_reaction("👍")

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        # get first message in thread
        first_message = thread.get_partial_message(thread.id)
        if first_message is None:
            return
        # pin
        await first_message.pin()

class UnbanPrompt(Modal, title=f"Unban Appeal"):
    reason = TextInput(
        label="Unban Confirmation",
        style=discord.TextStyle.short,
        placeholder="Are you sure? Please type 'yes' to confirm.",
    )

    def __init__(self, interaction, button, ban, email, bot, cog):
        super().__init__()
        self.interaction = interaction
        self.button = button
        self.ban = ban
        self.email = email
        self.bot = bot
        self.cog = cog

    async def on_submit(self, interaction):
        if self.reason.value.lower() != "yes":
            await interaction.response.send_message(
                f"{interaction.user.mention} has not unbanned {self.ban.user} because they did not confirm.",
                ephemeral=True,
            )
            return
        await interaction.guild.unban(self.ban.user, reason=f"Ban appealed accepted by {interaction.user}")
        await interaction.response.send_message(
            f"{interaction.user.mention} has unbanned {self.ban.user}.", ephemeral=True
        )
        async with self.cog.config.guild(interaction.guild).appeals() as appeals:
            appeals[str(self.interaction.message.id)]["handled"] = True
        await modlog.create_case(
            self.bot,
            interaction.guild,
            interaction.created_at,
            "unban",
            self.ban.user,
            self.interaction.user,
            f"Unban appeal accepted by {interaction.user}",
        )
        await send_email(
            self.email,
            f"Your ban appeal for {interaction.guild} has been accepted. You have been unbanned.\n\nThanks,\nBallsdex Staff\n\nThis is an automated message, please do not reply to this email.",
            self.cog,
            interaction.guild,
        )
        # remove buttons from original interaction
        await self.interaction.message.edit(
            view=None,
            content=f"{self.interaction.message.content}\n\n{interaction.user.mention} has unbanned this user.",
        )


async def send_email(email, contents, cog, guild):
    message = EmailMessage()
    message["From"] = await cog.config.guild(guild).email()
    message["To"] = email
    message["Subject"] = "Ballsdex Ban Appeal Result"
    contents = contents
    message.set_content(contents)
    await aiosmtplib.send(
        message,
        recipients=[email],
        hostname="smtp.gmail.com",
        port=465,
        username=await cog.config.guild(guild).email(),
        password=await cog.config.guild(guild).password(),
        use_tls=True,
    )


class UnbanDenyPrompt(Modal, title=f"Unban Appeal"):
    reason = TextInput(label="Reason for denial", style=discord.TextStyle.long)

    def __init__(self, interaction, button, ban, email, cog):
        super().__init__()
        self.interaction = interaction
        self.button = button
        self.ban = ban
        self.email = email
        self.cog = cog

    async def on_submit(self, interaction):
        await interaction.response.send_message(
            f"{interaction.user.mention} has denied {self.ban.user}'s appeal for {self.reason.value}.",
            ephemeral=True,
        )
        async with self.cog.config.guild(interaction.guild).appeals() as appeals:
            appeals[str(self.interaction.message.id)]["handled"] = True
        contents = f"Your ban appeal for {interaction.guild} has been denied for the following reason: {self.reason.value}\n\nThanks,\nBallsdex Staff\n\nThis is an automated message, please do not reply to this email."
        await send_email(self.email, contents, self.cog, interaction.guild)
        # # remove buttons from original interaction
        await self.interaction.message.edit(
            view=None,
            content=f"{self.interaction.message.content}\n\n{interaction.user.mention} has denied this appeal for the following reason: {self.reason.value}",
        )


class UnbanView(View):
    def __init__(self, interaction: discord.Interaction, bot, cog):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.ban = None
        self.email = None
        self.bot = bot
        self.cog = cog
        self.admin = None
        self.handled = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        await self.get_data(interaction)
        if 1049119446372986921 in [
            x.id for x in interaction.user.roles
        ] or 718365766671663144 not in [x.id for x in interaction.user.roles]:
            return True
        if self.admin is not None and interaction.user.id != self.admin:
            await interaction.response.send_message(
                "You are not the banning admin.", ephemeral=True
            )
            return False
        return True

    async def get_data(self, interaction: discord.Interaction):
        message = interaction.message
        async with self.cog.config.guild(interaction.guild).appeals() as appeals:
            appeal = appeals[str(message.id)]
        self.email = appeal["email"]
        self.handled = appeal.get("handled", False)
        try:
            self.ban = await interaction.guild.fetch_ban(discord.Object(appeal["id"]))
        except discord.NotFound:
            self.ban = None
            return
        admin_search = ID_REGEX.findall(self.ban.reason)
        if admin_search:
            self.admin = message.guild.get_member(int(admin_search[0]))
        else:
            self.admin = None

    @discord.ui.button(
        style=discord.ButtonStyle.success, label="Unban User", custom_id="unban_button"
    )
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        await self.get_data(interaction)
        if self.ban is None:
            await interaction.response.send_message(
                "This user is not banned.", ephemeral=True
            )
            await interaction.message.edit(view=None)
            return
        if self.handled:
            await interaction.response.send_message(
                "This appeal has already been handled.", ephemeral=True
            )
            return
        await interaction.response.send_modal(
            UnbanPrompt(interaction, button, self.ban, self.email, self.bot, self.cog)
        )

    @discord.ui.button(
        style=discord.ButtonStyle.danger,
        label="Reject Appeal",
        custom_id="reject-button",
    )
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        await self.get_data(interaction)
        if self.ban is None:
            await interaction.response.send_message(
                "This user is not banned.", ephemeral=True
            )
            await interaction.message.edit(view=None)

            return
        await interaction.response.send_modal(
            UnbanDenyPrompt(interaction, button, self.ban, self.email, self.cog)
        )
