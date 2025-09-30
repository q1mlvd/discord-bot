import discord

class Design:
    COLORS = {
        "primary": 0x5865F2, "success": 0x57F287, "warning": 0xFEE75C, 
        "danger": 0xED4245, "economy": 0xF1C40F, "music": 0x9B59B6,
        "moderation": 0xE74C3C, "shop": 0x9B59B6, "casino": 0xE67E22,
        "info": 0x3498DB, "premium": 0xFFD700, "roblox": 0xE74C3C,
        "discord": 0x5865F2, "tds": 0xF1C40F, "crypto": 0x16C60C,
        "event": 0x9B59B6, "credit": 0xE74C3C, "nft": 0x9C27B0
    }

    @staticmethod
    def create_embed(title: str, description: str = "", color: str = "primary"):
        embed = discord.Embed(title=title, description=description, color=Design.COLORS.get(color, Design.COLORS["primary"]))
        embed.set_footer(text="💎 Mega Economy Bot")
        return embed

    @staticmethod
    def create_economy_embed(user: discord.Member, balance: int, transaction: str = ""):
        embed = discord.Embed(title="💰 Экономика", color=Design.COLORS["economy"])
        embed.add_field(name="👤 Пользователь", value=user.mention, inline=True)
        embed.add_field(name="💵 Баланс", value=f"`{balance:,} монет`", inline=True)
        if transaction:
            embed.add_field(name="📊 Транзакция", value=transaction, inline=False)
        return embed

    @staticmethod
    def create_music_embed(track: str, duration: str, requester: discord.Member):
        embed = discord.Embed(title="🎵 Сейчас играет", color=Design.COLORS["music"])
        embed.add_field(name="Трек", value=track, inline=False)
        embed.add_field(name="Длительность", value=duration, inline=True)
        embed.add_field(name="Заказал", value=requester.mention, inline=True)
        return embed
