import discord
from discord.ext import commands, tasks
import aiosqlite
import asyncio
from datetime import datetime, timedelta
import os
import random
from typing import Optional, Dict, List
from dotenv import load_dotenv
import yt_dlp
import matplotlib.pyplot as plt
import io
import aiohttp
from fastapi import FastAPI
import uvicorn
import threading
from enum import Enum

# 🔧 КОНСТАНТЫ
ADMIN_IDS = [1195144951546265675, 766767256742526996, 1078693283695448064, 1138140772097597472, 691904643181314078]
MODERATION_ROLES = [1167093102868172911, 1360243534946373672, 993043931342319636, 1338611327022923910, 1338609155203661915, 1365798715930968244, 1188261847850299514]
THREADS_CHANNEL_ID = 1422557295811887175
EVENTS_CHANNEL_ID = 1418738569081786459

# 🛡️ ДАННЫЕ ДЛЯ СИСТЕМ (переносим в классы)
class DataStorage:
    def __init__(self):
        self.user_warns = {}
        self.mute_data = {}
        self.user_credits = {}
        self.user_investments = {}
        self.user_insurance = {}
        self.user_lottery_tickets = {}
        self.server_tax_pool = 0
        self.user_mining_farms = {}
        self.crypto_prices = {"BITCOIN": 50000, "ETHEREUM": 3000, "DOGECOIN": 0.15}
        self.active_events = {}
        self.user_reports = {}
        self.user_crypto = {}
        self.rob_cooldowns = {}
        self.economic_bans = {}
        self.user_reputation = {}
        self.marketplace_items = {}
        self.stock_prices = {}
        self.user_stocks = {}
        self.seasonal_events = {}

storage = DataStorage()

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
        if ban_key in storage.economic_bans:
            ban_info = storage.economic_bans[ban_key]
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
                del storage.economic_bans[ban_key]
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
        "event": 0x9B59B6, "credit": 0xE74C3C, "reputation": 0x9B59B6,
        "marketplace": 0x2ECC71, "stocks": 0xE67E22, "seasonal": 0xFF69B4
    }

    @staticmethod
    def create_embed(title: str, description: str = "", color: str = "primary"):
        return discord.Embed(title=title, description=description, color=Design.COLORS.get(color, Design.COLORS["primary"]))

