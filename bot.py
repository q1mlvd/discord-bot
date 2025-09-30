import discord
from discord.ext import commands, tasks
from discord.app_commands import check
import aiosqlite
import asyncio
from datetime import datetime, timedelta
import os
import random
from typing import Optional
from dotenv import load_dotenv
import yt_dlp

# 🔧 КОНСТАНТЫ
ADMIN_IDS = [1195144951546265675, 766767256742526996, 1078693283695448064, 1138140772097597472, 691904643181314078]
MODERATION_ROLES = [1167093102868172911, 1360243534946373672, 993043931342319636, 1338611327022923910, 1338609155203661915, 1365798715930968244, 1188261847850299514]
THREADS_CHANNEL_ID = 1422557295811887175
EVENTS_CHANNEL_ID = 1418738569081786459

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
        "discord": 0x5865F2, "tds": 0xF1C40F, "crypto": 0x16C60C,
        "event": 0x9B59B6, "credit": 0xE74C3C
    }

    @staticmethod
    def create_embed(title: str, description: str = "", color: str = "primary"):
        return discord.Embed(title=title, description=description, color=Design.COLORS.get(color, Design.COLORS["primary"]))

# 🔒 ФУНКЦИИ ПРОВЕРКИ ПРАВ
def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id in ADMIN_IDS
    return check(predicate)

def is_moderator():
    async def predicate(interaction: discord.Interaction) -> bool:
        user_roles = [role.id for role in interaction.user.roles]
        return any(role_id in MODERATION_ROLES for role_id in user_roles)
    return check(predicate)

def check_economic_ban():
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            async with aiosqlite.connect("data/bot.db") as db:
                async with db.execute(
                    'SELECT end_time FROM economic_bans WHERE user_id = ? AND end_time > ?',
                    (interaction.user.id, datetime.utcnow().isoformat())
                ) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        end_time = datetime.fromisoformat(result[0])
                        time_left = end_time - datetime.utcnow()
                        hours_left = int(time_left.total_seconds() // 3600)
                        minutes_left = int((time_left.total_seconds() % 3600) // 60)
                        
                        embed = Design.create_embed(
                            "🚫 Экономика заблокирована",
                            f"**Причина:** Просрочка кредита\n"
                            f"**Разблокировка через:** {hours_left}ч {minutes_left}м\n"
                            f"**Заблокированы:** /работа, /ежедневно, /передать, /ограбить, /слоты",
                            "danger"
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return False
            return True
        except Exception as e:
            print(f"Ошибка проверки экономического бана: {e}")
            return True
    return check(predicate)

# 💾 БАЗА ДАННЫХ
class Database:
    def __init__(self):
        self.db_path = "data/bot.db"
        self.connection = None
        os.makedirs("data", exist_ok=True)
    
    async def get_connection(self):
        if self.connection is None:
            self.connection = await aiosqlite.connect(self.db_path)
            self.connection.row_factory = aiosqlite.Row
        return self.connection
    
    async def close(self):
        if self.connection:
            await self.connection.close()
            self.connection = None
    
    async def init_db(self):
        conn = await self.get_connection()
        
        # Основная таблица пользователей
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 1000,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                daily_claimed TEXT,
                work_cooldown TEXT
            )
        ''')
        
        # Инвентарь
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_id INTEGER,
                quantity INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, item_id)
            )
        ''')
        
        # Заказы
        await conn.execute('DROP TABLE IF EXISTS orders')
        await conn.execute('''
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
        
        # Кредиты
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_credits (
                user_id INTEGER PRIMARY KEY,
                company TEXT,
                amount INTEGER,
                interest_rate INTEGER,
                due_date TEXT,
                original_amount INTEGER
            )
        ''')
        
        # Фермы для майнинга
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS mining_farms (
                user_id INTEGER PRIMARY KEY,
                level INTEGER DEFAULT 1,
                last_collected TEXT,
                created_at TEXT
            )
        ''')
        
        # Предупреждения
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_warns (
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                timestamp TEXT,
                id INTEGER PRIMARY KEY AUTOINCREMENT
            )
        ''')
        
        # Криптовалюта
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_crypto (
                user_id INTEGER,
                crypto_type TEXT,
                amount REAL,
                PRIMARY KEY (user_id, crypto_type)
            )
        ''')
        
        # Экономические баны
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS economic_bans (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                end_time TEXT
            )
        ''')
        
        # Коулдауны ограблений
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS rob_cooldowns (
                user_id INTEGER PRIMARY KEY,
                last_rob_time TEXT
            )
        ''')
        
        # Активные ивенты
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS active_events (
                event_type TEXT PRIMARY KEY,
                start_time TEXT,
                end_time TEXT,
                event_data TEXT
            )
        ''')
        
        await conn.commit()
        print("✅ База данных инициализирована")

