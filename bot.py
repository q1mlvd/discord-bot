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

# 🔧 КОНСТАНТЫ
ADMIN_IDS = [1195144951546265675, 766767256742526996, 1078693283695448064, 1138140772097597472, 691904643181314078]
MODERATION_ROLES = [1167093102868172911, 1360243534946373672, 993043931342319636, 1338611327022923910, 1338609155203661915, 1365798715930968244, 1188261847850299514]
THREADS_CHANNEL_ID = 1422557295811887175

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

def is_admin():
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
        "discord": 0x5865F2, "tds": 0xF1C40F, "crypto": 0x16C60C,
        "event": 0x9B59B6, "credit": 0xE74C3C
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
            
            # Новые таблицы
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
                    PRIMARY KEY (user_id)
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
        days_passed = (datetime.now() - (credit["due_date"] - timedelta(days=credit["term_days"]))).days
        total_to_repay = credit["original_amount"] + (credit["original_amount"] * credit["interest_rate"] * days_passed // 100)
        
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
                    {"type": "money", "min": 100, "max": 800, "chance": 100}
                ]
            },
            "rare": {
                "name": "🎁 Редкий лутбокс", 
                "price": 1500,
                "rewards": [
                    {"type": "money", "min": 500, "max": 2000, "chance": 85},
                    {"type": "role", "chance": 15}
                ]
            },
            "legendary": {
                "name": "💎 Легендарный лутбокс",
                "price": 5000,
                "rewards": [
                    {"type": "money", "min": 2000, "max": 10000, "chance": 70},
                    {"type": "role", "chance": 30}
                ]
            },
            "crypto": {
                "name": "₿ Крипто-бокс",
                "price": 3000,
                "rewards": [
                    {"type": "crypto", "chance": 100}
                ]
            }
        }
    
    async def open_lootbox(self, user_id: int, lootbox_type: str):
        lootbox = self.lootboxes.get(lootbox_type)
        if not lootbox:
            return False, "Лутбокс не найден"
        
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
                elif reward["type"] == "role":
                    rewards.append("🎭 Роль (создан тикет)")
                elif reward["type"] == "crypto":
                    crypto_type = random.choice(list(crypto_prices.keys()))
                    amount = random.uniform(0.001, 0.01)
                    if user_id not in user_crypto:
                        user_crypto[user_id] = {}
                    user_crypto[user_id][crypto_type] = user_crypto[user_id].get(crypto_type, 0) + amount
                    rewards.append(f"₿ {amount:.4f} {crypto_type}")
        
        return True, rewards

# 🔧 ИСПРАВЛЕННАЯ СИСТЕМА МАЙНИНГА:

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
            
            # Проверяем когда последний раз собирали
            if "last_collected" in farm and farm["last_collected"]:
                last_collect = datetime.fromisoformat(farm["last_collected"])
                time_passed = datetime.now() - last_collect
                if time_passed.seconds < 43200:  # 12 часов
                    hours_left = 12 - (time_passed.seconds // 3600)
                    minutes_left = (43200 - time_passed.seconds) // 60
                    return False, f"Доход можно собирать раз в 12 часов! Осталось: {hours_left}ч {minutes_left % 60}м"
            
            # Начисляем доход
            income = self.farm_levels[farm["level"]]["income"]
            await self.economy.update_balance(user_id, income)
            
            # Обновляем время сбора
            user_mining_farms[user_id]["last_collected"] = datetime.now().isoformat()
            
            return True, f"✅ Собрано {income} монет с фермы! Следующий сбор через 12 часов"
            
        except Exception as e:
            print(f"Ошибка при сборе дохода: {e}")
            return False, "❌ Произошла ошибка при сборе дохода"

# 🔧 ИСПРАВЛЕННАЯ КОМАНДА СБОРА ДОХОДА:
@bot.tree.command(name="собрать_доход", description="Собрать доход с фермы")
async def собрать_доход(interaction: discord.Interaction):
    # Отвечаем сразу чтобы бот не "зависал"
    await interaction.response.defer(ephemeral=True)
    
    try:
        success, message = await bot.mining_system.collect_income(interaction.user.id)
        
        if success:
            embed = Design.create_embed("💰 Доход собран!", message, "success")
        else:
            embed = Design.create_embed("❌ Ошибка", message, "danger")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        embed = Design.create_embed("❌ Критическая ошибка", 
                                  "Произошла ошибка при обработке запроса", "danger")
        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"Ошибка в команде собрать_доход: {e}")

