import discord
from discord.ext import commands

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="баланс", description="Посмотреть баланс")
    async def баланс(self, ctx, пользователь: discord.Member = None):
        user = пользователь or ctx.author
        embed = discord.Embed(title="💰 Баланс", description=f"**{user.display_name}**\nБаланс: `1000 монет`", color=0xF1C40F)
        await ctx.response.send_message(embed=embed)

    @commands.slash_command(name="ежедневно", description="Получить ежедневную награду")
    async def ежедневно(self, ctx):
        embed = discord.Embed(title="🎁 Ежедневная награда", description="**+500 монет!**\nБаланс: `1500 монет`", color=0x57F287)
        await ctx.response.send_message(embed=embed)

    @commands.slash_command(name="работа", description="Заработать деньги")
    async def работа(self, ctx):
        embed = discord.Embed(title="💼 Работа", description="**+200 монет!**\nБаланс: `1700 монет`", color=0x57F287)
        await ctx.response.send_message(embed=embed)

    @commands.slash_command(name="слоты", description="Играть в слоты")
    async def слоты(self, ctx, ставка: int = 100):
        symbols = ["🍒", "🍋", "🍊"]
        result = [random.choice(symbols) for _ in range(3)]
        
        if result[0] == result[1] == result[2]:
            win = ставка * 3
            embed = discord.Embed(title="🎰 ДЖЕКПОТ!", description=f"**{''.join(result)}**\nВыигрыш: {win} монет!", color=0x57F287)
        else:
            embed = discord.Embed(title="🎰 Слоты", description=f"**{''.join(result)}**\nПопробуй еще раз!", color=0xED4245)
        
        await ctx.response.send_message(embed=embed)

    @commands.slash_command(name="крипта", description="Курсы криптовалют")
    async def крипта(self, ctx):
        embed = discord.Embed(title="₿ Криптовалюты", color=0x16C60C)
        embed.add_field(name="BITCOIN", value=f"${crypto_prices['BITCOIN']:,.2f}", inline=True)
        embed.add_field(name="ETHEREUM", value=f"${crypto_prices['ETHEREUM']:,.2f}", inline=True)
        embed.add_field(name="DOGECOIN", value=f"${crypto_prices['DOGECOIN']:,.2f}", inline=True)
        await ctx.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
