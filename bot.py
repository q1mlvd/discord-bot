import discord
from discord.ext import commands, tasks
import aiosqlite
import asyncio
from datetime import datetime, timedelta
import os
import random
import json
import logging
from typing import Optional, Dict, List
from dotenv import load_dotenv
import yt_dlp
import aiohttp
import shutil

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 🔧 АДМИНЫ (твои ID)
ADMIN_IDS = [1195144951546265675, 766767256742526996, 1138140772097597472]

# 🛡️ ДЛЯ МОДЕРАЦИИ
user_warns = {}
mute_data = {}
user_reports = {}
automod_settings = {}
user_achievements = {}
clans_data = {}
marriages = {}
user_properties = {}
crypto_balances = {}
stock_market = {}
event_system = {}
temporary_roles = {}
user_activity = {}
polls_data = {}

def is_admin():
    """Проверка прав администратора"""
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id in ADMIN_IDS
    return commands.check(predicate)

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN:
    logging.error("❌ Токен не найден! Создай .env файл с DISCORD_BOT_TOKEN")
    exit(1)

# 🎨 ДИЗАЙН
class Design:
    COLORS = {
        "primary": 0x5865F2, "success": 0x57F287, "warning": 0xFEE75C, 
        "danger": 0xED4245, "economy": 0xF1C40F, "music": 0x9B59B6,
        "moderation": 0xE74C3C, "shop": 0x9B59B6, "casino": 0xE67E22,
        "info": 0x3498DB, "premium": 0xFFD700, "roblox": 0xE74C3C,
        "discord": 0x5865F2, "tds": 0xF1C40F, "crypto": 0x16C60C,
        "event": 0x9B59B6, "clan": 0xE74C3C, "marriage": 0xE91E63
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
            # Существующие таблицы
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
            await db.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER,
                    item_id INTEGER,
                    quantity INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, item_id)
                )
            ''')
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
            
            # Новые таблицы для дополнительных функций
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id INTEGER,
                    achievement_id TEXT,
                    achieved_at TEXT,
                    PRIMARY KEY (user_id, achievement_id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS clans (
                    clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clan_name TEXT,
                    clan_leader INTEGER,
                    clan_level INTEGER DEFAULT 1,
                    clan_xp INTEGER DEFAULT 0,
                    created_at TEXT
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS clan_members (
                    clan_id INTEGER,
                    user_id INTEGER,
                    role TEXT DEFAULT 'member',
                    joined_at TEXT,
                    PRIMARY KEY (clan_id, user_id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS marriages (
                    user1_id INTEGER,
                    user2_id INTEGER,
                    married_at TEXT,
                    divorce_cooldown TEXT,
                    PRIMARY KEY (user1_id, user2_id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_properties (
                    user_id INTEGER,
                    property_id TEXT,
                    property_name TEXT,
                    property_value INTEGER,
                    purchased_at TEXT,
                    PRIMARY KEY (user_id, property_id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS crypto_balances (
                    user_id INTEGER,
                    currency TEXT DEFAULT 'BITCOIN',
                    balance REAL DEFAULT 0,
                    PRIMARY KEY (user_id, currency)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    user_id INTEGER,
                    action_type TEXT,
                    action_details TEXT,
                    timestamp TEXT
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS moderation_logs (
                    moderator_id INTEGER,
                    target_id INTEGER,
                    action_type TEXT,
                    reason TEXT,
                    duration TEXT,
                    timestamp TEXT
                )
            ''')
            
            await db.commit()
            logging.info("✅ База данных инициализирована")

# 🔄 СИСТЕМА БЭКАПОВ
class BackupSystem:
    def __init__(self, db: Database):
        self.db = db
    
    async def create_backup(self):
        """Создание резервной копии базы данных"""
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{backup_dir}/backup_{timestamp}.db"
        
        async with aiosqlite.connect(self.db.db_path) as source:
            async with aiosqlite.connect(backup_path) as target:
                await source.backup(target)
        
        logging.info(f"✅ Создан бэкап: {backup_path}")
        return backup_path
    
    async def auto_backup(self):
        """Автоматическое создание бэкапов"""
        while True:
            await asyncio.sleep(86400)  # Каждые 24 часа
            await self.create_backup()

# 📊 СИСТЕМА ЛОГИРОВАНИЯ
class LoggingSystem:
    @staticmethod
    async def log_action(user_id: int, action_type: str, details: str):
        """Логирование действий пользователя"""
        timestamp = datetime.now().isoformat()
        
        async with aiosqlite.connect("data/bot.db") as db:
            await db.execute(
                'INSERT INTO activity_logs (user_id, action_type, action_details, timestamp) VALUES (?, ?, ?, ?)',
                (user_id, action_type, details, timestamp)
            )
            await db.commit()
        
        logging.info(f"👤 {user_id} - {action_type}: {details}")
    
    @staticmethod
    async def log_moderation(moderator_id: int, target_id: int, action_type: str, reason: str, duration: str = None):
        """Логирование действий модерации"""
        timestamp = datetime.now().isoformat()
        
        async with aiosqlite.connect("data/bot.db") as db:
            await db.execute(
                'INSERT INTO moderation_logs (moderator_id, target_id, action_type, reason, duration, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                (moderator_id, target_id, action_type, reason, duration, timestamp)
            )
            await db.commit()
        
        logging.info(f"🛡️ {moderator_id} -> {target_id} {action_type}: {reason}")