# 🔧 ТАКЖЕ ОБНОВИ КОМАНДУ ФЕРМЫ:
@bot.tree.command(name="ферма", description="Информация о майнинг ферме")
async def ферма(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if user_id not in user_mining_farms:
        embed = Design.create_embed("⛏️ Майнинг ферма", 
                                  "У вас еще нет фермы!\n"
                                  "Используйте `/создать_ферму` чтобы начать майнить", "info")
    else:
        farm = user_mining_farms[user_id]
        level_data = bot.mining_system.farm_levels[farm["level"]]
        
        # Рассчитываем оставшееся время
        can_collect = True
        time_left = "✅ Можно собрать"
        
        if "last_collected" in farm and farm["last_collected"]:
            last_collect = datetime.fromisoformat(farm["last_collected"])
            time_passed = datetime.now() - last_collect
            if time_passed.seconds < 43200:
                can_collect = False
                hours_left = 11 - (time_passed.seconds // 3600)
                minutes_left = 59 - ((time_passed.seconds % 3600) // 60)
                time_left = f"⏳ Через {hours_left}ч {minutes_left}м"
        
        embed = Design.create_embed("⛏️ Ваша ферма", 
                                  f"**Уровень:** {farm['level']}\n"
                                  f"**Доход:** {level_data['income']} монет/12ч\n"
                                  f"**Следующий уровень:** {level_data['upgrade_cost']} монет\n"
                                  f"**Статус:** {time_left}", "info")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 🎪 СИСТЕМА ИВЕНТОВ
class EventSystem:
    def __init__(self, economy: EconomySystem):
        self.economy = economy
        self.event_types = {
            "money_rain": {"name": "💰 Денежный дождь", "duration": 300, "multiplier": 2},
            "lucky_day": {"name": "🎰 Удачный день", "duration": 600, "casino_bonus": True},
            "work_bonus": {"name": "💼 Работяга", "duration": 1800, "work_multiplier": 3},
            "giveaway": {"name": "🎁 Раздача", "duration": 300, "giveaway": True}
        }
    
    async def start_event(self, event_type: str):
        event = self.event_types.get(event_type)
        if not event:
            return False
        
        active_events[event_type] = {
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(seconds=event["duration"]),
            "data": event
        }
        return True

# 🏪 МАГАЗИН
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

# 🎰 КАЗИНО
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

# 🛡️ МОДЕРАЦИЯ
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

# 🎵 МУЗЫКА
class MusicPlayer:
    def __init__(self):
        self.queues = {}
        self.voice_clients = {}
        self.now_playing = {}
        
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
        
        self.ytdl = yt_dlp.YoutubeDL(self.ytdl_format_options)

    def get_queue(self, guild_id: int):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    async def connect_to_voice_channel(self, interaction: discord.Interaction):
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
        voice_client = await self.connect_to_voice_channel(interaction)
        if not voice_client:
            return
        
        try:
            data = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.ytdl.extract_info(query, download=False)
            )
            
            if 'entries' in data:
                data = data['entries'][0]
            
            url = data['url']
            title = data.get('title', 'Неизвестный трек')
            duration = data.get('duration', 0)
            
            if duration:
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "Неизвестно"
            
            queue = self.get_queue(interaction.guild.id)
            track_info = {
                'url': url,
                'title': title,
                'duration': duration_str,
                'requester': interaction.user
            }
            queue.append(track_info)
            
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
            print(f"Ошибка музыки: {e}")

    async def play_next(self, guild_id: int, channel=None):
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
                    print(f'Ошибка воспроизведения: {error}')
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
                print(f'Ошибка воспроизведения: {e}')
                asyncio.run_coroutine_threadsafe(self.play_next(guild_id, channel), voice_client.loop)

    def get_queue_embed(self, guild_id: int):
        queue = self.get_queue(guild_id)
        embed = Design.create_embed("🎵 Очередь воспроизведения", "", "music")
        
        if guild_id in self.now_playing:
            current = self.now_playing[guild_id]
            embed.add_field(
                name="🎵 Сейчас играет",
                value=f"**{current['title']}**\n⏱️ {current['duration']} | 👤 {current['requester'].display_name}",
                inline=False
            )
        
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
        if guild_id in self.voice_clients:
            voice_client = self.voice_clients[guild_id]
            if voice_client.is_playing():
                voice_client.stop()
            
            self.queues[guild_id] = []
            if guild_id in self.now_playing:
                del self.now_playing[guild_id]
            
            await voice_client.disconnect()
            del self.voice_clients[guild_id]

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
        
        # Новые системы
        self.credit_system = CreditSystem(self.economy)
        self.lootbox_system = LootboxSystem(self.economy)
        self.mining_system = MiningSystem(self.economy)
        self.event_system = EventSystem(self.economy)
        
        self.start_time = datetime.now()
    
    async def setup_hook(self):
        await self.db.init_db()
        try:
            synced = await self.tree.sync()
            print(f"✅ Синхронизировано {len(synced)} команд")
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")
        
        # Запуск фоновых задач
        self.update_crypto_prices.start()
        self.check_credit_debts.start()
        self.random_events.start()

    @tasks.loop(minutes=30)
    async def update_crypto_prices(self):
        for crypto in crypto_prices:
            change = random.uniform(-0.1, 0.1)
            crypto_prices[crypto] = max(0.01, crypto_prices[crypto] * (1 + change))

    @tasks.loop(hours=24)
    async def check_credit_debts(self):
        current_time = datetime.now()
        for user_id, credit in list(user_credits.items()):
            if current_time > credit["due_date"]:
                del user_credits[user_id]
                print(f"Просрочен кредит у пользователя {user_id}")

    @tasks.loop(hours=3)
    async def random_events(self):
        if random.random() < 0.3:
            event_type = random.choice(list(self.event_system.event_types.keys()))
            await self.event_system.start_event(event_type)
            
            channel = self.get_channel(THREADS_CHANNEL_ID)
            if channel:
                embed = Design.create_embed(
                    "🎉 СЛУЧАЙНЫЙ ИВЕНТ!",
                    f"**{self.event_system.event_types[event_type]['name']}**\n"
                    f"Активен 5 минут! Успейте поучаствовать!",
                    "event"
                )
                await channel.send(embed=embed)

    async def weekly_reset_task(self):
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

# 🔧 ФУНКЦИИ ПРОВЕРОК
def parse_time(time_str: str) -> int:
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
    try:
        ban_entry = await interaction.guild.fetch_ban(пользователь)
        embed = Design.create_embed("⚠️ Пользователь забанен", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Причина:** {ban_entry.reason or 'Не указана'}", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return True
    except discord.NotFound:
        return False

# 💰 СУЩЕСТВУЮЩИЕ КОМАНДЫ ЭКОНОМИКИ
@bot.tree.command(name="баланс", description="Проверить баланс")
async def баланс(interaction: discord.Interaction, пользователь: Optional[discord.Member] = None):
    user = пользователь or interaction.user
    balance = await bot.economy.get_balance(user.id)
    embed = Design.create_embed("💰 Баланс", f"**{user.display_name}**\nБаланс: `{balance:,} монет`", "economy")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ежедневно", description="Получить ежедневную награду")
async def ежедневно(interaction: discord.Interaction):
    user_data = await bot.economy.get_user_data(interaction.user.id)
    
    if user_data["daily_claimed"]:
        last_claim = datetime.fromisoformat(user_data["daily_claimed"])
        if (datetime.now() - last_claim).days < 1:
            embed = Design.create_embed("⏳ Уже получали!", "Приходите завтра за новой наградой", "warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    reward = random.randint(100, 500)
    new_balance = await bot.economy.update_balance(interaction.user.id, reward)
    
    async with aiosqlite.connect(bot.db.db_path) as db:
        await db.execute('UPDATE users SET daily_claimed = ? WHERE user_id = ?', (datetime.now().isoformat(), interaction.user.id))
        await db.commit()
    
    embed = Design.create_embed("🎁 Ежедневная награда", f"**+{reward} монет!**\nНовый баланс: `{new_balance:,} монет`", "success")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="работа", description="Заработать деньги")
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
    
    # Налог 5%
    tax = сумма * 0.05
    net_amount = сумма - tax
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

@bot.tree.command(name="ограбить", description="Ограбить пользователя")
async def ограбить(interaction: discord.Interaction, жертва: discord.Member):
    if жертва.id == interaction.user.id:
        await interaction.response.send_message("❌ Нельзя ограбить самого себя!", ephemeral=True)
        return
    
    victim_balance = await bot.economy.get_balance(жертва.id)
    if victim_balance < 100:
        await interaction.response.send_message("❌ У жертвы меньше 100 монет!", ephemeral=True)
        return
    
    # Страхование
    insurance_active = user_insurance.get(interaction.user.id, False)
    
    if random.random() < 0.4:
        stolen = random.randint(100, min(500, victim_balance))
        await bot.economy.update_balance(жертва.id, -stolen)
        await bot.economy.update_balance(interaction.user.id, stolen)
        embed = Design.create_embed("💰 Ограбление успешно!", f"**Украдено:** {stolen} монет", "warning")
    else:
        fine = random.randint(50, 200)
        if insurance_active:
            fine = fine // 2  # Страхование возвращает 50%
            embed = Design.create_embed("🚓 Пойманы! (Со страховкой)", f"**Штраф:** {fine} монет (50% возвращено)", "warning")
        else:
            embed = Design.create_embed("🚓 Пойманы!", f"**Штраф:** {fine} монет", "danger")
        
        await bot.economy.update_balance(interaction.user.id, -fine)
    
    await interaction.response.send_message(embed=embed)

# 🏪 СУЩЕСТВУЮЩИЕ КОМАНДЫ МАГАЗИНА
@bot.tree.command(name="магазин", description="🎪 Главное меню магазина")
async def магазин(interaction: discord.Interaction):
    embed = Design.create_embed("🎪 МАГАЗИН ПЕХОТА ЗЕНИТА", """
**📦 КАТЕГОРИИ ТОВАРОВ:**

🎮 **TDS/TDX** - Башни, прохождение
🔴 **Roblox** - Робуксы  
🥊 **Blox Fruits** - Мифические фрукты
⚡ **Discord** - Премиум, роли

💼 **Мои заказы** - `/мои_заказы`
🛒 **Купить товар** - `/купить [ID]`

💬 **Поддержка:** <@691904643181314078>
    """, "shop")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="категория", description="📦 Показать товары категории")
async def категория(interaction: discord.Interaction, название: str):
    category_map = {
        "tds": "🎮 TDS/TDX", "tdx": "🎮 TDS/TDX", "roblox": "🔴 Roblox",
        "blox": "🥊 Blox Fruits", "blox fruits": "🥊 Blox Fruits", "discord": "⚡ Discord"
    }
    
    if название.lower() in category_map:
        название = category_map[название.lower()]
    
    if название not in bot.shop.categories:
        available_categories = "\n".join([f"• `{cat}`" for cat in bot.shop.categories.keys()])
        await interaction.response.send_message(f"❌ Категория не найдена!\n\n**Доступные категории:**\n{available_categories}", ephemeral=True)
        return
    
    category = bot.shop.categories[название]
    embed = Design.create_embed(f"📦 {название}", f"Товаров: {len(category['items'])}", category["color"])
    
    for item_id, item in category["items"].items():
        if item.get("per_unit"):
            price_info = f"💰 {item['price']} руб/ед."
        else:
            price_info = f"💰 {item['price']} руб"
        
        embed.add_field(name=f"{item['name']} (ID: {item_id})", value=price_info, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="купить", description="🛒 Купить товар")
async def купить(interaction: discord.Interaction, id_товара: int, количество: int = 1, детали: str = ""):
    if id_товара in [7, 8] and количество < 100:
        await interaction.response.send_message("❌ Минимальная покупка Robux: 100", ephemeral=True)
        return
    
    result = await bot.shop.create_order(interaction.user.id, id_товара, количество, детали)
    
    if not result["success"]:
        await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
        return
    
    product = result["product"]
    order_id = result["order_id"]
    total_price = result["total_price"]
    quantity = result["quantity"]
    
    embed = Design.create_embed("🛒 Заказ создан!", f"**Номер заказа:** `#{order_id}`", "success")
    embed.add_field(name="📦 Товар", value=product["name"], inline=False)
    embed.add_field(name="🔢 Количество", value=str(quantity), inline=True)
    embed.add_field(name="💰 Сумма", value=f"{total_price:.2f} руб", inline=True)
    
    if детали:
        embed.add_field(name="📝 Детали", value=детали, inline=False)
    
    embed.add_field(name="💳 Оплата", value=bot.shop.payment_details, inline=False)
    embed.add_field(name="📸 Подтверждение", value="После оплаты отправьте скриншот перевода в этот чат", inline=False)
    
    await interaction.response.send_message(embed=embed)
    
    try:
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        for admin_id in ADMIN_IDS:
            admin = guild.get_member(admin_id)
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        channel = await guild.create_text_channel(
            f'заказ-{order_id}-{interaction.user.display_name}',
            overwrites=overwrites,
            topic=f'Заказ #{order_id} | {product["name"]} | {interaction.user}'
        )
        
        ticket_embed = Design.create_embed(
            f"🎫 Тикет заказа #{order_id}", 
            f"**Покупатель:** {interaction.user.mention}\n"
            f"**Товар:** {product['name']}\n"
            f"**Количество:** {quantity}\n"
            f"**Сумма:** {total_price:.2f} руб\n"
            f"**Статус:** Ожидает оплаты", 
            "warning"
        )
        
        if детали:
            ticket_embed.add_field(name="📝 Детали заказа", value=детали, inline=False)
        
        await channel.send(embed=ticket_embed)
        await channel.send("⏳ Ожидаем скриншот оплаты...")
        
    except Exception as e:
        print(f"Ошибка создания тикета: {e}")
        await interaction.followup.send("❌ Не удалось создать тикет заказа, но заказ записан. Обратитесь к администратору.", ephemeral=True)

@bot.tree.command(name="мои_заказы", description="📋 История моих заказов")
async def мои_заказы(interaction: discord.Interaction):
    orders = await bot.shop.get_user_orders(interaction.user.id)
    
    if not orders:
        embed = Design.create_embed("📋 Мои заказы", "У вас пока нет заказов", "info")
        await interaction.response.send_message(embed=embed)
        return
    
    embed = Design.create_embed("📋 История заказов", f"Всего заказов: {len(orders)}", "shop")
    
    for order in orders[:5]:
        order_id, product_name, quantity, price, status, order_time = order
        
        status_emoji = {
            "ожидает оплаты": "⏳", "оплачен": "✅", "в процессе": "🔄",
            "выполнен": "🎉", "отменен": "❌"
        }.get(status, "❓")
        
        order_date = datetime.fromisoformat(order_time).strftime("%d.%m.%Y %H:%M")
        
        embed.add_field(
            name=f"{status_emoji} Заказ #{order_id}",
            value=f"**{product_name}**\nКоличество: {quantity}\nСумма: {price:.2f} руб\nСтатус: {status}\nДата: {order_date}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# 🎰 СУЩЕСТВУЮЩИЕ КОМАНДЫ КАЗИНО
@bot.tree.command(name="слоты", description="Играть в слоты")
async def слоты(interaction: discord.Interaction, ставка: int):
    result = await bot.casino.play_slots(interaction.user.id, ставка)
    
    if not result["success"]:
        await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
        return
    
    symbols = " | ".join(result["result"])
    
    if result["multiplier"] > 0:
        embed = Design.create_embed("🎰 Выигрыш!", f"**{symbols}**\nВыигрыш: {result['win_amount']} монет", "success")
    else:
        embed = Design.create_embed("🎰 Проигрыш", f"**{symbols}**\nПотеряно: {ставка} монет", "danger")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="монетка", description="Подбросить монетку")
async def монетка(interaction: discord.Interaction, ставка: int, выбор: str):
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
        embed = Design.create_embed("🪙 Победа!", f"Выпало: {outcome}\nВыигрыш: {ставка} монет", "success")
    else:
        await bot.economy.update_balance(interaction.user.id, -ставка)
        embed = Design.create_embed("🪙 Проигрыш", f"Выпало: {outcome}\nПотеряно: {ставка} монет", "danger")
    
    await interaction.response.send_message(embed=embed)

# 🏆 СУЩЕСТВУЮЩИЕ КОМАНДЫ УРОВНЕЙ
@bot.tree.command(name="уровень", description="Проверить уровень")
async def уровень(interaction: discord.Interaction, пользователь: Optional[discord.Member] = None):
    user = пользователь or interaction.user
    user_data = await bot.economy.get_user_data(user.id)
    
    level = user_data["level"]
    xp = user_data["xp"]
    xp_needed = level * 100
    
    embed = Design.create_embed("🏆 Уровень", 
                              f"**{user.display_name}**\n"
                              f"Уровень: {level}\n"
                              f"Опыт: {xp}/{xp_needed}", "primary")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="топ", description="Топ игроков")
async def топ(interaction: discord.Interaction, тип: str = "уровень"):
    async with aiosqlite.connect(bot.db.db_path) as db:
        if тип == "уровень":
            cursor = await db.execute('SELECT user_id, level, xp FROM users ORDER BY level DESC, xp DESC LIMIT 10')
            title = "🏆 Топ по уровням"
        else:
            cursor = await db.execute('SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10')
            title = "💰 Топ по деньгам"
        
        top_data = await cursor.fetchall()
    
    embed = Design.create_embed(title, "")
    for i, row in enumerate(top_data, 1):
        user_id = row[0]
        value = row[1] if len(row) == 2 else f"Ур. {row[1]} (XP: {row[2]})"
        
        try:
            user = await bot.fetch_user(user_id)
            name = user.display_name
        except:
            name = f"User {user_id}"
        
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        embed.add_field(name=f"{medal} {name}", value=str(value), inline=False)
    
    await interaction.response.send_message(embed=embed)

# 🛡️ СУЩЕСТВУЮЩИЕ КОМАНДЫ МОДЕРАЦИИ
@bot.tree.command(name="варн", description="Выдать варн пользователю (3 варна = мут на 1 час)")
@commands.has_permissions(manage_messages=True)
async def варн(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    try:
        if await check_user_banned(interaction, пользователь):
            return
        
        if await check_user_muted(interaction, пользователь):
            return
        
        if пользователь.id not in user_warns:
            user_warns[пользователь.id] = 0
        
        user_warns[пользователь.id] += 1
        current_warns = user_warns[пользователь.id]
        
        if current_warns >= 3:
            mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await interaction.guild.create_role(name="Muted")
                
                for channel in interaction.guild.channels:
                    await channel.set_permissions(mute_role, send_messages=False, speak=False)
            
            await пользователь.add_roles(mute_role)
            
            mute_data[пользователь.id] = {
                'end_time': datetime.now() + timedelta(hours=1),
                'reason': "Получено 3 предупреждения",
                'moderator': interaction.user.display_name,
                'guild_id': interaction.guild.id
            }
            
            user_warns[пользователь.id] = 0
            
            embed = Design.create_embed("⚠️ МУТ за 3 варна", 
                                      f"**Пользователь:** {пользователь.mention}\n"
                                      f"**Причина:** Получено 3 предупреждения\n"
                                      f"**Длительность:** 1 час\n"
                                      f"**Последнее нарушение:** {причина}", "danger")
            await interaction.response.send_message(embed=embed)
            
            await asyncio.sleep(3600)
            if mute_role in пользователь.roles and пользователь.id in mute_data:
                await пользователь.remove_roles(mute_role)
                del mute_data[пользователь.id]
                embed = Design.create_embed("✅ Мут снят", f"Мут с пользователя {пользователь.mention} снят", "success")
                await interaction.channel.send(embed=embed)
            
        else:
            embed = Design.create_embed("⚠️ Варн", 
                                      f"**Пользователь:** {пользователь.mention}\n"
                                      f"**Причина:** {причина}\n"
                                      f"**Текущее количество варнов:** {current_warns}/3\n"
                                      f"**Следующий варн:** мут на 1 час", "warning")
            await interaction.response.send_message(embed=embed)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="мут", description="Замутить пользователя (с, м, ч, д, н)")
@commands.has_permissions(manage_roles=True)
async def мут(interaction: discord.Interaction, пользователь: discord.Member, время: str, причина: str = "Не указана"):
    try:
        if await check_user_banned(interaction, пользователь):
            return
        
        if await check_user_muted(interaction, пользователь):
            return
        
        seconds = parse_time(время)
        
        if seconds <= 0:
            await interaction.response.send_message("❌ Неверный формат времени! Используйте: 1с, 5м, 1ч, 2д, 1н", ephemeral=True)
            return
        
        if seconds > 604800:
            await interaction.response.send_message("❌ Максимальное время мута - 1 неделя", ephemeral=True)
            return
        
        mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await interaction.guild.create_role(name="Muted")
            
            for channel in interaction.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        
        await пользователь.add_roles(mute_role)
        
        mute_data[пользователь.id] = {
            'end_time': datetime.now() + timedelta(seconds=seconds),
            'reason': причина,
            'moderator': interaction.user.display_name,
            'guild_id': interaction.guild.id
        }
        
        time_display = ""
        if seconds >= 604800:
            time_display = f"{seconds // 604800} недель"
        elif seconds >= 86400:
            time_display = f"{seconds // 86400} дней"
        elif seconds >= 3600:
            time_display = f"{seconds // 3600} часов"
        elif seconds >= 60:
            time_display = f"{seconds // 60} минут"
        else:
            time_display = f"{seconds} секунд"
        
        embed = Design.create_embed("✅ Мут", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Длительность:** {time_display}\n"
                                  f"**Причина:** {причина}\n"
                                  f"**Замутил:** {interaction.user.mention}", "success")
        await interaction.response.send_message(embed=embed)
        
        await asyncio.sleep(seconds)
        if mute_role in пользователь.roles and пользователь.id in mute_data:
            await пользователь.remove_roles(mute_role)
            del mute_data[пользователь.id]
            embed = Design.create_embed("✅ Мут снят", f"Мут с пользователя {пользователь.mention} снят", "success")
            await interaction.channel.send(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="бан", description="Забанить пользователя")
@commands.has_permissions(ban_members=True)
async def бан(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    try:
        if await check_user_banned(interaction, пользователь):
            return
        
        await пользователь.ban(reason=причина)
        embed = Design.create_embed("✅ Бан", f"Пользователь {пользователь.mention} забанен\n**Причина:** {причина}", "success")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="кик", description="Кикнуть пользователя")
@commands.has_permissions(kick_members=True)
async def кик(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    try:
        await пользователь.kick(reason=причина)
        embed = Design.create_embed("✅ Кик", f"Пользователь {пользователь.mention} кикнут\n**Причина:** {причина}", "success")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="очистить", description="Очистить сообщения")
@commands.has_permissions(manage_messages=True)
async def очистить(interaction: discord.Interaction, количество: int):
    try:
        if количество > 100:
            await interaction.response.send_message("❌ Можно удалить не более 100 сообщений за раз", ephemeral=True)
            return
            
        deleted = await interaction.channel.purge(limit=количество + 1)
        embed = Design.create_embed("✅ Очистка", f"Удалено {len(deleted) - 1} сообщений", "success")
        await interaction.response.send_message(embed=embed, delete_after=5)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="тикет", description="Создать тикет")
