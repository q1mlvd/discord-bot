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

# 🔧 ГЛОБАЛЬНАЯ ПЕРЕМЕННАЯ ДЛЯ ЭКОНОМИЧЕСКИХ БАНОВ
economic_bans = {}

# 🔧 ИСПРАВЛЕННЫЕ ФУНКЦИИ ПРОВЕРКИ ПРАВ
def is_admin():
    async def predicate(interaction: discord.Interaction):
        # ТОЛЬКО указанные админы
        return interaction.user.id in ADMIN_IDS
    return commands.check(predicate)

def is_moderator():
    async def predicate(interaction: discord.Interaction):
        # ТОЛЬКО указанные модераторские роли
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
                del economic_bans[ban_key]  # Бан закончился
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
                    created_at TEXT,
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
            },
            "legendary": {
                "name": "💎 Легендарный лутбокс",
                "price": 5000,
                "rewards": [
                    {"type": "money", "min": 500, "max": 1000, "chance": 100},
                    {"type": "money", "min": 800, "max": 1500, "chance": 30},
                    {"type": "nothing", "chance": 25},
                    {"type": "crypto", "min": 0.008, "max": 0.015, "chance": 20},
                    {"type": "role", "chance": 1},  # ТОЛЬКО 1% НА РОЛЬ!
                    {"type": "money", "min": 3000, "max": 5000, "chance": 10}
                ]
            },
            "crypto": {
                "name": "₿ Крипто-бокс",
                "price": 3000,
                "rewards": [
                    {"type": "crypto", "min": 0.005, "max": 0.01, "chance": 100},
                    {"type": "crypto", "min": 0.01, "max": 0.02, "chance": 25},
                    {"type": "nothing", "chance": 30},
                    {"type": "money", "min": 500, "max": 1000, "chance": 20}
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
                
                elif reward["type"] == "role":
                    rewards.append("🎭 РОЛЬ (тикет создан)")
                    await self.create_role_ticket(user_id, lootbox["name"])
        
        if not rewards:
            rewards.append("💔 Не повезло... Попробуй еще раз!")
        
        return True, rewards
    
    async def create_role_ticket(self, user_id: int, lootbox_name: str):
        try:
            channel = bot.get_channel(THREADS_CHANNEL_ID)
            if not channel:
                print("❌ Канал для тикетов не найден!")
                return
            
            user = await bot.fetch_user(user_id)
            thread = await channel.create_thread(
                name=f"роль-{user.display_name}",
                type=discord.ChannelType.public_thread,
                reason=f"Выпала роль из {lootbox_name}"
            )
            
            ping_text = " ".join([f"<@&{role_id}>" for role_id in MODERATION_ROLES])
            
            embed = Design.create_embed(
                "🎭 ВЫПАЛА РОЛЬ ИЗ ЛУТБОКСА!",
                f"**Пользователь:** {user.mention}\n"
                f"**Лутбокс:** {lootbox_name}\n"
                f"**Выдать роль на 7 дней**\n\n"
                f"*Пользователь выиграл роль в лутбоксе*",
                "premium"
            )
            
            await thread.send(f"{ping_text}")
            await thread.send(embed=embed)
            
        except Exception as e:
            print(f"❌ Ошибка создания тикета: {e}")

# 🔧 ИСПРАВЛЕННАЯ СИСТЕМА МАЙНИНГА (6 часов КД)
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
                    if time_passed.total_seconds() < 21600:  # 6 часов в секундах
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

# 🎪 ИСПРАВЛЕННАЯ СИСТЕМА ИВЕНТОВ
class EventSystem:
    def __init__(self, economy: EconomySystem):
        self.economy = economy
        self.event_types = {
            "money_rain": {
                "name": "💰 Денежный дождь", 
                "duration": 300, 
                "multiplier": 2,
                "description": "ВСЕ денежные операции приносят в 2 раза больше монет! Успей поработать и получить ежедневку!"
            },
            "lucky_day": {
                "name": "🎰 Удачный день", 
                "duration": 600, 
                "casino_bonus": True,
                "description": "Шансы в казино увеличены! Выигрывай больше в слотах и на монетке!"
            },
            "work_bonus": {
                "name": "💼 Работяга", 
                "duration": 1800, 
                "work_multiplier": 3,
                "description": "Работа приносит в 3 раза больше денег! Успей заработать!"
            },
            "giveaway": {
                "name": "🎁 Раздача", 
                "duration": 300, 
                "giveaway": True,
                "description": "Случайные пользователи получают денежные призы каждые 5 минут!"
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
                    f"⏰ **Длительность:** {event['duration'] // 60} минут\n"
                    f"🎯 **Успей поучаствовать!**\n\n"
                    f"*Ивент закончится <t:{int((datetime.now() + timedelta(seconds=event['duration'])).timestamp())}:R>*",
                    "event"
                )
                await channel.send(embed=embed)
        except Exception as e:
            print(f"❌ Ошибка отправки ивента: {e}")
        
        return True

# 🏪 МАГАЗИН (остается без изменений)
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

# 🎰 ИСПРАВЛЕННОЕ КАЗИНО С МИНИМАЛЬНОЙ СТАВКОЙ 0
class CasinoSystem:
    def __init__(self, economy: EconomySystem):
        self.economy = economy
    
    async def play_slots(self, user_id: int, bet: int):
        if bet < 0:  # Минимальная ставка 0
            return {"success": False, "error": "Ставка не может быть отрицательной!"}
        
        balance = await self.economy.get_balance(user_id)
        if balance < bet:
            return {"success": False, "error": "Недостаточно средств!"}
        
        symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎", "7️⃣"]
        result = [random.choice(symbols) for _ in range(3)]
        
        await self.economy.update_balance(user_id, -bet)
        
        # Проверка выигрыша
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

# 🛡️ МОДЕРАЦИЯ
class ModerationSystem:
    async def create_ticket(self, user: discord.Member, reason: str):
        # ... код без изменений
        pass

# 🎵 ИСПРАВЛЕННАЯ СИСТЕМА МУЗЫКИ
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
            'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
        }
        
        self.ytdl = yt_dlp.YoutubeDL(self.ytdl_format_options)

    async def connect_to_voice_channel(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Вы не в голосовом канале!", ephemeral=True)
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
        await interaction.response.defer()
        
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
                                          f"⏱️ {duration_str}\n"
                                          f"👤 {interaction.user.mention}", "music")
            else:
                embed = Design.create_embed("🎵 Добавлено в очередь", 
                                          f"**{title}**\n"
                                          f"⏱️ {duration_str}\n"
                                          f"👤 {interaction.user.mention}\n"
                                          f"📋 Позиция: {len(queue)}", "music")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send("❌ Не удалось найти или воспроизвести трек")
            print(f"Ошибка музыки: {e}")

    def get_queue(self, guild_id: int):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    async def play_next(self, guild_id: int, channel=None):
        queue = self.get_queue(guild_id)
        if not queue:
            return
        
        if guild_id not in self.voice_clients:
            return
        
        voice_client = self.voice_clients[guild_id]
        
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
                                              f"⏱️ {track['duration']}\n"
                                              f"👤 {track['requester'].mention}", "music")
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
        self.casino = CasinoSystem(self.economy)  # Исправлено: передаем economy вместо db
        self.moderation = ModerationSystem()
        self.music = MusicPlayer()
        
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
                company = credit["company"]
                penalty = self.credit_system.companies[company]["penalty"]
                
                if company == "fast_money":
                    await self.apply_economic_ban(user_id, days=2)
                elif company == "reliable_credit": 
                    balance = await self.economy.get_balance(user_id)
                    penalty_amount = balance // 2
                    await self.economy.update_balance(user_id, -penalty_amount)
                elif company == "premium_finance":
                    await self.economy.admin_set_money(user_id, 0)
                    await self.apply_economic_ban(user_id, days=7)
                
                del user_credits[user_id]
                
                try:
                    user = await self.fetch_user(user_id)
                    embed = Design.create_embed(
                        "💀 ПРОСРОЧКА КРЕДИТА!",
                        f"**Компания:** {self.credit_system.companies[company]['name']}\n"
                        f"**Наказание:** {penalty}\n"
                        f"**Сумма долга:** {credit['amount']} монет",
                        "danger"
                    )
                    await user.send(embed=embed)
                except:
                    pass

    async def apply_economic_ban(self, user_id: int, days: int):
        economic_ban_key = f"economic_ban_{user_id}"
        economic_bans[economic_ban_key] = {
            'end_time': datetime.now() + timedelta(days=days),
            'reason': 'Просрочка кредита'
        }

    @tasks.loop(hours=3)
    async def random_events(self):
        if random.random() < 0.3 and not active_events:
            event_type = random.choice(list(self.event_system.event_types.keys()))
            await self.event_system.start_event(event_type, self)

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

    async def reload_bot(self):
        """Перезагрузка бота"""
        try:
            # Синхронизация команд
            synced = await self.tree.sync()
            print(f"♻️ Бот перезагружен! Синхронизировано {len(synced)} команд")
            return True
        except Exception as e:
            print(f"❌ Ошибка перезагрузки: {e}")
            return False

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
                                          f"**Осталось:** {hours}ч {minutes}м\n"
                                          f"**Причина:** {mute_info['reason']}", "warning")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return True
            else:
                await пользователь.remove_roles(mute_role)
                del mute_data[пользователь.id]
        else:
            embed = Design.create_embed("⚠️ Пользователь уже в муте", 
                                      f"**Пользователь:** {пользователь.mention}", "warning")
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

