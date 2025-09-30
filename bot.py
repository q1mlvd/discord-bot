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
economic_bans = {}

# 🔧 ФУНКЦИИ ПРОВЕРКИ ПРАВ
def is_admin():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id in ADMIN_IDS
    return commands.check(predicate)

def is_moderator():
    async def predicate(interaction: discord.Interaction):
        user_roles = [role.id for role in interaction.user.roles]
        return any(role_id in MODERATION_ROLES for role_id in user_roles) or interaction.user.id in ADMIN_IDS
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

# 💾 ПОЛНОЦЕННАЯ БАЗА ДАННЫХ
class Database:
    def __init__(self):
        self.db_path = "data/bot.db"
        os.makedirs("data", exist_ok=True)
    
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Основная таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 1000,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    daily_claimed TEXT,
                    work_cooldown TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица инвентаря
            await db.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    item_id INTEGER,
                    item_name TEXT,
                    quantity INTEGER DEFAULT 1,
                    obtained_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица заказов магазина
            await db.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    category TEXT,
                    product_name TEXT,
                    quantity INTEGER,
                    price REAL,
                    details TEXT,
                    status TEXT DEFAULT 'ожидает оплаты',
                    order_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    admin_id INTEGER,
                    completion_time TEXT,
                    payment_screenshot TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица кредитов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_credits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    company TEXT,
                    amount INTEGER,
                    interest_rate INTEGER,
                    due_date TEXT,
                    original_amount INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица майнинг ферм
            await db.execute('''
                CREATE TABLE IF NOT EXISTS mining_farms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    level INTEGER DEFAULT 1,
                    last_collected TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица криптовалюты пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_crypto (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    crypto_type TEXT,
                    amount REAL DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, crypto_type)
                )
            ''')
            
            # Таблица варнов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_warns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    moderator_id INTEGER,
                    reason TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица мутов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_mutes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    moderator_id INTEGER,
                    reason TEXT,
                    end_time TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            await db.commit()
            print("✅ База данных инициализирована")
    
    async def backup_database(self):
        """Создание бэкапа базы данных"""
        backup_path = f"data/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        import shutil
        shutil.copy2(self.db_path, backup_path)
        return backup_path

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
                    await db.execute('INSERT INTO users (user_id, balance) VALUES (?, 1000)', (user_id,))
                    await db.commit()
                    return 1000
    
    async def update_balance(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 1000)', (user_id,))
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
    
    async def load_credits_from_db(self):
        """Загрузка кредитов из базы данных при запуске"""
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT user_id, company, amount, interest_rate, due_date, original_amount FROM user_credits') as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    user_id, company, amount, interest_rate, due_date, original_amount = row
                    user_credits[user_id] = {
                        "company": company,
                        "amount": amount,
                        "interest_rate": interest_rate,
                        "due_date": datetime.fromisoformat(due_date),
                        "original_amount": original_amount
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
        
        # Сохраняем в оперативную память
        user_credits[user_id] = {
            "company": company,
            "amount": amount + (amount * company_data["interest_rate"] // 100),
            "interest_rate": company_data["interest_rate"],
            "due_date": due_date,
            "original_amount": amount
        }
        
        # Сохраняем в базу данных
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('''
                INSERT INTO user_credits (user_id, company, amount, interest_rate, due_date, original_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, company, amount + (amount * company_data["interest_rate"] // 100), 
                  company_data["interest_rate"], due_date.isoformat(), amount))
            await db.commit()
        
        await self.economy.update_balance(user_id, amount)
        return True, f"Кредит одобрен! Вернуть {amount + (amount * company_data['interest_rate'] // 100)} монет до {due_date.strftime('%d.%m.%Y')}"

    async def repay_credit(self, user_id: int):
        if user_id not in user_credits:
            return False, "У вас нет активных кредитов"
        
        credit = user_credits[user_id]
        total_to_repay = credit["amount"]
        
        balance = await self.economy.get_balance(user_id)
        if balance < total_to_repay:
            return False, f"Недостаточно средств. Нужно: {total_to_repay} монет"
        
        await self.economy.update_balance(user_id, -total_to_repay)
        
        # Удаляем из базы данных
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('DELETE FROM user_credits WHERE user_id = ?', (user_id,))
            await db.commit()
        
        del user_credits[user_id]
        return True, f"Кредит погашен! Сумма: {total_to_repay} монет"

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

# ⛏️ СИСТЕМА МАЙНИНГА С БАЗОЙ ДАННЫХ
class MiningSystem:
    def __init__(self, economy: EconomySystem, db: Database):
        self.economy = economy
        self.db = db
        self.farm_levels = {
            1: {"income": 10, "upgrade_cost": 1000},
            2: {"income": 25, "upgrade_cost": 5000},
            3: {"income": 50, "upgrade_cost": 15000}
        }
    
    async def load_farms_from_db(self):
        """Загрузка ферм из базы данных при запуске"""
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT user_id, level, last_collected FROM mining_farms') as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    user_id, level, last_collected = row
                    user_mining_farms[user_id] = {
                        "level": level,
                        "last_collected": last_collected,
                        "created_at": datetime.now().isoformat()
                    }
    
    async def create_farm(self, user_id: int):
        """Создание фермы в базе данных"""
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT INTO mining_farms (user_id, level) VALUES (?, 1)', (user_id,))
            await db.commit()
        
        user_mining_farms[user_id] = {
            "level": 1,
            "last_collected": None,
            "created_at": datetime.now().isoformat()
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
            
            # Обновляем в базе данных
            new_last_collected = datetime.now().isoformat()
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute('UPDATE mining_farms SET last_collected = ? WHERE user_id = ?', (new_last_collected, user_id))
                await db.commit()
            
            user_mining_farms[user_id]["last_collected"] = new_last_collected
            
            return True, f"✅ Собрано {income} монет с фермы! Следующий сбор через 6 часов"
            
        except Exception as e:
            print(f"Ошибка при сборе дохода: {e}")
            return False, "❌ Произошла ошибка при сборе дохода"

# 🏗️ ГЛАВНЫЙ БОТ С ПЕРЕЗАГРУЗКОЙ
class MegaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        
        self.db = Database()
        self.economy = EconomySystem(self.db)
        self.casino = CasinoSystem(self.economy)
        self.credit_system = CreditSystem(self.economy, self.db)
        self.mining_system = MiningSystem(self.economy, self.db)
        
        self.start_time = datetime.now()
    
    async def setup_hook(self):
        await self.db.init_db()
        await self.credit_system.load_credits_from_db()
        await self.mining_system.load_farms_from_db()
        
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
                
                # Удаляем из базы данных
                async with aiosqlite.connect(self.db.db_path) as db:
                    await db.execute('DELETE FROM user_credits WHERE user_id = ?', (user_id,))
                    await db.commit()
                
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
            event_types = ["money_rain", "lucky_day", "work_bonus", "giveaway"]
            event_type = random.choice(event_types)
            # Здесь можно добавить логику ивентов

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

# 🔧 КОМАНДА ПЕРЕЗАГРУЗКИ
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

# 💰 ИСПРАВЛЕННЫЕ КОМАНДЫ ЭКОНОМИКИ С МИНИМАЛЬНОЙ СТАВКОЙ 0
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

# 🛡️ ИСПРАВЛЕННЫЕ КОМАНДЫ МОДЕРАЦИИ С ПРОВЕРКОЙ ПРАВ
@bot.tree.command(name="пред", description="Выдать предупреждение (3 пред = мут на 1 час)")
@is_moderator()
async def пред(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    try:
        # Проверка прав целевого пользователя
        target_roles = [role.id for role in пользователь.roles]
        if any(role_id in MODERATION_ROLES for role_id in target_roles) or пользователь.id in ADMIN_IDS:
            await interaction.response.send_message("❌ Нельзя выдать предупреждение модератору или администратору!", ephemeral=True)
            return
        
        # Сохраняем варн в базу данных
        async with aiosqlite.connect(bot.db.db_path) as db:
            await db.execute('INSERT INTO user_warns (user_id, moderator_id, reason) VALUES (?, ?, ?)', 
                           (пользователь.id, interaction.user.id, причина))
            await db.commit()
            
            # Получаем количество варнов
            async with db.execute('SELECT COUNT(*) FROM user_warns WHERE user_id = ?', (пользователь.id,)) as cursor:
                warn_count = (await cursor.fetchone())[0]
        
        if warn_count >= 3:
            # Выдача мута за 3 варна
            mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await interaction.guild.create_role(name="Muted")
                for channel in interaction.guild.channels:
                    await channel.set_permissions(mute_role, send_messages=False, speak=False)
            
            await пользователь.add_roles(mute_role)
            
            end_time = datetime.now() + timedelta(hours=1)
            # Сохраняем мут в базу данных
            await db.execute('INSERT INTO user_mutes (user_id, moderator_id, reason, end_time) VALUES (?, ?, ?, ?)',
                           (пользователь.id, interaction.user.id, "3 предупреждения", end_time.isoformat()))
            await db.commit()
            
            # Очищаем варны
            await db.execute('DELETE FROM user_warns WHERE user_id = ?', (пользователь.id,))
            await db.commit()
            
            embed = Design.create_embed("⚠️ МУТ за 3 пред", 
                                      f"**Пользователь:** {пользователь.mention}\n"
                                      f"**Причина:** Получено 3 предупреждения\n"
                                      f"**Длительность:** 1 час\n"
                                      f"**Последнее нарушение:** {причина}", "danger")
        else:
            embed = Design.create_embed("⚠️ Предупреждение", 
                                      f"**Пользователь:** {пользователь.mention}\n"
                                      f"**Причина:** {причина}\n"
                                      f"**Текущие пред:** {warn_count}/3\n"
                                      f"**Следующее пред:** мут на 1 час", "warning")
        
        await interaction.response.send_message(embed=embed)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="мут", description="Замутить пользователя")
@is_moderator()
async def мут(interaction: discord.Interaction, пользователь: discord.Member, время: str, причина: str = "Не указана"):
    try:
        # Проверка прав целевого пользователя
        target_roles = [role.id for role in пользователь.roles]
        if any(role_id in MODERATION_ROLES for role_id in target_roles) or пользователь.id in ADMIN_IDS:
            await interaction.response.send_message("❌ Нельзя замутить модератора или администратора!", ephemeral=True)
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
        
        end_time = datetime.now() + timedelta(seconds=seconds)
        
        # Сохраняем в базу данных
        async with aiosqlite.connect(bot.db.db_path) as db:
            await db.execute('INSERT INTO user_mutes (user_id, moderator_id, reason, end_time) VALUES (?, ?, ?, ?)',
                           (пользователь.id, interaction.user.id, причина, end_time.isoformat()))
            await db.commit()
        
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
                                  f"**Причина:** {причина}", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
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

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'🌐 Серверов: {len(bot.guilds)}')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Синхронизировано {len(synced)} команд')
    except Exception as e:
        print(f'❌ Ошибка синхронизации: {e}')
    
    # Запуск еженедельного сброса
    bot.loop.create_task(weekly_reset_task())

async def weekly_reset_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()
        next_monday = now + timedelta(days=(7 - now.weekday()))
        next_reset = datetime(next_monday.year, next_monday.month, next_monday.day, 0, 0, 0)
        wait_seconds = (next_reset - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        await bot.economy.reset_weekly_xp()
        print("✅ Еженедельный сброс опыта выполнен")

if __name__ == "__main__":
    try:
        print("🚀 Запуск бота...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
