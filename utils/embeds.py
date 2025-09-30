import discord

class Design:
    COLORS = {
        "primary": 0x5865F2,
        "success": 0x57F287, 
        "warning": 0xFEE75C,
        "danger": 0xED4245
    }

    @staticmethod
    def create_embed(title, description="", color="primary"):
        return discord.Embed(title=title, description=description, color=Design.COLORS.get(color, Design.COLORS["primary"]))
