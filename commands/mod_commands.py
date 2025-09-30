import discord
from discord.ext import commands

class ModCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.slash_command(name="пред", description="Выдать предупреждение")
    async def пред(self, ctx, пользователь: discord.Member, причина: str):
        pass
    
    @commands.slash_command(name="снять_пред", description="Снять предупреждение")
    async def снять_пред(self, ctx, пользователь: discord.Member, количество: int = 1):
        pass
    
    @commands.slash_command(name="варны", description="Посмотреть предупреждения")
    async def варны(self, ctx, пользователь: discord.Member = None):
        pass
    
    @commands.slash_command(name="мут", description="Замутить пользователя")
    async def мут(self, ctx, пользователь: discord.Member, время: str, причина: str):
        pass
    
    @commands.slash_command(name="размут", description="Размутить пользователя")
    async def размут(self, ctx, пользователь: discord.Member):
        pass
    
    @commands.slash_command(name="очистить", description="Очистить сообщения")
    async def очистить(self, ctx, количество: int):
        pass
    
    @commands.slash_command(name="стата_сервера", description="Статистика сервера")
    async def стата_сервера(self, ctx):
        pass
    
    @commands.slash_command(name="топ_нарушители", description="Топ нарушителей")
    async def топ_нарушители(self, ctx):
        pass

def setup(bot):
    bot.add_cog(ModCommands(bot))
