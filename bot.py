import discord
from discord.ext import commands
import aiosqlite
import asyncio
from datetime import datetime, timedelta
import os
import random
from typing import Optional
from dotenv import load_dotenv

# 🔧 АДМИНЫ (твои ID)
ADMIN_IDS = [1195144951546265675, 766767256742526996, 1138140772097597472]

def is_admin():
    """Проверка прав администратора"""
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id in ADMIN_IDS
    return commands.check(predicate)

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN:
    print("❌ Токен не найден! Создай .env файл с DISCORD_BOT_TOKEN")
    exit(1)

# 🎨 ДИЗАЙН
class Design:
    COLORS = {
        "primary": 0x5865F2, "success": 0x57F287, "warning": 0xFEE75C, 
        "danger": 0xED4245, "economy": 0xF1C40F, "music": 0x9B59B6,
        "moderation": 0xE74C3C, "shop": 0x9B59B6, "casino": 0xE67E22,
        "info": 0x3498DB, "premium": 0xFFD700, "roblox": 0xE74C3C,
        "discord": 0x5865F2, "tds": 0xF1C40F
    }

    @staticmethod
    def create_embed(title: str, description: str = "", color: str = "primary"):
        return discord.Embed(title=title, description=description, color=Design.COLORS.get(color, Design.COLORS["primary"]))

# 💾 БАЗА ДАННЫХ
class Database:
    def __init__(self):
        self.db_path = "data/bot.db"
        os.makedirs("data", exist_ok=True)
    
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 1000,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    daily_claimed TEXT,
                    work_cooldown TEXT
                )
            ''')
            
            # Таблица инвентаря
            await db.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER,
                    item_id INTEGER,
                    quantity INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, item_id)
                )
            ''')
            
            # Таблица заказов
            await db.execute('DROP TABLE IF EXISTS orders')
            await db.execute('''
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    category TEXT,
                    product_name TEXT,
                    quantity INTEGER,
                    price REAL,
                    details TEXT,
                    status TEXT DEFAULT 'ожидает оплаты',
                    order_time TEXT,
                    admin_id INTEGER,
                    completion_time TEXT,
                    payment_screenshot TEXT
                )
            ''')
            
            await db.commit()
            print("✅ База данных инициализирована")

# 💰 ЭКОНОМИКА
class EconomySystem:
    def __init__(self, db: Database):
        self.db = db

    async def get_balance(self, user_id: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return result[0]
                else:
                    await db.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
                    await db.commit()
                    return 1000
    
    async def update_balance(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
            await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            await db.commit()
            return await self.get_balance(user_id)
    
    async def get_user_data(self, user_id: int):
        """Получить все данные пользователя"""
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT balance, level, xp, daily_claimed, work_cooldown FROM users WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        "balance": result[0],
                        "level": result[1],
                        "xp": result[2],
                        "daily_claimed": result[3],
                        "work_cooldown": result[4]
                    }
                else:
                    await db.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
                    await db.commit()
                    return {
                        "balance": 1000,
                        "level": 1,
                        "xp": 0,
                        "daily_claimed": None,
                        "work_cooldown": None
                    }
    
    async def add_xp(self, user_id: int, xp_gain: int):
        """Добавить опыт пользователю"""
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
            await db.execute('UPDATE users SET xp = xp + ? WHERE user_id = ?', (xp_gain, user_id))
            
            async with db.execute('SELECT xp, level FROM users WHERE user_id = ?', (user_id,)) as cursor:
                user_data = await cursor.fetchone()
                if user_data:
                    xp, level = user_data
                    xp_needed = level * 100
                    
                    if xp >= xp_needed:
                        await db.execute('UPDATE users SET level = level + 1, xp = xp - ? WHERE user_id = ?', (xp_needed, user_id))
                        level_up = True
                    else:
                        level_up = False
            
            await db.commit()
            return level_up

    async def reset_weekly_xp(self):
        """Сброс опыта всех пользователей каждую неделю"""
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('UPDATE users SET xp = 0 WHERE xp > 0')
            await db.commit()
    
    # 🔧 АДМИН МЕТОДЫ
    async def admin_add_money(self, user_id: int, amount: int):
        """Админская выдача денег"""
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
            await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            await db.commit()
            return await self.get_balance(user_id)
    
    async def admin_set_money(self, user_id: int, amount: int):
        """Админская установка баланса"""
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
            await db.execute('UPDATE users SET balance = ? WHERE user_id = ?', (amount, user_id))
            await db.commit()
            return await self.get_balance(user_id)
    
    async def admin_reset_cooldowns(self, user_id: int):
        """Сброс кулдаунов"""
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
            await db.execute('UPDATE users SET daily_claimed = NULL, work_cooldown = NULL WHERE user_id = ?', (user_id,))
            await db.commit()

# 🏪 МАГАЗИН (остальной код без изменений)
SHOP_CATEGORIES = {
    "🎮 TDS/TDX": {
        "color": "tds",
        "items": {
            1: {"name": "🏗️ Инженер (4500 гемов)", "price": 860, "type": "игра"},
            # ... остальные товары
        }
    },
    # ... остальные категории
}

class ShopSystem:
    def __init__(self, db: Database):
        self.db = db
        self.categories = SHOP_CATEGORIES
        self.payment_details = "**💳 Реквизиты для оплаты:**\nКарта: `2200 0000 0000 0000`\nТинькофф\nПолучатель: Иван Иванов"
    
    async def create_order(self, user_id: int, item_id: int, quantity: int = 1, details: str = ""):
        # ... код без изменений
        pass
    
    async def get_user_orders(self, user_id: int):
        # ... код без изменений
        pass
    
    async def update_order_status(self, order_id: int, status: str, admin_id: int = None, screenshot: str = None):
        # ... код без изменений
        pass
    
    def get_product_by_id(self, item_id: int):
        # ... код без изменений
        pass

# 🎰 КАЗИНО
class CasinoSystem:
    def __init__(self, db: Database):
        self.db = db
    
    async def play_slots(self, user_id: int, bet: int):
        # ... код без изменений
        pass

# 🛡️ МОДЕРАЦИЯ
class ModerationSystem:
    async def create_ticket(self, user: discord.Member, reason: str):
        # ... код без изменений
        pass

# 🎵 МУЗЫКА
class MusicPlayer:
    def __init__(self):
        self.queues = {}
    
    def get_queue(self, guild_id: int):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]
    
    def get_queue_embed(self, guild_id: int):
        queue = self.get_queue(guild_id)
        if not queue:
            return Design.create_embed("🎵 Очередь пуста", "Добавьте треки с помощью /play", "music")
        
        embed = Design.create_embed("🎵 Очередь воспроизведения", f"Треков в очереди: {len(queue)}", "music")
        for i, track in enumerate(queue[:5], 1):
            embed.add_field(name=f"{i}. {track}", value="---", inline=False)
        return embed