# 💰 ЭКОНОМИКА
class EconomySystem:
    def __init__(self, db: Database):
        self.db = db

    async def get_balance(self, user_id: int) -> int:
        try:
            conn = await self.db.get_connection()
            async with conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return result['balance']
                else:
                    await conn.execute('INSERT INTO users (user_id, balance) VALUES (?, 1000)', (user_id,))
                    await conn.commit()
                    return 1000
        except Exception as e:
            print(f"Ошибка получения баланса: {e}")
            return 1000
    
    async def update_balance(self, user_id: int, amount: int) -> int:
        try:
            conn = await self.db.get_connection()
            await conn.execute('INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 1000)', (user_id,))
            await conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            await conn.commit()
            return await self.get_balance(user_id)
        except Exception as e:
            print(f"Ошибка обновления баланса: {e}")
            return 1000
    
    async def get_user_data(self, user_id: int) -> dict:
        try:
            conn = await self.db.get_connection()
            async with conn.execute(
                'SELECT balance, level, xp, daily_claimed, work_cooldown FROM users WHERE user_id = ?', 
                (user_id,)
            ) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        "balance": result['balance'],
                        "level": result['level'],
                        "xp": result['xp'],
                        "daily_claimed": result['daily_claimed'],
                        "work_cooldown": result['work_cooldown']
                    }
                else:
                    await conn.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
                    await conn.commit()
                    return {"balance": 1000, "level": 1, "xp": 0, "daily_claimed": None, "work_cooldown": None}
        except Exception as e:
            print(f"Ошибка получения данных пользователя: {e}")
            return {"balance": 1000, "level": 1, "xp": 0, "daily_claimed": None, "work_cooldown": None}

    async def admin_add_money(self, user_id: int, amount: int) -> int:
        try:
            if amount <= 0:
                raise ValueError("Сумма должна быть положительной")
                
            conn = await self.db.get_connection()
            await conn.execute('INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 1000)', (user_id,))
            await conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            await conn.commit()
            return await self.get_balance(user_id)
        except Exception as e:
            print(f"Ошибка выдачи денег: {e}")
            raise

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
    
    async def take_credit(self, user_id: int, company: str, amount: int) -> tuple[bool, str]:
        try:
            conn = await self.db.get_connection()
            
            # Проверка активного кредита
            async with conn.execute('SELECT * FROM user_credits WHERE user_id = ?', (user_id,)) as cursor:
                if await cursor.fetchone():
                    return False, "У вас уже есть активный кредит"
            
            company_data = self.companies.get(company)
            if not company_data:
                return False, "Компания не найдена"
            
            if amount < company_data["min_amount"] or amount > company_data["max_amount"]:
                return False, f"Сумма должна быть от {company_data['min_amount']} до {company_data['max_amount']}"
            
            due_date = datetime.utcnow() + timedelta(days=company_data["term_days"])
            
            await conn.execute(
                'INSERT INTO user_credits (user_id, company, amount, interest_rate, due_date, original_amount) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, company, amount, company_data["interest_rate"], due_date.isoformat(), amount)
            )
            await conn.commit()
            
            await self.economy.update_balance(user_id, amount)
            return True, f"Кредит одобрен! Вернуть до {due_date.strftime('%d.%m.%Y')}"
            
        except Exception as e:
            print(f"Ошибка взятия кредита: {e}")
            return False, "Произошла ошибка при взятии кредита"

    async def repay_credit(self, user_id: int) -> tuple[bool, str]:
        try:
            conn = await self.db.get_connection()
            async with conn.execute('SELECT * FROM user_credits WHERE user_id = ?', (user_id,)) as cursor:
                credit_data = await cursor.fetchone()
                if not credit_data:
                    return False, "У вас нет активных кредитов"
            
            total_to_repay = credit_data['amount']
            balance = await self.economy.get_balance(user_id)
            
            if balance < total_to_repay:
                return False, f"Недостаточно средств. Нужно: {total_to_repay} монет"
            
            await self.economy.update_balance(user_id, -total_to_repay)
            await conn.execute('DELETE FROM user_credits WHERE user_id = ?', (user_id,))
            await conn.commit()
            
            return True, f"Кредит погашен! Сумма: {total_to_repay} монет"
            
        except Exception as e:
            print(f"Ошибка погашения кредита: {e}")
            return False, "Произошла ошибка при погашении кредита"

    async def get_user_credit(self, user_id: int) -> Optional[dict]:
        try:
            conn = await self.db.get_connection()
            async with conn.execute('SELECT * FROM user_credits WHERE user_id = ?', (user_id,)) as cursor:
                credit_data = await cursor.fetchone()
                if credit_data:
                    return dict(credit_data)
            return None
        except Exception as e:
            print(f"Ошибка получения кредита: {e}")
            return None

    async def check_overdue_credits(self):
        try:
            conn = await self.db.get_connection()
            current_time = datetime.utcnow().isoformat()
            
            async with conn.execute(
                'SELECT * FROM user_credits WHERE due_date < ?', 
                (current_time,)
            ) as cursor:
                overdue_credits = await cursor.fetchall()
                
                for credit in overdue_credits:
                    user_id = credit['user_id']
                    company_data = self.companies[credit['company']]
                    penalty_duration = 48  # 2 дня в часах
                    
                    # Добавляем экономический бан
                    end_time = datetime.utcnow() + timedelta(hours=penalty_duration)
                    await conn.execute(
                        'INSERT OR REPLACE INTO economic_bans (user_id, reason, end_time) VALUES (?, ?, ?)',
                        (user_id, f"Просрочка кредита: {company_data['name']}", end_time.isoformat())
                    )
                    
                    print(f"Пользователь {user_id} получил экономический бан за просрочку кредита")
            
            await conn.commit()
            
        except Exception as e:
            print(f"Ошибка проверки просроченных кредитов: {e}")

