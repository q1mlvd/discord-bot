# ЗАМЕНИТЕ эти импорты в начале файла
import discord
from discord.ext import commands, tasks
import aiosqlite
import asyncio
from datetime import datetime, timedelta
import os
import random
from typing import Optional
from dotenv import load_dotenv
import json  # Добавьте этот импорт

# 🔧 КОНСТАНТЫ
ADMIN_IDS = [1195144951546265675, 766767256742526996, 1078693283695448064, 1138140772097597472, 691904643181314078]
MODERATION_ROLES = [1167093102868172911, 1360243534946373672, 993043931342319636, 1338611327022923910, 1338609155203661915, 1365798715930968244, 1188261847850299514]
THREADS_CHANNEL_ID = 1422557295811887175
EVENTS_CHANNEL_ID = 1418738569081786459

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

# 🔧 ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
economic_bans = {}

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
        "event": 0x9B59B6, "credit": 0xE74C3C, "nft": 0x9B59B6
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
            # Основные таблицы пользователей
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
            
            # Кредиты и майнинг
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_credits (
                    user_id INTEGER,
                    company TEXT,
                    amount INTEGER,
                    interest_rate INTEGER,
                    due_date TEXT,
                    PRIMARY KEY (user_id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS mining_farms (
                    user_id INTEGER,
                    level INTEGER DEFAULT 1,
                    last_collected TEXT,
                    created_at TEXT,
                    PRIMARY KEY (user_id)
                )
            ''')
            
            # NFT таблицы
            await db.execute('''
                CREATE TABLE IF NOT EXISTS nft_collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    creator_id INTEGER,
                    created_at TEXT,
                    image_url TEXT,
                    supply INTEGER,
                    available INTEGER
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS nft_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id INTEGER,
                    owner_id INTEGER,
                    token_id INTEGER,
                    metadata TEXT,
                    created_at TEXT,
                    price INTEGER,
                    for_sale BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (collection_id) REFERENCES nft_collections (id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS nft_sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nft_id INTEGER,
                    seller_id INTEGER,
                    buyer_id INTEGER,
                    price INTEGER,
                    sold_at TEXT,
                    FOREIGN KEY (nft_id) REFERENCES nft_items (id)
                )
            ''')
            
            # Система кейсов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    price INTEGER,
                    image_url TEXT,
                    available BOOLEAN DEFAULT TRUE
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS case_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER,
                    reward_type TEXT,
                    reward_id INTEGER,
                    reward_amount REAL,
                    chance REAL,
                    FOREIGN KEY (case_id) REFERENCES cases (id)
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

    async def admin_add_money(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
            await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            await db.commit()
            return await self.get_balance(user_id)

# 🏦 СИСТЕМА КРЕДИТОВ
class CreditSystem:
    def __init__(self, economy: EconomySystem):
        self.economy = economy
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
        if user_id in user_credits:
            return False, "У вас уже есть активный кредит"
        
        company_data = self.companies.get(company)
        if not company_data:
            return False, "Компания не найдена"
        
        if amount < company_data["min_amount"] or amount > company_data["max_amount"]:
            return False, f"Сумма должна быть от {company_data['min_amount']} до {company_data['max_amount']}"
        
        due_date = datetime.now() + timedelta(days=company_data["term_days"])
        user_credits[user_id] = {
            "company": company,
            "amount": amount,
            "interest_rate": company_data["interest_rate"],
            "due_date": due_date,
            "original_amount": amount
        }
        
        await self.economy.update_balance(user_id, amount)
        return True, f"Кредит одобрен! Вернуть до {due_date.strftime('%d.%m.%Y')}"

    async def repay_credit(self, user_id: int):
        if user_id not in user_credits:
            return False, "У вас нет активных кредитов"
        
        credit = user_credits[user_id]
        total_to_repay = credit["amount"]
        
        balance = await self.economy.get_balance(user_id)
        if balance < total_to_repay:
            return False, f"Недостаточно средств. Нужно: {total_to_repay} монет"
        
        await self.economy.update_balance(user_id, -total_to_repay)
        del user_credits[user_id]
        return True, f"Кредит погашен! Сумма: {total_to_repay} монет"

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
                    if user_id not in user_crypto:
                        user_crypto[user_id] = {}
                    user_crypto[user_id][crypto_type] = user_crypto[user_id].get(crypto_type, 0) + amount
                    rewards.append(f"₿ {amount:.4f} {crypto_type}")
        
        if not rewards:
            rewards.append("💔 Не повезло... Попробуй еще раз!")
        
        return True, rewards

class NFTSystem:
    def __init__(self, economy: EconomySystem, db_path: str):
        self.economy = economy
        self.db_path = db_path
    
    async def create_collection(self, creator_id: int, name: str, description: str, supply: int, image_url: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO nft_collections (name, description, creator_id, created_at, image_url, supply, available)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, description, creator_id, datetime.now().isoformat(), image_url, supply, supply))
            collection_id = cursor.lastrowid
            
            # Создаем NFT предметы для коллекции
            for token_id in range(1, supply + 1):
                metadata = {
                    "name": f"{name} #{token_id}",
                    "description": description,
                    "attributes": [],
                    "collection": name,
                    "token_id": token_id
                }
                await db.execute('''
                    INSERT INTO nft_items (collection_id, owner_id, token_id, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (collection_id, creator_id, token_id, json.dumps(metadata), datetime.now().isoformat()))
            
            await db.commit()
            return collection_id
    
    async def list_nft(self, nft_id: int, price: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE nft_items SET for_sale = TRUE, price = ? WHERE id = ?', (price, nft_id))
            await db.commit()
            return True
    
    async def buy_nft(self, buyer_id: int, nft_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT owner_id, price FROM nft_items WHERE id = ? AND for_sale = TRUE', (nft_id,)) as cursor:
                nft = await cursor.fetchone()
                if not nft:
                    return False, "NFT не найдена или не продается"
                
                seller_id, price = nft
                
                if seller_id == buyer_id:
                    return False, "Нельзя купить свою же NFT"
                
                balance = await self.economy.get_balance(buyer_id)
                if balance < price:
                    return False, "Недостаточно средств"
                
                await self.economy.update_balance(seller_id, price)
                await self.economy.update_balance(buyer_id, -price)
                
                await db.execute('UPDATE nft_items SET owner_id = ?, for_sale = FALSE WHERE id = ?', (buyer_id, nft_id))
                
                await db.execute('''
                    INSERT INTO nft_sales (nft_id, seller_id, buyer_id, price, sold_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (nft_id, seller_id, buyer_id, price, datetime.now().isoformat()))
                
                await db.commit()
                return True, f"NFT успешно куплена за {price} монет"
    
    async def get_user_nfts(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT ni.id, nc.name, ni.token_id, ni.metadata, ni.for_sale, ni.price
                FROM nft_items ni
                JOIN nft_collections nc ON ni.collection_id = nc.id
                WHERE ni.owner_id = ?
            ''', (user_id,)) as cursor:
                return await cursor.fetchall()
    
    async def get_marketplace_nfts(self):
        """Получить NFT с маркетплейса"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT ni.id, nc.name, ni.token_id, ni.metadata, ni.price, ni.owner_id
                FROM nft_items ni
                JOIN nft_collections nc ON ni.collection_id = nc.id
                WHERE ni.for_sale = TRUE
                LIMIT 20
            ''') as cursor:
                return await cursor.fetchall()

# 🎁 СИСТЕМА КЕЙСОВ
class CaseSystem:
    def __init__(self, economy: EconomySystem, nft_system: NFTSystem):
        self.economy = economy
        self.nft_system = nft_system
    
    async def create_case(self, name: str, description: str, price: int, image_url: str = None):
        async with aiosqlite.connect(bot.db.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO cases (name, description, price, image_url)
                VALUES (?, ?, ?, ?)
            ''', (name, description, price, image_url))
            case_id = cursor.lastrowid
            await db.commit()
            return case_id
    
    async def add_reward_to_case(self, case_id: int, reward_type: str, reward_id: int, reward_amount: float, chance: float):
        async with aiosqlite.connect(bot.db.db_path) as db:
            await db.execute('''
                INSERT INTO case_rewards (case_id, reward_type, reward_id, reward_amount, chance)
                VALUES (?, ?, ?, ?, ?)
            ''', (case_id, reward_type, reward_id, reward_amount, chance))
            await db.commit()
    
    async def open_case(self, user_id: int, case_id: int):
        async with aiosqlite.connect(bot.db.db_path) as db:
            # Проверяем кейс
            async with db.execute('SELECT name, price FROM cases WHERE id = ? AND available = TRUE', (case_id,)) as cursor:
                case_data = await cursor.fetchone()
                if not case_data:
                    return False, "Кейс не найден"
                
                case_name, price = case_data
                
                # Проверяем баланс
                balance = await self.economy.get_balance(user_id)
                if balance < price:
                    return False, "Недостаточно средств"
                
                # Списываем деньги
                await self.economy.update_balance(user_id, -price)
                
                # Получаем возможные награды
                async with db.execute('''
                    SELECT reward_type, reward_id, reward_amount, chance 
                    FROM case_rewards 
                    WHERE case_id = ?
                ''', (case_id,)) as cursor:
                    rewards = await cursor.fetchall()
                
                if not rewards:
                    return False, "В кейсе нет наград"
                
                # Выбираем награду по шансам
                total_chance = sum(reward[3] for reward in rewards)
                roll = random.uniform(0, total_chance)
                current_chance = 0
                
                selected_reward = None
                for reward in rewards:
                    current_chance += reward[3]
                    if roll <= current_chance:
                        selected_reward = reward
                        break
                
                if not selected_reward:
                    selected_reward = rewards[0]  # fallback
                
                reward_type, reward_id, reward_amount, chance = selected_reward
                
                # Выдаем награду
                reward_message = ""
                if reward_type == "money":
                    await self.economy.update_balance(user_id, reward_amount)
                    reward_message = f"💰 {int(reward_amount)} монет"
                elif reward_type == "nft":
                    # Передаем NFT пользователю
                    await db.execute('UPDATE nft_items SET owner_id = ? WHERE id = ?', (user_id, reward_id))
                    async with db.execute('SELECT metadata FROM nft_items WHERE id = ?', (reward_id,)) as cursor:
                        nft_metadata = await cursor.fetchone()
                        if nft_metadata:
                            metadata = json.loads(nft_metadata[0])
                            reward_message = f"🎨 NFT: {metadata.get('name', 'Неизвестно')}"
                elif reward_type == "crypto":
                    crypto_type = random.choice(list(crypto_prices.keys()))
                    if user_id not in user_crypto:
                        user_crypto[user_id] = {}
                    user_crypto[user_id][crypto_type] = user_crypto[user_id].get(crypto_type, 0) + reward_amount
                    reward_message = f"₿ {reward_amount:.4f} {crypto_type}"
                
                await db.commit()
                return True, reward_message
    
    async def get_available_cases(self):
        async with aiosqlite.connect(bot.db.db_path) as db:
            async with db.execute('SELECT id, name, description, price, image_url FROM cases WHERE available = TRUE') as cursor:
                return await cursor.fetchall()

# 🔧 СИСТЕМА МАЙНИНГА
class MiningSystem:
    def __init__(self, economy: EconomySystem):
        self.economy = economy
        self.farm_levels = {
            1: {"income": 10, "upgrade_cost": 1000},
            2: {"income": 25, "upgrade_cost": 5000},
            3: {"income": 50, "upgrade_cost": 15000}
        }
    
    async def collect_income(self, user_id: int):
        try:
            if user_id not in user_mining_farms:
                return False, "У вас нет фермы"
            
            farm = user_mining_farms[user_id]
            
            if farm.get("last_collected"):
                try:
                    last_collect = datetime.fromisoformat(farm["last_collected"])
                    time_passed = datetime.now() - last_collect
                    if time_passed.total_seconds() < 21600:
                        hours_left = 5 - int(time_passed.total_seconds() // 3600)
                        minutes_left = 59 - int((time_passed.total_seconds() % 3600) // 60)
                        return False, f"Доход можно собирать раз в 6 часов! Осталось: {hours_left}ч {minutes_left}м"
                except ValueError:
                    farm["last_collected"] = None
            
            income = self.farm_levels[farm["level"]]["income"]
            await self.economy.update_balance(user_id, income)
            
            user_mining_farms[user_id]["last_collected"] = datetime.now().isoformat()
            
            return True, f"✅ Собрано {income} монет с фермы! Следующий сбор через 6 часов"
            
        except Exception as e:
            print(f"Ошибка при сборе дохода: {e}")
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
            print(f"❌ Ошибка отправки ивента: {e}")
        
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
        
        self.credit_system = CreditSystem(self.economy)
        self.lootbox_system = LootboxSystem(self.economy)
        self.nft_system = NFTSystem(self.economy, self.db.db_path)  # Передаем путь к БД
        self.case_system = CaseSystem(self.economy, self.nft_system)
        self.mining_system = MiningSystem(self.economy)
        self.event_system = EventSystem(self.economy)
        
        self.start_time = datetime.now()
        self.nft_system = NFTSystem(self.economy, self.db.db_path)  # Убедись что передается db_path
    
    async def setup_hook(self):
        await self.db.init_db()
        try:
            synced = await self.tree.sync()
            print(f"✅ Синхронизировано {len(synced)} команд")
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")

    async def reload_bot(self):
        try:
            synced = await self.tree.sync()
            print(f"♻️ Бот перезагружен! Синхронизировано {len(synced)} команд")
            return True
        except Exception as e:
            print(f"❌ Ошибка перезагрузки: {e}")
            return False

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
    user = пользователь or interaction.user
    balance = await bot.economy.get_balance(user.id)
    embed = Design.create_embed("💰 Баланс", f"**{user.display_name}**\nБаланс: `{balance:,} монет`", "economy")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ежедневно", description="Получить ежедневную награду")
@check_economic_ban()
async def ежедневно(interaction: discord.Interaction):
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

@bot.tree.command(name="работа", description="Заработать деньги")
@check_economic_ban()
async def работа(interaction: discord.Interaction):
    try:
        user_data = await bot.economy.get_user_data(interaction.user.id)
        
        if user_data["work_cooldown"]:
            last_work = datetime.fromisoformat(user_data["work_cooldown"])
            if (datetime.now() - last_work).seconds < 600:
                embed = Design.create_embed("⏳ Отдохните!", "Подождите 10 минут", "warning")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        earnings = random.randint(50, 200)
        new_balance = await bot.economy.update_balance(interaction.user.id, earnings)
        
        async with aiosqlite.connect(bot.db.db_path) as db:
            await db.execute('UPDATE users SET work_cooldown = ? WHERE user_id = ?', (datetime.now().isoformat(), interaction.user.id))
            await db.commit()
        
        embed = Design.create_embed("💼 Работа", f"**Заработано:** +{earnings} монет\n**Баланс:** {new_balance:,} монет", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", "Не удалось выполнить работу", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="передать", description="Передать деньги")
@check_economic_ban()
async def передать(interaction: discord.Interaction, пользователь: discord.Member, сумма: int):
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
    
    tax = сумма * 0.05
    net_amount = сумма - tax
    global server_tax_pool
    server_tax_pool += tax
    
    await bot.economy.update_balance(interaction.user.id, -сумма)
    await bot.economy.update_balance(пользователь.id, net_amount)
    
    embed = Design.create_embed("✅ Перевод", 
                              f"**От:** {interaction.user.mention}\n"
                              f"**Кому:** {пользователь.mention}\n"
                              f"**Сумма:** {сумма} монет\n"
                              f"**Налог (5%):** {tax} монет\n"
                              f"**Получено:** {net_amount} монет", "success")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ограбить", description="Ограбить пользователя (КД: 30 минут)")
@check_economic_ban()
async def ограбить(interaction: discord.Interaction, жертва: discord.Member):
    user_id = interaction.user.id
    current_time = datetime.now()
    
    if user_id in rob_cooldowns:
        time_passed = current_time - rob_cooldowns[user_id]
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
        
        rob_cooldowns[user_id] = current_time
        
        embed = Design.create_embed("💰 Ограбление успешно!", 
                                  f"**Украдено:** {stolen} монет\n"
                                  f"**Следующее ограбление через:** 30 минут", 
                                  "warning")
    else:
        fine = random.randint(50, 200)
        await bot.economy.update_balance(interaction.user.id, -fine)
        rob_cooldowns[user_id] = current_time
        
        embed = Design.create_embed("🚓 Пойманы!", 
                                  f"**Штраф:** {fine} монет\n"
                                  f"**Следующее ограбление через:** 30 минут", 
                                  "danger")
    
    await interaction.response.send_message(embed=embed)

# 🎰 КОМАНДЫ КАЗИНО
@bot.tree.command(name="слоты", description="Играть в слоты")
@check_economic_ban()
async def слоты(interaction: discord.Interaction, ставка: int = 0):
    if ставка < 0:
        await interaction.response.send_message("❌ Ставка не может быть отрицательной!", ephemeral=True)
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

@bot.tree.command(name="монетка", description="Подбросить монетку")
@check_economic_ban()
async def монетка(interaction: discord.Interaction, ставка: int = 0, выбор: str = "орёл"):
    if ставка < 0:
        await interaction.response.send_message("❌ Ставка не может быть отрицательной!", ephemeral=True)
        return
    
    if выбор not in ["орёл", "решка"]:
        await interaction.response.send_message("❌ Выберите 'орёл' или 'решка'!", ephemeral=True)
        return
    
    balance = await bot.economy.get_balance(interaction.user.id)
    if balance < ставка:
        await interaction.response.send_message("❌ Недостаточно средств!", ephemeral=True)
        return
    
    outcome = random.choice(["орёл", "решка"])
    won = outcome == выбор
    
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

# 🛡️ КОМАНДЫ МОДЕРАЦИИ
@bot.tree.command(name="пред", description="Выдать предупреждение")
@is_moderator()
async def пред(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    try:
        target_roles = [role.id for role in пользователь.roles]
        if any(role_id in MODERATION_ROLES for role_id in target_roles) or пользователь.id in ADMIN_IDS:
            await interaction.response.send_message("❌ Нельзя выдать предупреждение модератору или администратору!", ephemeral=True)
            return
        
        if пользователь.id not in user_warns:
            user_warns[пользователь.id] = 0
        
        user_warns[пользователь.id] += 1
        current_warns = user_warns[пользователь.id]
        
        embed = Design.create_embed("⚠️ Предупреждение", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Причина:** {причина}\n"
                                  f"**Текущие пред:** {current_warns}/3", "warning")
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
        
        if пользователь.id not in user_warns or user_warns[пользователь.id] <= 0:
            await interaction.response.send_message("❌ У пользователя нет предупреждений!", ephemeral=True)
            return
        
        if количество <= 0:
            await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
            return
        
        current_warns = user_warns[пользователь.id]
        new_warns = max(0, current_warns - количество)
        user_warns[пользователь.id] = new_warns
        
        embed = Design.create_embed("✅ Предупреждение снято", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Снято предупреждений:** {min(количество, current_warns)}\n"
                                  f"**Текущие пред:** {new_warns}/3", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

# 🏦 КОМАНДЫ КРЕДИТОВ
@bot.tree.command(name="кредит", description="Взять кредит")
async def кредит(interaction: discord.Interaction):
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
    user_id = interaction.user.id
    if user_id not in user_credits:
        await interaction.response.send_message("❌ У вас нет активных кредитов", ephemeral=True)
        return
    
    credit = user_credits[user_id]
    company = bot.credit_system.companies[credit["company"]]
    days_left = (credit["due_date"] - datetime.now()).days
    
    embed = Design.create_embed("🏦 Мой кредит", 
                              f"**Компания:** {company['name']}\n"
                              f"**Сумма:** {credit['original_amount']:,} монет\n"
                              f"**Процент:** {credit['interest_rate']}%\n"
                              f"**Вернуть до:** {credit['due_date'].strftime('%d.%m.%Y')}\n"
                              f"**Осталось дней:** {max(0, days_left)}", "credit")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 🎁 КОМАНДЫ ЛУТБОКСОВ
@bot.tree.command(name="лутбоксы", description="Просмотреть лутбоксы")
async def лутбоксы(interaction: discord.Interaction):
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

@bot.tree.command(name="открыть_лутбокс", description="Открыть лутбокс")
async def открыть_лутбокс(interaction: discord.Interaction, тип: str):
    lootbox_aliases = {
        "обычный": "common", "common": "common",
        "редкий": "rare", "rare": "rare"
    }
    
    lootbox_type = lootbox_aliases.get(тип.lower())
    
    success, result = await bot.lootbox_system.open_lootbox(interaction.user.id, lootbox_type)
    
    if not success:
        await interaction.response.send_message("❌ Лутбокс не найден или недостаточно средств!", ephemeral=True)
        return
    
    lootbox = bot.lootbox_system.lootboxes[lootbox_type]
    embed = Design.create_embed(f"🎁 Открыт {lootbox['name']}!", "", "success")
    
    for reward in result:
        embed.add_field(name="🎉 Награда", value=reward, inline=False)
    
    await interaction.response.send_message(embed=embed)

# 🎨 NFT КОМАНДЫ
@bot.tree.command(name="нфт_коллекции", description="Просмотр коллекций NFT")
async def нфт_коллекции(interaction: discord.Interaction):
    async with aiosqlite.connect(bot.db.db_path) as db:
        async with db.execute('SELECT id, name, description, supply, available FROM nft_collections') as cursor:
            collections = await cursor.fetchall()
    
    if not collections:
        await interaction.response.send_message("❌ Пока нет коллекций NFT", ephemeral=True)
        return
    
    embed = Design.create_embed("🎨 NFT КОЛЛЕКЦИИ", "Доступные коллекции:", "nft")
    
    for col in collections:
        col_id, name, description, supply, available = col
        embed.add_field(
            name=name,
            value=f"ID: {col_id}\nОписание: {description}\nВыпущено: {available}/{supply}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="мои_нфт", description="Мои NFT")
async def мои_нфт(interaction: discord.Interaction):
    nfts = await bot.nft_system.get_user_nfts(interaction.user.id)
    
    if not nfts:
        await interaction.response.send_message("❌ У вас нет NFT", ephemeral=True)
        return
    
    embed = Design.create_embed("🎨 МОИ NFT", f"Найдено {len(nfts)} NFT:", "nft")
    
    for nft in nfts[:5]:  # Показываем первые 5
        nft_id, col_name, token_id, metadata, for_sale, price = nft
        metadata_obj = json.loads(metadata)
        
        status = "💰 Продается" if for_sale else "💎 В коллекции"
        price_info = f"Цена: {price} монет" if for_sale else ""
        
        embed.add_field(
            name=f"{metadata_obj.get('name', 'NFT')}",
            value=f"Коллекция: {col_name}\n{status}\n{price_info}",
            inline=True
        )
    
    if len(nfts) > 5:
        embed.set_footer(text=f"И еще {len(nfts) - 5} NFT...")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="продать_нфт", description="Выставить NFT на продажу")
async def продать_нфт(interaction: discord.Interaction, нфт_id: int, цена: int):
    if цена <= 0:
        await interaction.response.send_message("❌ Цена должна быть положительной!", ephemeral=True)
        return
    
    # Проверяем владение NFT
    nfts = await bot.nft_system.get_user_nfts(interaction.user.id)
    nft_owned = any(nft[0] == нфт_id for nft in nfts)
    
    if not nft_owned:
        await interaction.response.send_message("❌ У вас нет этой NFT или она не найдена!", ephemeral=True)
        return
    
    success = await bot.nft_system.list_nft(нфт_id, цена)
    
    if success:
        embed = Design.create_embed("✅ NFT выставлена на продажу", 
                                  f"NFT #{нфт_id} выставлена на продажу за {цена} монет", "success")
    else:
        embed = Design.create_embed("❌ Ошибка", "Не удалось выставить NFT на продажу", "danger")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="купить_нфт", description="Купить NFT")
async def купить_нфт(interaction: discord.Interaction, нфт_id: int):
    success, message = await bot.nft_system.buy_nft(interaction.user.id, нфт_id)
    
    if success:
        embed = Design.create_embed("✅ NFT куплена!", message, "success")
    else:
        embed = Design.create_embed("❌ Ошибка", message, "danger")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="маркетплейс", description="NFT маркетплейс")
async def маркетплейс(interaction: discord.Interaction):
    try:
        nfts = await bot.nft_system.get_marketplace_nfts()
        
        if not nfts:
            await interaction.response.send_message("❌ На маркетплейсе пока нет NFT", ephemeral=True)
            return
        
        embed = Design.create_embed("🛒 NFT МАРКЕТПЛЕЙС", "Доступные для покупки NFT:", "nft")
        
        for nft in nfts[:6]:  # Показываем первые 6
            nft_id, col_name, token_id, metadata, price, owner_id = nft
            metadata_obj = json.loads(metadata)
            
            # Пытаемся получить имя пользователя из Discord
            try:
                user = await bot.fetch_user(owner_id)
                username = user.display_name if user else f"ID {owner_id}"
            except:
                username = f"ID {owner_id}"
            
            embed.add_field(
                name=f"{metadata_obj.get('name', 'NFT')} #{token_id}",
                value=f"Коллекция: {col_name}\nЦена: {price} монет\nПродавец: {username}\nNFT ID: {nft_id}",
                inline=True
            )
        
        embed.set_footer(text="Используйте /купить_нфт [ID] для покупки")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка загрузки маркетплейса: {e}", ephemeral=True)

@bot.tree.command(name="создать_коллекцию", description="Создать NFT коллекцию (Админ)")
@is_admin()
async def создать_коллекцию(interaction: discord.Interaction, название: str, описание: str, количество: int):
    if количество <= 0 or количество > 10000:
        await interaction.response.send_message("❌ Количество должно быть от 1 до 10000", ephemeral=True)
        return
    
    collection_id = await bot.nft_system.create_collection(
        interaction.user.id, название, описание, количество
    )
    
    embed = Design.create_embed("✅ Коллекция создана!", 
                              f"**Название:** {название}\n"
                              f"**Описание:** {описание}\n"
                              f"**Количество:** {количество} NFT\n"
                              f"**ID коллекции:** {collection_id}", "success")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="тест_нфт", description="Создать тестовые NFT (Админ)")
@is_admin()
async def тест_нфт(interaction: discord.Interaction):
    try:
        # Сразу отвечаем, чтобы Discord знал что бот живой
        await interaction.response.defer(ephemeral=True)
        
        # Создаем тестовую коллекцию
        collection_id = await bot.nft_system.create_collection(
            interaction.user.id, 
            "Тестовая коллекция", 
            "Для тестирования маркетплейса", 
            3  # Создаем 3 NFT
        )
        
        # Выставляем одну NFT на продажу
        async with aiosqlite.connect(bot.db.db_path) as db:
            await db.execute('UPDATE nft_items SET for_sale = TRUE, price = 500 WHERE id = 1')
            await db.commit()
        
        embed = Design.create_embed("✅ Тестовые NFT созданы!", 
                                  "Создана коллекция из 3 NFT\nОдна NFT выставлена на продажу за 500 монет\n\nИспользуйте /маркетплейс для просмотра", 
                                  "success")
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")

# 🎁 КОМАНДЫ КЕЙСОВ
@bot.tree.command(name="кейсы", description="Просмотреть доступные кейсы")
async def кейсы(interaction: discord.Interaction):
    cases = await bot.case_system.get_available_cases()
    
    if not cases:
        await interaction.response.send_message("❌ Пока нет доступных кейсов", ephemeral=True)
        return
    
    embed = Design.create_embed("🎁 КЕЙСЫ", "Доступные кейсы для открытия:", "premium")
    
    for case in cases:
        case_id, name, description, price, image_url = case
        embed.add_field(
            name=f"{name} - {price} монет",
            value=f"{description}\nID: {case_id}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="открыть_кейс", description="Открыть кейс")
async def открыть_кейс(interaction: discord.Interaction, кейс_id: int):
    await interaction.response.defer()
    
    success, message = await bot.case_system.open_case(interaction.user.id, кейс_id)
    
    if success:
        embed = Design.create_embed("🎁 Кейс открыт!", 
                                  f"**Вы получили:** {message}", "success")
    else:
        embed = Design.create_embed("❌ Ошибка", message, "danger")
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="создать_кейс", description="Создать кейс (Админ)")
@is_admin()
async def создать_кейс(interaction: discord.Interaction, название: str, описание: str, цена: int):
    if цена <= 0:
        await interaction.response.send_message("❌ Цена должна быть положительной!", ephemeral=True)
        return
    
    case_id = await bot.case_system.create_case(название, описание, цена)
    
    embed = Design.create_embed("✅ Кейс создан!", 
                              f"**Название:** {название}\n"
                              f"**Описание:** {описание}\n"
                              f"**Цена:** {цена} монет\n"
                              f"**ID кейса:** {case_id}\n\n"
                              f"Теперь добавьте награды командой /добавить_награду", "success")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="добавить_награду", description="Добавить награду в кейс (Админ)")
@is_admin()
async def добавить_награду(interaction: discord.Interaction, кейс_id: int, тип: str, шанс: float, количество: float, нфт_id: Optional[int] = None):
    if шанс <= 0 or шанс > 100:
        await interaction.response.send_message("❌ Шанс должен быть от 0.1 до 100", ephemeral=True)
        return
    
    if тип == "nft" and not нфт_id:
        await interaction.response.send_message("❌ Для типа 'nft' укажите нфт_id", ephemeral=True)
        return
    
    reward_id = нфт_id if тип == "nft" else 0
    
    await bot.case_system.add_reward_to_case(кейс_id, тип, reward_id, количество, шанс)
    
    embed = Design.create_embed("✅ Награда добавлена!", 
                              f"**Кейс ID:** {кейс_id}\n"
                              f"**Тип:** {тип}\n"
                              f"**Количество:** {количество}\n"
                              f"**Шанс:** {шанс}%", "success")
    await interaction.response.send_message(embed=embed)

# ⛏️ КОМАНДЫ МАЙНИНГА
@bot.tree.command(name="ферма", description="Информация о ферме")
async def ферма(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if user_id not in user_mining_farms:
        embed = Design.create_embed("⛏️ Майнинг ферма", 
                                  "У вас еще нет фермы!\nИспользуйте `/создать_ферму` чтобы начать майнить", "info")
    else:
        farm = user_mining_farms[user_id]
        level_data = bot.mining_system.farm_levels[farm["level"]]
        
        can_collect = True
        time_left = "✅ Можно собрать"
        
        if "last_collected" in farm and farm["last_collected"]:
            last_collect = datetime.fromisoformat(farm["last_collected"])
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

@bot.tree.command(name="создать_ферму", description="Создать ферму")
async def создать_ферму(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if user_id in user_mining_farms:
        await interaction.response.send_message("❌ У вас уже есть ферма!", ephemeral=True)
        return
    
    creation_cost = 500
    balance = await bot.economy.get_balance(user_id)
    
    if balance < creation_cost:
        await interaction.response.send_message(f"❌ Недостаточно средств! Нужно {creation_cost} монет", ephemeral=True)
        return
    
    await bot.economy.update_balance(user_id, -creation_cost)
    user_mining_farms[user_id] = {
        "level": 1, 
        "last_collected": None,
        "created_at": datetime.now().isoformat()
    }
    
    embed = Design.create_embed("✅ Ферма создана!", 
                              f"Ваша майнинг ферма уровня 1 готова к работе!\n"
                              f"Стоимость создания: {creation_cost} монет", "success")
    await interaction.response.send_message(embed=embed)

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
        embed = Design.create_embed("❌ Ошибка", "Произошла ошибка при сборе дохода", "danger")
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="улучшить_ферму", description="Улучшить ферму")
async def улучшить_ферму(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if user_id not in user_mining_farms:
        await interaction.response.send_message("❌ У вас нет фермы!", ephemeral=True)
        return
    
    farm = user_mining_farms[user_id]
    current_level = farm["level"]
    
    if current_level >= 3:
        await interaction.response.send_message("❌ Ваша ферма уже максимального уровня!", ephemeral=True)
        return
    
    upgrade_cost = bot.mining_system.farm_levels[current_level]["upgrade_cost"]
    balance = await bot.economy.get_balance(user_id)
    
    if balance < upgrade_cost:
        await interaction.response.send_message(f"❌ Недостаточно средств! Нужно {upgrade_cost} монет", ephemeral=True)
        return
    
    await bot.economy.update_balance(user_id, -upgrade_cost)
    user_mining_farms[user_id]["level"] = current_level + 1
    
    embed = Design.create_embed("⚡ Ферма улучшена!", 
                              f"Уровень фермы повышен до {current_level + 1}!\n"
                              f"Новый доход: {bot.mining_system.farm_levels[current_level + 1]['income']} монет/6ч", "success")
    await interaction.response.send_message(embed=embed)

# ₿ КОМАНДЫ КРИПТОВАЛЮТЫ
@bot.tree.command(name="крипта", description="Курсы криптовалют")
async def крипта(interaction: discord.Interaction):
    embed = Design.create_embed("₿ КРИПТОВАЛЮТЫ", "Актуальные курсы:", "crypto")
    
    for crypto, price in crypto_prices.items():
        embed.add_field(
            name=crypto,
            value=f"${price:,.2f}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="мой_крипто", description="Мой крипто-портфель")
async def мой_крипто(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if user_id not in user_crypto or not user_crypto[user_id]:
        await interaction.response.send_message("❌ У вас нет криптовалюты", ephemeral=True)
        return
    
    embed = Design.create_embed("₿ Мой крипто-портфель", "", "crypto")
    total_value = 0
    
    for crypto, amount in user_crypto[user_id].items():
        value = amount * crypto_prices[crypto]
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

# 🎪 КОМАНДЫ ИВЕНТОВ
@bot.tree.command(name="ивенты", description="Активные ивенты")
async def ивенты(interaction: discord.Interaction):
    if not active_events:
        embed = Design.create_embed("🎪 Ивенты", "Сейчас нет активных ивентов", "info")
    else:
        embed = Design.create_embed("🎪 АКТИВНЫЕ ИВЕНТЫ", "", "event")
        for event_type, event_data in active_events.items():
            time_left = event_data["end_time"] - datetime.now()
            minutes_left = max(0, int(time_left.total_seconds() // 60))
            
            embed.add_field(
                name=bot.event_system.event_types[event_type]["name"],
                value=f"Осталось: {minutes_left} минут\n{bot.event_system.event_types[event_type]['description']}",
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="запустить_ивент", description="Запустить ивент")
@is_admin()
async def запустить_ивент(interaction: discord.Interaction, тип: str):
    event_types = {
        "дождь": "money_rain"
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

# 👑 АДМИН КОМАНДЫ
@bot.tree.command(name="выдать", description="Выдать монеты")
@is_admin()
async def выдать(interaction: discord.Interaction, пользователь: discord.Member, количество: int):
    if количество <= 0:
        await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
        return
    
    new_balance = await bot.economy.admin_add_money(пользователь.id, количество)
    
    embed = Design.create_embed("💰 Деньги выданы", 
                              f"**Пользователь:** {пользователь.mention}\n"
                              f"**Выдано:** {количество:,} монет\n"
                              f"**Новый баланс:** {new_balance:,} монет", "success")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="удалить_бд", description="Удалить базу данных")
@is_admin()
async def удалить_бд(interaction: discord.Interaction):
    import os
    try:
        if os.path.exists("data/bot.db"):
            os.remove("data/bot.db")
            await bot.db.init_db()
            embed = Design.create_embed("✅ База данных удалена", "Все данные сброшены!", "success")
        else:
            embed = Design.create_embed("ℹ️ База не найдена", "Файл data/bot.db не существует", "info")
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", f"Не удалось удалить БД: {e}", "danger")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="админ", description="Панель администратора")
@is_admin()
async def админ(interaction: discord.Interaction):
    description = (
        "**АДМИН КОМАНДЫ:**\n\n"
        "**Экономика:**\n"
        "`/выдать @user количество` - Выдать монеты\n\n"
        "**NFT система:**\n"
        "`/создать_коллекцию название описание количество` - Создать NFT коллекцию\n\n"
        "**Кейсы:**\n"
        "`/создать_кейс название описание цена` - Создать кейс\n"
        "`/добавить_награду кейс_id тип шанс количество [нфт_id]` - Добавить награду\n\n"
        "**Управление:**\n"
        "`/удалить_бд` - Очистить базу данных\n"
        "`/перезагрузить` - Перезагрузить бота\n"
        "`/запустить_ивент тип` - Запустить ивент"
    )
    
    embed = Design.create_embed("ПАНЕЛЬ АДМИНИСТРАТОРА", description, "premium")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="перезагрузить", description="Перезагрузить бота")
@is_admin()
async def перезагрузить(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    embed = Design.create_embed("🔄 Перезагрузка бота", "Выполняется перезагрузка...", "warning")
    await interaction.followup.send(embed=embed)
    
    success = await bot.reload_bot()
    
    if success:
        embed = Design.create_embed("✅ Перезагрузка завершена", "Бот успешно перезагружен!", "success")
    else:
        embed = Design.create_embed("❌ Ошибка перезагрузки", "Произошла ошибка при перезагрузке", "danger")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'🌐 Серверов: {len(bot.guilds)}')
    
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
        async with aiosqlite.connect(bot.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.author.id,))
            await db.commit()
    
    await bot.process_commands(message)

if __name__ == "__main__":
    try:
        print("🚀 Запуск бота...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")