# 🔧 КОМАНДА ПЕРЕЗАГРУЗКИ (ТОЛЬКО ДЛЯ АДМИНОВ)
@bot.tree.command(name="перезагрузить", description="[АДМИН] Перезагрузить бота")
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

# 💰 КОМАНДЫ ЭКОНОМИКИ (с проверкой бана)
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
    
    insurance_active = user_insurance.get(interaction.user.id, False)
    
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
        if insurance_active:
            fine = fine // 2
            embed = Design.create_embed("🚓 Пойманы! (Со страховкой)", 
                                      f"**Штраф:** {fine} монет (50% возвращено)\n"
                                      f"**Следующее ограбление через:** 30 минут", 
                                      "warning")
        else:
            embed = Design.create_embed("🚓 Пойманы!", 
                                      f"**Штраф:** {fine} монет\n"
                                      f"**Следующее ограбление через:** 30 минут", 
                                      "danger")
        
        await bot.economy.update_balance(interaction.user.id, -fine)
        rob_cooldowns[user_id] = current_time
    
    await interaction.response.send_message(embed=embed)

# 🎰 ИСПРАВЛЕННЫЕ КОМАНДЫ КАЗИНО С МИНИМАЛЬНОЙ СТАВКОЙ 0
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

# 🛡️ КОМАНДЫ МОДЕРАЦИИ С ПРОВЕРКОЙ ПРАВ
@bot.tree.command(name="пред", description="Выдать предупреждение (3 пред = мут на 1 час)")
@is_moderator()
async def пред(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    try:
        # Проверка прав целевого пользователя
        target_roles = [role.id for role in пользователь.roles]
        if any(role_id in MODERATION_ROLES for role_id in target_roles) or пользователь.id in ADMIN_IDS:
            await interaction.response.send_message("❌ Нельзя выдать предупреждение модератору или администратору!", ephemeral=True)
            return
        
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
            
            embed = Design.create_embed("⚠️ МУТ за 3 пред", 
                                      f"**Пользователь:** {пользователь.mention}\n"
                                      f"**Причина:** Получено 3 предупреждения\n"
                                      f"**Длительность:** 1 час\n"
                                      f"**Последнее нарушение:** {причина}", "danger")
            await interaction.response.send_message(embed=embed)
            
        else:
            embed = Design.create_embed("⚠️ Предупреждение", 
                                      f"**Пользователь:** {пользователь.mention}\n"
                                      f"**Причина:** {причина}\n"
                                      f"**Текущие пред:** {current_warns}/3\n"
                                      f"**Следующее пред:** мут на 1 час", "warning")
            await interaction.response.send_message(embed=embed)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="снять_пред", description="Снять предупреждение с пользователя")
