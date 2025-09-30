import discord
from discord.ext import commands, tasks
import os
import asyncio
import aiosqlite
from datetime import datetime, timedelta
import random
from typing import Optional
from dotenv import load_dotenv
import yt_dlp

# 🔧 КОНСТАНТЫ СЕРВЕРА
GUILD_ID = 993041244706066552
ADMIN_LOG_CHANNEL = 1419779743083003944
EVENTS_CHANNEL = 1418738569081786459
ECONOMY_CHANNEL = 1422641391682588734

# 🛡️ СИСТЕМА РОЛЕЙ (замени на реальные ID)
ADMIN_ROLES = [1195144951546265675, 766767256742526996, 1078693283695448064, 1138140772097597472, 691904643181314078]
MODERATOR_ROLES = [1167093102868172911, 1360243534946373672, 993043931342319636, 1338611327022923910, 1338609155203661915, 1365798715930968244, 1188261847850299514]

# 💰 ГЛОБАЛЬНЫЕ СИСТЕМЫ
user_warns = {}
mute_data = {}
user_credits = {}
user_mining_farms = {}
user_crypto = {}
rob_cooldowns = {}
economic_bans = {}
active_events = {}
server_tax_pool = 0

crypto_prices = {"BITCOIN": 50000, "ETHEREUM": 3000, "DOGECOIN": 0.15}

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

# 🛡️ СИСТЕМА ПРАВ
def is_admin():
    async def predicate(interaction: discord.Interaction):
        if interaction.guild.id != GUILD_ID:
            return False
        user_roles = [role.id for role in interaction.user.roles]
        return any(role in ADMIN_ROLES for role in user_roles)
    return commands.check(predicate)

def is_moderator():
    async def predicate(interaction: discord.Interaction):
        if interaction.guild.id != GUILD_ID:
            return False
        user_roles = [role.id for role in interaction.user.roles]
        return any(role in MODERATOR_ROLES + ADMIN_ROLES for role in user_roles)
    return commands.check(predicate)

def is_user():
    async def predicate(interaction: discord.Interaction):
        return interaction.guild.id == GUILD_ID
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
                    f"⏳ Разблокировка через: {hours_left} часов",
                    ephemeral=True
                )
                return False
            else:
                del economic_bans[ban_key]
        return True
    return commands.check(predicate)

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
        
    async def setup_hook(self):
        await self.db.init_db()
        
        # Загружаем команды
        await self.load_extension('commands.user_commands')
        await self.load_extension('commands.mod_commands')
        await self.load_extension('commands.admin_commands')
        
        # Синхронизируем для твоего сервера
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        
        print(f"✅ Синхронизировано команд для сервера {GUILD_ID}")

bot = MegaBot()

# 🔥 ОСНОВНЫЕ КОМАНДЫ ДЛЯ ВСЕХ УЧАСТНИКОВ
@bot.tree.command(name="баланс", description="Проверить баланс")
@is_user()
async def баланс(interaction: discord.Interaction, пользователь: Optional[discord.Member] = None):
    user = пользователь or interaction.user
    balance = await bot.economy.get_balance(user.id)
    embed = Design.create_embed("💰 Баланс", f"**{user.display_name}**\nБаланс: `{balance:,} монет`", "economy")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ежедневно", description="Получить ежедневную награду")
@is_user()
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
@is_user()
@check_economic_ban()
async def работа(interaction: discord.Interaction):
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

@bot.tree.command(name="передать", description="Передать деньги")
@is_user()
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

@bot.tree.command(name="слоты", description="Играть в слоты")
@is_user()
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

# 🔧 КОМАНДЫ МОДЕРАЦИИ
@bot.tree.command(name="пред", description="Выдать предупреждение")
@is_moderator()
async def пред(interaction: discord.Interaction, пользователь: discord.Member, причина: str = "Не указана"):
    try:
        target_roles = [role.id for role in пользователь.roles]
        if any(role in MODERATOR_ROLES + ADMIN_ROLES for role in target_roles):
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
        if any(role in MODERATOR_ROLES + ADMIN_ROLES for role in target_roles):
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

# 👑 АДМИН КОМАНДЫ
@bot.tree.command(name="выдать", description="Выдать монеты")
@is_admin()
async def выдать(interaction: discord.Interaction, пользователь: discord.Member, количество: int):
    if количество <= 0:
        await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
        return
    
    new_balance = await bot.economy.update_balance(пользователь.id, количество)
    
    embed = Design.create_embed("💰 Деньги выданы", 
                              f"**Пользователь:** {пользователь.mention}\n"
                              f"**Выдано:** {количество:,} монет\n"
                              f"**Новый баланс:** {new_balance:,} монет", "success")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="перезагрузить", description="Перезагрузить бота")
@is_admin()
async def перезагрузить(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    try:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        embed = Design.create_embed("✅ Перезагрузка завершена", "Бот успешно перезагружен!", "success")
    except Exception as e:
        embed = Design.create_embed("❌ Ошибка перезагрузки", f"Произошла ошибка: {e}", "danger")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен на сервере {GUILD_ID}!')
    print(f'🌐 Серверов: {len(bot.guilds)}')
    
    # Отправляем сообщение в админ-канал
    try:
        channel = bot.get_channel(ADMIN_LOG_CHANNEL)
        if channel:
            embed = Design.create_embed("🤖 Бот запущен", f"**Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n**Статус:** ✅ Активен", "success")
            await channel.send(embed=embed)
    except Exception as e:
        print(f"❌ Ошибка отправки в админ-канал: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.guild and message.guild.id == GUILD_ID:
        async with aiosqlite.connect(bot.db.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.author.id,))
            await db.commit()
    
    await bot.process_commands(message)

if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if not TOKEN:
        print("❌ Токен не найден! Проверь DISCORD_TOKEN в .env")
        exit(1)
    
    try:
        print("🚀 Запуск мега-бота...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