async def тикет(interaction: discord.Interaction, причина: str):
    try:
        channel = await bot.moderation.create_ticket(interaction.user, причина)
        embed = Design.create_embed("🎫 Тикет", f"Создан тикет: {channel.mention}", "success")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

# 🎵 СУЩЕСТВУЮЩИЕ КОМАНДЫ МУЗЫКИ
@bot.tree.command(name="play", description="Добавить трек в очередь (YouTube ссылка или название)")
async def play(interaction: discord.Interaction, запрос: str):
    await bot.music.play_music(interaction, запрос)

@bot.tree.command(name="стоп", description="Остановить музыку и отключиться")
async def стоп(interaction: discord.Interaction):
    try:
        await bot.music.stop_music(interaction.guild.id)
        embed = Design.create_embed("⏹️ Музыка", "Воспроизведение остановлено", "music")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="скип", description="Пропустить текущий трек")
async def скип(interaction: discord.Interaction):
    try:
        guild_id = interaction.guild.id
        if guild_id in bot.music.voice_clients:
            voice_client = bot.music.voice_clients[guild_id]
            if voice_client.is_playing():
                voice_client.stop()
                embed = Design.create_embed("⏭️ Музыка", "Трек пропущен", "music")
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("❌ Сейчас ничего не играет", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Бот не подключен к голосовому каналу", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="очередь", description="Показать очередь треков")
async def очередь(interaction: discord.Interaction):
    embed = bot.music.get_queue_embed(interaction.guild.id)
    await interaction.response.send_message(embed=embed)

# 🔧 СУЩЕСТВУЮЩИЕ КОМАНДЫ УТИЛИТ
@bot.tree.command(name="сервер", description="Информация о сервере")
async def сервер(interaction: discord.Interaction):
    guild = interaction.guild
    embed = Design.create_embed("🏠 Сервер", 
                              f"**{guild.name}**\n"
                              f"Участников: {guild.member_count}\n"
                              f"Каналов: {len(guild.channels)}\n"
                              f"Создан: {guild.created_at.strftime('%d.%m.%Y')}", "info")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="юзер", description="Информация о пользователе")
