import discord
from discord.ext import commands

class ModCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="пред", description="Выдать предупреждение")
    async def пред(self, ctx, пользователь: discord.Member, причина: str = "Не указана"):
        if пользователь.id not in user_warns:
            user_warns[пользователь.id] = 0
        
        user_warns[пользователь.id] += 1
        current_warns = user_warns[пользователь.id]
        
        embed = discord.Embed(title="⚠️ Предупреждение", color=0xFEE75C)
        embed.add_field(name="Пользователь", value=пользователь.mention, inline=True)
        embed.add_field(name="Причина", value=причина, inline=True)
        embed.add_field(name="Текущие пред", value=f"{current_warns}/3", inline=True)
        
        await ctx.response.send_message(embed=embed)

    @commands.slash_command(name="снять_пред", description="Снять предупреждение")
    async def снять_пред(self, ctx, пользователь: discord.Member, количество: int = 1):
        if пользователь.id in user_warns and user_warns[пользователь.id] > 0:
            user_warns[пользователь.id] = max(0, user_warns[пользователь.id] - количество)
            embed = discord.Embed(title="✅ Пред снято", description=f"Снято {количество} предупреждений у {пользователь.mention}", color=0x57F287)
        else:
            embed = discord.Embed(title="❌ Ошибка", description="У пользователя нет предупреждений", color=0xED4245)
        
        await ctx.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ModCommands(bot))