# 🛡️ АВТОМОДЕРАЦИЯ
class AutoModSystem:
    def __init__(self):
        self.user_message_count = {}
        self.last_message_time = {}
    
    async def check_spam(self, message: discord.Message) -> bool:
        """Проверка на спам"""
        user_id = message.author.id
        current_time = datetime.now()
        
        # Инициализация данных пользователя
        if user_id not in self.user_message_count:
            self.user_message_count[user_id] = 0
            self.last_message_time[user_id] = current_time
        
        # Сброс счетчика если прошло больше 10 секунд
        if (current_time - self.last_message_time[user_id]).seconds > 10:
            self.user_message_count[user_id] = 0
        
        self.user_message_count[user_id] += 1
        self.last_message_time[user_id] = current_time
        
        # Если больше 5 сообщений за 10 секунд - спам
        if self.user_message_count[user_id] > 5:
            await message.delete()
            warning_msg = await message.channel.send(
                f"⚠️ {message.author.mention}, не спамьте!"
            )
            await asyncio.sleep(5)
            await warning_msg.delete()
            return True
        
        return False
    
    async def check_mentions(self, message: discord.Message) -> bool:
        """Проверка массовых упоминаний"""
        if len(message.mentions) > 5:
            await message.delete()
            warning_msg = await message.channel.send(
                f"⚠️ {message.author.mention}, слишком много упоминаний!"
            )
            await asyncio.sleep(5)
            await warning_msg.delete()
            return True
        return False

# 🎯 СИСТЕМА РЕПОРТОВ
class ReportSystem:
    @staticmethod
    async def create_report(reporter: discord.Member, reported: discord.Member, reason: str, proof: str = None):
        """Создание жалобы на пользователя"""
        report_id = len(user_reports) + 1
        user_reports[report_id] = {
            'reporter_id': reporter.id,
            'reported_id': reported.id,
            'reason': reason,
            'proof': proof,
            'status': 'open',
            'created_at': datetime.now().isoformat()
        }
        
        return report_id
    
    @staticmethod
    async def get_report_channel(guild: discord.Guild):
        """Получение канала для жалоб"""
        channel = discord.utils.get(guild.channels, name="жалобы")
        if not channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            channel = await guild.create_text_channel("жалобы", overwrites=overwrites)
        return channel

# 🎪 СИСТЕМА ИВЕНТОВ
class EventSystem:
    def __init__(self, economy):
        self.economy = economy
        self.active_events = {}
    
    async def start_event(self, event_type: str, duration: int, reward: int):
        """Запуск ивента"""
        event_id = len(self.active_events) + 1
        end_time = datetime.now() + timedelta(hours=duration)
        
        self.active_events[event_id] = {
            'type': event_type,
            'start_time': datetime.now().isoformat(),
            'end_time': end_time.isoformat(),
            'reward': reward,
            'participants': []
        }
        
        return event_id
    
    async def add_participant(self, event_id: int, user_id: int):
        """Добавление участника ивента"""
        if event_id in self.active_events:
            if user_id not in self.active_events[event_id]['participants']:
                self.active_events[event_id]['participants'].append(user_id)
    
    async def finish_event(self, event_id: int):
        """Завершение ивента и выдача наград"""
        if event_id in self.active_events:
            event = self.active_events[event_id]
            for user_id in event['participants']:
                await self.economy.update_balance(user_id, event['reward'])
            del self.active_events[event_id]

# 💑 СИСТЕМА БРАКОВ
class MarriageSystem:
    def __init__(self, db: Database):
        self.db = db
    
    async def marry(self, user1_id: int, user2_id: int):
        """Заключение брака"""
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute(
                'INSERT INTO marriages (user1_id, user2_id, married_at) VALUES (?, ?, ?)',
                (user1_id, user2_id, datetime.now().isoformat())
            )
            await db.commit()
        
        marriages[user1_id] = user2_id
        marriages[user2_id] = user1_id
    
    async def divorce(self, user_id: int):
        """Развод"""
        if user_id in marriages:
            partner_id = marriages[user_id]
            
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute(
                    'DELETE FROM marriages WHERE user1_id = ? OR user2_id = ?',
                    (user_id, user_id)
                )
                await db.commit()
            
            del marriages[user_id]
            del marriages[partner_id]
            
            return partner_id
        return None

# 🏘️ СИСТЕМА КЛАНОВ
class ClanSystem:
    def __init__(self, db: Database):
        self.db = db
    
    async def create_clan(self, clan_name: str, leader_id: int):
        """Создание клана"""
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute(
                'INSERT INTO clans (clan_name, clan_leader, created_at) VALUES (?, ?, ?)',
                (clan_name, leader_id, datetime.now().isoformat())
            )
            clan_id = cursor.lastrowid
            
            await db.execute(
                'INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)',
                (clan_id, leader_id, 'leader', datetime.now().isoformat())
            )
            await db.commit()
        
        clans_data[clan_id] = {
            'name': clan_name,
            'leader': leader_id,
            'members': [leader_id],
            'level': 1,
            'xp': 0
        }
        
        return clan_id
    
    async def add_member(self, clan_id: int, user_id: int):
        """Добавление участника в клан"""
        if clan_id in clans_data:
            clans_data[clan_id]['members'].append(user_id)
            
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute(
                    'INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)',
                    (clan_id, user_id, 'member', datetime.now().isoformat())
                )
                await db.commit()