# 🏗️ ГЛАВНЫЙ БОТ
class MegaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        
        self.db = Database()
        self.economy = EconomySystem(self.db)
        self.shop = ShopSystem(self.db)
        self.casino = CasinoSystem(self.db)
        self.moderation = ModerationSystem()
        self.music = MusicPlayer()
        self.start_time = datetime.now()
    
    async def setup_hook(self):
        await self.db.init_db()
        try:
            synced = await self.tree.sync()
            print(f"✅ Синхронизировано {len(synced)} команд")
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")

    async def weekly_reset_task(self):
        """Задача для еженедельного сброса опыта"""
        await self.wait_until_ready()
        while not self.is_closed():
            now = datetime.now()
            next_monday = now + timedelta(days=(7 - now.weekday()))
            next_reset = datetime(next_monday.year, next_monday.month, next_monday.day, 0, 0, 0)
            wait_seconds = (next_reset - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            await self.economy.reset_weekly_xp()
            print("✅ Еженедельный сброс опыта выполнен")

bot = MegaBot()

# 💰 ЭКОНОМИКА КОМАНДЫ (без изменений)
@bot.tree.command(name="баланс", description="Проверить баланс")
async def баланс(interaction: discord.Interaction, пользователь: Optional[discord.Member] = None):
    user = пользователь or interaction.user
    balance = await bot.economy.get_balance(user.id)
    embed = Design.create_embed("💰 Баланс", f"**{user.display_name}**\nБаланс: `{balance:,} монет`", "economy")
    await interaction.response.send_message(embed=embed)

# ... остальные команды без изменений

@bot.tree.command(name="синхронизировать", description="[АДМИН] Пересинхронизировать команды")
@is_admin()
async def синхронизировать(interaction: discord.Interaction):
    await bot.tree.sync()
    embed = Design.create_embed("✅ Синхронизация", "Команды пересинхронизированы!", "success")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 🔧 ОБРАБОТЧИКИ
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'🌐 Серверов: {len(bot.guilds)}')
    # Запускаем фоновые задачи
    bot.loop.create_task(bot.weekly_reset_task())

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if isinstance(message.channel, discord.TextChannel):
        async with aiosqlite.connect(bot.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.author.id,))
            await db.commit()
        
        xp_gain = random.randint(5, 15)
        await bot.economy.add_xp(message.author.id, xp_gain)
    
    await bot.process_commands(message)

# 🚀 ЗАПУСК
if __name__ == "__main__":
    try:
        print("🚀 Запуск бота...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
