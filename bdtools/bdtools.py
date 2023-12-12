import discord
import enum
import re
import json
from email.message import EmailMessage

import aiosmtplib

from typing import Optional, Union, cast

from discord.ui import Button, Modal, TextInput, View

from redbot.core import commands, app_commands, Config, modlog
from redbot.core.bot import Red

URL_REGEX = re.compile(r"(http[s]?:\/\/[^\"\']*\.(?:png|jpg|jpeg))")
ROLE_IDS = {
    "ticket": 1059622470677704754,
    "boss": 1054624927879266404,
    "forum": 1055747502726447184,
    "reactions": 1052727000369995938,
    "ads": 1059931415069863976,
    "art": 1068426860964347904,
}


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
        self.config.register_guild(log_channel=None, email=None, password=None)
        self.bot.add_view(UnbanView(None, None, None, bot, self))

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
                message=f"{ctx.channel.mention} has been closed.\nReason: {reason}"
            )
        else:
            await ctx.channel.edit(
                locked=True, archived=True, reason=f"Requested by {str(ctx.author)}"
            )
            await self.maybe_send_logs(
                guild=ctx.guild,
                mod=ctx.author,
                event="Thread closed",
                message=f"{ctx.channel.mention} has been closed."
            )

    @commands.mod()
    @thread_group.command()
    async def lock(self, ctx: commands.Context, *, reason: Optional[str] = None):
        """Lock a forum/thread."""
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
                message=f"{ctx.channel.mention} has been locked.\nReason: {reason}"
            )
        else:
            await ctx.channel.edit(
                locked=True, reason=f"Requested by {str(ctx.author)}"
            )
            await self.maybe_send_logs(
                guild=ctx.guild,
                mod=ctx.author,
                event="Thread locked",
                message=f"{ctx.channel.mention} has been locked."
            )

    # --- Slash Commands ---
    @app_commands.command(name="clear-marketplace")
    @app_commands.guilds(discord.Object(id=1049118743101452329))
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_clear_marketplace(
        self, interaction: discord.Interaction,
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
        # This better not take 15 minutes!
        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = False
        overwrite.send_messages_in_threads = False
        overwrite.add_reactions = False

        marketplace = discord.utils.get(interaction.guild.channels, id=1092534995605782678)
        if marketplace is None:
            return await interaction.followup.send(
                "The marketplace channel could not be found.",
                ephemeral=True,
            )
        await marketplace.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        thread_list = marketplace.threads  # Store a local copy so we don't close our maintain message
        tag = discord.utils.get(marketplace.available_tags, name="Meta")

        try:
            pinned_thread = await marketplace.create_thread(
                name="Marketplace Maintenance 🧹",
                content="The marketplace is currently being cleaned. Please check back later.",
                applied_tags=[tag]
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
        await marketplace.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        trade = await marketplace.create_thread(
                name="Ask for Trade",
                content="Post your trades below.",
                applied_tags=[tag]
        )
        await trade.thread.edit(pinned=True)
        await marketplace.create_thread(
                name="Ask for Ball",
                content="Ask for balls below, any duplicate threads will be deleted..",
                applied_tags=[tag]
        )
        await interaction.followup.send("All done!")

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
    

    # --- Events ---
    @commands.Cog.listener()
    async def on_message(self, message):
        """Add a reaction to messages with attachments or links for art contest."""
        if message.channel.id == 1184084842405707828:
            try:
                ban_appeal = json.loads(message.content)
            except json.JSONDecodeError:
                return
            # check if user is banned
            # if not, return
            # if so, send message to ban-appeals channel
            try:
                ban_entry = await message.guild.fetch_ban(discord.Object(ban_appeal["id"]))
            except discord.NotFound:
                message = EmailMessage()
                message["From"] = await self.config.guild(message.guild).email()
                message["To"] = self.email
                message["Subject"] = "Ballsdex Ban Appeal"
                contents = "The user you are appealing for is not banned. Please appeal for a user that is banned.\n\nThanks,\nBallsdex Staff\n\nThis is an automated message, please do not reply to this email."
                message.set_content(contents)
                await aiosmtplib.send(
                    message,
                    recipients=[self.email],
                    hostname="smtp.gmail.com",
                    port=465,
                    username=await self.config.guild(message.guild).email(),
                    password=await self.config.guild(message.guild).password(),
                    use_tls=True,
                )
                return
            ban_appeal_channel = message.guild.get_channel(1184091996932022292)
            embed = discord.Embed(
                title=f"Ban Appeal for {ban_appeal['name']}",
                description=f"**Name**: {ban_appeal['name']}-{ban_appeal['id']}\n**Ban Reason**: {ban_entry.reason}\n**Ban Reason Supplied**: {ban_appeal['reason']}\n**Appeal Message**: {ban_appeal['msg'] if len(ban_appeal['msg']) < 750 else ban_appeal['msg'][:750] + '...'}\n**Banning Admin**: {ban_appeal['admin']}",

            )
            await ban_appeal_channel.send(embed=embed, view=UnbanView(message, ban_entry, ban_appeal["email"], self.bot, self))
            return

        if message.channel.id != 1177735598275035157: # Art channel.
            return
        if any(
            # Ballsdex and Proto helper bot, bots
            role.id in [1049119096517705762, 1091077320292438149, 1049188813508980806]
            for role in message.author.roles
        ):
            return
        await message.add_reaction("👍")



class UnbanPrompt(Modal, title=f"Unban Appeal"):
    reason = TextInput(
        label="Unban Confirmation", style=discord.TextStyle.short, placeholder="Are you sure? Please type 'yes' to confirm."
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
            await interaction.response.send_message(f"{interaction.user.mention} has not unbanned {self.ban.user} because they did not confirm.", ephemeral=True)
            return
        await interaction.guild.unban(self.ban.user, reason=self.reason.value)
        await interaction.response.send_message(f"{interaction.user.mention} has unbanned {self.ban.user} for {self.reason.value}.")
        await modlog.create_case(
            self.bot,
            interaction.guild,
            interaction.created_at,
            "unban",
            self.ban.user,
            self.interaction.user,
            self.reason.value,
        )
        message = EmailMessage()
        message["From"] = await self.cog.config.guild(interaction.guild).email()
        message["To"] = self.email
        message["Subject"] = "Ballsdex Ban Appeal Result"
        contents = f"Your ban appeal for {interaction.guild} has been accepted. You have been unbanned. Please follow the rules in the future.\nThe invite to rejoin is https://discord.gg/ballsdex\n\nThanks,\nBallsdex Staff\n\nThis is an automated message, please do not reply to this email."
        message.set_content(contents)
        await aiosmtplib.send(
            message,
            recipients=[self.email],
            hostname="smtp.gmail.com",
            port=465,
            username=await self.cog.config.guild(interaction.guild).email(),
            password=await self.cog.config.guild(interaction.guild).password(),
            use_tls=True,
        )
        # remove buttons from original interaction
        await self.interaction.message.edit(view=None)


class UnbanDenyPrompt(Modal, title=f"Unban Appeal"):
    reason = TextInput(
        label="Reason for denial", style=discord.TextStyle.long
    )

    def __init__(self, interaction, button, ban, email, cog):
        super().__init__()
        self.interaction = interaction
        self.button = button
        self.ban = ban
        self.email = email
        self.cog = cog


    async def on_submit(self, interaction):
        await interaction.response.send_message(f"{interaction.user.mention} has denied {self.ban.user}'s appeal for {self.reason.value}.")
        message = EmailMessage()
        message["From"] = await self.cog.config.guild(interaction.guild).email()
        message["To"] = self.email
        message["Subject"] = "Ballsdex Ban Appeal Result"
        contents = f"Your ban appeal for {interaction.guild} has been denied for the following reason: {self.reason.value}\n\nThanks,\nBallsdex Staff\n\nThis is an automated message, please do not reply to this email."
        message.set_content(contents)
        await aiosmtplib.send(
            message,
            recipients=[self.email],
            hostname="smtp.gmail.com",
            port=465,
            username=await self.cog.config.guild(interaction.guild).email(),
            password=await self.cog.config.guild(interaction.guild).password(),
            use_tls=True,
        )
        # remove buttons from original interaction
        await self.interaction.message.edit(view=None)


class UnbanView(View):
    def __init__(self, interaction: discord.Interaction, ban, email, bot, cog):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.ban = ban
        self.email = email
        self.bot = bot
        self.cog = cog

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if 1049119446372986921 not in [x.id for x in interaction.user.roles] or 1100043591625232404 not in [x.id for x in interaction.user.roles]:
            await interaction.response.send_message(
                "You are not allowed to use this command.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        style=discord.ButtonStyle.success, label="Unban User", custom_id="unban_button"
    )
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(UnbanPrompt(interaction, button, self.ban, self.email, self.bot, self.cog))

    @discord.ui.button(
        style=discord.ButtonStyle.danger,
        label="Reject Appeal",
        custom_id="reject-button"
    )
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
       await interaction.response.send_modal(UnbanDenyPrompt(interaction, button, self.ban, self.email, self.cog))