@is_moderator()
async def снять_пред(interaction: discord.Interaction, пользователь: discord.Member, количество: int = 1):
    try:
        # Проверка прав целевого пользователя
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
                                  f"**Текущие пред:** {new_warns}/3\n"
                                  f"**Модератор:** {interaction.user.mention}", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="варны", description="Посмотреть предупреждения пользователя")
@is_moderator()
async def варны(interaction: discord.Interaction, пользователь: discord.Member):
    try:
        current_warns = user_warns.get(пользователь.id, 0)
        
        embed = Design.create_embed("📊 Предупреждения пользователя", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Текущие пред:** {current_warns}/3\n"
                                  f"**До мута осталось:** {max(0, 3 - current_warns)} пред", 
                                  "info" if current_warns < 3 else "warning")
        
        if current_warns >= 3:
            embed.add_field(name="⚠️ Внимание", value="Пользователь должен получить мут за 3 предупреждения!", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="снять_все_варны", description="Снять все предупреждения с пользователя")
@is_moderator()
async def снять_все_варны(interaction: discord.Interaction, пользователь: discord.Member):
    try:
        # Проверка прав целевого пользователя
        target_roles = [role.id for role in пользователь.roles]
        if any(role_id in MODERATION_ROLES for role_id in target_roles) or пользователь.id in ADMIN_IDS:
            await interaction.response.send_message("❌ Нельзя снять предупреждения с модератора или администратора!", ephemeral=True)
            return
        
        if пользователь.id not in user_warns or user_warns[пользователь.id] <= 0:
            await interaction.response.send_message("❌ У пользователя нет предупреждений!", ephemeral=True)
            return
        
        removed_warns = user_warns[пользователь.id]
        user_warns[пользователь.id] = 0
        
        embed = Design.create_embed("✅ Все предупреждения сняты", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Снято предупреждений:** {removed_warns}\n"
                                  f"**Текущие пред:** 0/3\n"
                                  f"**Модератор:** {interaction.user.mention}", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

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
            elif reward["type"] == "nothing":
                rewards_text += f"💨 Пустота ({reward['chance']}%)\n"
        
        embed.add_field(
            name=f"{lootbox['name']} - {lootbox['price']} монет",
            value=rewards_text,
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="открыть_лутбокс", description="Купить и открыть лутбокс")
async def открыть_лутбокс(interaction: discord.Interaction, тип: str):
    lootbox_aliases = {
        "обычный": "common", "common": "common",
        "редкий": "rare", "rare": "rare", 
        "легендарный": "legendary", "legendary": "legendary",
        "крипто": "crypto", "crypto": "crypto", "крипта": "crypto"
    }
    
    lootbox_type = lootbox_aliases.get(тип.lower(), тип.lower())
    
    success, result = await bot.lootbox_system.open_lootbox(interaction.user.id, lootbox_type)
    
    if not success:
        available_boxes = "\n".join([
            f"• **обычный** (common) - 500 монет",
            f"• **редкий** (rare) - 1500 монет", 
            f"• **легендарный** (legendary) - 5000 монет",
            f"• **крипто** (crypto) - 3000 монет"
        ])
        
        embed = Design.create_embed("❌ Лутбокс не найден", 
                                  f"**Доступные лутбоксы:**\n{available_boxes}\n\n"
                                  f"**Пример:** `/открыть_лутбокс тип: обычный`", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    lootbox = bot.lootbox_system.lootboxes[lootbox_type]
    embed = Design.create_embed(f"🎁 Открыт {lootbox['name']}!", "", "success")
    
    if not result:
        embed.add_field(name="💔 Не повезло", value="К сожалению, вы ничего не выиграли", inline=False)
    else:
        for reward in result:
            embed.add_field(name="🎉 Награда", value=reward, inline=False)
    
    await interaction.response.send_message(embed=embed)

# ⛏️ КОМАНДЫ МАЙНИНГА
@bot.tree.command(name="ферма", description="Информация о майнинг ферме")
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

@bot.tree.command(name="создать_ферму", description="Создать майнинг ферму")
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
                              f"Стоимость создания: {creation_cost} монет\n"
                              f"Используйте `/собрать_доход` каждые 6 часов", "success")
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
        embed = Design.create_embed("❌ Критическая ошибка", 
                                  "Произошла ошибка при обработке запроса", "danger")
        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"Ошибка в команде собрать_доход: {e}")

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

