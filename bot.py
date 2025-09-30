import discord
from discord.ext import commands, tasks
import aiosqlite
import asyncio
from datetime import datetime, timedelta
import os
import random
from typing import Optional
from dotenv import load_dotenv
import logging
import traceback
import aiohttp
import json
import shutil
import gzip
import psutil
import time
from pathlib import Path

# 🔧 КОНСТАНТЫ
ADMIN_IDS = [1195144951546265675, 766767256742526996, 1078693283695448064, 1138140772097597472, 691904643181314078]
MODERATION_ROLES = [1167093102868172911, 1360243534946373672, 993043931342319636, 1338611327022923910, 1338609155203661915, 1365798715930968244, 1188261847850299514]
THREADS_CHANNEL_ID = 1422557295811887175
EVENTS_CHANNEL_ID = 1418738569081786459
BACKUP_CHANNEL_ID = 1422557295811887175

# 🛡️ ГЛОБАЛЬНАЯ ПЕРЕМЕННАЯ ДЛЯ ЭКОНОМИЧЕСКИХ БАНОВ
economic_bans = {}

# 🔧 НАСТРОЙКА ЛОГИРОВАНИЯ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MegaBot')

# 📊 СИСТЕМА МОНИТОРИНГА
class MonitoringSystem:
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()
        self.command_stats = {}
        self.error_stats = {}
        self.user_activity = {}
        
    async def get_bot_stats(self):
        """Получить статистику бота"""
        try:
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024
            
            guild_count = len(self.bot.guilds)
            user_count = sum(guild.member_count for guild in self.bot.guilds)
            
            uptime = datetime.now() - self.start_time
            uptime_str = str(uptime).split('.')[0]
            
            total_commands = sum(self.command_stats.values())
            popular_commands = sorted(self.command_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                "uptime": uptime_str,
                "guilds": guild_count,
                "users": user_count,
                "memory_usage": f"{memory_usage:.2f} MB",
                "total_commands": total_commands,
                "popular_commands": popular_commands,
                "errors": sum(self.error_stats.values()),
                "cpu_usage": psutil.cpu_percent(),
                "disk_usage": psutil.disk_usage('/').percent
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def log_command(self, command_name: str):
        self.command_stats[command_name] = self.command_stats.get(command_name, 0) + 1
    
    def log_error(self, error_type: str):
        self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
    
    def log_user_activity(self, user_id: int):
        now = datetime.now()
        today = now.date()
        if user_id not in self.user_activity:
            self.user_activity[user_id] = {}
        self.user_activity[user_id][today] = self.user_activity[user_id].get(today, 0) + 1

# 💾 СИСТЕМА БЭКАПОВ
class BackupSystem:
    def __init__(self, bot, db_path: str):
        self.bot = bot
        self.db_path = db_path
        self.backup_dir = "backups"
        os.makedirs(self.backup_dir, exist_ok=True)
        
    async def create_backup(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"bot_backup_{timestamp}.db.gz"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            async with aiosqlite.connect(self.db_path) as source:
                await source.execute("VACUUM")
                
            with open(self.db_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            await self.send_backup_notification(backup_name, backup_path)
            await self.clean_old_backups()
            
            logger.info(f"✅ Бэкап создан: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания бэкапа: {e}")
            return False
    
    async def send_backup_notification(self, backup_name: str, backup_path: str):
        try:
            channel = self.bot.get_channel(BACKUP_CHANNEL_ID)
            if channel:
                file_size = os.path.getsize(backup_path) / 1024 / 1024
                embed = discord.Embed(
                    title="💾 Бэкап базы данных",
                    description=f"Бэкап успешно создан",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                embed.add_field(name="📁 Файл", value=backup_name, inline=False)
                embed.add_field(name="📊 Размер", value=f"{file_size:.2f} MB", inline=True)
                embed.add_field(name="🕒 Время", value=datetime.now().strftime("%H:%M:%S"), inline=True)
                await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о бэкапе: {e}")
    
    async def clean_old_backups(self):
        try:
            backup_files = []
            for file in os.listdir(self.backup_dir):
                if file.startswith("bot_backup_") and file.endswith(".db.gz"):
                    file_path = os.path.join(self.backup_dir, file)
                    backup_files.append((file_path, os.path.getctime(file_path)))
            
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            for file_path, _ in backup_files[10:]:
                os.remove(file_path)
                logger.info(f"🗑️ Удален старый бэкап: {os.path.basename(file_path)}")
                
        except Exception as e:
            logger.error(f"Ошибка очистки бэкапов: {e}")

# 🔧 ФУНКЦИИ ПРОВЕРКИ ПРАВ
def is_admin():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id in ADMIN_IDS
    return commands.check(predicate)

def is_moderator():
    async def predicate(interaction: discord.Interaction):
        user_roles = [role.id for role in interaction.user.roles]
        return any(role_id in MODERATION_ROLES for role_id in user_roles)
    return commands.check(predicate)

def check_economic_ban():
    async def predicate(interaction: discord.Interaction):
        ban_key = f"economic_ban_{interaction.user.id}"
        if ban_key in economic_bans:
            ban_info = economic_bans[ban_key]
            if datetime.now() < ban_info['end_time']:
                time_left = ban_info['end_time'] - datetime.now()
                hours_left = int(time_left.total_seconds() // 3600)
                await interaction.response.send_message(
                    f"🚫 Ваша экономика заблокирована за просрочку кредита!\n"
                    f"⏳ Разблокировка через: {hours_left} часов\n"
                    f"📋 Заблокированы: /работа, /ежедневно, /передать, /ограбить, /слоты",
                    ephemeral=True
                )
                return False
            else:
                del economic_bans[ban_key]
        return True
    return commands.check(predicate)

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN:
    logger.error("❌ Токен не найден! Создай .env файл с DISCORD_BOT_TOKEN")
    exit(1)

# 🎨 ДИЗАЙН
class Design:
    COLORS = {
        "primary": 0x5865F2, "success": 0x57F287, "warning": 0xFEE75C, 
        "danger": 0xED4245, "economy": 0xF1C40F, "music": 0x9B59B6,
        "moderation": 0xE74C3C, "shop": 0x9B59B6, "casino": 0xE67E22,
        "info": 0x3498DB, "premium": 0xFFD700, "roblox": 0xE74C3C,
        "discord": 0x5865F2, "tds": 0xF1C40F, "crypto": 0x16C60C,
        "event": 0x9B59B6, "credit": 0xE74C3C, "monitoring": 0x9B59B6,
        "backup": 0x3498DB
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
        try:
            async with aiosqlite.connect(self.db_path) as db:
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
                    CREATE TABLE IF NOT EXISTS warnings (
                        user_id INTEGER PRIMARY KEY,
                        warns INTEGER DEFAULT 0,
                        last_updated TEXT
                    )
                ''')
                
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS user_credits (
                        user_id INTEGER PRIMARY KEY,
                        company TEXT,
                        amount INTEGER,
                        interest_rate INTEGER,
                        due_date TEXT,
                        original_amount INTEGER,
                        created_at TEXT
                    )
                ''')
                
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS mining_farms (
                        user_id INTEGER PRIMARY KEY,
                        level INTEGER DEFAULT 1,
                        last_collected TEXT,
                        created_at TEXT
                    )
                ''')
                
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS user_crypto (
                        user_id INTEGER,
                        crypto_type TEXT,
                        amount REAL,
                        PRIMARY KEY (user_id, crypto_type)
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
                
                await db.execute('CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_credits_due ON user_credits(due_date)')
                
                await db.commit()
                logger.info("✅ База данных инициализирована")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise

    async def get_warns(self, user_id: int) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT warns FROM warnings WHERE user_id = ?', (user_id,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logger.error(f"Ошибка получения варнов для {user_id}: {e}")
            return 0

    async def add_warn(self, user_id: int) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO warnings (user_id, warns, last_updated) 
                    VALUES (?, COALESCE((SELECT warns FROM warnings WHERE user_id = ?), 0) + 1, ?)
                ''', (user_id, user_id, datetime.now().isoformat()))
                await db.commit()
                
                async with db.execute('SELECT warns FROM warnings WHERE user_id = ?', (user_id,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 1
        except Exception as e:
            logger.error(f"Ошибка добавления варна для {user_id}: {e}")
            return 0

    async def remove_warns(self, user_id: int, count: int) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    UPDATE warnings SET warns = MAX(0, warns - ?), last_updated = ? 
                    WHERE user_id = ?
                ''', (count, datetime.now().isoformat(), user_id))
                await db.commit()
                
                async with db.execute('SELECT warns FROM warnings WHERE user_id = ?', (user_id,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logger.error(f"Ошибка удаления варнов для {user_id}: {e}")
            return 0

    async def get_credit(self, user_id: int) -> Optional[dict]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT company, amount, interest_rate, due_date, original_amount FROM user_credits WHERE user_id = ?', (user_id,)) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        return {
                            "company": result[0],
                            "amount": result[1],
                            "interest_rate": result[2],
                            "due_date": datetime.fromisoformat(result[3]),
                            "original_amount": result[4]
                        }
                    return None
        except Exception as e:
            logger.error(f"Ошибка получения кредита для {user_id}: {e}")
            return None

    async def add_credit(self, user_id: int, company: str, amount: int, interest_rate: int, due_date: datetime, original_amount: int):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO user_credits 
                    (user_id, company, amount, interest_rate, due_date, original_amount, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, company, amount, interest_rate, due_date.isoformat(), original_amount, datetime.now().isoformat()))
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка добавления кредита для {user_id}: {e}")
            raise

    async def remove_credit(self, user_id: int):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('DELETE FROM user_credits WHERE user_id = ?', (user_id,))
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка удаления кредита для {user_id}: {e}")
            raise

    async def get_mining_farm(self, user_id: int) -> Optional[dict]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT level, last_collected, created_at FROM mining_farms WHERE user_id = ?', (user_id,)) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        last_collected = datetime.fromisoformat(result[1]) if result[1] else None
                        return {
                            "level": result[0],
                            "last_collected": last_collected,
                            "created_at": datetime.fromisoformat(result[2])
                        }
                    return None
        except Exception as e:
            logger.error(f"Ошибка получения фермы для {user_id}: {e}")
            return None

    async def create_mining_farm(self, user_id: int):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO mining_farms (user_id, level, last_collected, created_at)
                    VALUES (?, 1, NULL, ?)
                ''', (user_id, datetime.now().isoformat()))
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка создания фермы для {user_id}: {e}")
            raise

    async def update_mining_farm(self, user_id: int, level: int = None, last_collected: datetime = None):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if level is not None and last_collected is not None:
                    await db.execute('''
                        UPDATE mining_farms SET level = ?, last_collected = ? WHERE user_id = ?
                    ''', (level, last_collected.isoformat(), user_id))
                elif level is not None:
                    await db.execute('UPDATE mining_farms SET level = ? WHERE user_id = ?', (level, user_id))
                elif last_collected is not None:
                    await db.execute('UPDATE mining_farms SET last_collected = ? WHERE user_id = ?', (last_collected.isoformat(), user_id))
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления фермы для {user_id}: {e}")
            raise

    async def get_user_crypto(self, user_id: int) -> dict:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT crypto_type, amount FROM user_crypto WHERE user_id = ?', (user_id,)) as cursor:
                    return {row[0]: row[1] for row in await cursor.fetchall()}
        except Exception as e:
            logger.error(f"Ошибка получения крипты для {user_id}: {e}")
            return {}

    async def update_user_crypto(self, user_id: int, crypto_type: str, amount: float):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if amount <= 0:
                    await db.execute('DELETE FROM user_crypto WHERE user_id = ? AND crypto_type = ?', (user_id, crypto_type))
                else:
                    await db.execute('''
                        INSERT OR REPLACE INTO user_crypto (user_id, crypto_type, amount)
                        VALUES (?, ?, ?)
                    ''', (user_id, crypto_type, amount))
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления крипты для {user_id}: {e}")
            raise

# 💰 ЭКОНОМИКА
class EconomySystem:
    def __init__(self, db: Database):
        self.db = db

    async def get_balance(self, user_id: int):
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                async with db.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        return result[0]
                    else:
                        await db.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
                        await db.commit()
                        return 1000
        except Exception as e:
            logger.error(f"Ошибка получения баланса для {user_id}: {e}")
            return 1000
    
    async def update_balance(self, user_id: int, amount: int):
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
                await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
                await db.commit()
                return await self.get_balance(user_id)
        except Exception as e:
            logger.error(f"Ошибка обновления баланса для {user_id}: {e}")
            return await self.get_balance(user_id)
    
    async def get_user_data(self, user_id: int):
        try:
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
        except Exception as e:
            logger.error(f"Ошибка получения данных пользователя {user_id}: {e}")
            return {"balance": 1000, "level": 1, "xp": 0, "daily_claimed": None, "work_cooldown": None}

    async def admin_add_money(self, user_id: int, amount: int):
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
                await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
                await db.commit()
                return await self.get_balance(user_id)
        except Exception as e:
            logger.error(f"Ошибка выдачи денег для {user_id}: {e}")
            return await self.get_balance(user_id)

# 🏦 СИСТЕМА КРЕДИТОВ
class CreditSystem:
    def __init__(self, economy: EconomySystem, db: Database):
        self.economy = economy
        self.db = db
        self.companies = {
            "fast_money": {
                "name": "🚀 Быстрые Деньги",
                "min_amount": 1000,
                "max_amount": 5000,
                "interest_rate": 15,
                "term_days": 3,
                "penalty": "Бан экономики на 2 дня"
            },
            "reliable_credit": {
                "name": "🛡️ Надежный Кредит",
                "min_amount": 5000,
                "max_amount": 15000,
                "interest_rate": 8,
                "term_days": 7,
                "penalty": "-50% репутации"
            },
            "premium_finance": {
                "name": "💎 Премиум Финанс",
                "min_amount": 15000,
                "max_amount": 30000,
                "interest_rate": 5,
                "term_days": 14,
                "penalty": "-100% репутации + бан экономики"
            }
        }
    
    async def take_credit(self, user_id: int, company: str, amount: int):
        existing_credit = await self.db.get_credit(user_id)
        if existing_credit:
            return False, "У вас уже есть активный кредит"
        
        company_data = self.companies.get(company)
        if not company_data:
            return False, "Компания не найдена"
        
        if amount < company_data["min_amount"] or amount > company_data["max_amount"]:
            return False, f"Сумма должна быть от {company_data['min_amount']} до {company_data['max_amount']}"
        
        due_date = datetime.now() + timedelta(days=company_data["term_days"])
        
        await self.db.add_credit(
            user_id=user_id,
            company=company,
            amount=amount,
            interest_rate=company_data["interest_rate"],
            due_date=due_date,
            original_amount=amount
        )
        
        await self.economy.update_balance(user_id, amount)
        return True, f"Кредит одобрен! Вернуть до {due_date.strftime('%d.%m.%Y')}"

    async def repay_credit(self, user_id: int):
        credit = await self.db.get_credit(user_id)
        if not credit:
            return False, "У вас нет активных кредитов"
        
        total_to_repay = credit["amount"]
        
        balance = await self.economy.get_balance(user_id)
        if balance < total_to_repay:
            return False, f"Недостаточно средств. Нужно: {total_to_repay} монет"
        
        await self.economy.update_balance(user_id, -total_to_repay)
        await self.db.remove_credit(user_id)
        return True, f"Кредит погашен! Сумма: {total_to_repay} монет"

# 🎁 СИСТЕМА ЛУТБОКСОВ
class LootboxSystem:
    def __init__(self, economy: EconomySystem, db: Database):
        self.economy = economy
        self.db = db
        self.lootboxes = {
            "common": {
                "name": "📦 Обычный лутбокс",
                "price": 500,
                "rewards": [
                    {"type": "money", "min": 50, "max": 200, "chance": 100},
                    {"type": "money", "min": 100, "max": 300, "chance": 20},
                    {"type": "nothing", "chance": 40},
                    {"type": "crypto", "min": 0.001, "max": 0.003, "chance": 10}
                ]
            },
            "rare": {
                "name": "🎁 Редкий лутбокс", 
                "price": 1500,
                "rewards": [
                    {"type": "money", "min": 200, "max": 500, "chance": 100},
                    {"type": "money", "min": 300, "max": 700, "chance": 25},
                    {"type": "nothing", "chance": 35},
                    {"type": "crypto", "min": 0.003, "max": 0.008, "chance": 15},
                    {"type": "money", "min": 1000, "max": 2000, "chance": 8}
                ]
            }
        }
    
    async def open_lootbox(self, user_id: int, lootbox_type: str):
        lootbox = self.lootboxes.get(lootbox_type)
        if not lootbox:
            return False, None
        
        balance = await self.economy.get_balance(user_id)
        if balance < lootbox["price"]:
            return False, "Недостаточно средств"
        
        await self.economy.update_balance(user_id, -lootbox["price"])
        
        rewards = []
        for reward in lootbox["rewards"]:
            if random.randint(1, 100) <= reward["chance"]:
                if reward["type"] == "money":
                    amount = random.randint(reward["min"], reward["max"])
                    await self.economy.update_balance(user_id, amount)
                    rewards.append(f"💰 {amount} монет")
                elif reward["type"] == "nothing":
                    rewards.append("💨 Пустота...")
                elif reward["type"] == "crypto":
                    crypto_type = random.choice(["BITCOIN", "ETHEREUM", "DOGECOIN"])
                    amount = random.uniform(reward["min"], reward["max"])
                    
                    user_crypto_data = await self.db.get_user_crypto(user_id)
                    current_amount = user_crypto_data.get(crypto_type, 0)
                    new_amount = current_amount + amount
                    
                    await self.db.update_user_crypto(user_id, crypto_type, new_amount)
                    rewards.append(f"₿ {amount:.4f} {crypto_type}")
        
        if not rewards:
            rewards.append("💔 Не повезло... Попробуй еще раз!")
        
        return True, rewards

# 🔧 СИСТЕМА МАЙНИНГА
class MiningSystem:
    def __init__(self, economy: EconomySystem, db: Database):
        self.economy = economy
        self.db = db
        self.farm_levels = {
            1: {"income": 10, "upgrade_cost": 1000},
            2: {"income": 25, "upgrade_cost": 5000},
            3: {"income": 50, "upgrade_cost": 15000}
        }
    
    async def collect_income(self, user_id: int):
        try:
            farm = await self.db.get_mining_farm(user_id)
            if not farm:
                return False, "У вас нет фермы"
            
            if farm.get("last_collected"):
                last_collect = farm["last_collected"]
                time_passed = datetime.now() - last_collect
                if time_passed.total_seconds() < 21600:
                    hours_left = 5 - int(time_passed.total_seconds() // 3600)
                    minutes_left = 59 - int((time_passed.total_seconds() % 3600) // 60)
                    return False, f"Доход можно собирать раз в 6 часов! Осталось: {hours_left}ч {minutes_left}м"
            
            income = self.farm_levels[farm["level"]]["income"]
            await self.economy.update_balance(user_id, income)
            
            await self.db.update_mining_farm(user_id, last_collected=datetime.now())
            
            return True, f"✅ Собрано {income} монет с фермы! Следующий сбор через 6 часов"
            
        except Exception as e:
            logger.error(f"Ошибка при сборе дохода: {e}")
            return False, "❌ Произошла ошибка при сборе дохода"

# 🎪 СИСТЕМА ИВЕНТОВ
class EventSystem:
    def __init__(self, economy: EconomySystem):
        self.economy = economy
        self.event_types = {
            "money_rain": {
                "name": "💰 Денежный дождь", 
                "duration": 300, 
                "multiplier": 2,
                "description": "ВСЕ денежные операции приносят в 2 раза больше монет!"
            }
        }
    
    async def start_event(self, event_type: str, bot_instance):
        event = self.event_types.get(event_type)
        if not event:
            return False
        
        bot_instance.active_events[event_type] = {
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(seconds=event["duration"]),
            "data": event
        }
        
        try:
            channel = bot_instance.get_channel(EVENTS_CHANNEL_ID)
            if channel:
                embed = Design.create_embed(
                    "🎉 НАЧАЛСЯ ИВЕНТ!",
                    f"**{event['name']}**\n\n"
                    f"📝 **Описание:** {event['description']}\n"
                    f"⏰ **Длительность:** {event['duration'] // 60} минут",
                    "event"
                )
                await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки ивента: {e}")
        
        return True

# 🎰 КАЗИНО
class CasinoSystem:
    def __init__(self, economy: EconomySystem):
        self.economy = economy
    
    async def play_slots(self, user_id: int, bet: int):
        if bet < 0:
            return {"success": False, "error": "Ставка не может быть отрицательной!"}
        
        balance = await self.economy.get_balance(user_id)
        if balance < bet:
            return {"success": False, "error": "Недостаточно средств!"}
        
        symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎", "7️⃣"]
        result = [random.choice(symbols) for _ in range(3)]
        
        await self.economy.update_balance(user_id, -bet)
        
        if result[0] == result[1] == result[2]:
            multiplier = 10
        elif result[0] == result[1] or result[1] == result[2]:
            multiplier = 3
        else:
            multiplier = 0
        
        win_amount = bet * multiplier
        if win_amount > 0:
            await self.economy.update_balance(user_id, win_amount)
        
        return {
            "success": True,
            "result": result,
            "multiplier": multiplier,
            "win_amount": win_amount
        }

# 🏗️ ГЛАВНЫЙ БОТ
class MegaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        
        self.db = Database()
        self.economy = EconomySystem(self.db)
        self.casino = CasinoSystem(self.economy)
        
        self.credit_system = CreditSystem(self.economy, self.db)
        self.lootbox_system = LootboxSystem(self.economy, self.db)
        self.mining_system = MiningSystem(self.economy, self.db)
        self.event_system = EventSystem(self.economy)
        
        self.monitoring = MonitoringSystem(self)
        self.backup_system = BackupSystem(self, self.db.db_path)
        
        self.start_time = datetime.now()
        self.server_tax_pool = 0
        self.rob_cooldowns = {}
        self.crypto_prices = {"BITCOIN": 50000, "ETHEREUM": 3000, "DOGECOIN": 0.15}
        self.active_events = {}
    
    async def setup_hook(self):
        await self.db.init_db()
        try:
            synced = await self.tree.sync()
            logger.info(f"✅ Синхронизировано {len(synced)} команд")
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации: {e}")
        
        self.backup_task.start()
        self.monitoring_task.start()

    async def reload_bot(self):
        try:
            synced = await self.tree.sync()
            logger.info(f"♻️ Бот перезагружен! Синхронизировано {len(synced)} команд")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка перезагрузки: {e}")
            return False

    async def close(self):
        logger.info("🔴 Бот выключается...")
        self.backup_task.cancel()
        self.monitoring_task.cancel()
        await super().close()

    @tasks.loop(hours=6)
    async def backup_task(self):
        try:
            await self.backup_system.create_backup()
        except Exception as e:
            logger.error(f"Ошибка в задаче бэкапа: {e}")

    @tasks.loop(minutes=5)
    async def monitoring_task(self):
        try:
            stats = await self.monitoring.get_bot_stats()
            
            if datetime.now().minute % 30 == 0:
                logger.info(f"📊 Статистика бота: {stats}")
                
                if stats.get('memory_usage', '0 MB') > 500:
                    try:
                        channel = self.get_channel(BACKUP_CHANNEL_ID)
                        if channel:
                            embed = Design.create_embed(
                                "⚠️ ВНИМАНИЕ: ВЫСОКАЯ ЗАГРУЗКА",
                                f"**Память бота:** {stats.get('memory_usage', 'N/A')}\n"
                                f"**Использование CPU:** {stats.get('cpu_usage', 'N/A')}%\n"
                                f"**Диск:** {stats.get('disk_usage', 'N/A')}%\n\n"
                                f"Рекомендуется перезагрузка бота!",
                                "warning"
                            )
                            await channel.send(embed=embed)
                    except Exception as e:
                        logger.error(f"Ошибка отправки предупреждения: {e}")
                
                if stats.get('memory_usage', 0) > 400 or stats.get('cpu_usage', 0) > 80:
                    await self.backup_system.create_backup()
            
            await self.check_overdue_credits()
            await self.update_crypto_prices()
            await self.check_events()
            
            if datetime.now().minute % 30 == 0:
                await self.cleanup_old_data()
                
        except Exception as e:
            logger.error(f"❌ Ошибка в задаче мониторинга: {e}")

    async def check_overdue_credits(self):
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                async with db.execute(
                    'SELECT user_id, company, amount, due_date FROM user_credits WHERE due_date < ?',
                    (datetime.now().isoformat(),)
                ) as cursor:
                    overdue_credits = await cursor.fetchall()
                    
            for user_id, company, amount, due_date in overdue_credits:
                ban_key = f"economic_ban_{user_id}"
                economic_bans[ban_key] = {
                    'end_time': datetime.now() + timedelta(hours=48),
                    'reason': f'Просрочка кредита в {company}'
                }
                
                await self.db.remove_credit(user_id)
                
                try:
                    user = self.get_user(user_id)
                    if user:
                        embed = Design.create_embed(
                            "🚫 КРЕДИТ ПРОСРОЧЕН!",
                            f"**Компания:** {company}\n"
                            f"**Сумма:** {amount} монет\n"
                            f"**Дата возврата:** {due_date[:10]}\n\n"
                            f"⚠️ Ваша экономика заблокирована на 48 часов!",
                            "danger"
                        )
                        await user.send(embed=embed)
                except:
                    pass
                
                logger.info(f"🚫 Кредит пользователя {user_id} просрочен, бан экономики")
                
        except Exception as e:
            logger.error(f"Ошибка проверки кредитов: {e}")

    async def update_crypto_prices(self):
        try:
            for crypto in self.crypto_prices:
                change_percent = random.uniform(-0.05, 0.05)
                self.crypto_prices[crypto] = max(0.01, self.crypto_prices[crypto] * (1 + change_percent))
            
            if datetime.now().minute % 30 == 0:
                logger.info(f"₿ Обновлены цены крипты: {self.crypto_prices}")
                
        except Exception as e:
            logger.error(f"Ошибка обновления цен крипты: {e}")

    async def check_events(self):
        try:
            current_time = datetime.now()
            expired_events = []
            
            for event_type, event_data in self.active_events.items():
                if current_time > event_data["end_time"]:
                    expired_events.append(event_type)
                    
                    try:
                        channel = self.get_channel(EVENTS_CHANNEL_ID)
                        if channel:
                            embed = Design.create_embed(
                                "🎉 ИВЕНТ ЗАВЕРШЕН!",
                                f"**{event_data['data']['name']}** завершился!\n"
                                f"Спасибо всем участникам!",
                                "event"
                            )
                            await channel.send(embed=embed)
                    except Exception as e:
                        logger.error(f"Ошибка отправки завершения ивента: {e}")
            
            for event_type in expired_events:
                del self.active_events[event_type]
                
        except Exception as e:
            logger.error(f"Ошибка проверки ивентов: {e}")

    async def cleanup_old_data(self):
        try:
            current_time = time.time()
            expired_robs = []
            
            for user_id, rob_time in self.rob_cooldowns.items():
                if current_time - rob_time > 3600:
                    expired_robs.append(user_id)
            
            for user_id in expired_robs:
                del self.rob_cooldowns[user_id]
            
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute(
                    'UPDATE warnings SET warns = GREATEST(0, warns - 1) WHERE last_updated < ?',
                    (week_ago,)
                )
                await db.commit()
            
            logger.info("🧹 Авто-очистка данных выполнена")
            
        except Exception as e:
            logger.error(f"Ошибка очистки данных: {e}")

# 🎮 ДОПОЛНИТЕЛЬНЫЕ СИСТЕМЫ
class NFTSystem:
    def __init__(self, db: Database):
        self.db = db
        self.nft_collections = {
            "starter": {
                "name": "🎨 Стартовая коллекция",
                "nfts": {
                    1: {"name": "🔥 Огненный дракон", "rarity": "legendary", "value": 5000},
                    2: {"name": "💎 Кристальный воин", "rarity": "epic", "value": 2500},
                    3: {"name": "🌿 Лесной эльф", "rarity": "rare", "value": 1000},
                    4: {"name": "⚡ Молниевый волк", "rarity": "uncommon", "value": 500},
                    5: {"name": "💧 Водяной дух", "rarity": "common", "value": 100}
                }
            },
            "crypto": {
                "name": "₿ Крипто коллекция", 
                "nfts": {
                    6: {"name": "Биткоин Сатоши", "rarity": "legendary", "value": 10000},
                    7: {"name": "Эфириум Виталик", "rarity": "epic", "value": 5000},
                    8: {"name": "Доджкоин Маск", "rarity": "rare", "value": 2000}
                }
            }
        }
    
    async def buy_nft_pack(self, user_id: int, collection: str):
        collection_data = self.nft_collections.get(collection)
        if not collection_data:
            return False, "Коллекция не найдена"
        
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                if not result or result[0] < 2000:
                    return False, "Недостаточно средств для покупки пака (2000 монет)"
            
            rarity_weights = {"common": 50, "uncommon": 30, "rare": 15, "epic": 4, "legendary": 1}
            weighted_nfts = []
            
            for nft_id, nft_data in collection_data["nfts"].items():
                weighted_nfts.extend([nft_id] * rarity_weights[nft_data["rarity"]])
            
            chosen_nft_id = random.choice(weighted_nfts)
            chosen_nft = collection_data["nfts"][chosen_nft_id]
            
            await db.execute('''
                INSERT OR REPLACE INTO inventory (user_id, item_id, quantity)
                VALUES (?, ?, COALESCE((SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?), 0) + 1)
            ''', (user_id, chosen_nft_id, user_id, chosen_nft_id))
            
            await db.execute('UPDATE users SET balance = balance - 2000 WHERE user_id = ?', (user_id,))
            await db.commit()
            
            return True, chosen_nft

class StockMarket:
    def __init__(self, db: Database):
        self.db = db
        self.stocks = {
            "TECH": {"name": "🔮 TechCorp", "price": 100, "volatility": 0.2},
            "ENERGY": {"name": "⚡ EnergyPlus", "price": 80, "volatility": 0.15},
            "GOLD": {"name": "🥇 GoldMine Inc", "price": 150, "volatility": 0.1},
            "GAME": {"name": "🎮 GameStudio", "price": 60, "volatility": 0.25},
            "CRYPTO": {"name": "₿ CryptoBank", "price": 120, "volatility": 0.3}
        }
        self.last_update = datetime.now()
    
    async def update_prices(self):
        current_time = datetime.now()
        if (current_time - self.last_update).total_seconds() < 300:
            return
        
        for symbol, stock in self.stocks.items():
            change_percent = random.uniform(-stock["volatility"], stock["volatility"])
            stock["price"] = max(10, stock["price"] * (1 + change_percent))
        
        self.last_update = current_time
    
    async def buy_stock(self, user_id: int, symbol: str, quantity: int):
        await self.update_prices()
        
        stock = self.stocks.get(symbol)
        if not stock:
            return False, "Акция не найдена"
        
        total_cost = stock["price"] * quantity
        
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                if not result or result[0] < total_cost:
                    return False, f"Недостаточно средств. Нужно: {total_cost:.2f} монет"
            
            await db.execute('''
                INSERT OR REPLACE INTO user_stocks (user_id, symbol, quantity, avg_price)
                VALUES (?, ?, ?, COALESCE(
                    (SELECT (avg_price * quantity + ? * ?) / (quantity + ?) 
                     FROM user_stocks WHERE user_id = ? AND symbol = ?),
                    ?
                ))
            ''', (user_id, symbol, quantity, stock["price"], quantity, quantity, user_id, symbol, stock["price"]))
            
            await db.execute('''
                UPDATE user_stocks SET quantity = quantity + ? 
                WHERE user_id = ? AND symbol = ?
            ''', (quantity, user_id, symbol))
            
            await db.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (total_cost, user_id))
            await db.commit()
            
            return True, f"✅ Куплено {quantity} акций {stock['name']} за {total_cost:.2f} монет"

class ClanSystem:
    def __init__(self, db: Database):
        self.db = db
    
    async def create_clan(self, user_id: int, clan_name: str, clan_tag: str):
        if len(clan_tag) > 5:
            return False, "Тег клана не может быть длиннее 5 символов"
        
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT id FROM clans WHERE name = ? OR tag = ?', (clan_name, clan_tag)) as cursor:
                if await cursor.fetchone():
                    return False, "Клан с таким именем или тегом уже существует"
            
            async with db.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                if not result or result[0] < 5000:
                    return False, "Недостаточно средств для создания клана (5000 монет)"
            
            await db.execute('''
                INSERT INTO clans (name, tag, owner_id, created_at, level, treasury)
                VALUES (?, ?, ?, ?, 1, 0)
            ''', (clan_name, clan_tag, user_id, datetime.now().isoformat()))
            
            clan_id = db.last_insert_id
            await db.execute('''
                INSERT INTO clan_members (clan_id, user_id, role, joined_at)
                VALUES (?, ?, 'leader', ?)
            ''', (clan_id, user_id, datetime.now().isoformat()))
            
            await db.execute('UPDATE users SET balance = balance - 5000 WHERE user_id = ?', (user_id,))
            await db.commit()
            
            return True, f"✅ Клан {clan_name} [{clan_tag}] создан!"

class QuestSystem:
    def __init__(self, db: Database):
        self.db = db
        self.quests = {
            "daily_work": {"name": "💼 Работать 3 раза", "target": 3, "reward": 500},
            "daily_slots": {"name": "🎰 Сыграть в слоты", "target": 1, "reward": 300},
            "daily_rob": {"name": "🏴‍☠️ Ограбить банк", "target": 1, "reward": 700},
            "daily_crypto": {"name": "₿ Купить крипту", "target": 1, "reward": 400},
            "weekly_rich": {"name": "💰 Накопить 10к монет", "target": 10000, "reward": 2000}
        }
    
    async def get_daily_quests(self, user_id: int):
        today = datetime.now().date().isoformat()
        
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute(
                'SELECT quests_data FROM daily_quests WHERE user_id = ? AND date = ?', 
                (user_id, today)
            ) as cursor:
                result = await cursor.fetchone()
                
                if result:
                    return json.loads(result[0])
                else:
                    daily_quests = random.sample(list(self.quests.keys()), 3)
                    quests_data = {}
                    
                    for quest_key in daily_quests:
                        quest = self.quests[quest_key]
                        quests_data[quest_key] = {
                            "name": quest["name"],
                            "progress": 0,
                            "target": quest["target"],
                            "reward": quest["reward"],
                            "completed": False
                        }
                    
                    await db.execute('''
                        INSERT OR REPLACE INTO daily_quests (user_id, date, quests_data)
                        VALUES (?, ?, ?)
                    ''', (user_id, today, json.dumps(quests_data)))
                    await db.commit()
                    
                    return quests_data

class MusicPlayer:
    def __init__(self):
        self.players = {}
    
    async def play_music(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Подключись к голосовому каналу!", ephemeral=True)
            return
        
        await interaction.response.send_message(
            f"🎵 Музыкальная система в разработке! Запрос: {query}",
            ephemeral=True
        )

# 🎉 СОЗДАЕМ БОТА
bot = MegaBot()

# 🆕 КОМАНДА СТАТУСА СИСТЕМЫ
@bot.tree.command(name="статус", description="📊 Статус бота и систем")
async def status_command(interaction: discord.Interaction):
    try:
        stats = await bot.monitoring.get_bot_stats()
        
        embed = Design.create_embed("📊 СТАТУС СИСТЕМ БОТА", "", "monitoring")
        
        embed.add_field(
            name="🖥️ ОСНОВНЫЕ МЕТРИКИ",
            value=f"**Время работы:** {stats.get('uptime', 'N/A')}\n"
                  f"**Серверов:** {stats.get('guilds', 0)}\n"
                  f"**Пользователей:** {stats.get('users', 0)}\n"
                  f"**Память:** {stats.get('memory_usage', 'N/A')}\n"
                  f"**CPU:** {stats.get('cpu_usage', 0)}%",
            inline=False
        )
        
        embed.add_field(
            name="📈 АКТИВНОСТЬ",
            value=f"**Всего команд:** {stats.get('total_commands', 0)}\n"
                  f"**Ошибки:** {stats.get('errors', 0)}\n"
                  f"**Популярные команды:** {', '.join([cmd[0] for cmd in stats.get('popular_commands', [])[:3]])}",
            inline=False
        )
        
        systems_status = []
        
        overdue_count = 0
        async with aiosqlite.connect(bot.db.db_path) as db:
            async with db.execute(
                'SELECT COUNT(*) FROM user_credits WHERE due_date < ?',
                (datetime.now().isoformat(),)
            ) as cursor:
                overdue_count = (await cursor.fetchone())[0]
        
        systems_status.append(f"🏦 Кредиты: {'⚠️' if overdue_count > 0 else '✅'} ({overdue_count} просрочек)")
        systems_status.append(f"🎉 Ивенты: {'✅' if bot.active_events else '🔴'} ({len(bot.active_events)} активных)")
        systems_status.append(f"₿ Крипта: ✅ ({len(bot.crypto_prices)} валют)")
        systems_status.append(f"🚫 Баны: {len(economic_bans)} пользователей")
        
        embed.add_field(
            name="⚙️ СТАТУС СИСТЕМ",
            value="\n".join(systems_status),
            inline=False
        )
        
        try:
            async with aiosqlite.connect(bot.db.db_path) as db:
                async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                    user_count = (await cursor.fetchone())[0]
                
                embed.add_field(
                    name="💾 БАЗА ДАННЫХ",
                    value=f"**Пользователей в БД:** {user_count}\n"
                          f"**Размер БД:** {os.path.getsize(bot.db.db_path) / 1024 / 1024:.2f} MB\n"
                          f"**Последний бэкап:** {datetime.now().strftime('%H:%M')}",
                    inline=False
                )
        except Exception as e:
            logger.error(f"Ошибка получения статуса БД: {e}")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Ошибка в команде статуса: {e}")
        await interaction.response.send_message("❌ Ошибка получения статуса!", ephemeral=True)

@bot.tree.command(name="нфт", description="🚀 Система NFT и коллекций")
async def nft_command(interaction: discord.Interaction, действие: str = None, коллекция: str = None):
    try:
        nft_system = NFTSystem(bot.db)
        
        if действие == "купить":
            if not коллекция:
                await interaction.response.send_message("❌ Укажи коллекцию: `starter` или `crypto`")
                return
            
            success, result = await nft_system.buy_nft_pack(interaction.user.id, коллекция)
            if success:
                embed = Design.create_embed(
                    "🎉 ТЫ ПОЛУЧИЛ NFT!",
                    f"**{result['name']}**\n"
                    f"📊 Редкость: {result['rarity']}\n"
                    f"💎 Ценность: {result['value']} монет\n"
                    f"🎨 Коллекция: {коллекция}",
                    "success"
                )
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(f"❌ {result}", ephemeral=True)
                
        elif действие == "инвентарь":
            async with aiosqlite.connect(bot.db.db_path) as db:
                async with db.execute(
                    'SELECT item_id, quantity FROM inventory WHERE user_id = ? AND item_id <= 8', 
                    (interaction.user.id,)
                ) as cursor:
                    nfts = await cursor.fetchall()
            
            if not nfts:
                await interaction.response.send_message("📭 У тебя пока нет NFT!", ephemeral=True)
                return
            
            embed = Design.create_embed("🎨 ТВОИ NFT", "", "premium")
            for nft_id, quantity in nfts:
                for collection in nft_system.nft_collections.values():
                    if nft_id in collection["nfts"]:
                        nft_data = collection["nfts"][nft_id]
                        embed.add_field(
                            name=f"{nft_data['name']} x{quantity}",
                            value=f"📊 {nft_data['rarity']} | 💎 {nft_data['value']}",
                            inline=False
                        )
                        break
            
            await interaction.response.send_message(embed=embed)
        else:
            embed = Design.create_embed(
                "🚀 СИСТЕМА NFT",
                "**Доступные команды:**\n"
                "`/нфт купить [коллекция]` - Купить NFT пак (2000 монет)\n"
                "`/нфт инвентарь` - Посмотреть свои NFT\n\n"
                "**Коллекции:**\n"
                "🎨 `starter` - Стартовая коллекция\n"
                "₿ `crypto` - Крипто коллекция",
                "info"
            )
            await interaction.response.send_message(embed=embed)
            
    except Exception as e:
        logger.error(f"Ошибка в NFT команде: {e}")
        await interaction.response.send_message("❌ Произошла ошибка!", ephemeral=True)

@bot.tree.command(name="акции", description="📈 Фондовый рынок")
async def stocks_command(interaction: discord.Interaction, действие: str = None, акция: str = None, количество: int = 1):
    try:
        stock_market = StockMarket(bot.db)
        
        if действие == "купить":
            if not акция:
                await stock_market.update_prices()
                
                embed = Design.create_embed("📈 ФОНДОВЫЙ РЫНОК", "**Доступные акции:**", "success")
                for symbol, stock in stock_market.stocks.items():
                    embed.add_field(
                        name=f"{stock['name']} ({symbol})",
                        value=f"💵 Цена: {stock['price']:.2f} монет",
                        inline=True
                    )
                
                embed.add_field(
                    name="🛒 Покупка",
                    value="Используй: `/акции купить [SYMBOL] [количество]`",
                    inline=False
                )
                await interaction.response.send_message(embed=embed)
                return
            
            success, result = await stock_market.buy_stock(interaction.user.id, акция, количество)
            if success:
                await interaction.response.send_message(f"✅ {result}")
            else:
                await interaction.response.send_message(f"❌ {result}", ephemeral=True)
                
        elif действие == "портфель":
            async with aiosqlite.connect(bot.db.db_path) as db:
                async with db.execute(
                    'SELECT symbol, quantity, avg_price FROM user_stocks WHERE user_id = ?', 
                    (interaction.user.id,)
                ) as cursor:
                    portfolio = await cursor.fetchall()
            
            if not portfolio:
                await interaction.response.send_message("📭 У тебя пока нет акций!", ephemeral=True)
                return
            
            await stock_market.update_prices()
            total_value = 0
            
            embed = Design.create_embed("💼 ТВОЙ ПОРТФЕЛЬ АКЦИЙ", "", "success")
            for symbol, quantity, avg_price in portfolio:
                current_price = stock_market.stocks[symbol]["price"]
                value = quantity * current_price
                total_value += value
                profit = ((current_price - avg_price) / avg_price) * 100
                
                embed.add_field(
                    name=f"{stock_market.stocks[symbol]['name']} x{quantity}",
                    value=f"💵 Текущая: {current_price:.2f}\n📊 Прибыль: {profit:+.1f}%",
                    inline=True
                )
            
            embed.add_field(
                name="💰 ОБЩАЯ СТОИМОСТЬ",
                value=f"{total_value:.2f} монет",
                inline=False
            )
            await interaction.response.send_message(embed=embed)
            
        else:
            embed = Design.create_embed(
                "📈 ФОНДОВЫЙ РЫНОК",
                "**Доступные команды:**\n"
                "`/акции купить` - Посмотреть акции для покупки\n"
                "`/акции купить [SYMBOL] [количество]` - Купить акции\n"
                "`/акции портфель` - Посмотреть свой портфель\n\n"
                "💡 *Цены обновляются каждые 5 минут*",
                "info"
            )
            await interaction.response.send_message(embed=embed)
            
    except Exception as e:
        logger.error(f"Ошибка в команде акций: {e}")
        await interaction.response.send_message("❌ Произошла ошибка!", ephemeral=True)

@bot.tree.command(name="клан", description="🏰 Система кланов")
async def clan_command(interaction: discord.Interaction, действие: str = None, название: str = None, тег: str = None):
    try:
        clan_system = ClanSystem(bot.db)
        
        if действие == "создать":
            if not название or not тег:
                await interaction.response.send_message("❌ Укажи название и тег клана!", ephemeral=True)
                return
            
            success, result = await clan_system.create_clan(interaction.user.id, название, тег)
            if success:
                await interaction.response.send_message(f"✅ {result}")
            else:
                await interaction.response.send_message(f"❌ {result}", ephemeral=True)
                
        elif действие == "список":
            async with aiosqlite.connect(bot.db.db_path) as db:
                async with db.execute(
                    'SELECT name, tag, level, treasury FROM clans ORDER BY level DESC LIMIT 10'
                ) as cursor:
                    clans = await cursor.fetchall()
            
            if not clans:
                await interaction.response.send_message("🏰 Кланов пока нет! Создай первый!", ephemeral=True)
                return
            
            embed = Design.create_embed("🏰 ТОП 10 КЛАНОВ", "", "success")
            for i, (name, tag, level, treasury) in enumerate(clans, 1):
                embed.add_field(
                    name=f"{i}. {name} [{tag}]",
                    value=f"⭐ Уровень: {level}\n💰 Казна: {treasury} монет",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        else:
            embed = Design.create_embed(
                "🏰 СИСТЕМА КЛАНОВ",
                "**Доступные команды:**\n"
                "`/клан создать [название] [тег]` - Создать клан (5000 монет)\n"
                "`/клан список` - Топ кланов сервера\n\n"
                "💡 *Кланы открывают доступ к клановым войнам и бонусам!*",
                "info"
            )
            await interaction.response.send_message(embed=embed)
            
    except Exception as e:
        logger.error(f"Ошибка в команде кланов: {e}")
        await interaction.response.send_message("❌ Произошла ошибка!", ephemeral=True)

@bot.tree.command(name="задания", description="🎯 Ежедневные задания")
async def quests_command(interaction: discord.Interaction):
    try:
        quest_system = QuestSystem(bot.db)
        quests = await quest_system.get_daily_quests(interaction.user.id)
        
        embed = Design.create_embed("🎯 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ", "Выполняй задания для получения наград!", "success")
        
        for quest_key, quest_data in quests.items():
            status = "✅ ВЫПОЛНЕНО" if quest_data["completed"] else f"📊 {quest_data['progress']}/{quest_data['target']}"
            embed.add_field(
                name=quest_data["name"],
                value=f"{status}\n🎁 Награда: {quest_data['reward']} монет",
                inline=False
            )
        
        embed.set_footer(text="Задания обновляются каждый день в 00:00")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Ошибка в команде заданий: {e}")
        await interaction.response.send_message("❌ Произошла ошибка!", ephemeral=True)

@bot.tree.command(name="музыка", description="🎵 Воспроизвести музыку")
async def music_command(interaction: discord.Interaction, запрос: str = None):
    try:
        if not запрос:
            embed = Design.create_embed(
                "🎵 МУЗЫКАЛЬНАЯ СИСТЕМА",
                "**Доступные команды:**\n"
                "`/музыка [название/url]` - Воспроизвести музыку\n\n"
                "💡 *Поддерживаются YouTube, SoundCloud, Spotify*",
                "music"
            )
            await interaction.response.send_message(embed=embed)
            return
        
        music_player = MusicPlayer()
        await music_player.play_music(interaction, запрос)
        
    except Exception as e:
        logger.error(f"Ошибка в музыкальной команде: {e}")
        await interaction.response.send_message("❌ Произошла ошибка!", ephemeral=True)

@bot.tree.command(name="развлечения", description="🎮 Развлекательные команды")
async def fun_command(interaction: discord.Interaction):
    embed = Design.create_embed(
        "🎮 РАЗВЛЕКАТЕЛЬНЫЕ КОМАНДЫ",
        "**Доступные развлечения:**\n\n"
        "🎰 **Казино:**\n"
        "`/слоты [ставка]` - Игра в слоты\n"
        "`/рулетка [ставка] [число/цвет]` - Русская рулетка\n\n"
        "🎯 **Игры:**\n" 
        "`/викторина` - Случайная викторина\n"
        "`/угадайчисло` - Угадай число от 1 до 100\n"
        "`/крестики-нолики @игрок` - Игра с другом\n\n"
        "🚀 **Другое:**\n"
        "`/мем` - Случайный мем\n"
        "`/котик` - Милый котик\n"
        "`/собака` - Милая собака\n"
        "`/факт` - Интересный факт",
        "premium"
    )
    await interaction.response.send_message(embed=embed)

# 🚀 ЗАПУСК БОТА
if __name__ == "__main__":
    async def create_missing_tables():
        async with aiosqlite.connect("data/bot.db") as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_stocks (
                    user_id INTEGER,
                    symbol TEXT,
                    quantity INTEGER DEFAULT 0,
                    avg_price REAL,
                    PRIMARY KEY (user_id, symbol)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS clans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    tag TEXT UNIQUE,
                    owner_id INTEGER,
                    created_at TEXT,
                    level INTEGER DEFAULT 1,
                    treasury INTEGER DEFAULT 0
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
                CREATE TABLE IF NOT EXISTS daily_quests (
                    user_id INTEGER,
                    date TEXT,
                    quests_data TEXT,
                    PRIMARY KEY (user_id, date)
                )
            ''')
            
            await db.commit()
    
    asyncio.run(create_missing_tables())
    
    logger.info("🚀 Запуск улучшенного MegaBot...")
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("🔴 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