async def юзер(interaction: discord.Interaction, пользователь: Optional[discord.Member] = None):
    user = пользователь or interaction.user
    embed = Design.create_embed("👤 Пользователь", 
                              f"**{user.display_name}**\n"
                              f"ID: {user.id}\n"
                              f"Присоединился: {user.joined_at.strftime('%d.%m.%Y') if user.joined_at else 'N/A'}", "info")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="статистика", description="Статистика бота")
async def статистика(interaction: discord.Interaction):
    uptime = datetime.now() - bot.start_time
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    
    embed = Design.create_embed("📊 Статистика", 
                              f"Серверов: {len(bot.guilds)}\n"
                              f"Пользователей: {len(bot.users)}\n"
                              f"Аптайм: {uptime.days}д {hours}ч {minutes}м\n"
                              f"Пинг: {round(bot.latency * 1000)}мс", "info")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="помощь", description="Помощь по командам")
async def помощь(interaction: discord.Interaction):
    embed = Design.create_embed("🎪 ПОМОЩЬ", """
**💰 ЭКОНОМИКА:**
`/баланс` `/ежедневно` `/работа` `/передать` `/ограбить`

**🏪 МАГАЗИН:**
`/магазин` `/категория` `/купить` `/мои_заказы`

**🎰 КАЗИНО:**
`/слоты` `/монетка`

**🏆 УРОВНИ:**
`/уровень` `/топ`

**🛡️ МОДЕРАЦИЯ:**
`/модер` - Панель модератора
`/мут` `/бан` `/кик` `/очистить` `/варн` `/тикет`

**🎵 МУЗЫКА:**
`/play` `/стоп` `/скип` `/очередь`

**🔧 УТИЛИТЫ:**
`/сервер` `/юзер` `/статистика`

**🏦 НОВЫЕ СИСТЕМЫ:**
`/кредит` `/вернуть_кредит` `/мой_кредит`
`/лутбоксы` `/открыть_лутбокс`
`/ферма` `/создать_ферму` `/собрать_доход` `/улучшить_ферму`
`/крипта` `/ивенты`
    """, "primary")
    await interaction.response.send_message(embed=embed)

