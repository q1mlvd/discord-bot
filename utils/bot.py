import discord
from discord.ext import commands, tasks
import aiosqlite
import asyncio
from datetime import datetime, timedelta
import os
import random
from typing import Optional
from dotenv import load_dotenv
import yt_dlp
import aiohttp
import json

# 🔧 КОНСТАНТЫ
ADMIN_IDS = [1195144951546265675, 766767256742526996, 1078693283695448064, 1138140772097597472, 691904643181314078]
MODERATION_ROLES = [1167093102868172911, 1360243534946373672, 993043931342319636, 1338611327022923910, 1338609155203661915, 1365798715930968244, 1188261847850299514]
THREADS_CHANNEL_ID = 1422557295811887175
EVENTS_CHANNEL_ID = 1418738569081786459
ECONOMY_CHANNEL_ID = 1422641391682588734
ADMIN_LOG_CHANNEL = 1419779743083003944

# 🛡️ ДАННЫЕ ДЛЯ СИСТЕМ
user_warns = {}
mute_data = {}
user_credits = {}
user_investments = {}
user_insurance = {}
user_lottery_tickets = {}
server_tax_pool = 0
user_mining_farms = {}
crypto_prices = {"BITCOIN": 50000, "ETHEREUM": 3000, "DOGECOIN": 0.15}
active_events = {}
user_reports = {}
user_crypto = {}
rob_cooldowns = {}
economic_bans = {}
user_stats = {}
clans = {}
active_duels = {}
quests = {}

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class MegaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        
    async def setup_hook(self):
        await self.load_extension('commands.user_commands')
        await self.load_extension('commands.mod_commands')
        await self.load_extension('commands.admin_commands')
        
        # Запускаем фоновые задачи
        self.update_crypto_prices.start()
        self.check_duels.start()
        
        print("✅ Все системы загружены!")

bot = MegaBot()

# 🎨 ДИЗАЙН
class Design:
    COLORS = {
        "primary": 0x5865F2, "success": 0x57F287, "warning": 0xFEE75C, 
        "danger": 0xED4245, "economy": 0xF1C40F, "music": 0x9B59B6,
        "moderation": 0xE74C3C, "crypto": 0x16C60C, "event": 0x9B59B6
    }

    @staticmethod
    def create_embed(title: str, description: str = "", color: str = "primary"):
        embed = discord.Embed(title=title, description=description, color=Design.COLORS.get(color, Design.COLORS["primary"]))
        embed.set_footer(text="💎 Mega Economy Bot")
        return embed

# 🔧 СИСТЕМА ПРАВ
def is_admin():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id in ADMIN_IDS
    return commands.check(predicate)

def is_moderator():
    async def predicate(interaction: discord.Interaction):
        user_roles = [role.id for role in interaction.user.roles]
        return any(role_id in MODERATION_ROLES for role_id in user_roles)
    return commands.check(predicate)

# 🎵 МУЗЫКАЛЬНАЯ СИСТЕМА
class MusicSystem:
    def __init__(self):
        self.queues = {}
    
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Зайди в голосовой канал!", ephemeral=True)
            return
        
        embed = Design.create_embed("🎵 Музыка", f"**Добавлено:** {query}\nИспользуй `/stop` для остановки", "music")
        await interaction.response.send_message(embed=embed)

music_system = MusicSystem()

# ₿ КРИПТО-СИСТЕМА
class CryptoSystem:
    def __init__(self):
        self.real_prices = {}
    
    async def get_real_prices(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.binance.com/api/v3/ticker/price') as resp:
                    data = await resp.json()
                    for item in data:
                        if item['symbol'] == 'BTCUSDT':
                            crypto_prices["BITCOIN"] = float(item['price'])
                        elif item['symbol'] == 'ETHUSDT':
                            crypto_prices["ETHEREUM"] = float(item['price'])
        except:
            pass

crypto_system = CryptoSystem()

# 👥 СИСТЕМА КЛАНОВ
class ClanSystem:
    async def create_clan(self, user_id: int, name: str):
        clan_id = len(clans) + 1
        clans[clan_id] = {
            'name': name,
            'leader': user_id,
            'members': [user_id],
            'treasury': 0,
            'level': 1
        }
        return True, f"✅ Клан '{name}' создан!"

clan_system = ClanSystem()

# ⚔️ PvP СИСТЕМА
class PvPSystem:
    async def start_duel(self, challenger: int, target: int, bet: int):
        duel_id = f"{challenger}_{target}_{datetime.now().timestamp()}"
        active_duels[duel_id] = {
            'challenger': challenger,
            'target': target,
            'bet': bet,
            'time': datetime.now()
        }
        return True, duel_id

pvp_system = PvPSystem()

# 🔄 ФОНОВЫЕ ЗАДАЧИ
@tasks.loop(minutes=5)
async def update_crypto_prices():
    await crypto_system.get_real_prices()

@tasks.loop(seconds=30)
async def check_duels():
    current_time = datetime.now()
    for duel_id, duel in list(active_duels.items()):
        if (current_time - duel['time']).seconds > 60:
            del active_duels[duel_id]

# 🎯 БАЗОВЫЕ КОМАНДЫ
@bot.tree.command(name="play", description="Включить музыку")
async def play(interaction: discord.Interaction, запрос: str):
    await music_system.play(interaction, запрос)

@bot.tree.command(name="создать_клан", description="Создать клан")
async def создать_клан(interaction: discord.Interaction, название: str):
    success, message = await clan_system.create_clan(interaction.user.id, название)
    embed = Design.create_embed("👥 Клан", message, "success" if success else "danger")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="дуэль", description="Вызвать на дуэль")
async def дуэль(interaction: discord.Interaction, соперник: discord.Member, ставка: int):
    success, duel_id = await pvp_system.start_duel(interaction.user.id, соперник.id, ставка)
    if success:
        embed = Design.create_embed("⚔️ Дуэль", 
                                  f"**Вызов от:** {interaction.user.mention}\n"
                                  f"**Соперник:** {соперник.mention}\n"
                                  f"**Ставка:** {ставка} монет\n"
                                  f"Прими вызов в течение 60 секунд!", "warning")
    else:
        embed = Design.create_embed("❌ Ошибка", "Не удалось создать дуэль", "danger")
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    
    # Синхронизируем команды
    try:
        synced = await bot.tree.sync()
        print(f'✅ Синхронизировано {len(synced)} команд')
    except Exception as e:
        print(f'❌ Ошибка синхронизации: {e}')

if __name__ == "__main__":
    bot.run(TOKEN)
