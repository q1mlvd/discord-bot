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

# 🎵 ДЛЯ МУЗЫКИ
import yt_dlp
import asyncio

# Словарь для хранения варнов пользователей
user_warns = {}

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
        """Создание заказа с тикетом"""
        # Находим товар
        product = None
        category_name = ""
        for cat_name, category in self.categories.items():
            if item_id in category["items"]:
                product = category["items"][item_id]
                category_name = cat_name
                break
        
        if not product:
            return {"success": False, "error": "Товар не найден"}
        
        # Расчет цены
        if product.get("per_unit"):
            total_price = product["price"] * quantity
        else:
            total_price = product["price"]
            quantity = 1
        
        # Создаем заказ в БД
        async with aiosqlite.connect(self.db.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO orders (user_id, category, product_name, quantity, price, details, order_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, category_name, product["name"], quantity, total_price, details, datetime.now().isoformat()))
            
            order_id = cursor.lastrowid
            await db.commit()
        
        return {
            "success": True, 
            "order_id": order_id,
            "product": product,
            "total_price": total_price,
            "quantity": quantity
        }
    
    async def get_user_orders(self, user_id: int):
        """Получить заказы пользователя"""
        async with aiosqlite.connect(self.db.db_path) as db:
            async with db.execute('''
                SELECT id, product_name, quantity, price, status, order_time 
                FROM orders WHERE user_id = ? ORDER BY order_time DESC
            ''', (user_id,)) as cursor:
                return await cursor.fetchall()
    
    async def update_order_status(self, order_id: int, status: str, admin_id: int = None, screenshot: str = None):
        """Обновить статус заказа"""
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
        """Найти товар по ID"""
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
        """Упрощенное воспроизведение музыки"""
        voice_client = await self.connect_to_voice_channel(interaction)
        if not voice_client:
            return
        
        # Добавляем в очередь (без реального воспроизведения)
        queue = self.get_queue(interaction.guild.id)
        queue.append({
            'title': query,
            'requester': interaction.user
        })
        
        embed = Design.create_embed("🎵 Музыка", 
                                  f"Добавлено в очередь: **{query}**\n"
                                  f"Позиция в очереди: {len(queue)}\n\n"
                                  f"⚠️ *Для работы музыки нужны дополнительные настройки*", "music")
        await interaction.response.send_message(embed=embed)

    async def stop_music(self, guild_id: int):
        """Остановка музыки"""
        if guild_id in self.voice_clients:
            voice_client = self.voice_clients[guild_id]
            if voice_client.is_playing():
                voice_client.stop()
            
            self.queues[guild_id] = []
            
            await voice_client.disconnect()
            del self.voice_clients[guild_id]

    def get_queue_embed(self, guild_id: int):
        queue = self.get_queue(guild_id)
        if not queue:
            return Design.create_embed("🎵 Очередь пуста", "Добавьте треки с помощью /play", "music")
        
        embed = Design.create_embed("🎵 Очередь воспроизведения", f"Треков в очереди: {len(queue)}", "music")
        for i, track in enumerate(queue[:5], 1):
            embed.add_field(name=f"{i}. {track['title']}", value=f"Запросил: {track['requester'].display_name}", inline=False)
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

# 💰 ЭКОНОМИКА КОМАНДЫ
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
    
    await bot.economy.update_balance(interaction.user.id, -сумма)
    await bot.economy.update_balance(пользователь.id, сумма)
    
    embed = Design.create_embed("✅ Перевод", f"**От:** {interaction.user.mention}\n**Кому:** {пользователь.mention}\n**Сумма:** {сумма} монет", "success")
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
    
    if random.random() < 0.4:
        stolen = random.randint(100, min(500, victim_balance))
        await bot.economy.update_balance(жертва.id, -stolen)
        await bot.economy.update_balance(interaction.user.id, stolen)
        embed = Design.create_embed("💰 Ограбление успешно!", f"**Украдено:** {stolen} монет", "warning")
    else:
        fine = random.randint(50, 200)
        await bot.economy.update_balance(interaction.user.id, -fine)
        embed = Design.create_embed("🚓 Пойманы!", f"**Штраф:** {fine} монет", "danger")
    
    await interaction.response.send_message(embed=embed)