# 👑 СУЩЕСТВУЮЩИЕ АДМИН КОМАНДЫ
@bot.tree.command(name="выдать", description="📊 [АДМИН] Выдать монеты пользователю")
@is_admin()
async def выдать(interaction: discord.Interaction, пользователь: discord.Member, количество: int):
    if количество <= 0:
        await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
        return
    
    new_balance = await bot.economy.admin_add_money(пользователь.id, количество)
    
    embed = Design.create_embed("💰 АДМИН: Деньги выданы", 
                              f"**Пользователь:** {пользователь.mention}\n"
                              f"**Выдано:** {количество:,} монет\n"
                              f"**Новый баланс:** {new_balance:,} монет\n"
                              f"**Выдал:** {interaction.user.mention}", "success")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="забрать", description="📊 [АДМИН] Забрать монеты у пользователя")
@is_admin()
async def забрать(interaction: discord.Interaction, пользователь: discord.Member, количество: int):
    if количество <= 0:
        await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
        return
    
    current_balance = await bot.economy.get_balance(пользователь.id)
    if количество > current_balance:
        количество = current_balance
    
    new_balance = await bot.economy.admin_add_money(пользователь.id, -количество)
    
    embed = Design.create_embed("💰 АДМИН: Деньги забраны", 
                              f"**Пользователь:** {пользователь.mention}\n"
                              f"**Забрано:** {количество:,} монет\n"
                              f"**Новый баланс:** {new_balance:,} монет\n"
                              f"**Забрал:** {interaction.user.mention}", "warning")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="установить", description="📊 [АДМИН] Установить баланс пользователя")
