import discord
from discord.ext import commands

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="выдать", description="Выдать монеты")
    async def выдать(self, ctx, пользователь: discord.Member, количество: int):
        embed = discord.Embed(title="💰 Деньги выданы", color=0x57F287)
        embed.add_field(name="Пользователь", value=пользователь.mention, inline=True)
        embed.add_field(name="Сумма", value=f"{количество} монет", inline=True)
        await ctx.response.send_message(embed=embed)

    @commands.slash_command(name="перезагрузить", description="Перезагрузить бота")
    async def перезагрузить(self, ctx):
        embed = discord.Embed(title="🔄 Перезагрузка", description="Бот перезагружается...", color=0xF1C40F)
        await ctx.response.send_message(embed=embed, ephemeral=True)
        
        # Перезагрузка когов
        await self.bot.reload_extension('commands.user_commands')
        await self.bot.reload_extension('commands.mod_commands')
        await self.bot.reload_extension('commands.admin_commands')

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