# 🎁 СИСТЕМА ЛУТБОКСОВ
class LootboxSystem:
    def __init__(self, economy: EconomySystem):
        self.economy = economy
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
    
    async def open_lootbox(self, user_id: int, lootbox_type: str) -> tuple[bool, list]:
        try:
            lootbox = self.lootboxes.get(lootbox_type)
            if not lootbox:
                return False, []
            
            balance = await self.economy.get_balance(user_id)
            if balance < lootbox["price"]:
                return False, []
            
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
                        await self._add_crypto(user_id, crypto_type, amount)
                        rewards.append(f"₿ {amount:.4f} {crypto_type}")
            
            if not rewards:
                rewards.append("💔 Не повезло... Попробуй еще раз!")
            
            return True, rewards
            
        except Exception as e:
            print(f"Ошибка открытия лутбокса: {e}")
            return False, ["Произошла ошибка при открытии лутбокса"]

    async def _add_crypto(self, user_id: int, crypto_type: str, amount: float):
        try:
            conn = await self.db.get_connection()
            await conn.execute(
                'INSERT INTO user_crypto (user_id, crypto_type, amount) VALUES (?, ?, ?) '
                'ON CONFLICT(user_id, crypto_type) DO UPDATE SET amount = amount + excluded.amount',
                (user_id, crypto_type, amount)
            )
            await conn.commit()
        except Exception as e:
            print(f"Ошибка добавления криптовалюты: {e}")

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
    
    async def get_user_farm(self, user_id: int) -> Optional[dict]:
        try:
            conn = await self.db.get_connection()
            async with conn.execute('SELECT * FROM mining_farms WHERE user_id = ?', (user_id,)) as cursor:
                farm_data = await cursor.fetchone()
                if farm_data:
                    return dict(farm_data)
            return None
        except Exception as e:
            print(f"Ошибка получения фермы: {e}")
            return None
    
    async def create_farm(self, user_id: int) -> bool:
        try:
            conn = await self.db.get_connection()
            await conn.execute(
                'INSERT INTO mining_farms (user_id, level, created_at) VALUES (?, 1, ?)',
                (user_id, datetime.utcnow().isoformat())
            )
            await conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка создания фермы: {e}")
            return False
    
    async def upgrade_farm(self, user_id: int) -> tuple[bool, str]:
        try:
            farm = await self.get_user_farm(user_id)
            if not farm:
                return False, "У вас нет фермы"
            
            current_level = farm['level']
            if current_level >= 3:
                return False, "Ваша ферма уже максимального уровня"
            
            upgrade_cost = self.farm_levels[current_level]["upgrade_cost"]
            balance = await self.economy.get_balance(user_id)
            
            if balance < upgrade_cost:
                return False, f"Недостаточно средств! Нужно {upgrade_cost} монет"
            
            await self.economy.update_balance(user_id, -upgrade_cost)
            
            conn = await self.db.get_connection()
            await conn.execute(
                'UPDATE mining_farms SET level = ? WHERE user_id = ?',
                (current_level + 1, user_id)
            )
            await conn.commit()
            
            return True, f"Ферма улучшена до уровня {current_level + 1}!"
            
        except Exception as e:
            print(f"Ошибка улучшения фермы: {e}")
            return False, "Произошла ошибка при улучшении фермы"
    
    async def collect_income(self, user_id: int) -> tuple[bool, str]:
        try:
            farm = await self.get_user_farm(user_id)
            if not farm:
                return False, "У вас нет фермы"
            
            if farm.get('last_collected'):
                last_collect = datetime.fromisoformat(farm['last_collected'])
                time_passed = datetime.utcnow() - last_collect
                if time_passed.total_seconds() < 21600:  # 6 часов
                    hours_left = 5 - int(time_passed.total_seconds() // 3600)
                    minutes_left = 59 - int((time_passed.total_seconds() % 3600) // 60)
                    return False, f"Доход можно собирать раз в 6 часов! Осталось: {hours_left}ч {minutes_left}м"
            
            income = self.farm_levels[farm['level']]["income"]
            await self.economy.update_balance(user_id, income)
            
            conn = await self.db.get_connection()
            await conn.execute(
                'UPDATE mining_farms SET last_collected = ? WHERE user_id = ?',
                (datetime.utcnow().isoformat(), user_id)
            )
            await conn.commit()
            
            return True, f"✅ Собрано {income} монет с фермы! Следующий сбор через 6 часов"
            
        except Exception as e:
            print(f"Ошибка сбора дохода: {e}")
            return False, "❌ Произошла ошибка при сборе дохода"

# 🎪 СИСТЕМА ИВЕНТОВ
class EventSystem:
    def __init__(self, economy: EconomySystem, db: Database):
        self.economy = economy
        self.db = db
        self.event_types = {
            "money_rain": {
                "name": "💰 Денежный дождь", 
                "duration": 300, 
                "multiplier": 2,
                "description": "ВСЕ денежные операции приносят в 2 раза больше монет!"
            }
        }
    
    async def start_event(self, event_type: str, bot_instance) -> bool:
        try:
            event = self.event_types.get(event_type)
            if not event:
                return False
            
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(seconds=event["duration"])
            
            conn = await self.db.get_connection()
            await conn.execute(
                'INSERT OR REPLACE INTO active_events (event_type, start_time, end_time, event_data) VALUES (?, ?, ?, ?)',
                (event_type, start_time.isoformat(), end_time.isoformat(), str(event))
            )
            await conn.commit()
            
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
                print(f"❌ Ошибка отправки ивента: {e}")
            
            return True
            
        except Exception as e:
            print(f"Ошибка запуска ивента: {e}")
            return False

    async def get_active_events(self) -> dict:
        try:
            conn = await self.db.get_connection()
            async with conn.execute('SELECT * FROM active_events WHERE end_time > ?', 
                                  (datetime.utcnow().isoformat(),)) as cursor:
                events = await cursor.fetchall()
                return {event['event_type']: dict(event) for event in events}
        except Exception as e:
            print(f"Ошибка получения активных ивентов: {e}")
            return {}

# 🎰 КАЗИНО
class CasinoSystem:
    def __init__(self, economy: EconomySystem):
        self.economy = economy
    
    async def play_slots(self, user_id: int, bet: int) -> dict:
        try:
            if bet <= 0:
                return {"success": False, "error": "Ставка должна быть положительной!"}
            
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
            
        except Exception as e:
            print(f"Ошибка игры в слоты: {e}")
            return {"success": False, "error": "Произошла ошибка при игре"}

# ⚠️ СИСТЕМА ПРЕДУПРЕЖДЕНИЙ
class WarnSystem:
    def __init__(self, db: Database):
        self.db = db
    
    async def add_warn(self, user_id: int, moderator_id: int, reason: str) -> int:
        try:
            conn = await self.db.get_connection()
            await conn.execute(
                'INSERT INTO user_warns (user_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?)',
                (user_id, moderator_id, reason, datetime.utcnow().isoformat())
            )
            await conn.commit()
            
            # Получаем общее количество предупреждений
            async with conn.execute(
                'SELECT COUNT(*) as count FROM user_warns WHERE user_id = ?', 
                (user_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result['count']
                
        except Exception as e:
            print(f"Ошибка добавления предупреждения: {e}")
            return 0
    
    async def remove_warns(self, user_id: int, count: int) -> tuple[int, int]:
        try:
            conn = await self.db.get_connection()
            
            # Получаем текущее количество
            async with conn.execute(
                'SELECT COUNT(*) as count FROM user_warns WHERE user_id = ?', 
                (user_id,)
            ) as cursor:
                current_count = (await cursor.fetchone())['count']
            
            # Удаляем указанное количество
            if current_count > 0:
                await conn.execute(
                    'DELETE FROM user_warns WHERE user_id = ? LIMIT ?',
                    (user_id, min(count, current_count))
                )
                await conn.commit()
                
                # Получаем новое количество
                async with conn.execute(
                    'SELECT COUNT(*) as count FROM user_warns WHERE user_id = ?', 
                    (user_id,)
                ) as cursor:
                    new_count = (await cursor.fetchone())['count']
                
                return new_count, min(count, current_count)
            return current_count, 0
            
        except Exception as e:
            print(f"Ошибка удаления предупреждений: {e}")
            return 0, 0
    
    async def get_warn_count(self, user_id: int) -> int:
        try:
            conn = await self.db.get_connection()
            async with conn.execute(
                'SELECT COUNT(*) as count FROM user_warns WHERE user_id = ?', 
                (user_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result['count']
        except Exception as e:
            print(f"Ошибка получения количества предупреждений: {e}")
            return 0

# ₿ СИСТЕМА КРИПТОВАЛЮТЫ
class CryptoSystem:
    def __init__(self, db: Database):
        self.db = db
        self.prices = {"BITCOIN": 50000, "ETHEREUM": 3000, "DOGECOIN": 0.15}
    
    async def get_user_crypto(self, user_id: int) -> dict:
        try:
            conn = await self.db.get_connection()
            async with conn.execute(
                'SELECT crypto_type, amount FROM user_crypto WHERE user_id = ?', 
                (user_id,)
            ) as cursor:
                crypto_data = await cursor.fetchall()
                return {row['crypto_type']: row['amount'] for row in crypto_data}
        except Exception as e:
            print(f"Ошибка получения криптовалюты: {e}")
            return {}
    
    async def add_crypto(self, user_id: int, crypto_type: str, amount: float):
        try:
            conn = await self.db.get_connection()
            await conn.execute(
                'INSERT INTO user_crypto (user_id, crypto_type, amount) VALUES (?, ?, ?) '
                'ON CONFLICT(user_id, crypto_type) DO UPDATE SET amount = amount + excluded.amount',
                (user_id, crypto_type, amount)
            )
            await conn.commit()
        except Exception as e:
            print(f"Ошибка добавления криптовалюты: {e}")

# 🏗️ ГЛАВНЫЙ БОТ
class MegaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        
        self.db = Database()
        self.economy = EconomySystem(self.db)
        self.casino = CasinoSystem(self.economy)
        
        self.credit_system = CreditSystem(self.economy, self.db)
        self.lootbox_system = LootboxSystem(self.economy)
        self.mining_system = MiningSystem(self.economy, self.db)
        self.event_system = EventSystem(self.economy, self.db)
        self.warn_system = WarnSystem(self.db)
        self.crypto_system = CryptoSystem(self.db)
        
        self.start_time = datetime.utcnow()
        self.background_tasks = []
    
    async def setup_hook(self):
        await self.db.init_db()
        await self.start_background_tasks()
        
        try:
            synced = await self.tree.sync()
            print(f"✅ Синхронизировано {len(synced)} команд")
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")

    async def start_background_tasks(self):
        """Запуск фоновых задач"""
        task = asyncio.create_task(self.background_credit_check())
        self.background_tasks.append(task)
    
    async def background_credit_check(self):
        """Фоновая проверка просроченных кредитов"""
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await self.credit_system.check_overdue_credits()
                await asyncio.sleep(3600)  # Проверка каждый час
            except Exception as e:
                print(f"Ошибка в фоновой задаче проверки кредитов: {e}")
                await asyncio.sleep(300)

    async def reload_bot(self) -> bool:
        try:
            synced = await self.tree.sync()
            print(f"♻️ Бот перезагружен! Синхронизировано {len(synced)} команд")
            return True
        except Exception as e:
            print(f"❌ Ошибка перезагрузки: {e}")
            return False

    async def close(self):
        """Закрытие бота с очисткой ресурсов"""
        for task in self.background_tasks:
            task.cancel()
        await self.db.close()
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

# 💰 КОМАНДЫ ДЛЯ ВСЕХ УЧАСТНИКОВ
@bot.tree.command(name="баланс", description="Проверить баланс")
async def баланс(interaction: discord.Interaction, пользователь: Optional[discord.Member] = None):
    try:
        user = пользователь or interaction.user
        balance = await bot.economy.get_balance(user.id)
        embed = Design.create_embed("💰 Баланс", f"**{user.display_name}**\nБаланс: `{balance:,} монет`", "economy")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось получить баланс", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ежедневно", description="Получить ежедневную награду")
@check_economic_ban()
async def ежедневно(interaction: discord.Interaction):
    try:
        user_data = await bot.economy.get_user_data(interaction.user.id)
        
        if user_data["daily_claimed"]:
            last_claim = datetime.fromisoformat(user_data["daily_claimed"])
            if (datetime.utcnow() - last_claim).days < 1:
                embed = Design.create_embed("⏳ Уже получали!", "Приходите завтра", "warning")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        reward = random.randint(100, 500)
        new_balance = await bot.economy.update_balance(interaction.user.id, reward)
        
        conn = await bot.db.get_connection()
        await conn.execute(
            'UPDATE users SET daily_claimed = ? WHERE user_id = ?', 
            (datetime.utcnow().isoformat(), interaction.user.id)
        )
        await conn.commit()
        
        embed = Design.create_embed("🎁 Ежедневная награда", f"**+{reward} монет!**\nБаланс: `{new_balance:,} монет`", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось получить ежедневную награду", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="работа", description="Заработать деньги")
@check_economic_ban()
async def работа(interaction: discord.Interaction):
    try:
        user_data = await bot.economy.get_user_data(interaction.user.id)
        
        if user_data["work_cooldown"]:
            last_work = datetime.fromisoformat(user_data["work_cooldown"])
            if (datetime.utcnow() - last_work).seconds < 600:
                embed = Design.create_embed("⏳ Отдохните!", "Подождите 10 минут", "warning")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        earnings = random.randint(50, 200)
        new_balance = await bot.economy.update_balance(interaction.user.id, earnings)
        
        conn = await bot.db.get_connection()
        await conn.execute(
            'UPDATE users SET work_cooldown = ? WHERE user_id = ?', 
            (datetime.utcnow().isoformat(), interaction.user.id)
        )
        await conn.commit()
        
        embed = Design.create_embed("💼 Работа", f"**Заработано:** +{earnings} монет\n**Баланс:** {new_balance:,} монет", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось выполнить работу", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="передать", description="Передать деньги")
@check_economic_ban()
async def передать(interaction: discord.Interaction, пользователь: discord.Member, сумма: int):
    try:
        if сумма <= 0:
            await interaction.response.send_message("❌ Сумма должна быть положительной!", ephemeral=True)
            return
        
        if пользователь.id == interaction.user.id:
            await interaction.response.send_message("❌ Нельзя передать самому себе!", ephemeral=True)
            return
        
        from_balance = await bot.economy.get_balance(interaction.user.id)
        if from_balance < сумма:
            await interaction.response.send_message("❌ Недостаточно средств!", ephemeral=True)
            return
        
        tax = int(сумма * 0.05)
        net_amount = сумма - tax
        
        await bot.economy.update_balance(interaction.user.id, -сумма)
        await bot.economy.update_balance(пользователь.id, net_amount)
        
        embed = Design.create_embed("✅ Перевод", 
                                  f"**От:** {interaction.user.mention}\n"
                                  f"**Кому:** {пользователь.mention}\n"
                                  f"**Сумма:** {сумма} монет\n"
                                  f"**Налог (5%):** {tax} монет\n"
                                  f"**Получено:** {net_amount} монет", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось выполнить перевод", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ограбить", description="Ограбить пользователя (КД: 30 минут)")
@check_economic_ban()
async def ограбить(interaction: discord.Interaction, жертва: discord.Member):
    try:
        user_id = interaction.user.id
        current_time = datetime.utcnow()
        
        conn = await bot.db.get_connection()
        async with conn.execute(
            'SELECT last_rob_time FROM rob_cooldowns WHERE user_id = ?', 
            (user_id,)
        ) as cursor:
            cooldown_data = await cursor.fetchone()
            
            if cooldown_data:
                last_rob = datetime.fromisoformat(cooldown_data['last_rob_time'])
                time_passed = current_time - last_rob
                if time_passed.total_seconds() < 1800:
                    minutes_left = 30 - int(time_passed.total_seconds() // 60)
                    embed = Design.create_embed("⏳ Кулдаун", 
                                              f"Подожди еще {minutes_left} минут!", 
                                              "warning")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
        
        if жертва.id == interaction.user.id:
            await interaction.response.send_message("❌ Нельзя ограбить самого себя!", ephemeral=True)
            return
        
        victim_balance = await bot.economy.get_balance(жертва.id)
        if victim_balance < 100:
            await interaction.response.send_message("❌ У жертвы меньше 100 монет!", ephemeral=True)
            return
        
        if random.random() < 0.4:
            stolen = random.randint(100, min(500, victim_balance))
            await bot.economy.update_balance(жертва.id, -stolen)
            await bot.economy.update_balance(interaction.user.id, stolen)
            
            await conn.execute(
                'INSERT OR REPLACE INTO rob_cooldowns (user_id, last_rob_time) VALUES (?, ?)',
                (user_id, current_time.isoformat())
            )
            await conn.commit()
            
            embed = Design.create_embed("💰 Ограбление успешно!", 
                                      f"**Украдено:** {stolen} монет\n"
                                      f"**Следующее ограбление через:** 30 минут", 
                                      "warning")
        else:
            fine = random.randint(50, 200)
            await bot.economy.update_balance(interaction.user.id, -fine)
            
            await conn.execute(
                'INSERT OR REPLACE INTO rob_cooldowns (user_id, last_rob_time) VALUES (?, ?)',
                (user_id, current_time.isoformat())
            )
            await conn.commit()
            
            embed = Design.create_embed("🚓 Пойманы!", 
                                      f"**Штраф:** {fine} монет\n"
                                      f"**Следующее ограбление через:** 30 минут", 
                                      "danger")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось выполнить ограбление", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# 🎰 КОМАНДЫ КАЗИНО
@bot.tree.command(name="слоты", description="Играть в слоты")
@check_economic_ban()
async def слоты(interaction: discord.Interaction, ставка: int):
    try:
        if ставка <= 0:
            await interaction.response.send_message("❌ Ставка должна быть положительной!", ephemeral=True)
            return
        
        result = await bot.casino.play_slots(interaction.user.id, ставка)
        
        if not result["success"]:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            return
        
        symbols = " | ".join(result["result"])
        
        if result["multiplier"] > 0:
            embed = Design.create_embed("🎰 Выигрыш!", 
                                      f"**{symbols}**\n"
                                      f"Ставка: {ставка} монет\n"
                                      f"Множитель: x{result['multiplier']}\n"
                                      f"Выигрыш: {result['win_amount']} монет", "success")
        else:
            embed = Design.create_embed("🎰 Проигрыш", 
                                      f"**{symbols}**\n"
                                      f"Потеряно: {ставка} монет", "danger")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось сыграть в слоты", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="монетка", description="Подбросить монетку")
@check_economic_ban()
async def монетка(interaction: discord.Interaction, ставка: int, выбор: str):
    try:
        if ставка <= 0:
            await interaction.response.send_message("❌ Ставка должна быть положительной!", ephemeral=True)
            return
        
        if выбор.lower() not in ["орёл", "орел", "решка"]:
            await interaction.response.send_message("❌ Выберите 'орёл' или 'решка'!", ephemeral=True)
            return
        
        balance = await bot.economy.get_balance(interaction.user.id)
        if balance < ставка:
            await interaction.response.send_message("❌ Недостаточно средств!", ephemeral=True)
            return
        
        outcome = random.choice(["орёл", "решка"])
        won = outcome == выбор.lower()
        
        if won:
            await bot.economy.update_balance(interaction.user.id, ставка)
            embed = Design.create_embed("🪙 Победа!", 
                                      f"Выпало: {outcome}\n"
                                      f"Ваш выбор: {выбор}\n"
                                      f"Выигрыш: {ставка} монет", "success")
        else:
            await bot.economy.update_balance(interaction.user.id, -ставка)
            embed = Design.create_embed("🪙 Проигрыш", 
                                      f"Выпало: {outcome}\n"
                                      f"Ваш выбор: {выбор}\n"
                                      f"Потеряно: {ставка} монет", "danger")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось подбросить монетку", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# 🛡️ КОМАНДЫ МОДЕРАЦИИ
@bot.tree.command(name="пред", description="Выдать предупреждение")
@is_moderator()
async def пред(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    try:
        target_roles = [role.id for role in пользователь.roles]
        if any(role_id in MODERATION_ROLES for role_id in target_roles) or пользователь.id in ADMIN_IDS:
            await interaction.response.send_message("❌ Нельзя выдать предупреждение модератору или администратору!", ephemeral=True)
            return
        
        warn_count = await bot.warn_system.add_warn(пользователь.id, interaction.user.id, причина)
        
        embed = Design.create_embed("⚠️ Предупреждение", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Причина:** {причина}\n"
                                  f"**Текущие пред:** {warn_count}/3", "warning")
        await interaction.response.send_message(embed=embed)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="снять_пред", description="Снять предупреждение")
@is_moderator()
async def снять_пред(interaction: discord.Interaction, пользователь: discord.Member, количество: int = 1):
    try:
        target_roles = [role.id for role in пользователь.roles]
        if any(role_id in MODERATION_ROLES for role_id in target_roles) or пользователь.id in ADMIN_IDS:
            await interaction.response.send_message("❌ Нельзя снять предупреждение с модератора или администратора!", ephemeral=True)
            return
        
        if количество <= 0:
            await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
            return
        
        new_count, removed_count = await bot.warn_system.remove_warns(пользователь.id, количество)
        
        if removed_count == 0:
            await interaction.response.send_message("❌ У пользователя нет предупреждений!", ephemeral=True)
            return
        
        embed = Design.create_embed("✅ Предупреждение снято", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Снято предупреждений:** {removed_count}\n"
                                  f"**Текущие пред:** {new_count}/3", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="преды", description="Посмотреть предупреждения пользователя")
@is_moderator()
async def преды(interaction: discord.Interaction, пользователь: discord.Member):
    try:
        warn_count = await bot.warn_system.get_warn_count(пользователь.id)
        
        embed = Design.create_embed("⚠️ Предупреждения", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Количество предупреждений:** {warn_count}/3", "warning")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

# 🏦 КОМАНДЫ КРЕДИТОВ
@bot.tree.command(name="кредит", description="Взять кредит")
async def кредит(interaction: discord.Interaction):
    try:
        embed = Design.create_embed("🏦 КРЕДИТЫ", "Используйте кнопки ниже для взятия кредита:", "credit")
        
        for company_id, company in bot.credit_system.companies.items():
            embed.add_field(
                name=f"{company['name']}",
                value=f"Сумма: {company['min_amount']:,}-{company['max_amount']:,} монет\n"
                      f"Процент: {company['interest_rate']}%\n"
                      f"Срок: {company['term_days']} дней\n"
                      f"Штраф: {company['penalty']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось загрузить информацию о кредитах", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
        embed = Design.create_embed("❌ Ошибка", "Произошла ошибка при возврате кредита", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="мой_кредит", description="Информация о кредите")
async def мой_кредит(interaction: discord.Interaction):
    try:
        credit_data = await bot.credit_system.get_user_credit(interaction.user.id)
        if not credit_data:
            await interaction.response.send_message("❌ У вас нет активных кредитов", ephemeral=True)
            return
        
        company = bot.credit_system.companies[credit_data["company"]]
        due_date = datetime.fromisoformat(credit_data["due_date"])
        days_left = (due_date - datetime.utcnow()).days
        
        embed = Design.create_embed("🏦 Мой кредит", 
                                  f"**Компания:** {company['name']}\n"
                                  f"**Сумма:** {credit_data['original_amount']:,} монет\n"
                                  f"**К возврату:** {credit_data['amount']:,} монет\n"
                                  f"**Процент:** {credit_data['interest_rate']}%\n"
                                  f"**Вернуть до:** {due_date.strftime('%d.%m.%Y')}\n"
                                  f"**Осталось дней:** {max(0, days_left)}", "credit")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось получить информацию о кредите", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# 🎁 КОМАНДЫ ЛУТБОКСОВ
@bot.tree.command(name="лутбоксы", description="Просмотреть лутбоксы")
async def лутбоксы(interaction: discord.Interaction):
    try:
        embed = Design.create_embed("🎁 ЛУТБОКСЫ", "Доступные лутбоксы:", "premium")
        
        for lootbox_id, lootbox in bot.lootbox_system.lootboxes.items():
            rewards_text = ""
            for reward in lootbox["rewards"]:
                if reward["type"] == "money":
                    rewards_text += f"💰 Деньги: {reward['min']}-{reward['max']} монет ({reward['chance']}%)\n"
                elif reward["type"] == "crypto":
                    rewards_text += f"₿ Криптовалюта ({reward['chance']}%)\n"
                elif reward["type"] == "nothing":
                    rewards_text += f"💨 Пустота ({reward['chance']}%)\n"
            
            embed.add_field(
                name=f"{lootbox['name']} - {lootbox['price']} монет",
                value=rewards_text,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось загрузить информацию о лутбоксах", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="открыть_лутбокс", description="Открыть лутбокс")
async def открыть_лутбокс(interaction: discord.Interaction, тип: str):
    try:
        lootbox_aliases = {
            "обычный": "common", "common": "common",
            "редкий": "rare", "rare": "rare"
        }
        
        lootbox_type = lootbox_aliases.get(тип.lower())
        if not lootbox_type:
            await interaction.response.send_message("❌ Неверный тип лутбокса! Доступно: `обычный`, `редкий`", ephemeral=True)
            return
        
        success, result = await bot.lootbox_system.open_lootbox(interaction.user.id, lootbox_type)
        
        if not success:
            await interaction.response.send_message("❌ Лутбокс не найден или недостаточно средств!", ephemeral=True)
            return
        
        lootbox = bot.lootbox_system.lootboxes[lootbox_type]
        embed = Design.create_embed(f"🎁 Открыт {lootbox['name']}!", "", "success")
        
        for reward in result:
            embed.add_field(name="🎉 Награда", value=reward, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось открыть лутбокс", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ⛏️ КОМАНДЫ МАЙНИНГА
@bot.tree.command(name="ферма", description="Информация о ферме")
async def ферма(interaction: discord.Interaction):
    try:
        farm_data = await bot.mining_system.get_user_farm(interaction.user.id)
        
        if not farm_data:
            embed = Design.create_embed("⛏️ Майнинг ферма", 
                                      "У вас еще нет фермы!\nИспользуйте `/создать_ферму` чтобы начать майнить", "info")
        else:
            level_data = bot.mining_system.farm_levels[farm_data['level']]
            
            can_collect = True
            time_left = "✅ Можно собрать"
            
            if farm_data.get('last_collected'):
                last_collect = datetime.fromisoformat(farm_data['last_collected'])
                time_passed = datetime.utcnow() - last_collect
                if time_passed.total_seconds() < 21600:
                    can_collect = False
                    hours_left = 5 - int(time_passed.total_seconds() // 3600)
                    minutes_left = 59 - int((time_passed.total_seconds() % 3600) // 60)
                    time_left = f"⏳ Через {hours_left}ч {minutes_left}м"
            
            embed = Design.create_embed("⛏️ Ваша ферма", 
                                      f"**Уровень:** {farm_data['level']}\n"
                                      f"**Доход:** {level_data['income']} монет/6ч\n"
                                      f"**Следующий уровень:** {level_data['upgrade_cost']} монет\n"
                                      f"**Статус:** {time_left}", "info")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось получить информацию о ферме", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="создать_ферму", description="Создать ферму")
async def создать_ферму(interaction: discord.Interaction):
    try:
        farm_data = await bot.mining_system.get_user_farm(interaction.user.id)
        if farm_data:
            await interaction.response.send_message("❌ У вас уже есть ферма!", ephemeral=True)
            return
        
        creation_cost = 500
        balance = await bot.economy.get_balance(interaction.user.id)
        
        if balance < creation_cost:
            await interaction.response.send_message(f"❌ Недостаточно средств! Нужно {creation_cost} монет", ephemeral=True)
            return
        
        await bot.economy.update_balance(interaction.user.id, -creation_cost)
        success = await bot.mining_system.create_farm(interaction.user.id)
        
        if success:
            embed = Design.create_embed("✅ Ферма создана!", 
                                      f"Ваша майнинг ферма уровня 1 готова к работе!\n"
                                      f"Стоимость создания: {creation_cost} монет", "success")
        else:
            embed = Design.create_embed("❌ Ошибка", "Не удалось создать ферму", "danger")
            await bot.economy.update_balance(interaction.user.id, creation_cost)  # Возвращаем деньги
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось создать ферму", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="собрать_доход", description="Собрать доход с фермы")
async def собрать_доход(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
        
        success, message = await bot.mining_system.collect_income(interaction.user.id)
        
        if success:
            embed = Design.create_embed("💰 Доход собран!", message, "success")
        else:
            embed = Design.create_embed("❌ Ошибка", message, "danger")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Произошла ошибка при сборе дохода", "danger")
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="улучшить_ферму", description="Улучшить ферму")
async def улучшить_ферму(interaction: discord.Interaction):
    try:
        success, message = await bot.mining_system.upgrade_farm(interaction.user.id)
        
        if success:
            embed = Design.create_embed("⚡ Ферма улучшена!", message, "success")
        else:
            embed = Design.create_embed("❌ Ошибка", message, "danger")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось улучшить ферму", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ₿ КОМАНДЫ КРИПТОВАЛЮТЫ
@bot.tree.command(name="крипта", description="Курсы криптовалют")
async def крипта(interaction: discord.Interaction):
    try:
        embed = Design.create_embed("₿ КРИПТОВАЛЮТЫ", "Актуальные курсы:", "crypto")
        
        for crypto, price in bot.crypto_system.prices.items():
            embed.add_field(
                name=crypto,
                value=f"${price:,.2f}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось получить курсы криптовалют", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="мой_крипто", description="Мой крипто-портфель")
async def мой_крипто(interaction: discord.Interaction):
    try:
        user_crypto = await bot.crypto_system.get_user_crypto(interaction.user.id)
        
        if not user_crypto:
            await interaction.response.send_message("❌ У вас нет криптовалюты", ephemeral=True)
            return
        
        embed = Design.create_embed("₿ Мой крипто-портфель", "", "crypto")
        total_value = 0
        
        for crypto, amount in user_crypto.items():
            value = amount * bot.crypto_system.prices[crypto]
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
        embed = Design.create_embed("❌ Ошибка", "Не удалось получить информацию о криптовалюте", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# 🎪 КОМАНДЫ ИВЕНТОВ
@bot.tree.command(name="ивенты", description="Активные ивенты")
async def ивенты(interaction: discord.Interaction):
    try:
        active_events = await bot.event_system.get_active_events()
        
        if not active_events:
            embed = Design.create_embed("🎪 Ивенты", "Сейчас нет активных ивентов", "info")
        else:
            embed = Design.create_embed("🎪 АКТИВНЫЕ ИВЕНТЫ", "", "event")
            for event_type, event_data in active_events.items():
                end_time = datetime.fromisoformat(event_data['end_time'])
                time_left = end_time - datetime.utcnow()
                minutes_left = max(0, int(time_left.total_seconds() // 60))
                
                event_info = eval(event_data['event_data'])  # Безопасно, т.к. мы сами сохраняли
                
                embed.add_field(
                    name=event_info['name'],
                    value=f"Осталось: {minutes_left} минут\n{event_info['description']}",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось получить информацию об ивентах", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="запустить_ивент", description="Запустить ивент")
@is_admin()
async def запустить_ивент(interaction: discord.Interaction, тип: str):
    try:
        event_types = {
            "дождь": "money_rain",
            "money_rain": "money_rain"
        }
        
        event_type = event_types.get(тип.lower())
        if not event_type:
            await interaction.response.send_message("❌ Неверный тип ивента! Доступно: `дождь`", ephemeral=True)
            return
        
        success = await bot.event_system.start_event(event_type, bot)
        
        if success:
            embed = Design.create_embed("✅ Ивент запущен!", f"Ивент **{bot.event_system.event_types[event_type]['name']}** активирован!", "success")
        else:
            embed = Design.create_embed("❌ Ошибка", "Не удалось запустить ивент", "danger")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Произошла ошибка при запуске ивента", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
        embed = Design.create_embed("❌ Ошибка", f"Не удалось выдать деньги: {e}", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="удалить_бд", description="Удалить базу данных")
@is_admin()
async def удалить_бд(interaction: discord.Interaction):
    try:
        import os
        import shutil
        
        if os.path.exists("data"):
            shutil.rmtree("data")
            await bot.db.init_db()
            embed = Design.create_embed("✅ База данных удалена", "Все данные сброшены!", "success")
        else:
            embed = Design.create_embed("ℹ️ База не найдена", "Папка data не существует", "info")
            
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
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
            "`/запустить_ивент тип` - Запустить ивент\n\n"
            "**Статистика:**\n"
            "`/статус` - Статус бота"
        )
        
        embed = Design.create_embed("👑 ПАНЕЛЬ АДМИНИСТРАТОРА", description, "premium")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось загрузить панель администратора", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="перезагрузить", description="Перезагрузить бота")
@is_admin()
async def перезагрузить(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
        
        embed = Design.create_embed("🔄 Перезагрузка бота", "Выполняется перезагрузка...", "warning")
        await interaction.followup.send(embed=embed)
        
        success = await bot.reload_bot()
        
        if success:
            embed = Design.create_embed("✅ Перезагрузка завершена", "Бот успешно перезагружен!", "success")
        else:
            embed = Design.create_embed("❌ Ошибка перезагрузки", "Произошла ошибка при перезагрузке", "danger")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось перезагрузить бота", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="статус", description="Статус бота")
@is_admin()
async def статус(interaction: discord.Interaction):
    try:
        uptime = datetime.utcnow() - bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed = Design.create_embed("📊 Статус бота", "", "info")
        embed.add_field(name="⏰ Аптайм", value=f"{hours}ч {minutes}м {seconds}с", inline=True)
        embed.add_field(name="🌐 Серверов", value=str(len(bot.guilds)), inline=True)
        embed.add_field(name="👥 Пользователей", value=str(len(bot.users)), inline=True)
        embed.add_field(name="📈 Пинг", value=f"{round(bot.latency * 1000)}мс", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось получить статус бота", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'🌐 Серверов: {len(bot.guilds)}')
    print(f'👥 Пользователей: {len(bot.users)}')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Синхронизировано {len(synced)} команд')
    except Exception as e:
        print(f'❌ Ошибка синхронизации: {e}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if isinstance(message.channel, discord.TextChannel):
        try:
            conn = await bot.db.get_connection()
            await conn.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.author.id,))
            await conn.commit()
        except Exception as e:
            print(f"Ошибка регистрации пользователя: {e}")
    
    await bot.process_commands(message)

if __name__ == "__main__":
    try:
        print("🚀 Запуск бота...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
