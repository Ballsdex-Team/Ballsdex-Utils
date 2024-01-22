from .dragontools import DragonTools, report, report_user

async def setup(bot):
    cog = DragonTools(bot)
    bot.tree.add_command(report)
    bot.tree.add_command(report_user)
    await bot.add_cog(cog)