from .encavacog import EncavaCog

async def setup(bot):
    await bot.add_cog(EncavaCog(bot))