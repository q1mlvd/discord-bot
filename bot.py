import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Твои каналы
ADMIN_LOG_CHANNEL = 1419779743083003944
EVENTS_CHANNEL = 1418738569081786459
ECONOMY_CHANNEL = 1422641391682588734
GUILD_ID = 993041244706066552

# Твои роли (замени на реальные ID)
ADMIN_ROLES = [993042425809473596, 1188261847850299514, 1365798715930968244, 1269614293108789278, 1259892523053092874]
MOD_ROLES = [1167093102868172911, 1360243534946373672, 993043931342319636, 1338611327022923910, 1338609155203661915]

class MegaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix='!', 
            intents=intents,
            help_command=None
        )
        
    async def setup_hook(self):
        # Загружаем команды по категориям
        await self.load_extension('commands.user_commands')
        await self.load_extension('commands.mod_commands') 
        await self.load_extension('commands.admin_commands')
        
        # Синхронизируем команды только для твоего сервера
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        
        print("✅ МЕГА-БОТ ЗАПУЩЕН!")

# Система прав
def is_admin():
    async def predicate(interaction: discord.Interaction):
        if interaction.guild.id != GUILD_ID:
            return False
        user_roles = [role.id for role in interaction.user.roles]
        return any(role in ADMIN_ROLES for role in user_roles)
    return commands.check(predicate)

def is_moderator():
    async def predicate(interaction: discord.Interaction):
        if interaction.guild.id != GUILD_ID:
            return False
        user_roles = [role.id for role in interaction.user.roles]
        return any(role in MOD_ROLES + ADMIN_ROLES for role in user_roles)
    return commands.check(predicate)

bot = MegaBot()

# 🔥 КОМАНДЫ ДЛЯ ВСЕХ УЧАСТНИКОВ
@bot.tree.command(name="баланс", description="Посмотреть баланс")
async def баланс(interaction: discord.Interaction, пользователь: discord.Member = None):
    # Твоя экономика здесь
    await interaction.response.send_message("💰 Баланс: 1000 монет")

@bot.tree.command(name="ежедневно", description="Получить ежедневную награду")  
async def ежедневно(interaction: discord.Interaction):
    await interaction.response.send_message("🎁 +500 монет!")

# ЕЩЕ 25 команд для участников...

# 🔧 КОМАНДЫ ДЛЯ МОДЕРОВ  
@bot.tree.command(name="пред", description="Выдать предупреждение")
@is_moderator()
async def пред(interaction: discord.Interaction, пользователь: discord.Member, причина: str):
    await interaction.response.send_message(f"⚠️ {пользователь.mention} получил предупреждение!")

# ЕЩЕ 7 команд для модеров...

# 👑 КОМАНДЫ ДЛЯ АДМИНОВ
@bot.tree.command(name="выдать", description="Выдать монеты")
@is_admin() 
async def выдать(interaction: discord.Interaction, пользователь: discord.Member, количество: int):
    await interaction.response.send_message(f"💰 Выдано {количество} монет!")

# ЕЩЕ 11 команд для админов...

@bot.event
async def on_ready():
    print(f'✅ {bot.user} запущен на сервере {GUILD_ID}')
    print(f'📊 Каналы: логи={ADMIN_LOG_CHANNEL}, ивенты={EVENTS_CHANNEL}, экономика={ECONOMY_CHANNEL}')

if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    bot.run(TOKEN)
