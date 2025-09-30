import discord

class Design:
    COLORS = {
        "primary": 0x5865F2,
        "success": 0x57F287,
        "warning": 0xFEE75C,
        "danger": 0xED4245,
        "economy": 0xF1C40F,
        "music": 0x9B59B6,
        "crypto": 0x16C60C
    }

    @staticmethod
    def create_embed(title: str, description: str = "", color: str = "primary"):
        embed = discord.Embed(title=title, description=description, color=Design.COLORS.get(color, Design.COLORS["primary"]))
        embed.set_footer(text="💎 Mega Economy Bot")
        return embed

    @staticmethod
    def create_economy_embed(user: discord.Member, balance: int):
        embed = discord.Embed(title="💰 Экономика", color=Design.COLORS["economy"])
        embed.add_field(name="👤 Пользователь", value=user.mention, inline=True)
        embed.add_field(name="💵 Баланс", value=f"`{balance:,} монет`", inline=True)
        return embed
