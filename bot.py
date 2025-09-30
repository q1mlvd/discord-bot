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

# 🔧 КОНСТАНТЫ
ADMIN_IDS = [1195144951546265675, 766767256742526996, 1078693283695448064, 1138140772097597472, 691904643181314078]
MODERATION_ROLES = [1167093102868172911, 1360243534946373672, 993043931342319636, 1338611327022923910, 1338609155203661915, 1365798715930968244, 1188261847850299514]
THREADS_CHANNEL_ID = 1422557295811887175
EVENTS_CHANNEL_ID = 1418738569081786459

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

# 🔒 ФУНКЦИЯ ПРОВЕРКИ ЭКОНОМИЧЕСКОГО БАНА
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
        "event": 0x9B59B6, "credit": 0xE74C3C
    }

    @staticmethod
    def create_embed(title: str, description: str = "", color: str = "primary"):
        return discord.Embed(title=title, description=description, color=Design.COLORS.get(color, Design.COLORS["primary"]))

# 💾 БАЗА ДАННЫХ (ОБНОВЛЕННАЯ)
class Database:
    def __init__(self):
        self.db_path = "data/bot.db"
        os.makedirs("data", exist_ok=True)
    
    async def init_db(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Основная таблица пользователей
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
                
                # Таблица варнов
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS warnings (
                        user_id INTEGER PRIMARY KEY,
                        warns INTEGER DEFAULT 0,
                        last_updated TEXT
                    )
                ''')
                
                # Таблица кредитов
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
                
                # Таблица майнинг ферм
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS mining_farms (
                        user_id INTEGER PRIMARY KEY,
                        level INTEGER DEFAULT 1,
                        last_collected TEXT,
                        created_at TEXT
                    )
                ''')
                
                # Таблица криптовалют
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS user_crypto (
                        user_id INTEGER,
                        crypto_type TEXT,
                        amount REAL,
                        PRIMARY KEY (user_id, crypto_type)
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
                
                # Индексы для производительности
                await db.execute('CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_credits_due ON user_credits(due_date)')
                
                await db.commit()
                logger.info("✅ База данных инициализирована")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise

    # 🔧 МЕТОДЫ ДЛЯ РАБОТЫ С ДАННЫМИ
    
    async def get_warns(self, user_id: int) -> int:
        """Получить количество варнов пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT warns FROM warnings WHERE user_id = ?', (user_id,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logger.error(f"Ошибка получения варнов для {user_id}: {e}")
            return 0

    async def add_warn(self, user_id: int) -> int:
        """Добавить варн пользователю"""
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
        """Удалить варны пользователю"""
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
        """Получить кредит пользователя"""
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
        """Добавить кредит пользователю"""
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
        """Удалить кредит пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('DELETE FROM user_credits WHERE user_id = ?', (user_id,))
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка удаления кредита для {user_id}: {e}")
            raise

    async def get_mining_farm(self, user_id: int) -> Optional[dict]:
        """Получить майнинг ферму пользователя"""
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
        """Создать майнинг ферму"""
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
        """Обновить майнинг ферму"""
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
        """Получить криптовалюту пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT crypto_type, amount FROM user_crypto WHERE user_id = ?', (user_id,)) as cursor:
                    return {row[0]: row[1] for row in await cursor.fetchall()}
        except Exception as e:
            logger.error(f"Ошибка получения крипты для {user_id}: {e}")
            return {}

    async def update_user_crypto(self, user_id: int, crypto_type: str, amount: float):
        """Обновить криптовалюту пользователя"""
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

# 🏦 СИСТЕМА КРЕДИТОВ (ОБНОВЛЕННАЯ)
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
        # Проверяем есть ли активный кредит через БД
        existing_credit = await self.db.get_credit(user_id)
        if existing_credit:
            return False, "У вас уже есть активный кредит"
        
        company_data = self.companies.get(company)
        if not company_data:
            return False, "Компания не найдена"
        
        if amount < company_data["min_amount"] or amount > company_data["max_amount"]:
            return False, f"Сумма должна быть от {company_data['min_amount']} до {company_data['max_amount']}"
        
        due_date = datetime.now() + timedelta(days=company_data["term_days"])
        
        # Сохраняем в БД
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

# 🎁 СИСТЕМА ЛУТБОКСОВ (ОБНОВЛЕННАЯ)
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
                    crypto_type = random.choice(list(crypto_prices.keys()))
                    amount = random.uniform(reward["min"], reward["max"])
                    
                    # Получаем текущую крипту из БД
                    user_crypto_data = await self.db.get_user_crypto(user_id)
                    current_amount = user_crypto_data.get(crypto_type, 0)
                    new_amount = current_amount + amount
                    
                    # Сохраняем в БД
                    await self.db.update_user_crypto(user_id, crypto_type, new_amount)
                    rewards.append(f"₿ {amount:.4f} {crypto_type}")
        
        if not rewards:
            rewards.append("💔 Не повезло... Попробуй еще раз!")
        
        return True, rewards

# 🔧 СИСТЕМА МАЙНИНГА (ОБНОВЛЕННАЯ)
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
            
            # Обновляем время сбора в БД
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
        
        active_events[event_type] = {
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

# 🏗️ ГЛАВНЫЙ БОТ (ОБНОВЛЕННЫЙ)
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

    async def reload_bot(self):
        try:
            synced = await self.tree.sync()
            logger.info(f"♻️ Бот перезагружен! Синхронизировано {len(synced)} команд")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка перезагрузки: {e}")
            return False

    async def close(self):
        """Закрытие соединений при выключении бота"""
        logger.info("🔴 Бот выключается...")
        await super().close()

bot = MegaBot()

# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def parse_time(time_str: str) -> int:
    time_units = {
        'с': 1, 'сек': 1, 'секунд': 1,
        'м': 60, 'мин': 60, 'минут': 60, 
        'ч': 3600, 'час': 3600, 'часов': 3600,
        'д': 86400, 'день': 86400, 'дней': 86400
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

# 💰 КОМАНДЫ ДЛЯ ВСЕХ УЧАСТНИКОВ (ОБНОВЛЕННЫЕ)
@bot.tree.command(name="баланс", description="Проверить баланс")
async def баланс(interaction: discord.Interaction, пользователь: Optional[discord.Member] = None):
    try:
        user = пользователь or interaction.user
        balance = await bot.economy.get_balance(user.id)
        embed = Design.create_embed("💰 Баланс", f"**{user.display_name}**\nБаланс: `{balance:,} монет`", "economy")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Ошибка в команде баланс: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при получении баланса", ephemeral=True)

@bot.tree.command(name="ежедневно", description="Получить ежедневную награду")
@check_economic_ban()
async def ежедневно(interaction: discord.Interaction):
    try:
        user_data = await bot.economy.get_user_data(interaction.user.id)
        
        if user_data["daily_claimed"]:
            last_claim = datetime.fromisoformat(user_data["daily_claimed"])
            if (datetime.now() - last_claim).days < 1:
                embed = Design.create_embed("⏳ Уже получали!", "Приходите завтра", "warning")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        reward = random.randint(100, 500)
        new_balance = await bot.economy.update_balance(interaction.user.id, reward)
        
        async with aiosqlite.connect(bot.db.db_path) as db:
            await db.execute('UPDATE users SET daily_claimed = ? WHERE user_id = ?', (datetime.now().isoformat(), interaction.user.id))
            await db.commit()
        
        embed = Design.create_embed("🎁 Ежедневная награда", f"**+{reward} монет!**\nБаланс: `{new_balance:,} монет`", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Ошибка в команде ежедневно: {e}")
        embed = Design.create_embed("❌ Ошибка", "Не удалось получить награду", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# 🛡️ КОМАНДЫ МОДЕРАЦИИ (ОБНОВЛЕННЫЕ)
@bot.tree.command(name="пред", description="Выдать предупреждение")
@is_moderator()
async def пред(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    try:
        target_roles = [role.id for role in пользователь.roles]
        if any(role_id in MODERATION_ROLES for role_id in target_roles) or пользователь.id in ADMIN_IDS:
            await interaction.response.send_message("❌ Нельзя выдать предупреждение модератору или администратору!", ephemeral=True)
            return
        
        current_warns = await bot.db.add_warn(пользователь.id)
        
        embed = Design.create_embed("⚠️ Предупреждение", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Причина:** {причина}\n"
                                  f"**Текущие пред:** {current_warns}/3", "warning")
        await interaction.response.send_message(embed=embed)
            
    except Exception as e:
        logger.error(f"Ошибка в команде пред: {e}")
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="снять_пред", description="Снять предупреждение")
@is_moderator()
async def снять_пред(interaction: discord.Interaction, пользователь: discord.Member, количество: int = 1):
    try:
        target_roles = [role.id for role in пользователь.roles]
        if any(role_id in MODERATION_ROLES for role_id in target_roles) or пользователь.id in ADMIN_IDS:
            await interaction.response.send_message("❌ Нельзя снять предупреждение с модератора или администратора!", ephemeral=True)
            return
        
        current_warns = await bot.db.get_warns(пользователь.id)
        if current_warns <= 0:
            await interaction.response.send_message("❌ У пользователя нет предупреждений!", ephemeral=True)
            return
        
        if количество <= 0:
            await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
            return
        
        new_warns = await bot.db.remove_warns(пользователь.id, количество)
        
        embed = Design.create_embed("✅ Предупреждение снято", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Снято предупреждений:** {min(количество, current_warns)}\n"
                                  f"**Текущие пред:** {new_warns}/3", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Ошибка в команде снять_пред: {e}")
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

# 🏦 КОМАНДЫ КРЕДИТОВ (ОБНОВЛЕННЫЕ)
@bot.tree.command(name="кредит", description="Взять кредит")
async def кредит(interaction: discord.Interaction):
    try:
        embed = Design.create_embed("🏦 КРЕДИТЫ", "Используйте кнопки ниже для взятия кредита:", "credit")
        
        for company_id, company in bot.credit_system.companies.items():
            embed.add_field(
                name=f"{company['name']}",
                value=f"Сумма: {company['min_amount']:,}-{company['max_amount']:,} монет\n"
                      f"Процент: {company['interest_rate']}%\n"
                      f"Срок: {company['term_days']} дней",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Ошибка в команде кредит: {e}")
        await interaction.response.send_message("❌ Произошла ошибка", ephemeral=True)

@bot.tree.command(name="вернуть_кредит", description="Вернуть кредит")
async def вернуть_кредит(interaction: discord.Interaction):
    try:
        success, message = await bot.credit_system.repay_credit(interaction.user.id)
        
        if success:
            embed = Design.create_embed("✅ Кредит погашен!", message, "success")
        else:
            embed = Design.create_embed("❌ Ошибка", message, "danger")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Ошибка в команде вернуть_кредит: {e}")
        embed = Design.create_embed("❌ Ошибка", "Произошла ошибка при возврате кредита", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="мой_кредит", description="Информация о кредите")
async def мой_кредит(interaction: discord.Interaction):
    try:
        credit = await bot.db.get_credit(interaction.user.id)
        if not credit:
            await interaction.response.send_message("❌ У вас нет активных кредитов", ephemeral=True)
            return
        
        company = bot.credit_system.companies[credit["company"]]
        days_left = (credit["due_date"] - datetime.now()).days
        
        embed = Design.create_embed("🏦 Мой кредит", 
                                  f"**Компания:** {company['name']}\n"
                                  f"**Сумма:** {credit['original_amount']:,} монет\n"
                                  f"**Процент:** {credit['interest_rate']}%\n"
                                  f"**Вернуть до:** {credit['due_date'].strftime('%d.%m.%Y')}\n"
                                  f"**Осталось дней:** {max(0, days_left)}", "credit")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Ошибка в команде мой_кредит: {e}")
        await interaction.response.send_message("❌ Произошла ошибка", ephemeral=True)

# ⛏️ КОМАНДЫ МАЙНИНГА (ОБНОВЛЕННЫЕ)
@bot.tree.command(name="ферма", description="Информация о ферме")
async def ферма(interaction: discord.Interaction):
    try:
        farm = await bot.db.get_mining_farm(interaction.user.id)
        
        if not farm:
            embed = Design.create_embed("⛏️ Майнинг ферма", 
                                      "У вас еще нет фермы!\nИспользуйте `/создать_ферму` чтобы начать майнить", "info")
        else:
            level_data = bot.mining_system.farm_levels[farm["level"]]
            
            can_collect = True
            time_left = "✅ Можно собрать"
            
            if farm.get("last_collected"):
                last_collect = farm["last_collected"]
                time_passed = datetime.now() - last_collect
                if time_passed.total_seconds() < 21600:
                    can_collect = False
                    hours_left = 5 - int(time_passed.total_seconds() // 3600)
                    minutes_left = 59 - int((time_passed.total_seconds() % 3600) // 60)
                    time_left = f"⏳ Через {hours_left}ч {minutes_left}м"
            
            embed = Design.create_embed("⛏️ Ваша ферма", 
                                      f"**Уровень:** {farm['level']}\n"
                                      f"**Доход:** {level_data['income']} монет/6ч\n"
                                      f"**Следующий уровень:** {level_data['upgrade_cost']} монет\n"
                                      f"**Статус:** {time_left}", "info")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Ошибка в команде ферма: {e}")
        await interaction.response.send_message("❌ Произошла ошибка", ephemeral=True)

@bot.tree.command(name="создать_ферму", description="Создать ферму")
async def создать_ферму(interaction: discord.Interaction):
    try:
        farm = await bot.db.get_mining_farm(interaction.user.id)
        if farm:
            await interaction.response.send_message("❌ У вас уже есть ферма!", ephemeral=True)
            return
        
        creation_cost = 500
        balance = await bot.economy.get_balance(interaction.user.id)
        
        if balance < creation_cost:
            await interaction.response.send_message(f"❌ Недостаточно средств! Нужно {creation_cost} монет", ephemeral=True)
            return
        
        await bot.economy.update_balance(interaction.user.id, -creation_cost)
        await bot.db.create_mining_farm(interaction.user.id)
        
        embed = Design.create_embed("✅ Ферма создана!", 
                                  f"Ваша майнинг ферма уровня 1 готова к работе!\n"
                                  f"Стоимость создания: {creation_cost} монет", "success")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Ошибка в команде создать_ферму: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при создании фермы", ephemeral=True)

@bot.tree.command(name="собрать_доход", description="Собрать доход с фермы")
async def собрать_доход(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    try:
        success, message = await bot.mining_system.collect_income(interaction.user.id)
        
        if success:
            embed = Design.create_embed("💰 Доход собран!", message, "success")
        else:
            embed = Design.create_embed("❌ Ошибка", message, "danger")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Ошибка в команде собрать_доход: {e}")
        embed = Design.create_embed("❌ Ошибка", "Произошла ошибка при сборе дохода", "danger")
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="улучшить_ферму", description="Улучшить ферму")
async def улучшить_ферму(interaction: discord.Interaction):
    try:
        farm = await bot.db.get_mining_farm(interaction.user.id)
        if not farm:
            await interaction.response.send_message("❌ У вас нет фермы!", ephemeral=True)
            return
        
        current_level = farm["level"]
        
        if current_level >= 3:
            await interaction.response.send_message("❌ Ваша ферма уже максимального уровня!", ephemeral=True)
            return
        
        upgrade_cost = bot.mining_system.farm_levels[current_level]["upgrade_cost"]
        balance = await bot.economy.get_balance(interaction.user.id)
        
        if balance < upgrade_cost:
            await interaction.response.send_message(f"❌ Недостаточно средств! Нужно {upgrade_cost} монет", ephemeral=True)
            return
        
        await bot.economy.update_balance(interaction.user.id, -upgrade_cost)
        await bot.db.update_mining_farm(interaction.user.id, level=current_level + 1)
        
        embed = Design.create_embed("⚡ Ферма улучшена!", 
                                  f"Уровень фермы повышен до {current_level + 1}!\n"
                                  f"Новый доход: {bot.mining_system.farm_levels[current_level + 1]['income']} монет/6ч", "success")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Ошибка в команде улучшить_ферму: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при улучшении фермы", ephemeral=True)

# ₿ КОМАНДЫ КРИПТОВАЛЮТЫ (ОБНОВЛЕННЫЕ)
@bot.tree.command(name="крипта", description="Курсы криптовалют")
async def крипта(interaction: discord.Interaction):
    try:
        embed = Design.create_embed("₿ КРИПТОВАЛЮТЫ", "Актуальные курсы:", "crypto")
        
        for crypto, price in bot.crypto_prices.items():
            embed.add_field(
                name=crypto,
                value=f"${price:,.2f}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Ошибка в команде крипта: {e}")
        await interaction.response.send_message("❌ Произошла ошибка", ephemeral=True)

@bot.tree.command(name="мой_крипто", description="Мой крипто-портфель")
async def мой_крипто(interaction: discord.Interaction):
    try:
        user_crypto_data = await bot.db.get_user_crypto(interaction.user.id)
        
        if not user_crypto_data:
            await interaction.response.send_message("❌ У вас нет криптовалюты", ephemeral=True)
            return
        
        embed = Design.create_embed("₿ Мой крипто-портфель", "", "crypto")
        total_value = 0
        
        for crypto, amount in user_crypto_data.items():
            value = amount * bot.crypto_prices[crypto]
            total_value += value
            embed.add_field(
                name=crypto,
                value=f"Количество: {amount:.4f}\nСтоимость: ${value:.2f}",
                inline=True
            )
        
        embed.add_field(
            name="💰 Общая стоимость",
            value=f"${total_value:.2f}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Ошибка в команде мой_крипто: {e}")
        await interaction.response.send_message("❌ Произошла ошибка", ephemeral=True)

# 🎪 КОМАНДЫ ИВЕНТОВ
@bot.tree.command(name="ивенты", description="Активные ивенты")
async def ивенты(interaction: discord.Interaction):
    try:
        if not bot.active_events:
            embed = Design.create_embed("🎪 Ивенты", "Сейчас нет активных ивентов", "info")
        else:
            embed = Design.create_embed("🎪 АКТИВНЫЕ ИВЕНТЫ", "", "event")
            for event_type, event_data in bot.active_events.items():
                time_left = event_data["end_time"] - datetime.now()
                minutes_left = max(0, int(time_left.total_seconds() // 60))
                
                embed.add_field(
                    name=bot.event_system.event_types[event_type]["name"],
                    value=f"Осталось: {minutes_left} минут\n{bot.event_system.event_types[event_type]['description']}",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Ошибка в команде ивенты: {e}")
        await interaction.response.send_message("❌ Произошла ошибка", ephemeral=True)

# 👑 АДМИН КОМАНДЫ
@bot.tree.command(name="выдать", description="Выдать монеты")
@is_admin()
async def выдать(interaction: discord.Interaction, пользователь: discord.Member, количество: int):
    try:
        if количество <= 0:
            await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
            return
        
        new_balance = await bot.economy.admin_add_money(пользователь.id, количество)
        
        embed = Design.create_embed("💰 Деньги выданы", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Выдано:** {количество:,} монет\n"
                                  f"**Новый баланс:** {new_balance:,} монет", "success")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Ошибка в команде выдать: {e}")
        await interaction.response.send_message("❌ Произошла ошибка", ephemeral=True)

@bot.tree.command(name="удалить_бд", description="Удалить базу данных")
@is_admin()
async def удалить_бд(interaction: discord.Interaction):
    try:
        import os
        if os.path.exists("data/bot.db"):
            os.remove("data/bot.db")
            await bot.db.init_db()
            embed = Design.create_embed("✅ База данных удалена", "Все данные сброшены!", "success")
        else:
            embed = Design.create_embed("ℹ️ База не найдена", "Файл data/bot.db не существует", "info")
    except Exception as e:
        logger.error(f"Ошибка в команде удалить_бд: {e}")
        embed = Design.create_embed("❌ Ошибка", f"Не удалось удалить БД: {e}", "danger")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="админ", description="Панель администратора")
@is_admin()
async def админ(interaction: discord.Interaction):
    try:
        description = (
            "**АДМИН КОМАНДЫ:**\n\n"
            "**Экономика:**\n"
            "`/выдать @user количество` - Выдать монеты\n\n"
            "**Управление:**\n"
            "`/удалить_бд` - Очистить базу данных\n"
            "`/перезагрузить` - Перезагрузить бота\n"
            "`/запустить_ивент тип` - Запустить ивент"
        )
        
        embed = Design.create_embed("ПАНЕЛЬ АДМИНИСТРАТОРА", description, "premium")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Ошибка в команде админ: {e}")
        await interaction.response.send_message("❌ Произошла ошибка", ephemeral=True)

@bot.tree.command(name="перезагрузить", description="Перезагрузить бота")
@is_admin()
async def перезагрузить(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    try:
        embed = Design.create_embed("🔄 Перезагрузка бота", "Выполняется перезагрузка...", "warning")
        await interaction.followup.send(embed=embed)
        
        success = await bot.reload_bot()
        
        if success:
            embed = Design.create_embed("✅ Перезагрузка завершена", "Бот успешно перезагружен!", "success")
        else:
            embed = Design.create_embed("❌ Ошибка перезагрузки", "Произошла ошибка при перезагрузке", "danger")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Ошибка в команде перезагрузить: {e}")
        await interaction.followup.send("❌ Произошла ошибка при перезагрузке", ephemeral=True)

# 🔧 ОБРАБОТЧИКИ СОБЫТИЙ С ЛОГИРОВАНИЕМ
@bot.event
async def on_ready():
    logger.info(f'✅ Бот {bot.user} запущен!')
    logger.info(f'🌐 Серверов: {len(bot.guilds)}')
    
    try:
        synced = await bot.tree.sync()
        logger.info(f'✅ Синхронизировано {len(synced)} команд')
    except Exception as e:
        logger.error(f'❌ Ошибка синхронизации: {e}')

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f'Ошибка в событии {event}: {args} {kwargs}')
    logger.error(traceback.format_exc())

@bot.event
async def on_command_error(ctx, error):
    logger.error(f'Ошибка команды {ctx.command}: {error}')
    logger.error(traceback.format_exc())

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if isinstance(message.channel, discord.TextChannel):
        try:
            async with aiosqlite.connect(bot.db.db_path) as db:
                await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.author.id,))
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя {message.author.id}: {e}")
    
    await bot.process_commands(message)

if __name__ == "__main__":
    try:
        logger.info("🚀 Запуск бота...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("\n🛑 Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {e}")
        logger.error(traceback.format_exc())
