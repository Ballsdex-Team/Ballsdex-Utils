import discord
import enum
import re

from typing import Optional

from redbot.core import commands, app_commands
from redbot.core.bot import Red

URL_REGEX = re.compile(r"(http[s]?:\/\/[^\"\']*\.(?:png|jpg|jpeg))")
ROLE_IDS = {
    "ticket": 1059622470677704754,
    "boss": 1054624927879266404,
    "forum": 1055747502726447184,
    "reactions": 1052727000369995938,
    "ads": 1059931415069863976,
    "art": 1068426860964347904
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

    @commands.mod()
    @commands.command()
    async def slowmode(self, ctx: commands.Context, time: int):
        """Set the slowmode for the channel."""
        if time < 0 or time > 60:
            await ctx.send("The time your have provided is out of bounds. It should be between 0 and 60.")
            return
        await ctx.channel.edit(slowmode_delay=time, reason=f"Requested by {str(ctx.author)}")
        await ctx.send(f"Slowmode has been set to {time} seconds.")

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
                reason=f"Requested by {str(ctx.author)} | {reason}"
            )
        else:
            await ctx.channel.edit(
                locked=True,
                archived=True,
                reason=f"Requested by {str(ctx.author)}"
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
                locked=True,
                reason=f"Requested by {str(ctx.author)} | {reason}"
            )
        else:
            await ctx.channel.edit(
                locked=True,
                reason=f"Requested by {str(ctx.author)}"
            )

    @app_commands.command(name="blacklist", description="Blacklist a member from various parts of the server.")
    @app_commands.guilds(discord.Object(id=1049118743101452329))
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_blacklist(self, interaction: discord.Interaction, member: discord.Member, blacklist_type: BlacklistChoices) -> None:
        """Blacklist a member from various parts of the server.

        Parameters
        -----------
        member: discord.Member
            A member to blacklist.
        blacklist_type: BlacklistChoices
            The type of blacklist to add a member to.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Security checks
        if member.bot is True:
            return await interaction.followup.send("You're not allowed to blacklist bots.")
        if any(role.id in ROLE_IDS.values() for role in member.roles):
            return await interaction.followup.send("Member is already blacklisted.")
        if any(role.id in [1049119786988212296, 1073776116898218036, 1073775485840003102] for role in member.roles):
            return await interaction.followup.send("You're not allowed to blacklist a moderator or administrator.")

        role = interaction.guild.get_role(ROLE_IDS[blacklist_type.name])
        if type(role) is None:
            return await interaction.followup.send("Role not found. Please notify the proper people.")
        await member.add_roles(
            role,
            reason=f"Requested by {str(interaction.user)}"
        )
        return await interaction.followup.send(f"Successfully blacklisted `{member.display_name}` from `{blacklist_type.name}`")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Add a reaction to messages with attachments or links for art contest."""
        if any(role.id in [1049119786988212296, 1073776116898218036, 1073775485840003102] for role in message.author.roles):
            return
        if message.channel.id != 1097569050734891059:
            return
        if message.attachments or URL_REGEX.search(message.content):
            await message.add_reaction("👍")
            return
        await message.delete()
