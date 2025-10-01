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
import math
import io
import json

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
        "event": 0x9B59B6, "credit": 0xE74C3C, "nft": 0x9C27B0,
        "market": 0x4CAF50, "auction": 0xFF9800
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
            
            # NFT таблицы
            await db.execute('''
                CREATE TABLE IF NOT EXISTS nft_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    rarity TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    image_data TEXT,
                    created_at TEXT,
                    creator_id INTEGER,
                    metadata TEXT
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_nft (
                    user_id INTEGER,
                    nft_id INTEGER,
                    acquired_at TEXT,
                    PRIMARY KEY (user_id, nft_id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS nft_market (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nft_id INTEGER,
                    seller_id INTEGER,
                    price INTEGER NOT NULL,
                    listed_at TEXT,
                    status TEXT DEFAULT 'active'
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
                    await db.execute('INSERT INTO users (user_id, balance) VALUES (?, 1000)', (user_id,))
                    await db.commit()
                    return 1000
    
    async def update_balance(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 1000)', (user_id,))
            await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
            await db.commit()
            return await self.get_balance(user_id)

# 🎨 ПРОСТАЯ СИСТЕМА NFT (с текстовыми "изображениями")
class NFTSystem:
    def __init__(self, db: Database, economy: EconomySystem):
        self.db = db
        self.economy = economy
        self.rarity_colors = {
            "common": "🟢",
            "rare": "🔵", 
            "epic": "🟣",
            "legendary": "🟡"
        }
        self.item_types = ["Art", "Collectible", "Game Item", "Music", "Domain", "Meme"]
        
    async def create_nft(self, name: str, description: str, rarity: str, item_type: str, creator_id: int) -> dict:
        """Создает новый NFT"""
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                created_at = datetime.now().isoformat()
                
                # Создаем текстовое "изображение"
                image_data = self._generate_text_image(name, rarity, item_type)
                
                metadata = json.dumps({
                    "created": created_at,
                    "attributes": {
                        "rarity": rarity,
                        "type": item_type,
                        "generation": "1.0"
                    }
                })
                
                await db.execute(
                    'INSERT INTO nft_items (name, description, rarity, item_type, image_data, created_at, creator_id, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (name, description, rarity, item_type, image_data, created_at, creator_id, metadata)
                )
                
                nft_id = db.last_insert_rowid
                
                # Добавляем NFT создателю
                await db.execute(
                    'INSERT INTO user_nft (user_id, nft_id, acquired_at) VALUES (?, ?, ?)',
                    (creator_id, nft_id, created_at)
                )
                
                await db.commit()
                
                return {
                    "success": True,
                    "nft_id": nft_id,
                    "name": name,
                    "rarity": rarity,
                    "image_data": image_data
                }
                
        except Exception as e:
            print(f"Ошибка создания NFT: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_text_image(self, name: str, rarity: str, item_type: str) -> str:
        """Генерирует текстовое представление NFT"""
        color = self.rarity_colors.get(rarity, "⚪")
        return f"""
{color} {name.upper()} {color}
📊 Редкость: {rarity.upper()}
🎨 Тип: {item_type}
✨ Уникальный цифровой актив
        """.strip()
    
    async def get_nft(self, nft_id: int) -> Optional[dict]:
        """Получает информацию о NFT"""
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                async with db.execute('SELECT * FROM nft_items WHERE id = ?', (nft_id,)) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        return {
                            "id": result[0], "name": result[1], "description": result[2],
                            "rarity": result[3], "item_type": result[4], "image_data": result[5],
                            "created_at": result[6], "creator_id": result[7], "metadata": result[8]
                        }
            return None
        except Exception as e:
            print(f"Ошибка получения NFT: {e}")
            return None
    
    async def get_user_nfts(self, user_id: int) -> list:
        """Получает все NFT пользователя"""
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                async with db.execute('''
                    SELECT ni.*, un.acquired_at 
                    FROM nft_items ni 
                    JOIN user_nft un ON ni.id = un.nft_id 
                    WHERE un.user_id = ?
                ''', (user_id,)) as cursor:
                    results = await cursor.fetchall()
                    nfts = []
                    for result in results:
                        nfts.append({
                            "id": result[0], "name": result[1], "description": result[2],
                            "rarity": result[3], "item_type": result[4], "image_data": result[5],
                            "created_at": result[6], "creator_id": result[7], "metadata": result[8],
                            "acquired_at": result[9]
                        })
                    return nfts
        except Exception as e:
            print(f"Ошибка получения NFT пользователя: {e}")
            return []
    
    async def transfer_nft(self, nft_id: int, from_user_id: int, to_user_id: int) -> bool:
        """Передает NFT другому пользователю"""
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                # Проверяем владение
                async with db.execute(
                    'SELECT * FROM user_nft WHERE user_id = ? AND nft_id = ?',
                    (from_user_id, nft_id)
                ) as cursor:
                    if not await cursor.fetchone():
                        return False
                
                # Передаем NFT
                await db.execute(
                    'DELETE FROM user_nft WHERE user_id = ? AND nft_id = ?',
                    (from_user_id, nft_id)
                )
                
                await db.execute(
                    'INSERT INTO user_nft (user_id, nft_id, acquired_at) VALUES (?, ?, ?)',
                    (to_user_id, nft_id, datetime.now().isoformat())
                )
                
                await db.commit()
                return True
                
        except Exception as e:
            print(f"Ошибка передачи NFT: {e}")
            return False

# 🛒 СИСТЕМА МАРКЕТПЛЕЙСА
class MarketplaceSystem:
    def __init__(self, db: Database, economy: EconomySystem, nft_system: NFTSystem):
        self.db = db
        self.economy = economy
        self.nft_system = nft_system
    
    async def list_nft(self, nft_id: int, seller_id: int, price: int) -> bool:
        """Выставляет NFT на маркетплейс"""
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                # Проверяем владение
                nfts = await self.nft_system.get_user_nfts(seller_id)
                if not any(nft['id'] == nft_id for nft in nfts):
                    return False
                
                # Проверяем, не выставлен ли уже NFT
                async with db.execute(
                    'SELECT * FROM nft_market WHERE nft_id = ? AND status = "active"',
                    (nft_id,)
                ) as cursor:
                    if await cursor.fetchone():
                        return False
                
                # Выставляем на маркет
                await db.execute(
                    'INSERT INTO nft_market (nft_id, seller_id, price, listed_at) VALUES (?, ?, ?, ?)',
                    (nft_id, seller_id, price, datetime.now().isoformat())
                )
                
                await db.commit()
                return True
                
        except Exception as e:
            print(f"Ошибка выставления NFT: {e}")
            return False
    
    async def buy_nft(self, listing_id: int, buyer_id: int) -> bool:
        """Покупает NFT с маркетплейса"""
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                # Получаем информацию о listing
                async with db.execute('''
                    SELECT nm.*, ni.name, nm.seller_id as seller_id 
                    FROM nft_market nm 
                    JOIN nft_items ni ON nm.nft_id = ni.id 
                    WHERE nm.id = ? AND nm.status = "active"
                ''', (listing_id,)) as cursor:
                    result = await cursor.fetchone()
                    if not result:
                        return False
                
                price = result[3]
                seller_id = result[2]
                nft_id = result[1]
                
                # Проверяем баланс покупателя
                buyer_balance = await self.economy.get_balance(buyer_id)
                if buyer_balance < price:
                    return False
                
                # Проверяем, что покупатель не является продавцом
                if buyer_id == seller_id:
                    return False
                
                # Выполняем транзакцию
                await self.economy.update_balance(buyer_id, -price)
                await self.economy.update_balance(seller_id, price)
                
                # Передаем NFT
                await self.nft_system.transfer_nft(nft_id, seller_id, buyer_id)
                
                # Обновляем статус listing
                await db.execute(
                    'UPDATE nft_market SET status = "sold" WHERE id = ?',
                    (listing_id,)
                )
                
                await db.commit()
                return True
                
        except Exception as e:
            print(f"Ошибка покупки NFT: {e}")
            return False
    
    async def get_market_listings(self) -> list:
        """Получает активные listings маркетплейса"""
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                async with db.execute('''
                    SELECT nm.*, ni.name, ni.rarity, ni.item_type, ni.image_data
                    FROM nft_market nm
                    JOIN nft_items ni ON nm.nft_id = ni.id
                    WHERE nm.status = "active"
                    ORDER BY nm.listed_at DESC
                ''') as cursor:
                    results = await cursor.fetchall()
                    listings = []
                    for result in results:
                        listings.append({
                            "id": result[0], "nft_id": result[1], "seller_id": result[2],
                            "price": result[3], "listed_at": result[4], "status": result[5],
                            "name": result[6], "rarity": result[7], "item_type": result[8],
                            "image_data": result[9]
                        })
                    return listings
        except Exception as e:
            print(f"Ошибка получения listings: {e}")
            return []

# 🏗️ ГЛАВНЫЙ БОТ
class MegaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        
        self.db = Database()
        self.economy = EconomySystem(self.db)
        
        # NFT системы
        self.nft_system = NFTSystem(self.db, self.economy)
        self.marketplace_system = MarketplaceSystem(self.db, self.economy, self.nft_system)
        
        self.start_time = datetime.now()
    
    async def setup_hook(self):
        await self.db.init_db()
        try:
            synced = await self.tree.sync()
            print(f"✅ Синхронизировано {len(synced)} команд")
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")

bot = MegaBot()

# 🎨 NFT КОМАНДЫ
@bot.tree.command(name="создать_nft", description="Создать новый NFT")
async def создать_nft(interaction: discord.Interaction, название: str, описание: str, редкость: str, тип: str):
    try:
        valid_rarities = ["common", "rare", "epic", "legendary"]
        valid_types = ["Art", "Collectible", "Game Item", "Music", "Domain", "Meme"]
        
        if редкость.lower() not in valid_rarities:
            await interaction.response.send_message(
                f"❌ Неверная редкость! Доступно: {', '.join(valid_rarities)}", 
                ephemeral=True
            )
            return
        
        if тип not in valid_types:
            await interaction.response.send_message(
                f"❌ Неверный тип! Доступно: {', '.join(valid_types)}", 
                ephemeral=True
            )
            return
        
        # Создаем NFT
        result = await bot.nft_system.create_nft(
            название, описание, редкость.lower(), тип, interaction.user.id
        )
        
        if result["success"]:
            embed = Design.create_embed(
                "🎨 NFT Создан!",
                f"```{result['image_data']}```\n"
                f"**Название:** {название}\n"
                f"**Описание:** {описание}\n"
                f"**Редкость:** {редкость}\n"
                f"**Тип:** {тип}\n"
                f"**ID:** #{result['nft_id']}",
                "nft"
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                f"❌ Ошибка создания NFT: {result.get('error', 'Неизвестная ошибка')}", 
                ephemeral=True
            )
            
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Ошибка создания NFT: {e}", 
            ephemeral=True
        )

@bot.tree.command(name="мои_nft", description="Показать мои NFT")
async def мои_nft(interaction: discord.Interaction):
    try:
        nfts = await bot.nft_system.get_user_nfts(interaction.user.id)
        
        if not nfts:
            embed = Design.create_embed("🎨 Мои NFT", "У вас пока нет NFT", "nft")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = Design.create_embed(
            f"🎨 Коллекция NFT ({len(nfts)} items)",
            f"**Владелец:** {interaction.user.mention}",
            "nft"
        )
        
        for nft in nfts[:5]:
            embed.add_field(
                name=f"#{nft['id']} - {nft['name']}",
                value=f"```{nft['image_data']}```\n**Редкость:** {nft['rarity']}\n**Тип:** {nft['item_type']}",
                inline=False
            )
        
        if len(nfts) > 5:
            embed.set_footer(text=f"И еще {len(nfts) - 5} NFT...")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Ошибка получения NFT: {e}", 
            ephemeral=True
        )

@bot.tree.command(name="маркетплейс", description="Просмотр маркетплейса NFT")
async def маркетплейс(interaction: discord.Interaction):
    try:
        listings = await bot.marketplace_system.get_market_listings()
        
        if not listings:
            embed = Design.create_embed("🛒 Маркетплейс NFT", "На маркетплейсе пока нет NFT", "market")
            await interaction.response.send_message(embed=embed)
            return
        
        embed = Design.create_embed(
            "🛒 Маркетплейс NFT",
            f"**Доступно NFT:** {len(listings)}",
            "market"
        )
        
        for listing in listings[:3]:
            embed.add_field(
                name=f"#{listing['nft_id']} - {listing['name']}",
                value=f"```{listing['image_data']}```\n**Цена:** {listing['price']} монет\n**Редкость:** {listing['rarity']}\n**Тип:** {listing['item_type']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Ошибка загрузки маркетплейса: {e}", 
            ephemeral=True
        )

@bot.tree.command(name="выставить_на_маркет", description="Выставить NFT на маркетплейс")
async def выставить_на_маркет(interaction: discord.Interaction, nft_id: int, цена: int):
    try:
        if цена <= 0:
            await interaction.response.send_message("❌ Цена должна быть положительной!", ephemeral=True)
            return
        
        success = await bot.marketplace_system.list_nft(nft_id, interaction.user.id, цена)
        
        if success:
            embed = Design.create_embed(
                "🛒 NFT на маркетплейсе!",
                f"**NFT ID:** #{nft_id}\n"
                f"**Цена:** {цена} монет\n"
                f"**Продавец:** {interaction.user.mention}",
                "market"
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                "❌ Не удалось выставить NFT. Проверьте ID и владение.", 
                ephemeral=True
            )
            
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Ошибка выставления NFT: {e}", 
            ephemeral=True
        )

@bot.tree.command(name="купить_nft", description="Купить NFT с маркетплейса")
async def купить_nft(interaction: discord.Interaction, listing_id: int):
    try:
        success = await bot.marketplace_system.buy_nft(listing_id, interaction.user.id)
        
        if success:
            embed = Design.create_embed(
                "✅ NFT Куплен!",
                f"**Покупка:** Listing #{listing_id}\n"
                f"**Покупатель:** {interaction.user.mention}",
                "success"
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                "❌ Не удалось купить NFT. Проверьте ID и баланс.", 
                ephemeral=True
            )
            
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Ошибка покупки NFT: {e}", 
            ephemeral=True
        )

@bot.tree.command(name="nft_инфо", description="Информация о конкретном NFT")
async def nft_инфо(interaction: discord.Interaction, nft_id: int):
    try:
        nft = await bot.nft_system.get_nft(nft_id)
        
        if not nft:
            await interaction.response.send_message("❌ NFT не найден!", ephemeral=True)
            return
        
        embed = Design.create_embed(
            f"🎨 NFT #{nft_id} - {nft['name']}",
            f"```{nft['image_data']}```\n"
            f"**Описание:** {nft['description']}\n"
            f"**Редкость:** {nft['rarity']}\n"
            f"**Тип:** {nft['item_type']}\n"
            f"**Создан:** {datetime.fromisoformat(nft['created_at']).strftime('%d.%m.%Y')}",
            "nft"
        )
        
        await interaction.response.send_message(embed=embed)
            
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Ошибка получения информации: {e}", 
            ephemeral=True
        )

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
            await db.execute('INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 1000)', (message.author.id,))
            await db.commit()
    
    await bot.process_commands(message)

if __name__ == "__main__":
    try:
        print("🚀 Запуск бота с NFT маркетом...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
