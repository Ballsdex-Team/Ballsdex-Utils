import discord
import enum
import re

from typing import Optional, Union

from redbot.core import commands, app_commands, Config
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

        self.config.register_guild(log_channel=None)

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

    # --- Events ---
    @commands.Cog.listener()
    async def on_message(self, message):
        """Add a reaction to messages with attachments or links for art contest."""
        if message.channel.id != 1177735598275035157: # Art channel.
            return
        if any(
            # Ballsdex and Proto helper bot.
            role.id in [1049119096517705762, 1091077320292438149]
            for role in message.author.roles
        ):
            return
        await message.add_reaction("👍")