@bot.tree.command(name="запустить_ивент", description="[АДМИН] Запустить ивент вручную")
@is_admin()
async def запустить_ивент(interaction: discord.Interaction, тип: str):
    event_types = {
        "дождь": "money_rain",
        "удача": "lucky_day", 
        "работа": "work_bonus",
        "раздача": "giveaway"
    }
    
    event_type = event_types.get(тип.lower())
    if not event_type:
        available = "\n".join([f"• `{key}` - {value}" for key, value in event_types.items()])
        await interaction.response.send_message(f"❌ Неверный тип ивента!\n\n**Доступные:**\n{available}", ephemeral=True)
        return
    
    success = await bot.event_system.start_event(event_type, bot)
    
    if success:
        embed = Design.create_embed("✅ Ивент запущен!", f"Ивент **{bot.event_system.event_types[event_type]['name']}** активирован!", "success")
    else:
        embed = Design.create_embed("❌ Ошибка", "Не удалось запустить ивент", "danger")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="модер", description="🛡️ Панель модератора")
@is_moderator()
async def модер(interaction: discord.Interaction):
    embed = Design.create_embed("🛡️ ПАНЕЛЬ МОДЕРАТОРА", """
@bot.tree.command(name="модер", description="🛡️ Панель модератора")
@is_moderator()
async def модер(interaction: discord.Interaction):
    embed = Design.create_embed("🛡️ ПАНЕЛЬ МОДЕРАТОРА", """
**⚡ КОМАНДЫ МОДЕРАЦИИ:**

🔨 **Наказания:**
`/мут @user время причина` - Замутить
`/размут @user` - Снять мут
`/пред @user причина` - Предупреждение  
`/снять_пред @user количество` - Снять пред
`/снять_все_варны @user` - Снять все варны
`/варны @user` - Посмотреть варны
`/бан @user причина` - Забанить
`/разбан user_id` - Разбанить
`/кик @user причина` - Кикнуть

🧹 **Управление чатом:**
`/очистить количество` - Очистить сообщения
`/тикет причина` - Создать тикет

👤 **Информация:**
`/юзер @user` - Информация
`/сервер` - Информация о сервере
    """, "moderation")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 👑 АДМИН КОМАНДЫ
@bot.tree.command(name="выдать", description="[АДМИН] Выдать монеты")
@is_admin()
async def выдать(interaction: discord.Interaction, пользователь: discord.Member, количество: int):
    if количество <= 0:
        await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
        return
    
    new_balance = await bot.economy.admin_add_money(пользователь.id, количество)
    
    embed = Design.create_embed("💰 АДМИН: Деньги выданы", 
                              f"**Пользователь:** {пользователь.mention}\n"
                              f"**Выдано:** {количество:,} монет\n"
                              f"**Новый баланс:** {new_balance:,} монет", "success")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="удалить_бд", description="[АДМИН] Полностью удалить базу данных")
@is_admin()
async def удалить_бд(interaction: discord.Interaction):
    import os
    try:
        if os.path.exists("data/bot.db"):
            os.remove("data/bot.db")
            await bot.db.init_db()
            embed = Design.create_embed("✅ База данных удалена", "Все данные сброшены к начальным!", "success")
        else:
            embed = Design.create_embed("ℹ️ База не найдена", "Файл data/bot.db не существует", "info")
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка", f"Не удалось удалить БД: {e}", "danger")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="админ", description="[АДМИН] Панель администратора")
@is_admin()
async def админ(interaction: discord.Interaction):
    embed = Design.create_embed("👑 ПАНЕЛЬ АДМИНИСТРАТОРА", """
**⚡ АДМИН КОМАНДЫ:**

💰 **Экономика:**
`/выдать @user количество` - Выдать монеты
`/перезагрузить` - Перезагрузить бота

🛠️ **Управление:**
`/удалить_бд` - Очистить базу данных
`/запустить_ивент тип` - Запустить ивент

📊 **Информация:**
`/статистика` - Статистика бота
`/юзер @user` - Подробная информация
    """, "premium")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

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

if __name__ == "__main__":
    try:
        print("🚀 Запуск бота...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