@is_admin()
async def установить(interaction: discord.Interaction, пользователь: discord.Member, количество: int):
    if количество < 0:
        await interaction.response.send_message("❌ Баланс не может быть отрицательным!", ephemeral=True)
        return
    
    new_balance = await bot.economy.admin_set_money(пользователь.id, количество)
    
    embed = Design.create_embed("💰 АДМИН: Баланс установлен", 
                              f"**Пользователь:** {пользователь.mention}\n"
                              f"**Новый баланс:** {new_balance:,} монет\n"
                              f"**Установил:** {interaction.user.mention}", "success")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="сбросить", description="📊 [АДМИН] Сбросить кулдауны пользователя")
@is_admin()
async def сбросить(interaction: discord.Interaction, пользователь: discord.Member):
    await bot.economy.admin_reset_cooldowns(пользователь.id)
    
    embed = Design.create_embed("⏰ АДМИН: Кулдауны сброшены", 
                              f"**Пользователь:** {пользователь.mention}\n"
                              f"**Сброшены:** ежедневные награды, работа\n"
                              f"**Сбросил:** {interaction.user.mention}", "success")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="админ", description="📊 [АДМИН] Панель администратора")
@is_admin()
async def админ(interaction: discord.Interaction):
    embed = Design.create_embed("👑 ПАНЕЛЬ АДМИНИСТРАТОРА", """
**Доступные команды:**
    
💰 **Управление деньгами:**
`/выдать @user сумма` - Выдать монеты
`/забрать @user сумма` - Забрать монеты  
`/установить @user сумма` - Установить баланс

⏰ **Управление кулдаунами:**
`/сбросить @user` - Сбросить кулдауны

📊 **Информация:**
`/баланс @user` - Проверить баланс
`/топ` - Статистика сервера
    """, "premium")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 🆕 НОВЫЕ КОМАНДЫ