# 🏪 МАГАЗИН КОМАНДЫ
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
        "tds": "🎮 TDS/TDX",
        "tdx": "🎮 TDS/TDX", 
        "roblox": "🔴 Roblox",
        "blox": "🥊 Blox Fruits",
        "blox fruits": "🥊 Blox Fruits",
        "discord": "⚡ Discord"
    }
    
    if название.lower() in category_map:
        название = category_map[название.lower()]
    
    if название not in bot.shop.categories:
        available_categories = "\n".join([f"• `{cat}`" for cat in bot.shop.categories.keys()])
        await interaction.response.send_message(
            f"❌ Категория не найдена!\n\n**Доступные категории:**\n{available_categories}", 
            ephemeral=True
        )
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
            "ожидает оплаты": "⏳",
            "оплачен": "✅", 
            "в процессе": "🔄",
            "выполнен": "🎉",
            "отменен": "❌"
        }.get(status, "❓")
        
        order_date = datetime.fromisoformat(order_time).strftime("%d.%m.%Y %H:%M")
        
        embed.add_field(
            name=f"{status_emoji} Заказ #{order_id}",
            value=f"**{product_name}**\nКоличество: {quantity}\nСумма: {price:.2f} руб\nСтатус: {status}\nДата: {order_date}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# 🎰 КАЗИНО КОМАНДЫ
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

# 🏆 УРОВНИ КОМАНДЫ
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

# 🛡️ МОДЕРАЦИЯ КОМАНДЫ - ИСПРАВЛЕННЫЕ
def parse_time(time_str: str) -> int:
    """Парсинг времени из строки (1с, 1м, 1ч, 1д, 1н)"""
    time_units = {
        'с': 1, 'сек': 1, 'секунд': 1,
        'м': 60, 'мин': 60, 'минут': 60, 
        'ч': 3600, 'час': 3600, 'часов': 3600,
        'д': 86400, 'день': 86400, 'дней': 86400,
        'н': 604800, 'неделя': 604800, 'недель': 604800
    }
    
    # Убираем пробелы и приводим к нижнему регистру
    time_str = time_str.lower().replace(' ', '')
    
    # Ищем число и единицу измерения
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

@bot.tree.command(name="варн", description="Выдать варн пользователю (3 варна = мут на 1 час)")
@commands.has_permissions(manage_messages=True)
async def варн(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    # Инициализируем счетчик варнов для пользователя
    if пользователь.id not in user_warns:
        user_warns[пользователь.id] = 0
    
    user_warns[пользователь.id] += 1
    current_warns = user_warns[пользователь.id]
    
    if current_warns >= 3:
        # 3 варна = мут на 1 час
        try:
            mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await interaction.guild.create_role(name="Muted")
                
                for channel in interaction.guild.channels:
                    await channel.set_permissions(mute_role, send_messages=False, speak=False)
            
            await пользователь.add_roles(mute_role)
            
            # Сбрасываем варны
            user_warns[пользователь.id] = 0
            
            embed = Design.create_embed("⚠️ МУТ за 3 варна", 
                                      f"**Пользователь:** {пользователь.mention}\n"
                                      f"**Причина:** Получено 3 предупреждения\n"
                                      f"**Длительность:** 1 час\n"
                                      f"**Последнее нарушение:** {причина}", "danger")
            await interaction.response.send_message(embed=embed)
            
            # Автоматическое снятие мута через 1 час
            await asyncio.sleep(3600)
            if mute_role in пользователь.roles:
                await пользователь.remove_roles(mute_role)
                embed = Design.create_embed("✅ Мут снят", f"Мут с пользователя {пользователь.mention} снят", "success")
                await interaction.channel.send(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
    else:
        embed = Design.create_embed("⚠️ Варн", 
                                  f"**Пользователь:** {пользователь.mention}\n"
                                  f"**Причина:** {причина}\n"
                                  f"**Текущее количество варнов:** {current_warns}/3\n"
                                  f"**Следующий варн:** мут на 1 час", "warning")
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="мут", description="Замутить пользователя (с, м, ч, д, н)")
@commands.has_permissions(manage_roles=True)
async def мут(interaction: discord.Interaction, пользователь: discord.Member, время: str, причина: str = "Не указана"):
    try:
        # Парсим время
        seconds = parse_time(время)
        
        if seconds <= 0:
            await interaction.response.send_message("❌ Неверный формат времени! Используйте: 1с, 5м, 1ч, 2д, 1н", ephemeral=True)
            return
        
        if seconds > 604800:  # Максимум 1 неделя
            await interaction.response.send_message("❌ Максимальное время мута - 1 неделя", ephemeral=True)
            return
        
        mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await interaction.guild.create_role(name="Muted")
            
            for channel in interaction.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        
        await пользователь.add_roles(mute_role)
        
        # Форматируем время для вывода
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
        
        # Автоматическое снятие мута
        await asyncio.sleep(seconds)
        if mute_role in пользователь.roles:
            await пользователь.remove_roles(mute_role)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="бан", description="Забанить пользователя")
@commands.has_permissions(ban_members=True)
async def бан(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    try:
        await пользователь.ban(reason=причина)
        embed = Design.create_embed("✅ Бан", f"Пользователь {пользователь.mention} забанен", "success")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="кик", description="Кикнуть пользователя")
@commands.has_permissions(kick_members=True)
async def кик(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    try:
        await пользователь.kick(reason=причина)
        embed = Design.create_embed("✅ Кик", f"Пользователь {пользователь.mention} кикнут", "success")
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

# 🎵 МУЗЫКА КОМАНДЫ - УПРОЩЕННЫЕ
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

# 🔧 УТИЛИТЫ КОМАНДЫ
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
    `/мут` `/бан` `/кик` `/очистить` `/варн` `/тикет`

    **🎵 МУЗЫКА:**
    `/play` `/стоп` `/скип` `/очередь`

    **🔧 УТИЛИТЫ:**
    `/сервер` `/юзер` `/статистика`
    """, "primary")
    await interaction.response.send_message(embed=embed)

# 👑 АДМИН КОМАНДЫ
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

# 🔧 Обработчики ошибок
@выдать.error
@забрать.error
@установить.error
@сбросить.error
@админ.error
async def admin_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.CheckFailure):
        await interaction.response.send_message("❌ У вас нет прав администратора!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Ошибка: {error}", ephemeral=True)

@мут.error
@бан.error  
@кик.error
@очистить.error
@варн.error
async def mod_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.MissingPermissions):
        await interaction.response.send_message("❌ Недостаточно прав для выполнения этой команды!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Ошибка: {error}", ephemeral=True)

# 🔧 ОБРАБОТЧИКИ
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'🌐 Серверов: {len(bot.guilds)}')
    
    # ПРИНУДИТЕЛЬНАЯ СИНХРОНИЗАЦИЯ КОМАНД
    try:
        synced = await bot.tree.sync()
        print(f'✅ Синхронизировано {len(synced)} команд')
        
        # Выводим список всех команд для проверки
        commands_list = [cmd.name for cmd in bot.tree.get_commands()]
        print(f'📋 Доступные команды: {commands_list}')
    except Exception as e:
        print(f'❌ Ошибка синхронизации: {e}')
    
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