# 💎 КРИПТОВАЛЮТА
class CryptoSystem:
    def __init__(self, db: Database):
        self.db = db
        self.crypto_prices = {
            'BITCOIN': 50000,
            'ETHEREUM': 3000,
            'DOGECOIN': 0.15
        }
    
    async def get_crypto_balance(self, user_id: int, currency: str = 'BITCOIN'):
        """Получение баланса криптовалюты"""
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute(
                'SELECT balance FROM crypto_balances WHERE user_id = ? AND currency = ?',
                (user_id, currency)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    
    async def update_crypto_balance(self, user_id: int, amount: float, currency: str = 'BITCOIN'):
        """Обновление баланса криптовалюты"""
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO crypto_balances (user_id, currency, balance)
                VALUES (?, ?, COALESCE((SELECT balance FROM crypto_balances WHERE user_id = ? AND currency = ?), 0) + ?)
            ''', (user_id, currency, user_id, currency, amount))
            await db.commit()

# 📈 БИРЖА АКЦИЙ
class StockMarket:
    def __init__(self):
        self.stocks = {
            'GOLD': {'price': 100, 'volatility': 5},
            'OIL': {'price': 80, 'volatility': 8},
            'TECH': {'price': 150, 'volatility': 12}
        }
    
    def update_prices(self):
        """Обновление цен акций"""
        for stock in self.stocks.values():
            change = random.uniform(-stock['volatility'], stock['volatility'])
            stock['price'] = max(1, stock['price'] + change)
    
    def get_stock_price(self, symbol: str):
        """Получение текущей цены акции"""
        return self.stocks.get(symbol, {}).get('price', 0)

# 🏠 СИСТЕМА НЕДВИЖИМОСТИ
class PropertySystem:
    def __init__(self, db: Database):
        self.db = db
        self.properties = {
            'HOUSE_SMALL': {'name': 'Маленький дом', 'price': 5000, 'income': 50},
            'HOUSE_MEDIUM': {'name': 'Средний дом', 'price': 15000, 'income': 150},
            'HOUSE_LARGE': {'name': 'Большой дом', 'price': 50000, 'income': 500},
            'CASTLE': {'name': 'Замок', 'price': 200000, 'income': 2000}
        }
    
    async def buy_property(self, user_id: int, property_id: str):
        """Покупка недвижимости"""
        if property_id not in self.properties:
            return False
        
        property_data = self.properties[property_id]
        
        async with aiosqlite.connect(self.db.db_path) as db:
            # Проверяем, есть ли уже эта недвижимость
            async with db.execute(
                'SELECT 1 FROM user_properties WHERE user_id = ? AND property_id = ?',
                (user_id, property_id)
            ) as cursor:
                if await cursor.fetchone():
                    return False
            
            await db.execute(
                'INSERT INTO user_properties (user_id, property_id, property_name, property_value, purchased_at) VALUES (?, ?, ?, ?, ?)',
                (user_id, property_id, property_data['name'], property_data['price'], datetime.now().isoformat())
            )
            await db.commit()
        
        user_properties[user_id] = user_properties.get(user_id, {})
        user_properties[user_id][property_id] = property_data
        
        return True

# 🏆 СИСТЕМА ДОСТИЖЕНИЙ
class AchievementSystem:
    def __init__(self, db: Database):
        self.db = db
        self.achievements = {
            'FIRST_STEPS': {'name': 'Первые шаги', 'description': 'Заработать первую 1000 монет'},
            'RICH': {'name': 'Богач', 'description': 'Накопить 10,000 монет'},
            'GAMBLER': {'name': 'Азартный игрок', 'description': 'Выиграть в казино 1000 монет'},
            'WORKAHOLIC': {'name': 'Трудоголик', 'description': 'Выполнить работу 50 раз'}
        }
    
    async def check_achievements(self, user_id: int, achievement_type: str, progress: int):
        """Проверка и выдача достижений"""
        # Здесь будет логика проверки достижений
        pass
    
    async def grant_achievement(self, user_id: int, achievement_id: str):
        """Выдача достижения"""
        if achievement_id in self.achievements:
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, achieved_at) VALUES (?, ?, ?)',
                    (user_id, achievement_id, datetime.now().isoformat())
                )
                await db.commit()
            
            user_achievements[user_id] = user_achievements.get(user_id, [])
            user_achievements[user_id].append(achievement_id)

# 🎮 СИСТЕМА МИНИ-ИГР
class MiniGameSystem:
    def __init__(self, economy):
        self.economy = economy
    
    async def start_quiz(self, interaction: discord.Interaction, topic: str):
        """Запуск викторины"""
        questions = {
            'general': [
                {'question': 'Столица России?', 'answer': 'Москва'},
                {'question': '2+2?', 'answer': '4'}
            ],
            'games': [
                {'question': 'Самый популярный игровой движок?', 'answer': 'Unreal Engine'}
            ]
        }
        
        if topic not in questions:
            await interaction.response.send_message("❌ Тема не найдена!", ephemeral=True)
            return
        
        question_data = random.choice(questions[topic])
        return question_data

# 💰 ЭКОНОМИКА (существующий класс с дополнениями)
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
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT balance, level, xp, daily_claimed, work_cooldown FROM users WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        "balance": result[0], "level": result[1], "xp": result[2],
                        "daily_claimed": result[3], "work_cooldown": result[4]
                    }
                else:
                    await db.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
                    await db.commit()
                    return {"balance": 1000, "level": 1, "xp": 0, "daily_claimed": None, "work_cooldown": None}
    
    async def add_xp(self, user_id: int, xp_gain: int):
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
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('UPDATE users SET xp = 0 WHERE xp > 0')
            await db.commit()
    
    async def admin_add_money(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
            await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            await db.commit()
            return await self.get_balance(user_id)
    
    async def admin_set_money(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
            await db.execute('UPDATE users SET balance = ? WHERE user_id = ?', (amount, user_id))
            await db.commit()
            return await self.get_balance(user_id)
    
    async def admin_reset_cooldowns(self, user_id: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
            await db.execute('UPDATE users SET daily_claimed = NULL, work_cooldown = NULL WHERE user_id = ?', (user_id,))
            await db.commit()

# 🏗️ ГЛАВНЫЙ БОТ С ВСЕМИ СИСТЕМАМИ
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
        self.backup_system = BackupSystem(self.db)
        self.logging_system = LoggingSystem()
        self.automod = AutoModSystem()
        self.report_system = ReportSystem()
        self.event_system = EventSystem(self.economy)
        self.marriage_system = MarriageSystem(self.db)
        self.clan_system = ClanSystem(self.db)
        self.crypto_system = CryptoSystem(self.db)
        self.stock_market = StockMarket()
        self.property_system = PropertySystem(self.db)
        self.achievement_system = AchievementSystem(self.db)
        self.minigame_system = MiniGameSystem(self.economy)
        
        self.start_time = datetime.now()
    
    async def setup_hook(self):
        await self.db.init_db()
        try:
            synced = await self.tree.sync()
            logging.info(f"✅ Синхронизировано {len(synced)} команд")
        except Exception as e:
            logging.error(f"❌ Ошибка синхронизации: {e}")
        
        # Запуск фоновых задач
        self.auto_backup.start()
        self.update_stock_prices.start()
        self.weekly_bonuses.start()

    @tasks.loop(hours=24)
    async def auto_backup(self):
        """Автоматическое создание бэкапов"""
        await self.backup_system.create_backup()
    
    @tasks.loop(minutes=5)
    async def update_stock_prices(self):
        """Обновление цен акций"""
        self.stock_market.update_prices()
    
    @tasks.loop(hours=168)  # 1 неделя
    async def weekly_bonuses(self):
        """Еженедельные бонусы за активность"""
        # Логика выдачи бонусов
        pass

    async def weekly_reset_task(self):
        await self.wait_until_ready()
        while not self.is_closed():
            now = datetime.now()
            next_monday = now + timedelta(days=(7 - now.weekday()))
            next_reset = datetime(next_monday.year, next_monday.month, next_monday.day, 0, 0, 0)
            wait_seconds = (next_reset - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            await self.economy.reset_weekly_xp()
            logging.info("✅ Еженедельный сброс опыта выполнен")

# 🎵 МУЗЫКА - ИСПРАВЛЕННАЯ ВЕРСИЯ
class MusicPlayer:
    def __init__(self):
        self.queues = {}
        self.voice_clients = {}
        self.now_playing = {}
        
        # Настройки для yt-dlp
        self.ytdl_format_options = {
            'format': 'bestaudio/best',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0'
        }
        
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        
        try:
            self.ytdl = yt_dlp.YoutubeDL(self.ytdl_format_options)
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации yt-dlp: {e}")
            self.ytdl = None

    def get_queue(self, guild_id: int):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    async def connect_to_voice_channel(self, interaction: discord.Interaction):
        """Подключение к голосовому каналу"""
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Вы не в голосовом канале! Зайдите в голосовой канал.", ephemeral=True)
            return None
        
        voice_channel = interaction.user.voice.channel
        
        if interaction.guild.id in self.voice_clients:
            voice_client = self.voice_clients[interaction.guild.id]
            if voice_client.is_connected():
                await voice_client.move_to(voice_channel)
                return voice_client
        
        try:
            voice_client = await voice_channel.connect()
            self.voice_clients[interaction.guild.id] = voice_client
            return voice_client
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка подключения: {e}", ephemeral=True)
            return None

    async def play_music(self, interaction: discord.Interaction, query: str):
        """Воспроизведение музыки"""
        if not self.ytdl:
            await interaction.response.send_message("❌ Музыкальная система недоступна", ephemeral=True)
            return
        
        voice_client = await self.connect_to_voice_channel(interaction)
        if not voice_client:
            return
        
        try:
            # Получаем информацию о треке
            data = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.ytdl.extract_info(query, download=False)
            )
            
            if 'entries' in data:
                data = data['entries'][0]
            
            url = data['url']
            title = data.get('title', 'Неизвестный трек')
            duration = data.get('duration', 0)
            
            # Форматируем длительность
            if duration:
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "Неизвестно"
            
            # Добавляем в очередь
            queue = self.get_queue(interaction.guild.id)
            track_info = {
                'url': url,
                'title': title,
                'duration': duration_str,
                'requester': interaction.user
            }
            queue.append(track_info)
            
            # Если ничего не играет, начинаем воспроизведение
            if not voice_client.is_playing():
                await self.play_next(interaction.guild.id, interaction.channel)
                embed = Design.create_embed("🎵 Сейчас играет", 
                                          f"**{title}**\n"
                                          f"⏱️ Длительность: {duration_str}\n"
                                          f"👤 Запросил: {interaction.user.mention}", "music")
            else:
                embed = Design.create_embed("🎵 Добавлено в очередь", 
                                          f"**{title}**\n"
                                          f"⏱️ Длительность: {duration_str}\n"
                                          f"👤 Запросил: {interaction.user.mention}\n"
                                          f"📋 Позиция в очереди: {len(queue)}", "music")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: Не удалось найти или воспроизвести трек", ephemeral=True)
            logging.error(f"Ошибка музыки: {e}")

    async def play_next(self, guild_id: int, channel=None):
        """Воспроизведение следующего трека"""
        queue = self.get_queue(guild_id)
        if not queue:
            return
        
        if guild_id not in self.voice_clients:
            return
        
        voice_client = self.voice_clients[guild_id]
        
        if voice_client.is_playing():
            return
        
        if queue:
            track = queue.pop(0)
            self.now_playing[guild_id] = track
            
            def after_playing(error):
                if error:
                    logging.error(f'Ошибка воспроизведения: {error}')
                asyncio.run_coroutine_threadsafe(self.play_next(guild_id, channel), voice_client.loop)
            
            try:
                source = discord.FFmpegPCMAudio(track['url'], **self.ffmpeg_options)
                voice_client.play(source, after=after_playing)
                
                if channel:
                    embed = Design.create_embed("🎵 Сейчас играет", 
                                              f"**{track['title']}**\n"
                                              f"⏱️ Длительность: {track['duration']}\n"
                                              f"👤 Запросил: {track['requester'].mention}", "music")
                    asyncio.run_coroutine_threadsafe(channel.send(embed=embed), voice_client.loop)
                    
            except Exception as e:
                logging.error(f'Ошибка воспроизведения: {e}')
                asyncio.run_coroutine_threadsafe(self.play_next(guild_id, channel), voice_client.loop)

    def get_queue_embed(self, guild_id: int):
        queue = self.get_queue(guild_id)
        embed = Design.create_embed("🎵 Очередь воспроизведения", "", "music")
        
        # Текущий трек
        if guild_id in self.now_playing:
            current = self.now_playing[guild_id]
            embed.add_field(
                name="🎵 Сейчас играет",
                value=f"**{current['title']}**\n⏱️ {current['duration']} | 👤 {current['requester'].display_name}",
                inline=False
            )
        
        # Очередь
        if queue:
            embed.add_field(name=f"📋 Очередь ({len(queue)} треков)", value="", inline=False)
            for i, track in enumerate(queue[:5], 1):
                embed.add_field(
                    name=f"{i}. {track['title']}",
                    value=f"⏱️ {track['duration']} | 👤 {track['requester'].display_name}",
                    inline=False
                )
        else:
            embed.add_field(name="📋 Очередь", value="Очередь пуста", inline=False)
        
        return embed

    async def stop_music(self, guild_id: int):
        """Остановка музыки"""
        if guild_id in self.voice_clients:
            voice_client = self.voice_clients[guild_id]
            if voice_client.is_playing():
                voice_client.stop()
            
            self.queues[guild_id] = []
            if guild_id in self.now_playing:
                del self.now_playing[guild_id]
            
            await voice_client.disconnect()
            del self.voice_clients[guild_id]

# 🏪 МАГАЗИН (существующий класс)
class ShopSystem:
    def __init__(self, db: Database):
        self.db = db
        self.categories = SHOP_CATEGORIES
        self.payment_details = "**💳 Реквизиты для оплаты:**\nКарта: `2200 0000 0000 0000`\nТинькофф\nПолучатель: Иван Иванов"
    
    async def create_order(self, user_id: int, item_id: int, quantity: int = 1, details: str = ""):
        product = None
        category_name = ""
        for cat_name, category in self.categories.items():
            if item_id in category["items"]:
                product = category["items"][item_id]
                category_name = cat_name
                break
        
        if not product:
            return {"success": False, "error": "Товар не найден"}
        
        if product.get("per_unit"):
            total_price = product["price"] * quantity
        else:
            total_price = product["price"]
            quantity = 1
        
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO orders (user_id, category, product_name, quantity, price, details, order_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, category_name, product["name"], quantity, total_price, details, datetime.now().isoformat()))
            order_id = cursor.lastrowid
            await db.commit()
        
        return {"success": True, "order_id": order_id, "product": product, "total_price": total_price, "quantity": quantity}
    
    async def get_user_orders(self, user_id: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('''
                SELECT id, product_name, quantity, price, status, order_time 
                FROM orders WHERE user_id = ? ORDER BY order_time DESC
            ''', (user_id,)) as cursor:
                return await cursor.fetchall()
    
    async def update_order_status(self, order_id: int, status: str, admin_id: int = None, screenshot: str = None):
        async with aiosqlite.connect(self.db.db_path) as db:
            if status == "выполнен":
                await db.execute('''
                    UPDATE orders SET status = ?, admin_id = ?, completion_time = ?, payment_screenshot = ?
                    WHERE id = ?
                ''', (status, admin_id, datetime.now().isoformat(), screenshot, order_id))
            else:
                await db.execute('UPDATE orders SET status = ?, payment_screenshot = ? WHERE id = ?', 
                               (status, screenshot, order_id))
            await db.commit()
    
    def get_product_by_id(self, item_id: int):
        for category in self.categories.values():
            if item_id in category["items"]:
                return category["items"][item_id]
        return None

# 🎰 КАЗИНО (существующий класс)
class CasinoSystem:
    def __init__(self, db: Database):
        self.db = db
    
    async def play_slots(self, user_id: int, bet: int):
        if bet <= 0:
            return {"success": False, "error": "Ставка должна быть положительной"}
        
        economy = EconomySystem(self.db)
        balance = await economy.get_balance(user_id)
        
        if balance < bet:
            return {"success": False, "error": "Недостаточно средств"}
        
        symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎"]
        result = [random.choice(symbols) for _ in range(3)]
        
        if result[0] == result[1] == result[2]:
            multiplier = 5
        elif result[0] == result[1] or result[1] == result[2]:
            multiplier = 2
        else:
            multiplier = 0
        
        win_amount = bet * multiplier
        net_win = win_amount - bet
        
        await economy.update_balance(user_id, net_win)
        
        return {
            "success": True,
            "result": result,
            "bet": bet,
            "win_amount": win_amount,
            "multiplier": multiplier
        }

# 🛡️ МОДЕРАЦИЯ (существующий класс)
class ModerationSystem:
    async def create_ticket(self, user: discord.Member, reason: str):
        guild = user.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        for admin_id in ADMIN_IDS:
            admin = guild.get_member(admin_id)
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        channel = await guild.create_text_channel(
            f'ticket-{user.display_name}',
            overwrites=overwrites,
            topic=f'Тикет: {reason}'
        )
        
        embed = Design.create_embed("🎫 Тикет создан", 
                                  f"**Пользователь:** {user.mention}\n"
                                  f"**Причина:** {reason}", "success")
        
        await channel.send(embed=embed)
        return channel

# Категории магазина (существующие)
SHOP_CATEGORIES = {
    "🎮 TDS/TDX": {
        "color": "tds",
        "items": {
            1: {"name": "🏗️ Инженер (4500 гемов)", "price": 860, "type": "игра"},
            2: {"name": "⚡ Ускоритель (2500 гемов)", "price": 490, "type": "игра"},
            3: {"name": "💀 Некромансер (1800 гемов)", "price": 350, "type": "игра"},
            4: {"name": "🥊 Бравлер (1250 гемов)", "price": 240, "type": "игра"},
            5: {"name": "🎯 Прохождение Хардкор", "price": 90, "type": "услуга"},
            6: {"name": "🍕 Прохождение Пицца Пати", "price": 45, "type": "услуга"},
        }
    },
    "🔴 Roblox": {
        "color": "roblox", 
        "items": {
            7: {"name": "🎁 Robux Gift (курс: 1 руб = 2 robux)", "price": 0.5, "per_unit": True, "type": "цифровой"},
            8: {"name": "🎫 Robux Gamepass (курс: 1 руб = 1.5 robux)", "price": 0.67, "per_unit": True, "type": "цифровой"},
        }
    },
    "🥊 Blox Fruits": {
        "color": "roblox",
        "items": {
            9: {"name": "🎲 Рандом Мифик", "price": 15, "type": "игра"},
            10: {"name": "🐆 Leopard", "price": 55, "type": "игра"},
            11: {"name": "💨 Gas", "price": 60, "type": "игра"},
        }
    },
    "⚡ Discord": {
        "color": "discord",
        "items": {
            12: {"name": "⭐ Премиум+ (месяц)", "price": 999, "type": "подписка"},
            13: {"name": "🎖️ Спонсор (навсегда)", "price": 405, "type": "роль"},
            14: {"name": "🎨 Кастом роль (месяц)", "price": 76, "type": "роль"},
        }
    }
}

bot = MegaBot()

# 🔧 ФУНКЦИИ ПРОВЕРОК МУТОВ И БАНОВ (существующие)
def parse_time(time_str: str) -> int:
    """Парсинг времени из строки (1с, 1м, 1ч, 1д, 1н)"""
    time_units = {
        'с': 1, 'сек': 1, 'секунд': 1,
        'м': 60, 'мин': 60, 'минут': 60, 
        'ч': 3600, 'час': 3600, 'часов': 3600,
        'д': 86400, 'день': 86400, 'дней': 86400,
        'н': 604800, 'неделя': 604800, 'недель': 604800
    }
    
    time_str = time_str.lower().replace(' ', '')
    num_str = ''
    unit_str = ''
    
    for char in time_str:
        if char.isdigit():
            num_str += char
        else:
            unit_str += char
    
    if not num_str:
        return 0
    
    number = int(num_str)
    unit = unit_str.lower()
    
    if unit in time_units:
        return number * time_units[unit]
    else:
        return 0

async def check_user_muted(interaction: discord.Interaction, пользователь: discord.Member) -> bool:
    """Проверка, замучен ли пользователь"""
    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if mute_role and mute_role in пользователь.roles:
        if пользователь.id in mute_data:
            mute_info = mute_data[пользователь.id]
            remaining_time = mute_info['end_time'] - datetime.now()
            if remaining_time.total_seconds() > 0:
                hours = int(remaining_time.total_seconds() // 3600)
                minutes = int((remaining_time.total_seconds() % 3600) // 60)
                
                embed = Design.create_embed("⚠️ Пользователь уже в муте", 
                                          f"**Пользователь:** {пользователь.mention}\n"
                                          f"**Осталось времени:** {hours}ч {minutes}м\n"
                                          f"**Причина:** {mute_info['reason']}\n"
                                          f"**Замутил:** {mute_info['moderator']}", "warning")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return True
            else:
                await пользователь.remove_roles(mute_role)
                del mute_data[пользователь.id]
        else:
            embed = Design.create_embed("⚠️ Пользователь уже в муте", 
                                      f"**Пользователь:** {пользователь.mention}\n"
                                      f"**Статус:** В муте (время не указано)", "warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return True
    return False

async def check_user_banned(interaction: discord.Interaction, пользователь: discord.Member) -> bool:
    """Проверка, забанен ли пользователь"""
    try:
        ban_entry = await interaction.guild.fetch_ban(пользователь)
        embed = Design.create_embed("⚠️ Пользователь забанен", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Причина:** {ban_entry.reason or 'Не указана'}", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return True
    except discord.NotFound:
        return False

# 🔄 НОВЫЕ КОМАНДЫ ДЛЯ ДОПОЛНИТЕЛЬНЫХ СИСТЕМ

# 🛡️ КОМАНДЫ АВТОМОДЕРАЦИИ И РЕПОРТОВ
@bot.tree.command(name="репорт", description="Пожаловаться на пользователя")
async def репорт(interaction: discord.Interaction, пользователь: discord.Member, причина: str, доказательства: str = None):
    """Команда для жалоб на пользователей"""
    report_id = await bot.report_system.create_report(interaction.user, пользователь, причина, доказательства)
    
    report_channel = await bot.report_system.get_report_channel(interaction.guild)
    
    embed = Design.create_embed("🛡️ Новая жалоба", 
                              f"**Жалоба #{report_id}**\n"
                              f"👤 **От:** {interaction.user.mention}\n"
                              f"⚠️ **На:** {пользователь.mention}\n"
                              f"📝 **Причина:** {причина}", "warning")
    
    if доказательства:
        embed.add_field(name="📎 Доказательства", value=доказательства, inline=False)
    
    await report_channel.send(embed=embed)
    await interaction.response.send_message("✅ Жалоба отправлена модераторам!", ephemeral=True)

@bot.tree.command(name="автомод", description="Настройка автомодерации")
@commands.has_permissions(administrator=True)
async def автомод(interaction: discord.Interaction, анти_спам: bool = True, анти_упоминания: bool = True):
    """Настройка автомодерации"""
    automod_settings[interaction.guild.id] = {
        'anti_spam': анти_спам,
        'anti_mentions': анти_упоминания
    }
    
    embed = Design.create_embed("⚙️ Настройки автомодерации", 
                              f"**Анти-спам:** {'✅' if анти_спам else '❌'}\n"
                              f"**Анти-упоминания:** {'✅' if анти_упоминания else '❌'}", "success")
    await interaction.response.send_message(embed=embed)

# 🎯 КОМАНДЫ ИВЕНТОВ
@bot.tree.command(name="ивент", description="Создать ивент")
@is_admin()
async def ивент(interaction: discord.Interaction, тип: str, длительность: int, награда: int):
    """Создание ивента"""
    event_id = await bot.event_system.start_event(тип, длительность, награда)
    
    embed = Design.create_embed("🎪 Новый ивент!", 
                              f"**Ивент #{event_id}**\n"
                              f"🎯 **Тип:** {тип}\n"
                              f"⏱️ **Длительность:** {длительность} часов\n"
                              f"💰 **Награда:** {награда} монет", "event")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="участвовать", description="Участвовать в ивенте")
async def участвовать(interaction: discord.Interaction, id_ивента: int):
    """Участие в ивенте"""
    await bot.event_system.add_participant(id_ивента, interaction.user.id)
    await interaction.response.send_message("✅ Вы участвуете в ивенте!", ephemeral=True)

# 💑 КОМАНДЫ БРАКОВ
@bot.tree.command(name="брак", description="Предложить брак")
async def брак(interaction: discord.Interaction, партнер: discord.Member):
    """Предложение брака"""
    if партнер.id == interaction.user.id:
        await interaction.response.send_message("❌ Нельзя жениться на себе!", ephemeral=True)
        return
    
    embed = Design.create_embed("💍 Предложение брака", 
                              f"{interaction.user.mention} предлагает брак {партнер.mention}!\n"
                              f"Для согласия используйте `/принять_брак {interaction.user.id}`", "marriage")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="принять_брак", description="Принять предложение брака")
async def принять_брак(interaction: discord.Interaction, партнер_id: str):
    """Принятие предложения брака"""
    try:
        partner_id = int(партнер_id)
        await bot.marriage_system.marry(interaction.user.id, partner_id)
        
        partner = await bot.fetch_user(partner_id)
        embed = Design.create_embed("💑 Брак заключен!", 
                                  f"Поздравляем {interaction.user.mention} и {partner.mention} с браком! 💕", "marriage")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message("❌ Ошибка при заключении брака", ephemeral=True)

# 🏘️ КОМАНДЫ КЛАНОВ
@bot.tree.command(name="создать_клан", description="Создать клан")
async def создать_клан(interaction: discord.Interaction, название: str):
    """Создание клана"""
    clan_id = await bot.clan_system.create_clan(название, interaction.user.id)
    
    embed = Design.create_embed("🏘️ Клан создан!", 
                              f"**Клан:** {название}\n"
                              f"👑 **Лидер:** {interaction.user.mention}\n"
                              f"🆔 **ID клана:** {clan_id}", "clan")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="вступить_в_клан", description="Вступить в клан")
async def вступить_в_клан(interaction: discord.Interaction, id_клана: int):
    """Вступление в клан"""
    await bot.clan_system.add_member(id_клана, interaction.user.id)
    await interaction.response.send_message("✅ Вы вступили в клан!", ephemeral=True)

# 💎 КОМАНДЫ КРИПТОВАЛЮТЫ
@bot.tree.command(name="крипто", description="Проверить баланс криптовалюты")
async def крипто(interaction: discord.Interaction, валюта: str = "BITCOIN"):
    """Проверка баланса криптовалюты"""
    balance = await bot.crypto_system.get_crypto_balance(interaction.user.id, валюта)
    price = bot.crypto_system.crypto_prices.get(валюта, 0)
    
    embed = Design.create_embed("💎 Криптовалюта", 
                              f"**Баланс {валюта}:** {balance:.8f}\n"
                              f"**Текущая цена:** ${price:,.2f}\n"
                              f"**Примерная стоимость:** ${balance * price:,.2f}", "crypto")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="купить_крипто", description="Купить криптовалюту")
async def купить_крипто(interaction: discord.Interaction, валюта: str, количество: float):
    """Покупка криптовалюты"""
    price = bot.crypto_system.crypto_prices.get(валюта, 0)
    total_cost = price * количество
    
    balance = await bot.economy.get_balance(interaction.user.id)
    if balance < total_cost:
        await interaction.response.send_message("❌ Недостаточно средств!", ephemeral=True)
        return
    
    await bot.economy.update_balance(interaction.user.id, -total_cost)
    await bot.crypto_system.update_crypto_balance(interaction.user.id, количество, валюта)
    
    embed = Design.create_embed("💎 Покупка криптовалюты", 
                              f"**Куплено:** {количество:.8f} {валюта}\n"
                              f"**Потрачено:** {total_cost:,.2f} монет", "success")
    await interaction.response.send_message(embed=embed)

# 📈 КОМАНДЫ БИРЖИ
@bot.tree.command(name="акции", description="Просмотр цен акций")
async def акции(interaction: discord.Interaction):
    """Просмотр цен акций"""
    embed = Design.create_embed("📈 Биржа акций", "", "info")
    
    for symbol, data in bot.stock_market.stocks.items():
        embed.add_field(
            name=f"📊 {symbol}",
            value=f"Цена: ${data['price']:.2f}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)

# 🏠 КОМАНДЫ НЕДВИЖИМОСТИ
@bot.tree.command(name="недвижимость", description="Просмотр доступной недвижимости")
async def недвижимость(interaction: discord.Interaction):
    """Просмотр недвижимости"""
    embed = Design.create_embed("🏠 Недвижимость", "Доступные объекты для покупки:", "info")
    
    for prop_id, prop_data in bot.property_system.properties.items():
        embed.add_field(
            name=f"🏡 {prop_data['name']}",
            value=f"Цена: {prop_data['price']:,} монет\nДоход: {prop_data['income']} монет/день",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="купить_дом", description="Купить недвижимость")
async def купить_дом(interaction: discord.Interaction, id_недвижимости: str):
    """Покупка недвижимости"""
    success = await bot.property_system.buy_property(interaction.user.id, id_недвижимости)
    
    if success:
        prop_data = bot.property_system.properties[id_недвижимости]
        embed = Design.create_embed("✅ Недвижимость куплена!", 
                                  f"**Объект:** {prop_data['name']}\n"
                                  f"**Цена:** {prop_data['price']:,} монет\n"
                                  f"**Доход:** {prop_data['income']} монет/день", "success")
    else:
        embed = Design.create_embed("❌ Ошибка", "Не удалось купить недвижимость", "danger")
    
    await interaction.response.send_message(embed=embed)

# 🏆 КОМАНДЫ ДОСТИЖЕНИЙ
@bot.tree.command(name="достижения", description="Просмотр своих достижений")
async def достижения(interaction: discord.Interaction, пользователь: Optional[discord.Member] = None):
    """Просмотр достижений"""
    user = пользователь or interaction.user
    achievements = user_achievements.get(user.id, [])
    
    embed = Design.create_embed("🏆 Достижения", f"Достижения {user.display_name}:", "premium")
    
    if achievements:
        for ach_id in achievements[:10]:  # Показываем первые 10
            ach_data = bot.achievement_system.achievements.get(ach_id, {})
            embed.add_field(
                name=f"🎯 {ach_data.get('name', 'Неизвестно')}",
                value=ach_data.get('description', ''),
                inline=False
            )
    else:
        embed.description = "Пока нет достижений 😢"
    
    await interaction.response.send_message(embed=embed)

# 🎮 КОМАНДЫ МИНИ-ИГР
@bot.tree.command(name="викторина", description="Начать викторину")
async def викторина(interaction: discord.Interaction, тема: str = "general"):
    """Запуск викторины"""
    question_data = await bot.minigame_system.start_quiz(interaction, тема)
    
    if question_data:
        embed = Design.create_embed("🎮 Викторина", 
                                  f"**Вопрос:** {question_data['question']}\n\n"
                                  f"Отправьте ответ в чат!", "info")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Не удалось начать викторину", ephemeral=True)

# 📊 КОМАНДЫ АНАЛИТИКИ
@bot.tree.command(name="активность", description="Статистика активности")
@is_admin()
async def активность(interaction: discord.Interaction, пользователь: Optional[discord.Member] = None):
    """Статистика активности"""
    user = пользователь or interaction.user
    
    # Здесь будет логика сбора статистики
    embed = Design.create_embed("📊 Статистика активности", 
                              f"**Пользователь:** {user.mention}\n"
                              f"**Сообщений за день:** 0\n"  # Заглушка
                              f"**Команд использовано:** 0", "info")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="опрос", description="Создать опрос")
@commands.has_permissions(manage_messages=True)
async def опрос(interaction: discord.Interaction, вопрос: str, вариант1: str, вариант2: str, вариант3: str = None, вариант4: str = None):
    """Создание опроса"""
    embed = Design.create_embed("📊 Опрос", вопрос, "info")
    embed.add_field(name="1️⃣", value=вариант1, inline=False)
    embed.add_field(name="2️⃣", value=вариант2, inline=False)
    
    if вариант3:
        embed.add_field(name="3️⃣", value=вариант3, inline=False)
    if вариант4:
        embed.add_field(name="4️⃣", value=вариант4, inline=False)
    
    message = await interaction.response.send_message(embed=embed)
    
    # Добавляем реакции
    poll_msg = await interaction.original_response()
    reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']
    for i in range(2 + bool(вариант3) + bool(вариант4)):
        await poll_msg.add_reaction(reactions[i])

# 🔧 СУЩЕСТВУЮЩИЕ КОМАНДЫ (перенесены из оригинального кода)
# ... [Все существующие команды остаются без изменений] ...

# 🔄 ОБРАБОТЧИКИ СОБЫТИЙ С АВТОМОДЕРАЦИЕЙ
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Автомодерация
    guild_settings = automod_settings.get(message.guild.id, {})
    
    if guild_settings.get('anti_spam', True):
        if await bot.automod.check_spam(message):
            return
    
    if guild_settings.get('anti_mentions', True):
        if await bot.automod.check_mentions(message):
            return
    
    # Логирование активности
    await bot.logging_system.log_action(
        message.author.id, 
        'message', 
        f"Сообщение в #{message.channel.name}: {message.content[:50]}..."
    )
    
    if isinstance(message.channel, discord.TextChannel):
        async with aiosqlite.connect(bot.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.author.id,))
            await db.commit()
        
        xp_gain = random.randint(5, 15)
        level_up = await bot.economy.add_xp(message.author.id, xp_gain)
        
        if level_up:
            user_data = await bot.economy.get_user_data(message.author.id)
            embed = Design.create_embed("🎉 Уровень повышен!", 
                                      f"**{message.author.mention} достиг {user_data['level']} уровня!**", "success")
            await message.channel.send(embed=embed)
    
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    """Приветствие новых участников"""
    embed = Design.create_embed("👋 Добро пожаловать!", 
                              f"Приветствуем {member.mention} на сервере!\n"
                              f"Используй `/помощь` для просмотра команд", "success")
    
    # Ищем канал для приветствий
    channel = discord.utils.get(member.guild.channels, name="общее")
    if not channel:
        channel = member.guild.system_channel
    
    if channel:
        await channel.send(embed=embed)

@bot.event 
async def on_command_error(ctx, error):
    """Обработка ошибок команд"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Недостаточно прав для выполнения этой команды!", ephemeral=True)
    else:
        logging.error(f"Ошибка команды: {error}")
        await ctx.send("❌ Произошла ошибка при выполнении команды", ephemeral=True)

# 🚀 ЗАПУСК БОТА
if __name__ == "__main__":
    try:
        logging.info("🚀 Запуск улучшенного бота...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logging.info("\n🛑 Бот остановлен")
    except Exception as e:
        logging.error(f"❌ Ошибка запуска: {e}")


