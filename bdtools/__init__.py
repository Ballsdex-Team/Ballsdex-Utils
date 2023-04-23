import discord

from .bdtools import BDTools

from redbot.core.bot import Red

async def setup(bot: Red):
    await bot.add_cog(BDTools(bot), guilds=[discord.Object(id=1049118743101452329)])
