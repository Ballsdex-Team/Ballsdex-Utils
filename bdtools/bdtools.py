import discord

from redbot.core import commands
from redbot.core.bot import Red

ROLE_IDS = {
    "ticket": 1059622470677704754,
    "boss": 1054624927879266404,
    "forum": 1055747502726447184,
    "reactions": 1052727000369995938,
    "ads": 1059931415069863976,
    "art": 1068426860964347904
}

class BDTools(commands.Cog):
    """Tools used within the Ballsdex server"""


    def __init__(self, bot: Red):
        self.bot = bot

    @commands.mod()
    @commands.command()
    async def slowmode(self, ctx: commands.Context, time: int):
        """Set the slowmode for the channel."""
        if time < 0 or time > 60:
            await ctx.send("The time your have provided is out of bounds. It just be between 0 and 60.")
            return
        await ctx.channel.edit(slowmode_delay=time)
        await ctx.send(f"Slowmode has been set to {time} seconds.")

    @commands.mod()
    @commands.command()
    async def close(self, ctx: commands.Context, *, reason: str):
        """Close a thread/forum post."""
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send("This channel is not a thread or forum post.")
            return
        await ctx.channel.edit(locked=True, archived=True, reason=reason)
        await ctx.send("Topic has been closed.")
    
    @commands.mod()
    @commands.command()
    async def lock(self, ctx: commands.Context, *, reason: str):
        """Lock a forum/thread."""
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send("This channel is not a thread or forum post.")
            return
        await ctx.channel.edit(locked=True, reason=reason)
        await ctx.send("Topic has been closed.")

    @commands.mod()
    @commands.command(usage="<type> <user>")
    async def blacklist(self, ctx: commands.Context, _type: str, user: discord.Member):
        """Blacklist a user from various parts of the bot.
        

        Valid types:
            -   Ticket - Blacklist a user from tickets.
            -   Boss - Mute a user from boss fights.
            -   Forum - Blacklist a user from forums.
            -   Reactions - Blacklist a user from using reactions.
            -   Ads - Blacklist a user from advertisements.
            -   Art - Blacklist a user from art & media."""
        _type = _type.lower()
        if _type not in ROLE_IDS:
            await ctx.send(f"The type of blacklist you have provided does not exist, pleas use one of the following: {', '.join(ROLE_IDS.keys())}")
            return
        role = [ctx.guild.get_role(ROLE_IDS[_type])]
        await user.add_roles(*role)
        await ctx.tick()