# 🏦 КОМАНДЫ КРЕДИТОВ
class CreditModal(discord.ui.Modal):
    def __init__(self, company: str, bot_instance):
        self.company = company
        self.bot = bot_instance
        super().__init__(title=f"Кредит в {bot_instance.credit_system.companies[company]['name']}")
        
        self.amount = discord.ui.TextInput(
            label="Сумма кредита",
            placeholder=f"Введите сумму от {bot_instance.credit_system.companies[company]['min_amount']} до {bot_instance.credit_system.companies[company]['max_amount']}",
            required=True
        )
        self.add_item(self.amount)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            success, message = await self.bot.credit_system.take_credit(interaction.user.id, self.company, amount)
            
            if success:
                embed = Design.create_embed("✅ Кредит одобрен!", message, "success")
            else:
                embed = Design.create_embed("❌ Ошибка", message, "danger")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Введите корректную сумму!", ephemeral=True)

class CreditView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=60)
        self.bot = bot_instance
    
    @discord.ui.button(label="🚀 Быстрые Деньги", style=discord.ButtonStyle.primary)
    async def fast_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreditModal("fast_money", self.bot))
    
    @discord.ui.button(label="🛡️ Надежный Кредит", style=discord.ButtonStyle.success)
    async def reliable_credit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreditModal("reliable_credit", self.bot))
    
    @discord.ui.button(label="💎 Премиум Финанс", style=discord.ButtonStyle.danger)
    async def premium_finance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreditModal("premium_finance", self.bot))

@bot.tree.command(name="кредит", description="Взять кредит в микро-займах")
async def кредит(interaction: discord.Interaction):
    embed = Design.create_embed("🏦 МИКРО-ЗАЙМЫ", "Выберите компанию для кредита:", "credit")
    
    for company_id, company in bot.credit_system.companies.items():
        embed.add_field(
            name=f"{company['name']}",
            value=f"Сумма: {company['min_amount']:,}-{company['max_amount']:,} монет\n"
                  f"Процент: {company['interest_rate']}% в день\n"
                  f"Срок: {company['term_days']} дней\n"
                  f"Штраф: {company['penalty']}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, view=CreditView(bot), ephemeral=True)

@bot.tree.command(name="вернуть_кредит", description="Вернуть кредит")
async def вернуть_кредит(interaction: discord.Interaction):
    success, message = await bot.credit_system.repay_credit(interaction.user.id)
    
    if success:
        embed = Design.create_embed("✅ Кредит погашен!", message, "success")
    else:
        embed = Design.create_embed("❌ Ошибка", message, "danger")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="мой_кредит", description="Информация о моем кредите")
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
                              f"**Процент:** {credit['interest_rate']}% в день\n"
                              f"**Вернуть до:** {credit['due_date'].strftime('%d.%m.%Y')}\n"
                              f"**Осталось дней:** {max(0, days_left)}", "credit")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 🎁 КОМАНДЫ ЛУТБОКСОВ
@bot.tree.command(name="лутбоксы", description="Просмотреть доступные лутбоксы")
async def лутбоксы(interaction: discord.Interaction):
    embed = Design.create_embed("🎁 ЛУТБОКСЫ", "Откройте лутбокс и получите случайные награды!", "premium")
    
    for lootbox_id, lootbox in bot.lootbox_system.lootboxes.items():
        rewards_text = ""
        for reward in lootbox["rewards"]:
            if reward["type"] == "money":
                rewards_text += f"💰 Деньги: {reward['min']}-{reward['max']} монет ({reward['chance']}%)\n"
            elif reward["type"] == "role":
                rewards_text += f"🎭 Роль (тикет) ({reward['chance']}%)\n"
            elif reward["type"] == "crypto":
                rewards_text += f"₿ Криптовалюта ({reward['chance']}%)\n"
        
        embed.add_field(
            name=f"{lootbox['name']} - {lootbox['price']} монет",
            value=rewards_text,
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="открыть_лутбокс", description="Купить и открыть лутбокс")
async def открыть_лутбокс(interaction: discord.Interaction, тип: str):
    success, result = await bot.lootbox_system.open_lootbox(interaction.user.id, тип)
    
    if not success:
        await interaction.response.send_message(f"❌ {result}", ephemeral=True)
        return
    
    lootbox = bot.lootbox_system.lootboxes[тип]
    embed = Design.create_embed(f"🎁 Открыт {lootbox['name']}!", "", "success")
    
    for reward in result:
        embed.add_field(name="🎉 Награда", value=reward, inline=False)
        
        if "Роль" in reward:
            try:
                channel = bot.get_channel(THREADS_CHANNEL_ID)
                if channel:
                    thread = await channel.create_thread(
                        name=f"роль-{interaction.user.display_name}",
                        type=discord.ChannelType.public_thread
                    )
                    
                    role_embed = Design.create_embed(
                        "🎭 ВЫПАЛА РОЛЬ ИЗ ЛУТБОКСА!",
                        f"**Пользователь:** {interaction.user.mention}\n"
                        f"**Тип лутбокса:** {lootbox['name']}\n"
                        f"**Обсудите какую роль выдать на 3 дня**",
                        "premium"
                    )
                    
                    ping_text = " ".join([f"<@&{role_id}>" for role_id in MODERATION_ROLES[:2]])
                    await thread.send(f"{ping_text}")
                    await thread.send(embed=role_embed)
            except Exception as e:
                print(f"Ошибка создания треда для роли: {e}")
    
    await interaction.response.send_message(embed=embed)

