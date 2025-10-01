import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
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

# ID администраторов (используем целые числа)
ADMIN_IDS = [766767256742526996, 1195144951546265675, 691904643181314078, 1078693283695448064, 1138140772097597472]

# ID администратора для уведомлений
ADMIN_USER_ID = 1188261847850299514

# Эмодзи для оформления
EMOJIS = {
    'coin': '🪙',
    'daily': '📅',
    'case': '🎁',
    'win': '🎉',
    'lose': '💀',
    'steal': '🦹',
    'market': '🏪',
    'quest': '🗺️',
    'dice': '🎲',
    'duel': '⚔️',
    'admin': '⚙️'
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
        
        # Таблица квестов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quests (
                user_id INTEGER,
                quest_id TEXT,
                progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                last_quest TEXT,
                PRIMARY KEY (user_id, quest_id)
            )
        ''')
        
        # Таблица дуэлей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS duels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger_id INTEGER,
                target_id INTEGER,
                bet INTEGER,
                status TEXT DEFAULT 'pending',
                winner_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица предметов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                value INTEGER,
                rarity TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        self.initialize_default_data()
    
    def initialize_default_data(self):
        cursor = self.conn.cursor()
        
        # Проверяем, есть ли уже кейсы
        cursor.execute('SELECT COUNT(*) FROM cases')
        if cursor.fetchone()[0] == 0:
            # Добавляем стандартные кейсы без кастомных ролей
            default_cases = [
                ('📦 Малый кейс', 50, json.dumps([
                    {'type': 'coins', 'amount': [10, 40], 'chance': 0.7},
                    {'type': 'coins', 'amount': [41, 100], 'chance': 0.25},
                    {'type': 'coins', 'amount': [101, 300], 'chance': 0.05}
                ])),
                ('📦 Средний кейс', 150, json.dumps([
                    {'type': 'coins', 'amount': [50, 120], 'chance': 0.6},
                    {'type': 'coins', 'amount': [121, 300], 'chance': 0.3},
                    {'type': 'special_item', 'name': 'Магический свиток', 'chance': 0.05},
                    {'type': 'coins', 'amount': [301, 800], 'chance': 0.05}
                ])),
                ('💎 Большой кейс', 500, json.dumps([
                    {'type': 'coins', 'amount': [200, 400], 'chance': 0.5},
                    {'type': 'coins', 'amount': [401, 1000], 'chance': 0.3},
                    {'type': 'special_item', 'name': 'Золотой ключ', 'chance': 0.08},
                    {'type': 'bonus', 'multiplier': 1.5, 'duration': 24, 'chance': 0.07},
                    {'type': 'coins', 'amount': [1001, 2500], 'chance': 0.05}
                ])),
                ('👑 Элитный кейс', 1000, json.dumps([
                    {'type': 'coins', 'amount': [500, 1000], 'chance': 0.3},
                    {'type': 'coins', 'amount': [-300, -100], 'chance': 0.2},
                    {'type': 'special_item', 'name': 'Древний артефакт', 'chance': 0.15},
                    {'type': 'bonus', 'multiplier': 2.0, 'duration': 48, 'chance': 0.1},
                    {'type': 'coins', 'amount': [1001, 3000], 'chance': 0.15},
                    {'type': 'coins', 'amount': [3001, 6000], 'chance': 0.1}
                ])),
                ('🔮 Секретный кейс', 2000, json.dumps([
                    {'type': 'coins', 'amount': [800, 1500], 'chance': 0.3},
                    {'type': 'coins', 'amount': [-1000, -500], 'chance': 0.15},
                    {'type': 'special_item', 'name': 'Мифический предмет', 'chance': 0.15},
                    {'type': 'bonus', 'multiplier': 3.0, 'duration': 72, 'chance': 0.07},
                    {'type': 'multiple', 'count': 3, 'chance': 0.05},
                    {'type': 'coins', 'amount': [1501, 3000], 'chance': 0.15},
                    {'type': 'coins', 'amount': [4001, 7000], 'chance': 0.13}
                ]))
            ]
            
            for case in default_cases:
                cursor.execute('INSERT INTO cases (name, price, rewards) VALUES (?, ?, ?)', case)
        
        # Проверяем, есть ли уже предметы
        cursor.execute('SELECT COUNT(*) FROM items')
        if cursor.fetchone()[0] == 0:
            # Добавляем стандартные предметы
            default_items = [
                ('Золотой ключ', 'Открывает особые кейсы', 500, 'rare'),
                ('Древний артефакт', 'Мощный магический предмет', 1000, 'epic'),
                ('Мифический предмет', 'Легендарный артефакт', 2000, 'legendary'),
                ('Билет VIP', 'Дает доступ к VIP зоне', 300, 'uncommon'),
                ('Магический свиток', 'Увеличивает удачу', 150, 'common'),
                ('Сундук с сокровищами', 'Содержит случайные награды', 800, 'rare'),
                ('Зачарованный амулет', 'Дает защиту от проигрышей', 600, 'uncommon')
            ]
            
            for item in default_items:
                cursor.execute('INSERT INTO items (name, description, value, rarity) VALUES (?, ?, ?, ?)', item)
        
        self.conn.commit()

    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if not user:
            # Создаем пользователя с правильным JSON для инвентаря
            cursor.execute('INSERT INTO users (user_id, balance, inventory) VALUES (?, ?, ?)', 
                         (user_id, 100, json.dumps({"cases": {}, "items": {}})))
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
    
    def get_cases(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM cases')
        return cursor.fetchall()
    
    def get_case(self, case_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,))
        return cursor.fetchone()
    
    def create_case(self, name, price, rewards):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO cases (name, price, rewards) VALUES (?, ?, ?)', (name, price, json.dumps(rewards)))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_case(self, case_id, name, price, rewards):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE cases SET name = ?, price = ?, rewards = ? WHERE id = ?', 
                      (name, price, json.dumps(rewards), case_id))
        self.conn.commit()
    
    def delete_case(self, case_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM cases WHERE id = ?', (case_id,))
        self.conn.commit()
    
    def get_items(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM items')
        return cursor.fetchall()
    
    def get_item(self, item_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM items WHERE id = ?', (item_id,))
        return cursor.fetchone()
    
    def add_item_to_inventory(self, user_id, item_name):
        cursor = self.conn.cursor()
        cursor.execute('SELECT inventory FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            inventory = json.loads(result[0])
        else:
            inventory = {"cases": {}, "items": {}}
            
        if "items" not in inventory:
            inventory["items"] = {}
            
        if item_name in inventory["items"]:
            inventory["items"][item_name] += 1
        else:
            inventory["items"][item_name] = 1
        
        cursor.execute('UPDATE users SET inventory = ? WHERE user_id = ?', (json.dumps(inventory), user_id))
        self.conn.commit()
    
    def remove_item_from_inventory(self, user_id, item_name):
        cursor = self.conn.cursor()
        cursor.execute('SELECT inventory FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return False
            
        inventory = json.loads(result[0])
        
        if item_name in inventory.get("items", {}):
            if inventory["items"][item_name] > 1:
                inventory["items"][item_name] -= 1
            else:
                del inventory["items"][item_name]
            
            cursor.execute('UPDATE users SET inventory = ? WHERE user_id = ?', (json.dumps(inventory), user_id))
            self.conn.commit()
            return True
        return False

    def add_case_to_inventory(self, user_id, case_id, case_name, source="gifted"):
        cursor = self.conn.cursor()
        cursor.execute('SELECT inventory FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            inventory = json.loads(result[0])
        else:
            inventory = {"cases": {}, "items": {}}
        
        # Добавляем кейс в инвентарь
        if "cases" not in inventory:
            inventory["cases"] = {}
        
        case_key = f"case_{case_id}"
        if case_key in inventory["cases"]:
            inventory["cases"][case_key]["count"] += 1
        else:
            inventory["cases"][case_key] = {
                "name": case_name,
                "count": 1,
                "source": source
            }
        
        cursor.execute('UPDATE users SET inventory = ? WHERE user_id = ?', (json.dumps(inventory), user_id))
        self.conn.commit()
    
    def get_user_inventory(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT inventory FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            try:
                return json.loads(result[0])
            except json.JSONDecodeError:
                return {"cases": {}, "items": {}}
        return {"cases": {}, "items": {}}
    
    def remove_case_from_inventory(self, user_id, case_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT inventory FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return False
            
        inventory = json.loads(result[0])
        
        case_key = f"case_{case_id}"
        if case_key in inventory.get("cases", {}):
            if inventory["cases"][case_key]["count"] > 1:
                inventory["cases"][case_key]["count"] -= 1
            else:
                del inventory["cases"][case_key]
            
            cursor.execute('UPDATE users SET inventory = ? WHERE user_id = ?', (json.dumps(inventory), user_id))
            self.conn.commit()
            return True
        return False

db = Database()

# Система достижений
ACHIEVEMENTS = {
    'first_daily': {'name': 'Первый шаг', 'description': 'Получите первую ежедневную награду'},
    'rich': {'name': 'Богач', 'description': 'Накопите 1000 монет'},
    'gambler': {'name': 'Азартный игрок', 'description': 'Выиграйте в рулетку 10 раз'},
    'thief': {'name': 'Вор', 'description': 'Успешно украдите монеты 5 раз'},
    'case_opener': {'name': 'Коллекционер', 'description': 'Откройте 20 кейсов'},
    'duel_master': {'name': 'Мастер дуэлей', 'description': 'Выиграйте 10 дуэлей'}
}

# Система квестов
QUESTS = {
    'daily_rich': {'name': 'Ежедневный богач', 'description': 'Получите 3 ежедневные награды подряд', 'reward': 300},
    'gambling_king': {'name': 'Король азарта', 'description': 'Выиграйте 5000 монет в азартных играх', 'reward': 1000},
    'case_hunter': {'name': 'Охотник за кейсами', 'description': 'Откройте 5 кейсов любого типа', 'reward': 500}
}

# Вспомогательные функции для работы с наградами
def get_reward(case):
    rand = random.random()
    cumulative = 0
    for reward in case['rewards']:
        cumulative += reward['chance']
        if rand <= cumulative:
            return reward
    return case['rewards'][-1]

async def create_custom_role_webhook(user):
    try:
        # Получаем канал для логов
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            # Создаем вебхук
            webhook = await channel.create_webhook(name=f"Role-{user.name}")
            
            # Создаем сообщение с пингом
            message = f"🎉 <@{user.id}> Поздравляю, вам выпала кастом роль на 2 дня, администратор <@{ADMIN_USER_ID}> скоро вам ответит и вы выберете свою роль"
            
            # Отправляем сообщение через вебхук
            await webhook.send(
                content=message,
                username="Case System",
                avatar_url=bot.user.avatar.url if bot.user.avatar else None
            )
            
            # Удаляем вебхук после использования
            await webhook.delete()
            
            return True
    except Exception as e:
        print(f"Ошибка создания вебхука для роли: {e}")
    return False

async def process_reward(user, reward, case):
    if reward['type'] == 'coins':
        amount = random.randint(reward['amount'][0], reward['amount'][1])
        db.update_balance(user.id, amount)
        db.log_transaction(user.id, 'case_reward', amount, description=f"Награда из {case['name']}")
        return f"Монеты: {amount} {EMOJIS['coin']}"
    
    elif reward['type'] == 'custom_role':
        await create_custom_role_webhook(user)
        return "🎭 Кастомная роль! (Создан запрос в канале администрации)"
    
    elif reward['type'] == 'special_item':
        db.add_item_to_inventory(user.id, reward['name'])
        return f"📦 Особый предмет: {reward['name']}"
    
    elif reward['type'] == 'bonus':
        return f"🚀 Бонус x{reward['multiplier']} на {reward['duration']}ч"
    
    elif reward['type'] == 'multiple':
        rewards = []
        for _ in range(reward['count']):
            sub_reward = get_reward(case)
            rewards.append(await process_reward(user, sub_reward, case))
        return " + ".join(rewards)
    
    elif reward['type'] == 'role':
        return f"👑 Роль: {reward['name']} на {reward['duration']}ч"
    
    return "Неизвестная награда"

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
        case_data = db.get_case(self.case_id)
        if not case_data:
            await interaction.response.send_message("Кейс не найден!", ephemeral=True)
            return
        
        case = {
            'name': case_data[1],
            'price': case_data[2],
            'rewards': json.loads(case_data[3])
        }
        
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
        reward = get_reward(case)
        db.update_balance(self.user_id, -case['price'])
        db.log_transaction(self.user_id, 'case_purchase', -case['price'], description=f"Кейс: {case['name']}")
        
        # Выдача награды
        reward_text = await process_reward(interaction.user, reward, case)
        
        embed = discord.Embed(
            title=f"🎉 {case['name']} открыт!",
            description=reward_text,
            color=0x00ff00
        )
        embed.set_footer(text=f"Стоимость: {case['price']} {EMOJIS['coin']}")
        
        await interaction.edit_original_response(embed=embed)

# ОБНОВЛЕННЫЙ КЛАСС ДУЭЛИ С 50/50 ШАНСОМ
class DuelView(View):
    def __init__(self, challenger_id, target_id, bet):
        super().__init__(timeout=30)
        self.challenger_id = challenger_id
        self.target_id = target_id
        self.bet = bet
        self.accepted = False
    
    @discord.ui.button(label='Принять дуэль', style=discord.ButtonStyle.success, emoji='⚔️')
    async def accept_duel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("Эта дуэль не для вас!", ephemeral=True)
            return
        
        if self.accepted:
            await interaction.response.send_message("Дуэль уже принята!", ephemeral=True)
            return
        
        # Проверяем баланс
        target_data = db.get_user(self.target_id)
        if target_data[1] < self.bet:
            await interaction.response.send_message("У вас недостаточно монет для принятия дуэли!", ephemeral=True)
            return
        
        self.accepted = True
        
        # Снимаем ставки
        db.update_balance(self.challenger_id, -self.bet)
        db.update_balance(self.target_id, -self.bet)
        
        # Анимация дуэли
        embed = discord.Embed(
            title=f"{EMOJIS['duel']} Дуэль начинается!",
            description="⚔️ Противники готовятся к бою...",
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Анимация обратного отсчета
        for i in range(3, 0, -1):
            await asyncio.sleep(1)
            embed.description = f"⚔️ Дуэль начнется через {i}..."
            await interaction.edit_original_response(embed=embed)
        
        await asyncio.sleep(1)
        
        # Определяем победителя - настоящий 50/50 шанс
        winner_id = random.choice([self.challenger_id, self.target_id])
        loser_id = self.target_id if winner_id == self.challenger_id else self.challenger_id
        
        # Выдаем выигрыш
        db.update_balance(winner_id, self.bet * 2)
        
        # Логируем
        db.log_transaction(winner_id, 'duel_win', self.bet * 2, loser_id, "Победа в дуэли")
        db.log_transaction(loser_id, 'duel_loss', -self.bet, winner_id, "Проигрыш в дуэли")
        
        winner = bot.get_user(winner_id)
        loser = bot.get_user(loser_id)
        
        embed = discord.Embed(
            title=f"{EMOJIS['duel']} Результат дуэли",
            description=f"**Победитель:** {winner.mention}\n**Проигравший:** {loser.mention}",
            color=0x00ff00
        )
        embed.add_field(name="Выигрыш", value=f"{self.bet * 2} {EMOJIS['coin']}")
        embed.add_field(name="Шанс победы", value="50/50")
        
        await interaction.edit_original_response(embed=embed)

# Улучшенная функция проверки прав администратора
def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        # Проверяем ID пользователя
        is_admin = interaction.user.id in ADMIN_IDS
        
        # Если пользователь не админ, отправляем сообщение
        if not is_admin:
            await interaction.response.send_message(
                "❌ У вас нет прав для использования этой команды!",
                ephemeral=True
            )
        return is_admin
    return app_commands.check(predicate)

# Обработчик ошибок для команд
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        # Эта ошибка уже обработана в проверке is_admin
        return
    elif isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message("❌ Команда не найдена!", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Недостаточно прав!", ephemeral=True)
    else:
        print(f"Произошла ошибка: {error}")
        try:
            await interaction.response.send_message(
                "❌ Произошла неизвестная ошибка при выполнении команды!",
                ephemeral=True
            )
        except:
            # Если уже был ответ, используем followup
            await interaction.followup.send(
                "❌ Произошла неизвестная ошибка при выполнении команды!",
                ephemeral=True
            )

# Команды бота

# Экономические команды
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
    
    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)
    elif user.default_avatar:
        embed.set_thumbnail(url=user.default_avatar.url)
    
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

# Команды кейсов
@bot.tree.command(name="cases", description="Показать список доступных кейсов")
async def cases_list(interaction: discord.Interaction):
    cases = db.get_cases()
    
    embed = discord.Embed(title="🎁 Доступные кейсы", color=0xff69b4)
    
    for case in cases:
        rewards = json.loads(case[3])
        rewards_desc = "\n".join([f"• {r['type']} ({r['chance']*100:.1f}%)" for r in rewards])
        embed.add_field(
            name=f"{case[1]} - {case[2]} {EMOJIS['coin']} (ID: {case[0]})",
            value=rewards_desc,
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="opencase", description="Открыть кейс")
@app_commands.describe(case_id="ID кейса для открытия")
async def open_case(interaction: discord.Interaction, case_id: int):
    case_data = db.get_case(case_id)
    if not case_data:
        await interaction.response.send_message("Кейс не найден! Используйте /cases для списка.", ephemeral=True)
        return
    
    view = CaseView(case_id, interaction.user.id)
    
    embed = discord.Embed(
        title=f"🎁 {case_data[1]}",
        description=f"Стоимость: {case_data[2]} {EMOJIS['coin']}",
        color=0xff69b4
    )
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="giftcase", description="Подарить кейс другому пользователю")
@app_commands.describe(user="Пользователь, которому дарим кейс", case_id="ID кейса")
async def giftcase(interaction: discord.Interaction, user: discord.Member, case_id: int):
    if user.id == interaction.user.id:
        await interaction.response.send_message("Нельзя дарить кейс самому себе!", ephemeral=True)
        return
    
    case_data = db.get_case(case_id)
    if not case_data:
        await interaction.response.send_message("Кейс не найден!", ephemeral=True)
        return
    
    user_data = db.get_user(interaction.user.id)
    
    if user_data[1] < case_data[2]:
        await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
        return
    
    # Убедимся, что получатель существует в базе
    db.get_user(user.id)
    
    # Списание средств и добавление кейса в инвентарь получателя
    db.update_balance(interaction.user.id, -case_data[2])
    db.add_case_to_inventory(user.id, case_id, case_data[1], "gifted")
    db.log_transaction(interaction.user.id, 'gift_case', -case_data[2], user.id, f"Подарок: {case_data[1]}")
    
    embed = discord.Embed(
        title="🎁 Кейс в подарок!",
        description=f"{interaction.user.mention} подарил {case_data[1]} пользователю {user.mention}!",
        color=0xff69b4
    )
    embed.add_field(name="💼 Получатель", value=f"Кейс добавлен в инвентарь {user.mention}")
    embed.add_field(name="📦 Кейс", value=f"{case_data[1]}")
    embed.add_field(name="💰 Стоимость", value=f"{case_data[2]} {EMOJIS['coin']}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="inventory", description="Показать ваш инвентарь")
async def inventory(interaction: discord.Interaction):
    # Убедимся, что пользователь существует
    db.get_user(interaction.user.id)
    
    inventory_data = db.get_user_inventory(interaction.user.id)
    
    embed = discord.Embed(
        title=f"🎒 Инвентарь {interaction.user.display_name}",
        color=0x3498db
    )
    
    # Показываем кейсы
    cases = inventory_data.get("cases", {})
    if cases:
        cases_text = ""
        for case_key, case_info in cases.items():
            case_id = case_key.replace("case_", "")
            cases_text += f"• {case_info['name']} (ID: {case_id}) ×{case_info['count']}\n"
        embed.add_field(name="🎁 Кейсы", value=cases_text, inline=False)
    else:
        embed.add_field(name="🎁 Кейсы", value="Пусто", inline=False)
    
    # Показываем предметы
    items = inventory_data.get("items", {})
    if items:
        items_text = ""
        for item_name, count in items.items():
            items_text += f"• {item_name} ×{count}\n"
        embed.add_field(name="📦 Предметы", value=items_text, inline=False)
    else:
        embed.add_field(name="📦 Предметы", value="Пусто", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="openmycase", description="Открыть кейс из вашего инвентаря")
@app_commands.describe(case_id="ID кейса из инвентаря")
async def openmycase(interaction: discord.Interaction, case_id: int):
    # Убедимся, что пользователь существует
    db.get_user(interaction.user.id)
    
    # Проверяем, есть ли кейс в инвентаре
    inventory_data = db.get_user_inventory(interaction.user.id)
    case_key = f"case_{case_id}"
    
    if case_key not in inventory_data.get("cases", {}):
        await interaction.response.send_message("У вас нет такого кейса в инвентаре!", ephemeral=True)
        return
    
    case_data = db.get_case(case_id)
    if not case_data:
        await interaction.response.send_message("Кейс не найден в базе данных!", ephemeral=True)
        return
    
    # Убираем кейс из инвентаря
    db.remove_case_from_inventory(interaction.user.id, case_id)
    
    # Открываем кейс
    case = {
        'name': case_data[1],
        'price': case_data[2],
        'rewards': json.loads(case_data[3])
    }
    
    # Спин анимация
    embed = discord.Embed(title="🎰 Открытие кейса...", color=0xffd700)
    await interaction.response.send_message(embed=embed)
    
    for i in range(3):
        await asyncio.sleep(1)
        embed.description = "🎁" * (i + 1)
        await interaction.edit_original_response(embed=embed)
    
    # Определение награды
    reward = get_reward(case)
    reward_text = await process_reward(interaction.user, reward, case)
    
    embed = discord.Embed(
        title=f"🎉 {case['name']} открыт!",
        description=reward_text,
        color=0x00ff00
    )
    embed.set_footer(text="Кейс из инвентаря")
    
    await interaction.edit_original_response(embed=embed)

# Команды маркетплейса
@bot.tree.command(name="market", description="Взаимодействие с маркетплейсом")
@app_commands.describe(action="Действие на маркетплейсе")
@app_commands.choices(action=[
    app_commands.Choice(name="📋 Список товаров", value="list"),
    app_commands.Choice(name="💰 Продать предмет", value="sell"),
    app_commands.Choice(name="🛒 Купить предмет", value="buy")
])
async def market(interaction: discord.Interaction, action: app_commands.Choice[str], item_name: str = None, price: int = None):
    if action.value == "list":
        cursor = db.conn.cursor()
        cursor.execute('SELECT * FROM market LIMIT 10')
        items = cursor.fetchall()
        
        embed = discord.Embed(title="🏪 Маркетплейс", color=0x00ff00)
        
        for item in items:
            seller = bot.get_user(item[1])
            embed.add_field(
                name=f"#{item[0]} {item[2]}",
                value=f"Цена: {item[3]} {EMOJIS['coin']}\nПродавец: {seller.name if seller else 'Неизвестно'}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    elif action.value == "sell":
        if not item_name or not price:
            await interaction.response.send_message("Укажите название предмета и цену!", ephemeral=True)
            return
        
        cursor = db.conn.cursor()
        cursor.execute('INSERT INTO market (seller_id, item_name, price) VALUES (?, ?, ?)', 
                      (interaction.user.id, item_name, price))
        db.conn.commit()
        
        embed = discord.Embed(
            title="🏪 Предмет выставлен на продажу",
            description=f"Предмет: {item_name}\nЦена: {price} {EMOJIS['coin']}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    
    elif action.value == "buy":
        if not item_name:
            await interaction.response.send_message("Укажите ID предмета для покупки!", ephemeral=True)
            return
        
        cursor = db.conn.cursor()
        cursor.execute('SELECT * FROM market WHERE id = ?', (int(item_name),))
        item = cursor.fetchone()
        
        if not item:
            await interaction.response.send_message("Предмет не найден!", ephemeral=True)
            return
        
        user_data = db.get_user(interaction.user.id)
        if user_data[1] < item[3]:
            await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
            return
        
        # Покупка предмета
        db.update_balance(interaction.user.id, -item[3])
        db.update_balance(item[1], item[3])
        cursor.execute('DELETE FROM market WHERE id = ?', (int(item_name),))
        db.conn.commit()
        
        db.log_transaction(interaction.user.id, 'market_buy', -item[3], item[1], f"Покупка: {item[2]}")
        db.log_transaction(item[1], 'market_sell', item[3], interaction.user.id, f"Продажа: {item[2]}")
        
        embed = discord.Embed(
            title="🏪 Покупка совершена!",
            description=f"Вы купили {item[2]} за {item[3]} {EMOJIS['coin']}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)

# Мини-игры
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

@bot.tree.command(name="dice", description="Бросить кости на ставку")
@app_commands.describe(bet="Ставка в монетах")
async def dice(interaction: discord.Interaction, bet: int):
    user_data = db.get_user(interaction.user.id)
    
    if user_data[1] < bet:
        await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
        return
    
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    
    if user_roll > bot_roll:
        winnings = bet * 2
        db.update_balance(interaction.user.id, winnings)
        result = f"ПОБЕДА!\nВаш бросок: {user_roll}\nБросок бота: {bot_roll}\nВыигрыш: {winnings} {EMOJIS['coin']}"
        color = 0x00ff00
    elif user_roll < bot_roll:
        db.update_balance(interaction.user.id, -bet)
        result = f"ПРОИГРЫШ!\nВаш бросок: {user_roll}\nБросок бота: {bot_roll}"
        color = 0xff0000
    else:
        result = f"НИЧЬЯ!\nОба выбросили: {user_roll}"
        color = 0xffff00
    
    embed = discord.Embed(
        title=f"{EMOJIS['dice']} Игра в кости - Ставка: {bet} {EMOJIS['coin']}",
        description=result,
        color=color
    )
    await interaction.response.send_message(embed=embed)

# ОБНОВЛЕННАЯ КОМАНДА ДУЭЛИ С 50/50 ШАНСОМ
@bot.tree.command(name="duel", description="Вызвать пользователя на дуэль")
@app_commands.describe(user="Пользователь для дуэли", bet="Ставка в монетах")
async def duel(interaction: discord.Interaction, user: discord.Member, bet: int):
    if user.id == interaction.user.id:
        await interaction.response.send_message("Нельзя вызвать на дуэль самого себя!", ephemeral=True)
        return
    
    if bet <= 0:
        await interaction.response.send_message("Ставка должна быть положительной!", ephemeral=True)
        return
    
    user_data = db.get_user(interaction.user.id)
    if user_data[1] < bet:
        await interaction.response.send_message("У вас недостаточно монет для дуэли!", ephemeral=True)
        return
    
    target_data = db.get_user(user.id)
    if target_data[1] < bet:
        await interaction.response.send_message(f"У {user.mention} недостаточно монет для дуэли!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"{EMOJIS['duel']} Вызов на дуэль!",
        description=f"{interaction.user.mention} вызывает {user.mention} на дуэль!",
        color=0xff0000
    )
    embed.add_field(name="Ставка", value=f"{bet} {EMOJIS['coin']}", inline=True)
    embed.add_field(name="Шанс победы", value="50/50", inline=True)
    embed.add_field(name="Время на ответ", value="30 секунд", inline=True)
    embed.set_footer(text="Победитель забирает всю ставку!")
    
    view = DuelView(interaction.user.id, user.id, bet)
    await interaction.response.send_message(embed=embed, view=view)

# Измененная команда /steal с рандомной суммой
@bot.tree.command(name="steal", description="Попытаться украсть монеты у другого пользователя (КД 30 мин)")
@app_commands.describe(user="Пользователь, у которого крадем")
@app_commands.checks.cooldown(1, 1800.0, key=lambda i: (i.guild_id, i.user.id))  # 30 минут кд
async def steal(interaction: discord.Interaction, user: discord.Member):
    if user.id == interaction.user.id:
        await interaction.response.send_message("Нельзя красть у себя!", ephemeral=True)
        return
    
    thief_data = db.get_user(interaction.user.id)
    target_data = db.get_user(user.id)
    
    if thief_data[1] < 10:
        await interaction.response.send_message("Нужно минимум 10 монет для кражи!", ephemeral=True)
        return
    
    if target_data[1] < 10:
        await interaction.response.send_message("У цели недостаточно монет для кражи!", ephemeral=True)
        return
    
    # Вычисляем случайную сумму для кражи (от 5% до 20% от баланса цели, но не более 1000)
    max_steal = min(int(target_data[1] * 0.2), 1000)
    min_steal = max(int(target_data[1] * 0.05), 10)
    
    if max_steal < min_steal:
        amount = min_steal
    else:
        amount = random.randint(min_steal, max_steal)
    
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

# Обработчик кд для /steal
@steal.error
async def steal_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        # Преобразуем время в читаемый формат
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        
        await interaction.response.send_message(
            f"❌ Следующую кражу можно совершить через {minutes} минут {seconds:02d} секунд",
            ephemeral=True
        )
    else:
        raise error

# Команда /quest с кд 3 часа
@bot.tree.command(name="quest", description="Получить случайный квест")
@app_commands.checks.cooldown(1, 10800.0)  # 3 часа в секундах
async def quest(interaction: discord.Interaction):
    quest_id, quest_data = random.choice(list(QUESTS.items()))
    
    embed = discord.Embed(
        title=f"{EMOJIS['quest']} Новый квест!",
        description=quest_data['description'],
        color=0x00ff00
    )
    embed.add_field(name="Награда", value=f"{quest_data['reward']} {EMOJIS['coin']}")
    
    await interaction.response.send_message(embed=embed)

# Обработчик кд для /quest
@quest.error
async def quest_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        # Преобразуем время в читаемый формат
        hours = int(error.retry_after // 3600)
        minutes = int((error.retry_after % 3600) // 60)
        seconds = int(error.retry_after % 60)
        
        await interaction.response.send_message(
            f"❌ Следующий квест можно будет получить через {hours:02d}:{minutes:02d}:{seconds:02d}",
            ephemeral=True
        )
    else:
        raise error

# Достижения и лидерборды
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
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, balance) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{balance} {EMOJIS['coin']}",
                inline=False
            )
    
    elif type.value == 'wins':
        cursor.execute('''
            SELECT user_id, COUNT(*) as wins FROM transactions 
            WHERE type IN ('roulette_win', 'dice_win', 'duel_win') 
            GROUP BY user_id ORDER BY wins DESC LIMIT 10
        ''')
        title = "🏆 Лидеры по победам"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, wins) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{wins} побед",
                inline=False
            )
    
    elif type.value == 'steals':
        cursor.execute('''
            SELECT user_id, COUNT(*) as steals FROM transactions 
            WHERE type = 'steal' 
            GROUP BY user_id ORDER BY steals DESC LIMIT 10
        ''')
        title = "🏆 Лидеры по кражам"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, steals) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{steals} краж",
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="achievements", description="Показать ваши достижения")
async def achievements(interaction: discord.Interaction):
    cursor = db.conn.cursor()
    cursor.execute('SELECT achievement_id FROM achievements WHERE user_id = ?', (interaction.user.id,))
    user_achievements = [row[0] for row in cursor.fetchall()]
    
    embed = discord.Embed(title="🏅 Ваши достижения", color=0xffd700)
    
    for achievement_id, achievement in ACHIEVEMENTS.items():
        status = "✅" if achievement_id in user_achievements else "❌"
        embed.add_field(
            name=f"{status} {achievement['name']}",
            value=achievement['description'],
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# Админ-команды
@bot.tree.command(name="admin_addcoins", description="Добавить монеты пользователю (админ)")
@app_commands.describe(user="Пользователь", amount="Количество монет")
@is_admin()
async def admin_addcoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    try:
        db.update_balance(user.id, amount)
        db.log_transaction(interaction.user.id, 'admin_add', amount, user.id, f"Админ {interaction.user.name}")
        
        embed = discord.Embed(
            title="⚙️ Админ действие",
            description=f"Выдано {amount} {EMOJIS['coin']} пользователю {user.mention}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_removecoins", description="Забрать монеты у пользователя (админ)")
@app_commands.describe(user="Пользователь", amount="Количество монет")
@is_admin()
async def admin_removecoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    try:
        db.update_balance(user.id, -amount)
        db.log_transaction(interaction.user.id, 'admin_remove', -amount, user.id, f"Админ {interaction.user.name}")
        
        embed = discord.Embed(
            title="⚙️ Админ действие",
            description=f"Забрано {amount} {EMOJIS['coin']} у пользователя {user.mention}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_giveitem", description="Выдать предмет пользователю (админ)")
@app_commands.describe(user="Пользователь", item_name="Название предмета")
@is_admin()
async def admin_giveitem(interaction: discord.Interaction, user: discord.Member, item_name: str):
    try:
        db.add_item_to_inventory(user.id, item_name)
        
        embed = discord.Embed(
            title="⚙️ Админ действие",
            description=f"Предмет '{item_name}' выдан пользователю {user.mention}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_removeitem", description="Забрать предмет у пользователя (админ)")
@app_commands.describe(user="Пользователь", item_name="Название предмета")
@is_admin()
async def admin_removeitem(interaction: discord.Interaction, user: discord.Member, item_name: str):
    try:
        success = db.remove_item_from_inventory(user.id, item_name)
        
        if success:
            embed = discord.Embed(
                title="⚙️ Админ действие",
                description=f"Предмет '{item_name}' забран у пользователя {user.mention}",
                color=0xff0000
            )
        else:
            embed = discord.Embed(
                title="⚙️ Админ действие",
                description=f"У пользователя {user.mention} нет предмета '{item_name}'",
                color=0xff0000
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_createcase", description="Создать новый кейс (админ)")
@app_commands.describe(name="Название кейса", price="Цена кейса", rewards_json="Награды в формате JSON")
@is_admin()
async def admin_createcase(interaction: discord.Interaction, name: str, price: int, rewards_json: str):
    try:
        rewards = json.loads(rewards_json)
        case_id = db.create_case(name, price, rewards)
        
        embed = discord.Embed(
            title="⚙️ Админ действие",
            description=f"Создан новый кейс: {name}\nЦена: {price} {EMOJIS['coin']}\nID: {case_id}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except json.JSONDecodeError:
        await interaction.response.send_message("❌ Неверный формат JSON для наград", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_editcase", description="Редактировать кейс (админ)")
@app_commands.describe(case_id="ID кейса", name="Новое название", price="Новая цена", rewards_json="Новые награды в формате JSON")
@is_admin()
async def admin_editcase(interaction: discord.Interaction, case_id: int, name: str = None, price: int = None, rewards_json: str = None):
    try:
        case_data = db.get_case(case_id)
        if not case_data:
            await interaction.response.send_message("❌ Кейс не найден!", ephemeral=True)
            return
        
        current_name = case_data[1]
        current_price = case_data[2]
        current_rewards = case_data[3]
        
        new_name = name if name else current_name
        new_price = price if price else current_price
        
        new_rewards = json.loads(rewards_json) if rewards_json else json.loads(current_rewards)
        db.update_case(case_id, new_name, new_price, new_rewards)
        
        embed = discord.Embed(
            title="⚙️ Админ действие",
            description=f"Кейс ID {case_id} обновлен:\nНазвание: {new_name}\nЦена: {new_price} {EMOJIS['coin']}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except json.JSONDecodeError:
        await interaction.response.send_message("❌ Неверный формат JSON для наград", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_deletecase", description="Удалить кейс (админ)")
@app_commands.describe(case_id="ID кейса")
@is_admin()
async def admin_deletecase(interaction: discord.Interaction, case_id: int):
    try:
        case_data = db.get_case(case_id)
        if not case_data:
            await interaction.response.send_message("❌ Кейс не найден!", ephemeral=True)
            return
        
        db.delete_case(case_id)
        
        embed = discord.Embed(
            title="⚙️ Админ действие",
            description=f"Кейс '{case_data[1]}' (ID: {case_id}) удален",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_viewtransactions", description="Просмотр транзакций (админ)")
@app_commands.describe(user="Пользователь (опционально)")
@is_admin()
async def admin_viewtransactions(interaction: discord.Interaction, user: discord.Member = None):
    try:
        cursor = db.conn.cursor()
        
        if user:
            cursor.execute('SELECT * FROM transactions WHERE user_id = ? OR target_user_id = ? ORDER BY timestamp DESC LIMIT 10', (user.id, user.id))
            title = f"📊 Транзакции пользователя {user.name}"
        else:
            cursor.execute('SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 10')
            title = "📊 Последние транзакции"
        
        transactions = cursor.fetchall()
        
        embed = discord.Embed(title=title, color=0x3498db)
        
        for trans in transactions:
            trans_user = bot.get_user(trans[1])
            target_user = bot.get_user(trans[4]) if trans[4] else None
            
            embed.add_field(
                name=f"#{trans[0]} {trans[2]}",
                value=f"Сумма: {trans[3]} {EMOJIS['coin']}\nОт: {trans_user.name if trans_user else 'Система'}\nКому: {target_user.name if target_user else 'Нет'}\nОписание: {trans[5]}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_broadcast", description="Отправить объявление всем (админ)")
@app_commands.describe(message="Текст объявления")
@is_admin()
async def admin_broadcast(interaction: discord.Interaction, message: str):
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

# Команда помощи
@bot.tree.command(name="help", description="Показать информацию о боте и список команд")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Экономический Бот - Помощь",
        description="Добро пожаловать в экономическую игру! Этот бот предоставляет полную систему экономики с кейсами, мини-играми, маркетплейсом и достижениями.",
        color=0x3498db
    )
    
    # Основная информация о боте
    embed.add_field(
        name="📊 О боте",
        value="• Внутренняя валюта: монеты 🪙\n• Ежедневные бонусы 📅\n• Система кейсов 🎁\n• Маркетплейс 🏪\n• Мини-игры 🎰\n• Достижения 🏅",
        inline=False
    )
    
    # Экономические команды
    embed.add_field(
        name="💰 Экономические команды",
        value="""**/balance** [пользователь] - Показать баланс
**/daily** - Получить ежедневную награду
**/pay** @пользователь сумма - Перевести монеты
**/inventory** - Показать инвентарь""",
        inline=False
    )
    
    # Команды кейсов
    embed.add_field(
        name="🎁 Команды кейсов",
        value="""**/cases** - Список доступных кейсов
**/opencase** ID_кейса - Купить и открыть кейс
**/openmycase** ID_кейса - Открыть кейс из инвентаря
**/giftcase** @пользователь ID_кейса - Подарить кейс""",
        inline=False
    )
    
    # Маркетплейс
    embed.add_field(
        name="🏪 Маркетплейс",
        value="""**/market** list - Список товаров
**/market** sell название_предмета цена - Продать предмет
**/market** buy ID_товара - Купить товар""",
        inline=False
    )
    
    # Мини-игры
    embed.add_field(
        name="🎮 Мини-игры",
        value="""**/roulette** ставка - Игра в рулетку
**/dice** ставка - Игра в кости
**/duel** @пользователь ставка - Дуэль с игроком (50/50 шанс)
**/quest** - Получить случайный квест (КД 3 часа)
**/steal** @пользователь - Попытаться украсть монеты (случайная сумма, КД 30 мин)""",
        inline=False
    )
    
    # Достижения и лидерборды
    embed.add_field(
        name="🏅 Достижения и лидерборды",
        value="""**/leaderboard** balance - Лидеры по балансу
**/leaderboard** wins - Лидеры по победам
**/leaderboard** steals - Лидеры по кражам
**/achievements** - Ваши достижения""",
        inline=False
    )
    
    # Админ-команды (только для админов)
    if interaction.user.id in ADMIN_IDS:
        embed.add_field(
            name="⚙️ Админ-команды",
            value="""**/admin_addcoins** @пользователь сумма - Добавить монеты
**/admin_removecoins** @пользователь сумма - Забрать монеты
**/admin_giveitem** @пользователь предмет - Выдать предмет
**/admin_removeitem** @пользователь предмет - Забрать предмет
**/admin_createcase** название цена JSON_наград - Создать кейс
**/admin_editcase** ID_кейса [название] [цена] [JSON_наград] - Редактировать кейс
**/admin_deletecase** ID_кейса - Удалить кейс
**/admin_viewtransactions** [@пользователь] - Просмотр транзакций
**/admin_broadcast** сообщение - Отправить объявление""",
            inline=False
        )
    
    # Полезные советы
    embed.add_field(
        name="💡 Советы",
        value="""• Используйте **/daily** каждый день для увеличения серии
• Открывайте кейсы для получения редких предметов и ролей
• Торгуйте предметами на маркетплейсе
• Соревнуйтесь за место в лидербордах""",
        inline=False
    )
    
    embed.set_footer(text="Для подробной информации о команде используйте /команда")
    
    await interaction.response.send_message(embed=embed)

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
    
    await bot.change_presence(activity=discord.Game(name="Экономическую игру | /help"))

if __name__ == "__main__":
    bot.run(BOT_TOKEN)