# 💾 БАЗА ДАННЫХ (расширенная)
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
            
            # Существующие таблицы
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
            
            # НОВЫЕ ТАБЛИЦЫ ДЛЯ ДОПОЛНЕНИЙ
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_reputation (
                    user_id INTEGER PRIMARY KEY,
                    reputation INTEGER DEFAULT 0,
                    total_xp INTEGER DEFAULT 0,
                    reputation_level INTEGER DEFAULT 1,
                    last_reputation_update TEXT
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS marketplace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seller_id INTEGER,
                    item_name TEXT,
                    item_description TEXT,
                    price INTEGER,
                    quantity INTEGER,
                    category TEXT,
                    listed_at TEXT,
                    expires_at TEXT,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_stocks (
                    user_id INTEGER,
                    stock_symbol TEXT,
                    quantity INTEGER DEFAULT 0,
                    average_buy_price REAL,
                    total_invested INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, stock_symbol)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS stock_prices (
                    stock_symbol TEXT PRIMARY KEY,
                    current_price REAL,
                    daily_change REAL,
                    last_updated TEXT
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS seasonal_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_name TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    active BOOLEAN DEFAULT FALSE,
                    multiplier REAL DEFAULT 1.0
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS seasonal_items (
                    user_id INTEGER,
                    item_id TEXT,
                    item_name TEXT,
                    quantity INTEGER DEFAULT 1,
                    obtained_date TEXT,
                    event_id INTEGER,
                    PRIMARY KEY (user_id, item_id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tax_records (
                    user_id INTEGER,
                    tax_period TEXT,
                    income INTEGER DEFAULT 0,
                    tax_paid INTEGER DEFAULT 0,
                    tax_rate REAL DEFAULT 0.05,
                    PRIMARY KEY (user_id, tax_period)
                )
            ''')
            
            await db.commit()
            print("✅ База данных инициализирована")

# 🌟 СИСТЕМА РЕПУТАЦИИ И УРОВНЕЙ
class ReputationSystem:
    def __init__(self, db: Database):
        self.db = db
        self.levels = {
            1: {"min_rep": 0, "bonus": "Базовая ставка", "multiplier": 1.0},
            2: {"min_rep": 100, "bonus": "+10% к доходам", "multiplier": 1.1},
            3: {"min_rep": 300, "bonus": "+20% к доходам", "multiplier": 1.2},
            4: {"min_rep": 600, "bonus": "+30% к доходам", "multiplier": 1.3},
            5: {"min_rep": 1000, "bonus": "+50% к доходам", "multiplier": 1.5}
        }
    
    async def get_user_reputation(self, user_id: int) -> Dict:
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT reputation, reputation_level, total_xp FROM user_reputation WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {"reputation": result[0], "level": result[1], "total_xp": result[2]}
                else:
                    # Создаем запись если нет
                    await db.execute('INSERT INTO user_reputation (user_id) VALUES (?)', (user_id,))
                    await db.commit()
                    return {"reputation": 0, "level": 1, "total_xp": 0}
    
    async def add_reputation(self, user_id: int, amount: int, reason: str = ""):
        current_data = await self.get_user_reputation(user_id)
        new_rep = current_data["reputation"] + amount
        new_xp = current_data["total_xp"] + max(amount, 0)
        
        # Проверяем уровень
        new_level = 1
        for level, data in sorted(self.levels.items(), reverse=True):
            if new_rep >= data["min_rep"]:
                new_level = level
                break
        
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('''
                UPDATE user_reputation 
                SET reputation = ?, reputation_level = ?, total_xp = ?, last_reputation_update = ?
                WHERE user_id = ?
            ''', (new_rep, new_level, new_xp, datetime.now().isoformat(), user_id))
            await db.commit()
        
        level_up = new_level > current_data["level"]
        return new_rep, new_level, level_up
    
    def get_level_multiplier(self, level: int) -> float:
        return self.levels.get(level, {"multiplier": 1.0})["multiplier"]

# 🛒 СИСТЕМА МАРКЕТПЛЕЙСА
class MarketplaceSystem:
    def __init__(self, db: Database, economy):
        self.db = db
        self.economy = economy
        self.categories = ["криптовалюта", "предметы", "услуги", "фермы", "другое"]
    
    async def list_item(self, user_id: int, item_name: str, description: str, price: int, quantity: int = 1, category: str = "другое"):
        if category not in self.categories:
            return False, "Неверная категория"
        
        if price <= 0:
            return False, "Цена должна быть положительной"
        
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('''
                INSERT INTO marketplace (seller_id, item_name, item_description, price, quantity, category, listed_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, item_name, description, price, quantity, category, datetime.now().isoformat(), 
                 (datetime.now() + timedelta(days=7)).isoformat()))
            await db.commit()
            
            return True, "Товар успешно выставлен на продажу!"
    
    async def get_marketplace_items(self, category: str = None, page: int = 1):
        limit = 10
        offset = (page - 1) * limit
        
        async with aiosqlite.connect(self.db.db_path) as db:
            if category and category in self.categories:
                async with db.execute('''
                    SELECT * FROM marketplace 
                    WHERE status = "active" AND category = ? 
                    ORDER BY listed_at DESC 
                    LIMIT ? OFFSET ?
                ''', (category, limit, offset)) as cursor:
                    items = await cursor.fetchall()
            else:
                async with db.execute('''
                    SELECT * FROM marketplace 
                    WHERE status = "active" 
                    ORDER BY listed_at DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset)) as cursor:
                    items = await cursor.fetchall()
            
            return items
    
    async def buy_item(self, buyer_id: int, item_id: int, quantity: int = 1):
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT * FROM marketplace WHERE id = ? AND status = "active"', (item_id,)) as cursor:
                item = await cursor.fetchone()
                
            if not item:
                return False, "Товар не найден"
            
            seller_id, item_name, description, price, available_quantity = item[1], item[2], item[3], item[4], item[5]
            
            if buyer_id == seller_id:
                return False, "Нельзя купить собственный товар"
            
            if available_quantity < quantity:
                return False, "Недостаточно товара"
            
            total_cost = price * quantity
            buyer_balance = await self.economy.get_balance(buyer_id)
            
            if buyer_balance < total_cost:
                return False, "Недостаточно средств"
            
            # Проводим транзакцию
            await self.economy.update_balance(buyer_id, -total_cost)
            await self.economy.update_balance(seller_id, total_cost)
            
            # Обновляем количество или удаляем товар
            if available_quantity == quantity:
                await db.execute('DELETE FROM marketplace WHERE id = ?', (item_id,))
            else:
                await db.execute('UPDATE marketplace SET quantity = quantity - ? WHERE id = ?', (quantity, item_id))
            
            await db.commit()
            
            return True, f"Покупка успешна! Куплено: {quantity} x {item_name}"

# 📈 СИСТЕМА АКЦИЙ И ИНВЕСТИЦИЙ
class StockMarketSystem:
    def __init__(self, db: Database, economy):
        self.db = db
        self.economy = economy
        self.stocks = {
            "DISCORD": {"name": "Discord Inc", "base_price": 100, "volatility": 0.1},
            "ROBLOX": {"name": "Roblox Corporation", "base_price": 45, "volatility": 0.15},
            "TS": {"name": "Tower Defense Simulator", "base_price": 25, "volatility": 0.2},
            "EPIC": {"name": "Epic Games", "base_price": 85, "volatility": 0.12}
        }
        
        # Инициализируем цены
        for symbol in self.stocks:
            if symbol not in storage.stock_prices:
                storage.stock_prices[symbol] = self.stocks[symbol]["base_price"]
    
    async def update_stock_prices(self):
        """Обновляет цены акций с учетом волатильности"""
        for symbol, data in self.stocks.items():
            change_percent = random.uniform(-data["volatility"], data["volatility"])
            current_price = storage.stock_prices.get(symbol, data["base_price"])
            new_price = max(current_price * (1 + change_percent), data["base_price"] * 0.5)  # Не ниже 50% от базовой
            storage.stock_prices[symbol] = round(new_price, 2)
            
            # Сохраняем в БД
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO stock_prices (stock_symbol, current_price, daily_change, last_updated)
                    VALUES (?, ?, ?, ?)
                ''', (symbol, new_price, change_percent * 100, datetime.now().isoformat()))
                await db.commit()
    
    async def buy_stocks(self, user_id: int, symbol: str, quantity: int):
        if symbol not in self.stocks:
            return False, "Акция не найдена"
        
        current_price = storage.stock_prices.get(symbol, self.stocks[symbol]["base_price"])
        total_cost = current_price * quantity
        
        balance = await self.economy.get_balance(user_id)
        if balance < total_cost:
            return False, "Недостаточно средств"
        
        await self.economy.update_balance(user_id, -total_cost)
        
        async with aiosqlite.connect(self.db.db_path) as db:
            # Проверяем есть ли уже акции
            async with db.execute('SELECT quantity, average_buy_price, total_invested FROM user_stocks WHERE user_id = ? AND stock_symbol = ?', 
                                (user_id, symbol)) as cursor:
                existing = await cursor.fetchone()
            
            if existing:
                # Обновляем среднюю цену
                old_quantity, old_avg, old_invested = existing
                new_quantity = old_quantity + quantity
                new_invested = old_invested + total_cost
                new_avg = new_invested / new_quantity
                
                await db.execute('''
                    UPDATE user_stocks 
                    SET quantity = ?, average_buy_price = ?, total_invested = ?
                    WHERE user_id = ? AND stock_symbol = ?
                ''', (new_quantity, new_avg, new_invested, user_id, symbol))
            else:
                await db.execute('''
                    INSERT INTO user_stocks (user_id, stock_symbol, quantity, average_buy_price, total_invested)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, symbol, quantity, current_price, total_cost))
            
            await db.commit()
            
        return True, f"Куплено {quantity} акций {symbol} по {current_price} монет за штуку"
    
    async def sell_stocks(self, user_id: int, symbol: str, quantity: int):
        if symbol not in self.stocks:
            return False, "Акция не найдена"
        
        current_price = storage.stock_prices.get(symbol, self.stocks[symbol]["base_price"])
        
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT quantity FROM user_stocks WHERE user_id = ? AND stock_symbol = ?', 
                                (user_id, symbol)) as cursor:
                existing = await cursor.fetchone()
            
            if not existing or existing[0] < quantity:
                return False, "Недостаточно акций"
            
            total_income = current_price * quantity
            
            # Обновляем количество
            await db.execute('UPDATE user_stocks SET quantity = quantity - ? WHERE user_id = ? AND stock_symbol = ?', 
                           (quantity, user_id, symbol))
            
            # Удаляем запись если акций не осталось
            await db.execute('DELETE FROM user_stocks WHERE user_id = ? AND stock_symbol = ? AND quantity = 0', 
                           (user_id, symbol))
            
            await db.commit()
        
        await self.economy.update_balance(user_id, total_income)
        return True, f"Продано {quantity} акций {symbol} по {current_price} монет за штуку"
    
    async def get_user_portfolio(self, user_id: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('SELECT stock_symbol, quantity, average_buy_price FROM user_stocks WHERE user_id = ?', 
                                (user_id,)) as cursor:
                stocks = await cursor.fetchall()
        
        portfolio = []
        total_value = 0
        total_invested = 0
        
        for symbol, quantity, avg_price in stocks:
            current_price = storage.stock_prices.get(symbol, 0)
            value = current_price * quantity
            profit = value - (avg_price * quantity)
            profit_percent = (profit / (avg_price * quantity)) * 100 if avg_price * quantity > 0 else 0
            
            portfolio.append({
                "symbol": symbol,
                "quantity": quantity,
                "avg_price": avg_price,
                "current_price": current_price,
                "value": value,
                "profit": profit,
                "profit_percent": profit_percent
            })
            
            total_value += value
            total_invested += avg_price * quantity
        
        total_profit = total_value - total_invested
        total_profit_percent = (total_profit / total_invested) * 100 if total_invested > 0 else 0
        
        return {
            "stocks": portfolio,
            "total_value": total_value,
            "total_invested": total_invested,
            "total_profit": total_profit,
            "total_profit_percent": total_profit_percent
        }

# 🎄 СИСТЕМА СЕЗОННЫХ СОБЫТИЙ
class SeasonalEventSystem:
    def __init__(self, db: Database, economy):
        self.db = db
        self.economy = economy
        self.events = {
            "halloween": {
                "name": "🎃 Хэллоуин",
                "start": "10-25",
                "end": "11-05",
                "multiplier": 1.2,
                "special_items": ["Тыква", "Призрак", "Ведьмина шляпа"]
            },
            "christmas": {
                "name": "🎄 Рождество", 
                "start": "12-20",
                "end": "01-05",
                "multiplier": 1.3,
                "special_items": ["Подарок", "Снежинка", "Носок"]
            },
            "summer": {
                "name": "☀️ Лето",
                "start": "06-01", 
                "end": "08-31",
                "multiplier": 1.15,
                "special_items": ["Пляжный мяч", "Солнечные очки", "Кокос"]
            }
        }
    
    def get_current_event(self):
        current_date = datetime.now()
        for event_id, event_data in self.events.items():
            start_month, start_day = map(int, event_data["start"].split("-"))
            end_month, end_day = map(int, event_data["end"].split("-"))
            
            start_date = datetime(current_date.year, start_month, start_day)
            end_date = datetime(current_date.year, end_month, end_day)
            
            if start_date <= current_date <= end_date:
                return event_id, event_data
        
        return None, None
    
    async def give_seasonal_item(self, user_id: int, item_name: str):
        event_id, event_data = self.get_current_event()
        if not event_id:
            return False, "Сейчас нет активных событий"
        
        if item_name not in event_data["special_items"]:
            return False, "Этот предмет не относится к текущему событию"
        
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO seasonal_items (user_id, item_id, item_name, obtained_date, event_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, f"{event_id}_{item_name}", item_name, datetime.now().isoformat(), event_id))
            await db.commit()
        
        return True, f"Получен сезонный предмет: {item_name}"

# 💰 ЭКОНОМИКА (расширенная)
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

    async def calculate_tax(self, user_id: int, amount: int) -> int:
        """Прогрессивный налог в зависимости от дохода"""
        balance = await self.get_balance(user_id)
        total_wealth = balance + amount
        
        if total_wealth <= 10000:
            tax_rate = 0.05  # 5%
        elif total_wealth <= 50000:
            tax_rate = 0.08  # 8%
        elif total_wealth <= 100000:
            tax_rate = 0.12  # 12%
        else:
            tax_rate = 0.15  # 15% для богатых
        
        return int(amount * tax_rate)

# 🏦 СИСТЕМА КРЕДИТОВ (исправленная)
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
        if user_id in storage.user_credits:
            return False, "У вас уже есть активный кредит"
        
        company_data = self.companies.get(company)
        if not company_data:
            return False, "Компания не найдена"
        
        if amount < company_data["min_amount"] or amount > company_data["max_amount"]:
            return False, f"Сумма должна быть от {company_data['min_amount']} до {company_data['max_amount']}"
        
        due_date = datetime.now() + timedelta(days=company_data["term_days"])
        storage.user_credits[user_id] = {
            "company": company,
            "amount": amount,
            "interest_rate": company_data["interest_rate"],
            "due_date": due_date,
            "original_amount": amount
        }
        
        await self.economy.update_balance(user_id, amount)
        return True, f"Кредит одобрен! Вернуть до {due_date.strftime('%d.%m.%Y')}"

    async def repay_credit(self, user_id: int):
        if user_id not in storage.user_credits:
            return False, "У вас нет активных кредитов"
        
        credit = storage.user_credits[user_id]
        total_to_repay = credit["amount"]
        
        balance = await self.economy.get_balance(user_id)
        if balance < total_to_repay:
            return False, f"Недостаточно средств. Нужно: {total_to_repay} монет"
        
        await self.economy.update_balance(user_id, -total_to_repay)
        del storage.user_credits[user_id]
        return True, f"Кредит погашен! Сумма: {total_to_repay} монет"

# 🎰 КАЗИНО (исправленное)
class CasinoSystem:
    def __init__(self, economy: EconomySystem):
        self.economy = economy
    
    async def play_slots(self, user_id: int, bet: int):
        if bet <= 0:  # Исправлено
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

# 🏗️ ГЛАВНЫЙ БОТ (расширенный)
class MegaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        
        self.db = Database()
        self.economy = EconomySystem(self.db)
        self.casino = CasinoSystem(self.economy)
        
        # Существующие системы
        self.credit_system = CreditSystem(self.economy)
        self.lootbox_system = LootboxSystem(self.economy)
        self.mining_system = MiningSystem(self.economy)
        self.event_system = EventSystem(self.economy)
        
        # Новые системы
        self.reputation_system = ReputationSystem(self.db)
        self.marketplace_system = MarketplaceSystem(self.db, self.economy)
        self.stock_system = StockMarketSystem(self.db, self.economy)
        self.seasonal_system = SeasonalEventSystem(self.db, self.economy)
        
        self.start_time = datetime.now()
        
        # Задачи
        self.update_stock_prices.start()
        self.check_credits.start()
    
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

    @tasks.loop(minutes=5)
    async def update_stock_prices(self):
        await self.stock_system.update_stock_prices()
    
    @tasks.loop(hours=1)
    async def check_credits(self):
        """Проверка просроченных кредитов"""
        current_time = datetime.now()
        users_to_remove = []
        
        for user_id, credit in storage.user_credits.items():
            if current_time > credit["due_date"]:
                # Наказываем за просрочку
                storage.economic_bans[f"economic_ban_{user_id}"] = {
                    'end_time': current_time + timedelta(days=2),
                    'reason': 'Просрочка кредита'
                }
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del storage.user_credits[user_id]

    @update_stock_prices.before_loop
    @check_credits.before_loop
    async def before_tasks(self):
        await self.wait_until_ready()

bot = MegaBot()

# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (исправленные)
def parse_time(time_str: str) -> int:
    if not time_str:
        return 0
        
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
    
    try:
        number = int(num_str)
    except ValueError:
        return 0
    
    unit = unit_str.lower()
    
    if unit in time_units:
        return number * time_units[unit]
    else:
        return 0

# 🌟 НОВЫЕ КОМАНДЫ РЕПУТАЦИИ
@bot.tree.command(name="репутация", description="Проверить репутацию")
async def репутация(interaction: discord.Interaction, пользователь: Optional[discord.Member] = None):
    user = пользователь or interaction.user
    rep_data = await bot.reputation_system.get_user_reputation(user.id)
    
    embed = Design.create_embed(
        "⭐ Репутация", 
        f"**{user.display_name}**\n"
        f"🏅 Уровень репутации: {rep_data['level']}\n"
        f"⭐ Очки репутации: {rep_data['reputation']}\n"
        f"📊 Всего опыта: {rep_data['total_xp']}",
        "reputation"
    )
    
    level_data = bot.reputation_system.levels.get(rep_data['level'], {})
    if level_data:
        embed.add_field(name="Бонус уровня", value=level_data.get("bonus", "Нет"), inline=False)
    
    await interaction.response.send_message(embed=embed)

# 🛒 НОВЫЕ КОМАНДЫ МАРКЕТПЛЕЙСА
@bot.tree.command(name="продать", description="Выставить товар на продажу")
async def продать(interaction: discord.Interaction, название: str, описание: str, цена: int, количество: int = 1, категория: str = "другое"):
    success, message = await bot.marketplace_system.list_item(
        interaction.user.id, название, описание, цена, количество, категория
    )
    
    if success:
        embed = Design.create_embed("🛒 Товар выставлен", message, "marketplace")
    else:
        embed = Design.create_embed("❌ Ошибка", message, "danger")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="биржа", description="Просмотреть товары на бирже")
async def биржа(interaction: discord.Interaction, категория: Optional[str] = None, страница: int = 1):
    items = await bot.marketplace_system.get_marketplace_items(категория, страница)
    
    if not items:
        embed = Design.create_embed("🛒 Биржа", "Товаров не найдено", "marketplace")
        await interaction.response.send_message(embed=embed)
        return
    
    embed = Design.create_embed(f"🛒 Биржа (Страница {страница})", "", "marketplace")
    
    for item in items[:5]:  # Показываем первые 5 товаров
        item_id, seller_id, name, desc, price, quantity, category, listed_at = item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7]
        
        try:
            seller = await bot.fetch_user(seller_id)
            seller_name = seller.display_name
        except:
            seller_name = "Неизвестный"
        
        embed.add_field(
            name=f"#{item_id} {name}",
            value=f"💰 Цена: {price} монет\n"
                  f"📦 Количество: {quantity}\n"
                  f"🏷️ Категория: {category}\n"
                  f"👤 Продавец: {seller_name}\n"
                  f"📝 {desc}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# 📈 НОВЫЕ КОМАНДЫ АКЦИЙ
@bot.tree.command(name="акции", description="Просмотреть акции")
async def акции(interaction: discord.Interaction):
    embed = Design.create_embed("📈 Биржа акций", "Текущие котировки:", "stocks")
    
    for symbol, price in storage.stock_prices.items():
        stock_data = bot.stock_system.stocks.get(symbol, {})
        embed.add_field(
            name=f"{symbol} - {stock_data.get('name', 'Unknown')}",
            value=f"💰 Цена: {price} монет\n"
                  f"📊 Волатильность: {stock_data.get('volatility', 0)*100}%",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="купить_акции", description="Купить акции")
async def купить_акции(interaction: discord.Interaction, акция: str, количество: int):
    success, message = await bot.stock_system.buy_stocks(interaction.user.id, акция.upper(), количество)
    
    if success:
        embed = Design.create_embed("✅ Акции куплены", message, "success")
    else:
        embed = Design.create_embed("❌ Ошибка", message, "danger")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="портфель", description="Мой инвестиционный портфель")
async def портфель(interaction: discord.Interaction):
    portfolio = await bot.stock_system.get_user_portfolio(interaction.user.id)
    
    if not portfolio["stocks"]:
        await interaction.response.send_message("📊 У вас нет акций", ephemeral=True)
        return
    
    embed = Design.create_embed("📊 Инвестиционный портфель", "", "stocks")
    
    for stock in portfolio["stocks"]:
        profit_emoji = "📈" if stock["profit"] >= 0 else "📉"
        embed.add_field(
            name=f"{stock['symbol']}",
            value=f"Количество: {stock['quantity']}\n"
                  f"Средняя цена: {stock['avg_price']:.2f}\n"
                  f"Текущая цена: {stock['current_price']:.2f}\n"
                  f"Прибыль: {stock['profit']:.2f} ({stock['profit_percent']:.1f}%) {profit_emoji}",
            inline=True
        )
    
    embed.add_field(
        name="💰 Общая статистика",
        value=f"Общая стоимость: {portfolio['total_value']:.2f}\n"
              f"Всего вложено: {portfolio['total_invested']:.2f}\n"
              f"Общая прибыль: {portfolio['total_profit']:.2f} ({portfolio['total_profit_percent']:.1f}%)",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# 🎄 НОВЫЕ КОМАНДЫ СОБЫТИЙ
@bot.tree.command(name="событие", description="Текущее сезонное событие")
async def событие(interaction: discord.Interaction):
    event_id, event_data = bot.seasonal_system.get_current_event()
    
    if not event_id:
        embed = Design.create_embed("🎪 Сезонные события", "Сейчас нет активных событий", "info")
    else:
        embed = Design.create_embed(f"🎪 {event_data['name']}", 
                                  f"**Множитель доходов:** x{event_data['multiplier']}\n"
                                  f"**Особые предметы:** {', '.join(event_data['special_items'])}",
                                  "seasonal")
    
    await interaction.response.send_message(embed=embed)

# 🔧 СУЩЕСТВУЮЩИЕ КОМАНДЫ (с улучшениями)
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
        
        # Учитываем репутацию
        rep_data = await bot.reputation_system.get_user_reputation(interaction.user.id)
        multiplier = bot.reputation_system.get_level_multiplier(rep_data["level"])
        
        base_earnings = random.randint(50, 200)
        earnings = int(base_earnings * multiplier)
        
        new_balance = await bot.economy.update_balance(interaction.user.id, earnings)
        
        async with aiosqlite.connect(bot.db.db_path) as db:
            await db.execute('UPDATE users SET work_cooldown = ? WHERE user_id = ?', (datetime.now().isoformat(), interaction.user.id))
            await db.commit()
        
        embed = Design.create_embed("💼 Работа", 
                                  f"**Заработано:** +{earnings} монет\n"
                                  f"**Бонус репутации:** x{multiplier}\n"
                                  f"**Баланс:** {new_balance:,} монет", "success")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"Ошибка в работе: {e}")
        embed = Design.create_embed("❌ Ошибка", "Не удалось выполнить работу", "danger")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# 🌐 API ДЛЯ ВЕБ-ПАНЕЛИ
def start_api_server():
    """Запуск FastAPI сервера для веб-панели"""
    app = FastAPI(title="Bot Economy API")
    
    @app.get("/api/user/{user_id}")
    async def get_user_stats(user_id: int):
        try:
            balance = await bot.economy.get_balance(user_id)
            rep_data = await bot.reputation_system.get_user_reputation(user_id)
            portfolio = await bot.stock_system.get_user_portfolio(user_id)
            
            return {
                "user_id": user_id,
                "balance": balance,
                "reputation": rep_data["reputation"],
                "reputation_level": rep_data["level"],
                "portfolio_value": portfolio["total_value"],
                "total_profit": portfolio["total_profit"]
            }
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/api/economy/overview")
    async def get_economy_overview():
        # Статистика сервера
        return {
            "total_tax_pool": storage.server_tax_pool,
            "active_credits": len(storage.user_credits),
            "stock_prices": storage.stock_prices,
            "active_events": len(storage.active_events)
        }
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

# 🚀 ЗАПУСК БОТА И API
if __name__ == "__main__":
    try:
        print("🚀 Запуск бота...")
        
        # Запуск API в отдельном потоке
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        print("🌐 API сервер запущен на порту 8000")
        
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
