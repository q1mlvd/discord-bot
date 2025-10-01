import os
import discord
from discord.ext import commands, tasks
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
    print("Ошибка: BOT_TOKEN не установлен в переменных окружения!")
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
        message = await interaction.response.send_message(embed=embed)
        
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

# Команды бота
@bot.command(name='balance')
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_data = db.get_user(member.id)
    
    embed = discord.Embed(
        title=f"{EMOJIS['coin']} Баланс {member.display_name}",
        color=0xffd700
    )
    embed.add_field(name="Баланс", value=f"{user_data[1]} {EMOJIS['coin']}", inline=True)
    embed.add_field(name="Ежедневная серия", value=f"{user_data[2]} дней", inline=True)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='daily')
async def daily(ctx):
    user_data = db.get_user(ctx.author.id)
    last_daily = datetime.datetime.fromisoformat(user_data[3]) if user_data[3] else None
    now = datetime.datetime.now()
    
    if last_daily and (now - last_daily).days < 1:
        await ctx.send("Вы уже получали ежедневную награду сегодня!")
        return
    
    streak = user_data[2] + 1 if last_daily and (now - last_daily).days == 1 else 1
    reward = 100 + (streak * 10)
    
    db.update_balance(ctx.author.id, reward)
    cursor = db.conn.cursor()
    cursor.execute('UPDATE users SET daily_streak = ?, last_daily = ? WHERE user_id = ?', 
                   (streak, now.isoformat(), ctx.author.id))
    db.conn.commit()
    db.log_transaction(ctx.author.id, 'daily', reward)
    
    embed = discord.Embed(
        title=f"{EMOJIS['daily']} Ежедневная награда",
        description=f"Награда: {reward} {EMOJIS['coin']}\nСерия: {streak} дней",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='pay')
async def pay(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("Сумма должна быть положительной!")
        return
    
    sender_data = db.get_user(ctx.author.id)
    if sender_data[1] < amount:
        await ctx.send("Недостаточно монет!")
        return
    
    db.update_balance(ctx.author.id, -amount)
    db.update_balance(member.id, amount)
    db.log_transaction(ctx.author.id, 'transfer', -amount, member.id, f"Перевод {member.name}")
    db.log_transaction(member.id, 'transfer', amount, ctx.author.id, f"Получено от {ctx.author.name}")
    
    embed = discord.Embed(
        title=f"{EMOJIS['coin']} Перевод средств",
        description=f"{ctx.author.mention} → {member.mention}",
        color=0x00ff00
    )
    embed.add_field(name="Сумма", value=f"{amount} {EMOJIS['coin']}")
    await ctx.send(embed=embed)

@bot.command(name='cases')
async def cases_list(ctx):
    embed = discord.Embed(title="🎁 Доступные кейсы", color=0xff69b4)
    
    for case_id, case in CASES.items():
        rewards_desc = "\n".join([f"• {r['type']} ({r['chance']*100:.1f}%)" for r in case['rewards']])
        embed.add_field(
            name=f"{case['name']} - {case['price']} {EMOJIS['coin']}",
            value=rewards_desc,
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='opencase')
async def open_case(ctx, case_id: str):
    if case_id not in CASES:
        await ctx.send("Кейс не найден! Используйте `/cases` для списка.")
        return
    
    case = CASES[case_id]
    view = CaseView(case_id, ctx.author.id)
    
    embed = discord.Embed(
        title=f"🎁 {case['name']}",
        description=f"Стоимость: {case['price']} {EMOJIS['coin']}",
        color=0xff69b4
    )
    
    await ctx.send(embed=embed, view=view)

@bot.command(name='steal')
async def steal(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id:
        await ctx.send("Нельзя красть у себя!")
        return
    
    thief_data = db.get_user(ctx.author.id)
    target_data = db.get_user(member.id)
    
    if thief_data[1] < 10:
        await ctx.send("Нужно минимум 10 монет для кражи!")
        return
    
    if target_data[1] < amount:
        await ctx.send("У цели недостаточно монет!")
        return
    
    success_chance = 0.3
    if random.random() <= success_chance:
        db.update_balance(ctx.author.id, amount)
        db.update_balance(member.id, -amount)
        db.log_transaction(ctx.author.id, 'steal', amount, member.id, "Успешная кража")
        
        embed = discord.Embed(
            title=f"{EMOJIS['steal']} Успешная кража!",
            description=f"{ctx.author.mention} украл {amount} {EMOJIS['coin']} у {member.mention}!",
            color=0x00ff00
        )
    else:
        penalty = min(amount // 2, 100)
        db.update_balance(ctx.author.id, -penalty)
        db.log_transaction(ctx.author.id, 'steal_fail', -penalty, member.id, "Неудачная кража")
        
        embed = discord.Embed(
            title=f"{EMOJIS['lose']} Кража провалилась!",
            description=f"{ctx.author.mention} оштрафован на {penalty} {EMOJIS['coin']}!",
            color=0xff0000
        )
    
    await ctx.send(embed=embed)

@bot.command(name='roulette')
async def roulette(ctx, bet: int):
    user_data = db.get_user(ctx.author.id)
    
    if user_data[1] < bet:
        await ctx.send("Недостаточно монет!")
        return
    
    winning_number = random.randint(0, 36)
    user_number = random.randint(0, 36)
    
    if user_number == winning_number:
        multiplier = 35
        winnings = bet * multiplier
        db.update_balance(ctx.author.id, winnings)
        result = f"ПОБЕДА! x{multiplier}\nВыигрыш: {winnings} {EMOJIS['coin']}"
        color = 0x00ff00
    else:
        db.update_balance(ctx.author.id, -bet)
        result = f"ПРОИГРЫШ!\nВыпало: {winning_number}, Ваше: {user_number}"
        color = 0xff0000
    
    embed = discord.Embed(
        title=f"🎰 Рулетка - Ставка: {bet} {EMOJIS['coin']}",
        description=result,
        color=color
    )
    await ctx.send(embed=embed)

@bot.command(name='leaderboard')
async def leaderboard(ctx, type: str = 'balance'):
    cursor = db.conn.cursor()
    
    if type == 'balance':
        cursor.execute('SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10')
        title = "🏆 Лидеры по балансу"
    else:
        await ctx.send("Доступные типы: balance")
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
    
    await ctx.send(embed=embed)

# Админ команды
@bot.command(name='admin_addcoins')
@commands.has_any_role(*ADMIN_ROLES)
async def admin_addcoins(ctx, member: discord.Member, amount: int):
    db.update_balance(member.id, amount)
    db.log_transaction(ctx.author.id, 'admin_add', amount, member.id, f"Админ {ctx.author.name}")
    
    embed = discord.Embed(
        title="⚙️ Админ действие",
        description=f"Выдано {amount} {EMOJIS['coin']} пользователю {member.mention}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='admin_broadcast')
@commands.has_any_role(*ADMIN_ROLES)
async def admin_broadcast(ctx, *, message: str):
    embed = discord.Embed(
        title="📢 Объявление от администрации",
        description=message,
        color=0xff69b4,
        timestamp=datetime.datetime.now()
    )
    
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(embed=embed)
                break

# Запуск бота
@bot.event
async def on_ready():
    print(f'Бот {bot.user.name} запущен!')
    await bot.change_presence(activity=discord.Game(name="Экономическую игру"))

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