# ⛏️ КОМАНДЫ МАЙНИНГА
@bot.tree.command(name="ферма", description="Информация о майнинг ферме")
async def ферма(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if user_id not in user_mining_farms:
        embed = Design.create_embed("⛏️ Майнинг ферма", 
                                  "У вас еще нет фермы!\n"
                                  "Используйте `/создать_ферму` чтобы начать майнить", "info")
    else:
        farm = user_mining_farms[user_id]
        level_data = bot.mining_system.farm_levels[farm["level"]]
        
        can_collect = True
        if "last_collected" in farm:
            last_collect = datetime.fromisoformat(farm["last_collected"])
            can_collect = (datetime.now() - last_collect).seconds >= 43200
        
        embed = Design.create_embed("⛏️ Ваша ферма", 
                                  f"**Уровень:** {farm['level']}\n"
                                  f"**Доход:** {level_data['income']} монет/12ч\n"
                                  f"**Следующий уровень:** {level_data['upgrade_cost']} монет\n"
                                  f"**Статус:** {'✅ Можно собрать' if can_collect else '⏳ Еще рано'}", "info")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="создать_ферму", description="Создать майнинг ферму")
async def создать_ферму(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if user_id in user_mining_farms:
        await interaction.response.send_message("❌ У вас уже есть ферма!", ephemeral=True)
        return
    
    user_mining_farms[user_id] = {"level": 1, "last_collected": None}
    embed = Design.create_embed("✅ Ферма создана!", 
                              "Ваша майнинг ферма уровня 1 готова к работе!\n"
                              "Используйте `/собрать_доход` каждые 12 часов", "success")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="собрать_доход", description="Собрать доход с фермы")
async def собрать_доход(interaction: discord.Interaction):
    success, message = await bot.mining_system.collect_income(interaction.user.id)
    
    if success:
        embed = Design.create_embed("💰 Доход собран!", message, "success")
    else:
        embed = Design.create_embed("❌ Ошибка", message, "danger")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="улучшить_ферму", description="Улучшить майнинг ферму")
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
                              f"Новый доход: {bot.mining_system.farm_levels[current_level + 1]['income']} монет/12ч", "success")
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
                value=f"Осталось: {minutes_left} минут",
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)

# 🔧 ОБРАБОТЧИКИ
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'🌐 Серверов: {len(bot.guilds)}')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Синхронизировано {len(synced)} команд')
    except Exception as e:
        print(f'❌ Ошибка синхронизации: {e}')
    
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

@bot.tree.command(name="модер", description="🛡️ Панель модератора")
async def модер(interaction: discord.Interaction):
    """Панель управления для модераторов"""
    # Проверяем что пользователь модератор
    is_moderator = any(role.id in MODERATION_ROLES for role in interaction.user.roles)
    is_admin_user = interaction.user.id in ADMIN_IDS
    
    if not is_moderator and not is_admin_user:
        await interaction.response.send_message("❌ У вас нет прав модератора!", ephemeral=True)
        return
    
    embed = Design.create_embed("🛡️ ПАНЕЛЬ МОДЕРАТОРА", """
**⚡ КОМАНДЫ МОДЕРАЦИИ:**

🔨 **Наказания:**
`/мут @user время причина` - Замутить пользователя
`/варн @user причина` - Выдать предупреждение  
`/бан @user причина` - Забанить пользователя
`/кик @user причина` - Кикнуть пользователя

🧹 **Управление чатом:**
`/очистить количество` - Очистить сообщения
`/тикет причина` - Создать тикет поддержки

👤 **Информация:**
`/юзер @user` - Информация о пользователе
`/сервер` - Информация о сервере
`/статистика` - Статистика бота

🎫 **Тикеты и жалобы:**
- Автоматические тикеты при заказах
- Ветки для выдачи ролей из лутбоксов
    """, "moderation")
    
    # Если пользователь еще и админ - покажем дополнительную информацию
    if is_admin_user:
        embed.add_field(
            name="👑 ДОПОЛНИТЕЛЬНО ДЛЯ АДМИНОВ:",
            value="Используйте `/админ` для управления экономикой",
            inline=False
        )
    
    embed.add_field(
        name="📋 ЧЕК-ЛИСТ МОДЕРАТОРА:",
        value="• Проверяйте тикеты каждые 2 часа\n• Отвечайте на жалобы в течение 24 часов\n• Следите за порядком в чатах\n• Проверяйте ветки с ролями из лутбоксов",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 🚀 ЗАПУСК
@bot.tree.command(name="синхронизировать", description="[АДМИН] Пересинхронизировать команды")
@is_admin()
async def синхронизировать(interaction: discord.Interaction):
    await bot.tree.sync()
    embed = Design.create_embed("✅ Синхронизация", "Команды пересинхронизированы!", "success")
    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    try:
        print("🚀 Запуск бота...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")

