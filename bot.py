import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import sqlite3
import json
import random
import asyncio
import datetime
import aiohttp
from typing import Dict, List, Optional

# Получение токена из переменных окружения Railway
BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

if not BOT_TOKEN:
    print("Ошибка: DISCORD_BOT_TOKEN не установлен в переменных окружения!")
    exit(1)

# Настройки бота
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Конфигурация
DATABASE_FILE = 'economy.db'
LOG_CHANNEL_ID = 1422557295811887175
ADMIN_ROLES = ['Admin', 'Moderator']

# Эмодзи для оформления
EMOJIS = {
    'coin': '🪙',
    'daily': '📅',
    'case': '🎁',
    'win': '🎉',
    'lose': '💀',
    'steal': '🦹',
    'market': '🏪',
    'quest': '🗺️'
}

# База данных SQLite
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 100,
                daily_streak INTEGER DEFAULT 0,
                last_daily TEXT,
                inventory TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица транзакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                target_user_id INTEGER,
                description TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица кейсов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price INTEGER,
                rewards TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица маркета
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                item_name TEXT,
                price INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица достижений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                user_id INTEGER,
                achievement_id TEXT,
                unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, achievement_id)
            )
        ''')
        
        self.conn.commit()
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.execute('INSERT INTO users (user_id, balance) VALUES (?, ?)', (user_id, 100))
            self.conn.commit()
            return self.get_user(user_id)
        return user
    
    def update_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def log_transaction(self, user_id, transaction_type, amount, target_user_id=None, description=""):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, target_user_id, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, transaction_type, amount, target_user_id, description))
        self.conn.commit()

db = Database()

# Система кейсов
CASES = {
    'small': {
        'name': '📦 Малый кейс',
        'price': 50,
        'rewards': [
            {'type': 'coins', 'amount': (20, 50), 'chance': 0.7},
            {'type': 'coins', 'amount': (51, 100), 'chance': 0.3}
        ]
    },
    'medium': {
        'name': '📦 Средний кейс',
        'price': 150,
        'rewards': [
            {'type': 'coins', 'amount': (80, 150), 'chance': 0.6},
            {'type': 'coins', 'amount': (151, 300), 'chance': 0.3},
            {'type': 'role', 'name': 'Временный VIP', 'duration': 24, 'chance': 0.1}
        ]
    },
    'large': {
        'name': '💎 Большой кейс',
        'price': 500,
        'rewards': [
            {'type': 'coins', 'amount': (300, 600), 'chance': 0.5},
            {'type': 'coins', 'amount': (601, 1000), 'chance': 0.3},
            {'type': 'custom_role', 'chance': 0.15},
            {'type': 'special_item', 'name': 'Золотой ключ', 'chance': 0.05}
        ]
    },
    'elite': {
        'name': '👑 Элитный кейс',
        'price': 1000,
        'rewards': [
            {'type': 'coins', 'amount': (800, 1500), 'chance': 0.4},
            {'type': 'custom_role', 'chance': 0.3},
            {'type': 'special_item', 'name': 'Древний артефакт', 'chance': 0.2},
            {'type': 'bonus', 'multiplier': 2.0, 'duration': 48, 'chance': 0.1}
        ]
    },
    'secret': {
        'name': '🔮 Секретный кейс',
        'price': 2000,
        'rewards': [
            {'type': 'coins', 'amount': (1000, 5000), 'chance': 0.3},
            {'type': 'coins', 'amount': (-1000, -500), 'chance': 0.1},
            {'type': 'custom_role', 'chance': 0.2},
            {'type': 'special_item', 'name': 'Мифический предмет', 'chance': 0.15},
            {'type': 'bonus', 'multiplier': 3.0, 'duration': 72, 'chance': 0.1},
            {'type': 'multiple', 'count': 3, 'chance': 0.15}
        ]
    }
}

class CaseView(View):
    def __init__(self, case_id, user_id):
        super().__init__(timeout=60)
        self.case_id = case_id
        self.user_id = user_id
        self.opened = False
    
    @discord.ui.button(label='Открыть кейс', style=discord.ButtonStyle.primary, emoji='🎁')
    async def open_case(self, interaction: discord.Interaction, button: Button):
        if self.opened:
            return
        
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Этот кейс не для вас!", ephemeral=True)
            return
        
        self.opened = True
        case = CASES[self.case_id]
        user_data = db.get_user(self.user_id)
        
        if user_data[1] < case['price']:
            await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
            return
        
        # Спин анимация
        embed = discord.Embed(title="🎰 Открытие кейса...", color=0xffd700)
        await interaction.response.send_message(embed=embed)
        
        for i in range(3):
            await asyncio.sleep(1)
            embed.description = "🎁" * (i + 1)
            await interaction.edit_original_response(embed=embed)
        
        # Определение награды
        reward = self.get_reward(case)
        db.update_balance(self.user_id, -case['price'])
        db.log_transaction(self.user_id, 'case_purchase', -case['price'], description=f"Кейс: {case['name']}")
        
        # Выдача награды
        reward_text = await self.process_reward(interaction.user, reward, case)
        
        embed = discord.Embed(
            title=f"🎉 {case['name']} открыт!",
            description=reward_text,
            color=0x00ff00
        )
        embed.set_footer(text=f"Стоимость: {case['price']} {EMOJIS['coin']}")
        
        await interaction.edit_original_response(embed=embed)
    
    def get_reward(self, case):
        rand = random.random()
        cumulative = 0
        for reward in case['rewards']:
            cumulative += reward['chance']
            if rand <= cumulative:
                return reward
        return case['rewards'][-1]
    
    async def process_reward(self, user, reward, case):
        if reward['type'] == 'coins':
            amount = random.randint(*reward['amount'])
            db.update_balance(user.id, amount)
            db.log_transaction(user.id, 'case_reward', amount, description=f"Награда из {case['name']}")
            return f"Монеты: {amount} {EMOJIS['coin']}"
        
        elif reward['type'] == 'custom_role':
            await self.create_custom_role(user)
            return "🎭 Кастомная роль!"
        
        elif reward['type'] == 'special_item':
            return f"📦 Особый предмет: {reward['name']}"
        
        elif reward['type'] == 'bonus':
            return f"🚀 Бонус x{reward['multiplier']} на {reward['duration']}ч"
        
        elif reward['type'] == 'multiple':
            rewards = []
            for _ in range(reward['count']):
                sub_reward = self.get_reward(case)
                rewards.append(await self.process_reward(user, sub_reward, case))
            return " + ".join(rewards)
        
        elif reward['type'] == 'role':
            return f"👑 Роль: {reward['name']} на {reward['duration']}ч"
        
        return "Неизвестная награда"

    async def create_custom_role(self, user):
        try:
            # Создание тикета через вебхук
            channel = bot.get_channel(LOG_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="🎭 Запрос на создание кастомной роли",
                    description=f"Пользователь {user.mention} выиграл кастомную роль!",
                    color=0xff69b4,
                    timestamp=datetime.datetime.now()
                )
                embed.add_field(name="Пользователь", value=f"{user.name}#{user.discriminator}")
                embed.add_field(name="ID", value=user.id)
                
                webhook = await channel.create_webhook(name="Role Creator")
                await webhook.send(embed=embed, username="Case System")
                await webhook.delete()
                
        except Exception as e:
            print(f"Ошибка создания роли: {e}")

# Слеш-команды
@bot.tree.command(name="balance", description="Показать ваш баланс")
@app_commands.describe(user="Пользователь, чей баланс показать (опционально)")
async def balance(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user
    user_data = db.get_user(user.id)
    
    embed = discord.Embed(
        title=f"{EMOJIS['coin']} Баланс {user.display_name}",
        color=0xffd700
    )
    embed.add_field(name="Баланс", value=f"{user_data[1]} {EMOJIS['coin']}", inline=True)
    embed.add_field(name="Ежедневная серия", value=f"{user_data[2]} дней", inline=True)
    embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="daily", description="Получить ежедневную награду")
async def daily(interaction: discord.Interaction):
    user_data = db.get_user(interaction.user.id)
    last_daily = datetime.datetime.fromisoformat(user_data[3]) if user_data[3] else None
    now = datetime.datetime.now()
    
    if last_daily and (now - last_daily).days < 1:
        await interaction.response.send_message("Вы уже получали ежедневную награду сегодня!", ephemeral=True)
        return
    
    streak = user_data[2] + 1 if last_daily and (now - last_daily).days == 1 else 1
    reward = 100 + (streak * 10)
    
    db.update_balance(interaction.user.id, reward)
    cursor = db.conn.cursor()
    cursor.execute('UPDATE users SET daily_streak = ?, last_daily = ? WHERE user_id = ?', 
                   (streak, now.isoformat(), interaction.user.id))
    db.conn.commit()
    db.log_transaction(interaction.user.id, 'daily', reward)
    
    embed = discord.Embed(
        title=f"{EMOJIS['daily']} Ежедневная награда",
        description=f"Награда: {reward} {EMOJIS['coin']}\nСерия: {streak} дней",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="pay", description="Перевести монеты другому пользователю")
@app_commands.describe(user="Пользователь, которому переводим", amount="Сумма перевода")
async def pay(interaction: discord.Interaction, user: discord.Member, amount: int):
    if amount <= 0:
        await interaction.response.send_message("Сумма должна быть положительной!", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("Нельзя переводить самому себе!", ephemeral=True)
        return
    
    sender_data = db.get_user(interaction.user.id)
    if sender_data[1] < amount:
        await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
        return
    
    db.update_balance(interaction.user.id, -amount)
    db.update_balance(user.id, amount)
    db.log_transaction(interaction.user.id, 'transfer', -amount, user.id, f"Перевод {user.name}")
    db.log_transaction(user.id, 'transfer', amount, interaction.user.id, f"Получено от {interaction.user.name}")
    
    embed = discord.Embed(
        title=f"{EMOJIS['coin']} Перевод средств",
        description=f"{interaction.user.mention} → {user.mention}",
        color=0x00ff00
    )
    embed.add_field(name="Сумма", value=f"{amount} {EMOJIS['coin']}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="cases", description="Показать список доступных кейсов")
async def cases_list(interaction: discord.Interaction):
    embed = discord.Embed(title="🎁 Доступные кейсы", color=0xff69b4)
    
    for case_id, case in CASES.items():
        rewards_desc = "\n".join([f"• {r['type']} ({r['chance']*100:.1f}%)" for r in case['rewards']])
        embed.add_field(
            name=f"{case['name']} - {case['price']} {EMOJIS['coin']}",
            value=rewards_desc,
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="opencase", description="Открыть кейс")
@app_commands.describe(case_type="Тип кейса для открытия")
@app_commands.choices(case_type=[
    app_commands.Choice(name="📦 Малый кейс", value="small"),
    app_commands.Choice(name="📦 Средний кейс", value="medium"),
    app_commands.Choice(name="💎 Большой кейс", value="large"),
    app_commands.Choice(name="👑 Элитный кейс", value="elite"),
    app_commands.Choice(name="🔮 Секретный кейс", value="secret")
])
async def open_case(interaction: discord.Interaction, case_type: app_commands.Choice[str]):
    case = CASES[case_type.value]
    view = CaseView(case_type.value, interaction.user.id)
    
    embed = discord.Embed(
        title=f"🎁 {case['name']}",
        description=f"Стоимость: {case['price']} {EMOJIS['coin']}",
        color=0xff69b4
    )
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="steal", description="Попытаться украсть монеты у другого пользователя")
@app_commands.describe(user="Пользователь, у которого крадем", amount="Сумма для кражи")
async def steal(interaction: discord.Interaction, user: discord.Member, amount: int):
    if user.id == interaction.user.id:
        await interaction.response.send_message("Нельзя красть у себя!", ephemeral=True)
        return
    
    thief_data = db.get_user(interaction.user.id)
    target_data = db.get_user(user.id)
    
    if thief_data[1] < 10:
        await interaction.response.send_message("Нужно минимум 10 монет для кражи!", ephemeral=True)
        return
    
    if target_data[1] < amount:
        await interaction.response.send_message("У цели недостаточно монет!", ephemeral=True)
        return
    
    success_chance = 0.3
    if random.random() <= success_chance:
        db.update_balance(interaction.user.id, amount)
        db.update_balance(user.id, -amount)
        db.log_transaction(interaction.user.id, 'steal', amount, user.id, "Успешная кража")
        
        embed = discord.Embed(
            title=f"{EMOJIS['steal']} Успешная кража!",
            description=f"{interaction.user.mention} украл {amount} {EMOJIS['coin']} у {user.mention}!",
            color=0x00ff00
        )
    else:
        penalty = min(amount // 2, 100)
        db.update_balance(interaction.user.id, -penalty)
        db.log_transaction(interaction.user.id, 'steal_fail', -penalty, user.id, "Неудачная кража")
        
        embed = discord.Embed(
            title=f"{EMOJIS['lose']} Кража провалилась!",
            description=f"{interaction.user.mention} оштрафован на {penalty} {EMOJIS['coin']}!",
            color=0xff0000
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="roulette", description="Сыграть в рулетку")
@app_commands.describe(bet="Ставка в монетах")
async def roulette(interaction: discord.Interaction, bet: int):
    user_data = db.get_user(interaction.user.id)
    
    if user_data[1] < bet:
        await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
        return
    
    winning_number = random.randint(0, 36)
    user_number = random.randint(0, 36)
    
    if user_number == winning_number:
        multiplier = 35
        winnings = bet * multiplier
        db.update_balance(interaction.user.id, winnings)
        result = f"ПОБЕДА! x{multiplier}\nВыигрыш: {winnings} {EMOJIS['coin']}"
        color = 0x00ff00
    else:
        db.update_balance(interaction.user.id, -bet)
        result = f"ПРОИГРЫШ!\nВыпало: {winning_number}, Ваше: {user_number}"
        color = 0xff0000
    
    embed = discord.Embed(
        title=f"🎰 Рулетка - Ставка: {bet} {EMOJIS['coin']}",
        description=result,
        color=color
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="Показать таблицу лидеров")
@app_commands.describe(type="Тип лидерборда")
@app_commands.choices(type=[
    app_commands.Choice(name="Баланс", value="balance"),
    app_commands.Choice(name="Победы", value="wins"),
    app_commands.Choice(name="Кражи", value="steals")
])
async def leaderboard(interaction: discord.Interaction, type: app_commands.Choice[str]):
    cursor = db.conn.cursor()
    
    if type.value == 'balance':
        cursor.execute('SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10')
        title = "🏆 Лидеры по балансу"
    else:
        await interaction.response.send_message("Доступные типы: balance", ephemeral=True)
        return
    
    embed = discord.Embed(title=title, color=0xffd700)
    
    for i, (user_id, balance) in enumerate(cursor.fetchall(), 1):
        user = bot.get_user(user_id)
        name = user.name if user else f"User#{user_id}"
        embed.add_field(
            name=f"{i}. {name}",
            value=f"{balance} {EMOJIS['coin']}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# Админ команды
@bot.tree.command(name="admin_addcoins", description="Добавить монеты пользователю (админ)")
@app_commands.describe(user="Пользователь", amount="Количество монет")
async def admin_addcoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    # Проверка прав
    if not any(role.name in ADMIN_ROLES for role in interaction.user.roles):
        await interaction.response.send_message("У вас нет прав для использования этой команды!", ephemeral=True)
        return
    
    db.update_balance(user.id, amount)
    db.log_transaction(interaction.user.id, 'admin_add', amount, user.id, f"Админ {interaction.user.name}")
    
    embed = discord.Embed(
        title="⚙️ Админ действие",
        description=f"Выдано {amount} {EMOJIS['coin']} пользователю {user.mention}",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="admin_broadcast", description="Отправить объявление всем (админ)")
@app_commands.describe(message="Текст объявления")
async def admin_broadcast(interaction: discord.Interaction, message: str):
    # Проверка прав
    if not any(role.name in ADMIN_ROLES for role in interaction.user.roles):
        await interaction.response.send_message("У вас нет прав для использования этой команды!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📢 Объявление от администрации",
        description=message,
        color=0xff69b4,
        timestamp=datetime.datetime.now()
    )
    
    await interaction.response.send_message("Объявление отправляется...", ephemeral=True)
    
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(embed=embed)
                    break
                except:
                    continue

# Синхронизация команд при запуске
@bot.event
async def on_ready():
    print(f'Бот {bot.user.name} запущен!')
    
    # Синхронизация слеш-команд
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} команд")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")
    
    await bot.change_presence(activity=discord.Game(name="Экономическую игру"))

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
