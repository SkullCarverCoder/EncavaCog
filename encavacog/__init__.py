from .encavacog import EncavaCog

async def setup(bot):
    cog = EncavaCog(bot)
    await bot.add_cog()
    cog.start_up_task()