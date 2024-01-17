from .boss import Boss

async def setup(bot):
    await bot.add_cog(Boss(bot))