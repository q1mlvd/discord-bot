import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import json
import random
import datetime
import traceback
import asyncio

# Импорт PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("✅ psycopg2 импортирован успешно")
except ImportError:
    print("❌ psycopg2 не установлен, устанавливаем...")
    import subprocess
    subprocess.check_call(["pip", "install", "psycopg2-binary"])
    import psycopg2
    from psycopg2.extras import RealDictCursor

# ========== КОНФИГУРАЦИЯ ==========
def get_database_url():
    """Получаем DATABASE_URL разными способами"""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print("✅ DATABASE_URL найден в переменных окружения")
        return database_url
    
    alternative_names = ['POSTGRES_URL', 'POSTGRESQL_URL', 'RAILWAY_DATABASE_URL']
    for name in alternative_names:
        database_url = os.environ.get(name)
        if database_url:
            print(f"✅ DATABASE_URL найден как {name}")
            return database_url
    
    db_user = os.environ.get('PGUSER')
    db_password = os.environ.get('PGPASSWORD')
    db_host = os.environ.get('PGHOST')
    db_port = os.environ.get('PGPORT')
    db_name = os.environ.get('PGDATABASE')
    
    if all([db_user, db_password, db_host, db_port, db_name]):
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print("✅ DATABASE_URL собран из отдельных переменных")
        return database_url
    
    print("❌ DATABASE_URL не найден ни в одной переменной окружения")
    return None

# Получаем переменные
DATABASE_URL = get_database_url()
BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

# Проверка токена
if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: Неверный токен бота!")
    exit(1)

if not DATABASE_URL:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: DATABASE_URL не установлен!")
    exit(1)

# Настройки бота
LOG_CHANNEL_ID = 1423377881047896207
ADMIN_IDS = [766767256742526996, 1195144951546265675, 691904643181314078, 1078693283695448064, 1138140772097597472]
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
    'admin': '⚙️',
    'slot': '🎰',
    'coinflip': '🪙',
    'blackjack': '🃏'
}

# Система бафов от предметов
ITEM_BUFFS = {
    'Золотой амулет': {'type': 'daily_bonus', 'value': 1.2, 'description': '+20% к ежедневной награде'},
    'Серебряный амулет': {'type': 'daily_bonus', 'value': 1.1, 'description': '+10% к ежедневной награде'},
    'Кольцо удачи': {'type': 'case_bonus', 'value': 1.15, 'description': '+15% к наградам из кейсов'},
    'Браслет везения': {'type': 'game_bonus', 'value': 1.1, 'description': '+10% к выигрышам в играх'},
    'Защитный талисман': {'type': 'steal_protection', 'value': 0.5, 'description': '-50% к шансу кражи у вас'},
    'Перчатка вора': {'type': 'steal_bonus', 'value': 1.2, 'description': '+20% к шансу успешной кражи'},
    'Магический свиток': {'type': 'roulette_bonus', 'value': 1.25, 'description': '+25% к выигрышу в рулетке'},
    'Кристалл маны': {'type': 'multiplier', 'value': 1.3, 'description': 'x1.3 к любым наградам'},
    'Древний артефакт': {'type': 'multiplier', 'value': 1.5, 'description': 'x1.5 к любым наградам'},
    'Мифический предмет': {'type': 'multiplier', 'value': 2.0, 'description': 'x2.0 к любым наградам'},
    'Счастливая монета': {'type': 'coinflip_bonus', 'value': 1.2, 'description': '+20% к выигрышу в coinflip'},
    'Карточный шулер': {'type': 'blackjack_bonus', 'value': 1.15, 'description': '+15% к выигрышу в блэкджеке'},
    'Слот-мастер': {'type': 'slot_bonus', 'value': 1.25, 'description': '+25% к выигрышу в слотах'},
    'Щит богатства': {'type': 'loss_protection', 'value': 0.8, 'description': '-20% к проигрышам'},
    'Флакон зелья': {'type': 'quest_bonus', 'value': 1.2, 'description': '+20% к наградам за квесты'},
    'Зелье удачи': {'type': 'all_bonus', 'value': 1.1, 'description': '+10% ко всем наградам'},
    'Руна богатства': {'type': 'transfer_bonus', 'value': 0.9, 'description': '-10% к комиссии переводов'},
    'Тотем защиты': {'type': 'duel_bonus', 'value': 1.2, 'description': '+20% к шансу победы в дуэлях'},
    'Ожерелье мудрости': {'type': 'xp_bonus', 'value': 1.15, 'description': '+15% к опыту'},
    'Плащ тени': {'type': 'steal_chance', 'value': 1.15, 'description': '+15% к шансу кражи'}
}

# Система достижений
ACHIEVEMENTS = {
    'first_daily': {'name': 'Первый шаг', 'description': 'Получите первую ежедневную награду', 'reward': 100},
    'rich': {'name': 'Богач', 'description': 'Накопите 10,000 монет', 'reward': 500},
    'millionaire': {'name': 'Миллионер', 'description': 'Накопите 100,000 монет', 'reward': 5000},
    'gambler': {'name': 'Азартный игрок', 'description': 'Выиграйте в рулетку 25 раз', 'reward': 1000},
    'thief': {'name': 'Вор', 'description': 'Успешно украдите монеты 20 раз', 'reward': 800},
    'case_opener': {'name': 'Коллекционер', 'description': 'Откройте 50 кейсов', 'reward': 1500},
    'case_master': {'name': 'Мастер кейсов', 'description': 'Откройте 200 кейсов', 'reward': 5000},
    'duel_master': {'name': 'Мастер дуэлей', 'description': 'Выиграйте 25 дуэлей', 'reward': 1200},
    'slot_king': {'name': 'Король слотов', 'description': 'Выиграйте джекпот в слотах', 'reward': 3000},
    'blackjack_pro': {'name': 'Профи в блэкджеке', 'description': 'Выиграйте 10 раз в блэкджек', 'reward': 2000},
    'coinflip_champ': {'name': 'Чемпион монетки', 'description': 'Выиграйте 30 раз в подбрасывание монеты', 'reward': 1500},
    'trader': {'name': 'Торговец', 'description': 'Продайте 15 предметов на маркетплейсе', 'reward': 800},
    'gifter': {'name': 'Щедрый', 'description': 'Подарите 10 кейсов', 'reward': 1000},
    'veteran': {'name': 'Ветеран', 'description': 'Получите ежедневную награду 30 дней подряд', 'reward': 3000},
    'lucky': {'name': 'Везунчик', 'description': 'Выиграйте 3 раза подряд в любую игру', 'reward': 2000},
    'item_collector': {'name': 'Коллекционер предметов', 'description': 'Соберите 10 разных предметов', 'reward': 1500},
    'buff_master': {'name': 'Мастер бафов', 'description': 'Активируйте 5 разных бафов одновременно', 'reward': 2000}
}

# Система квестов
QUESTS = {
    'daily_rich': {'name': 'Ежедневный богач', 'description': 'Получите 7 ежедневных наград подряд', 'reward': 1000},
    'gambling_king': {'name': 'Король азарта', 'description': 'Выиграйте 10,000 монет в азартных играх', 'reward': 2500},
    'case_hunter': {'name': 'Охотник за кейсами', 'description': 'Откройте 15 кейсов любого типа', 'reward': 1200},
    'market_expert': {'name': 'Эксперт рынка', 'description': 'Купите и продайте 5 предметов на маркетплейсе', 'reward': 800},
    'duel_champion': {'name': 'Чемпион дуэлей', 'description': 'Выиграйте 5 дуэлей подряд', 'reward': 1500},
    'item_collector_quest': {'name': 'Коллекционер', 'description': 'Соберите 5 разных магических предметов', 'reward': 2000}
}

# ========== КЛАСС БОТА ==========
class CustomBot(commands.Bot):
    async def setup_hook(self):
        # Задержка перед началом работы
        await asyncio.sleep(5)
        
        # Предварительная синхронизация
        try:
            print("🔄 Начинаем предварительную синхронизацию команд...")
            synced = await self.tree.sync()
            print(f"✅ Предварительно синхронизировано {len(synced)} команд")
        except Exception as e:
            print(f"❌ Ошибка предварительной синхронизации: {e}")
        
    async def on_ready(self):
        print(f'✅ Бот {self.user.name} успешно запущен!')
        print(f'🔗 ID бота: {self.user.id}')
        print(f'👥 Бот находится на {len(self.guilds)} серверах')

        # Финальная синхронизация команд
        try:
            await asyncio.sleep(2)
            synced = await self.tree.sync()
            print(f"✅ Финально синхронизировано {len(synced)} команд")
            
            # Отладочная информация
            if synced:
                print("📋 Список синхронизированных команд:")
                for cmd in synced:
                    print(f"   - {cmd.name}: {cmd.description}")
            else:
                print("⚠️  Внимание: синхронизировано 0 команд")
                
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")
            traceback.print_exc()

# Создаем экземпляр бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = CustomBot(command_prefix='!', intents=intents, help_command=None)

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Подключение к базе данных с повторными попытками"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.conn = psycopg2.connect(DATABASE_URL, sslmode='require')
                print("✅ Успешное подключение к PostgreSQL!")
                return
            except Exception as e:
                print(f"❌ Попытка {attempt + 1}/{max_retries} не удалась: {e}")
                if attempt < max_retries - 1:
                    print("🔄 Повторная попытка через 5 секунд...")
                    import time
                    time.sleep(5)
                else:
                    print("💥 Не удалось подключиться к базе данных после нескольких попыток")
                    raise

    def create_tables(self):
        """Создание таблиц с улучшенной обработкой ошибок"""
        try:
            cursor = self.conn.cursor()
            
            print("🔄 Создание таблиц...")
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    balance INTEGER DEFAULT 100,
                    daily_streak INTEGER DEFAULT 0,
                    last_daily TEXT,
                    inventory TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица транзакций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    type TEXT,
                    amount INTEGER,
                    target_user_id BIGINT,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица кейсов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cases (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    price INTEGER,
                    rewards TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица маркета
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market (
                    id SERIAL PRIMARY KEY,
                    seller_id BIGINT,
                    item_name TEXT,
                    price INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица достижений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    user_id BIGINT,
                    achievement_id TEXT,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_id)
                )
            ''')
            
            # Таблица квестов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quests (
                    user_id BIGINT,
                    quest_id TEXT,
                    progress INTEGER DEFAULT 0,
                    completed BOOLEAN DEFAULT FALSE,
                    last_quest TEXT,
                    PRIMARY KEY (user_id, quest_id)
                )
            ''')
            
            # Таблица дуэлей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS duels (
                    id SERIAL PRIMARY KEY,
                    challenger_id BIGINT,
                    target_id BIGINT,
                    bet INTEGER,
                    status TEXT DEFAULT 'pending',
                    winner_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица предметов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    value INTEGER,
                    rarity TEXT,
                    buff_type TEXT,
                    buff_value REAL,
                    buff_description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица статистики пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id BIGINT PRIMARY KEY,
                    cases_opened INTEGER DEFAULT 0,
                    duels_won INTEGER DEFAULT 0,
                    steals_successful INTEGER DEFAULT 0,
                    steals_failed INTEGER DEFAULT 0,
                    roulette_wins INTEGER DEFAULT 0,
                    slot_wins INTEGER DEFAULT 0,
                    blackjack_wins INTEGER DEFAULT 0,
                    coinflip_wins INTEGER DEFAULT 0,
                    daily_claimed INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    market_sales INTEGER DEFAULT 0,
                    gifts_sent INTEGER DEFAULT 0,
                    consecutive_wins INTEGER DEFAULT 0,
                    items_collected INTEGER DEFAULT 0,
                    last_win_time TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            print("✅ Все таблицы успешно созданы!")
            
            # Инициализация начальных данных
            self.initialize_default_data()
            
        except Exception as e:
            print(f"❌ Ошибка при создании таблиц: {e}")
            self.conn.rollback()
            raise

    def initialize_default_data(self):
        """Инициализация начальных данных с улучшенными кейсами"""
        try:
            cursor = self.conn.cursor()
            
            # Проверяем текущее количество кейсов
            cursor.execute('SELECT COUNT(*) FROM cases')
            current_count = cursor.fetchone()[0]
            print(f"🔍 Текущее количество кейсов в базе: {current_count}")
            
            # Если кейсов нет, добавляем их
            if current_count == 0:
                print("🔄 Добавление улучшенных кейсов...")
                
                improved_cases = [
                    ('📦 Начинающий кейс', 25, json.dumps([
                        {'type': 'coins', 'amount': [10, 30], 'chance': 0.6, 'description': 'Небольшая сумма монет'},
                        {'type': 'coins', 'amount': [31, 80], 'chance': 0.3, 'description': 'Средняя сумма монет'},
                        {'type': 'coins', 'amount': [81, 150], 'chance': 0.1, 'description': 'Хорошая сумма монет'}
                    ])),
                    ('📦 Малый кейс', 50, json.dumps([
                        {'type': 'coins', 'amount': [20, 50], 'chance': 0.5, 'description': 'Небольшая сумма монет'},
                        {'type': 'coins', 'amount': [51, 120], 'chance': 0.3, 'description': 'Средняя сумма монет'},
                        {'type': 'coins', 'amount': [121, 250], 'chance': 0.15, 'description': 'Хорошая сумма монет'},
                        {'type': 'special_item', 'name': 'Серебряный амулет', 'chance': 0.05, 'description': 'Увеличивает ежедневную награду на 10%'}
                    ])),
                    ('💎 Большой кейс', 500, json.dumps([
                        {'type': 'coins', 'amount': [200, 400], 'chance': 0.6, 'description': 'Солидная сумма'},
                        {'type': 'coins', 'amount': [401, 1000], 'chance': 0.25, 'description': 'Очень хорошая сумма'},
                        {'type': 'special_item', 'name': 'Золотой амулет', 'chance': 0.08, 'description': 'Увеличивает ежедневную награду на 20%'},
                        {'type': 'bonus', 'multiplier': 1.5, 'duration': 24, 'chance': 0.07, 'description': 'Временный бонус x1.5 на 24 часа'}
                    ])),
                    ('👑 Элитный кейс', 1000, json.dumps([
                        {'type': 'coins', 'amount': [500, 1000], 'chance': 0.3, 'description': 'Элитные монеты'},
                        {'type': 'coins', 'amount': [-300, -100], 'chance': 0.2, 'description': 'Неудача (потеря монет)'},
                        {'type': 'special_item', 'name': 'Древний артефакт', 'chance': 0.15, 'description': 'Мощный множитель наград'},
                        {'type': 'bonus', 'multiplier': 2.0, 'duration': 48, 'chance': 0.1, 'description': 'Временный бонус x2.0 на 48 часов'},
                        {'type': 'coins', 'amount': [1001, 3000], 'chance': 0.15, 'description': 'Элитный выигрыш'},
                        {'type': 'coins', 'amount': [3001, 6000], 'chance': 0.1, 'description': 'Элитный джекпот'}
                    ]))
                ]
                
                for case in improved_cases:
                    cursor.execute('INSERT INTO cases (name, price, rewards) VALUES (%s, %s, %s)', case)
                
                print(f"✅ Добавлено {len(improved_cases)} улучшенных кейсов!")
            else:
                print(f"✅ В базе уже есть {current_count} кейсов, пропускаем инициализацию")
            
            # Проверяем и добавляем предметы если нужно
            cursor.execute('SELECT COUNT(*) FROM items')
            items_count = cursor.fetchone()[0]
            
            if items_count == 0:
                print("🔄 Добавление стандартных предметов...")
                
                default_items = [
                    ('Золотой амулет', 'Увеличивает ежедневную награду', 500, 'rare', 'daily_bonus', 1.2, '+20% к ежедневной награде'),
                    ('Серебряный амулет', 'Небольшой бонус к ежедневной награде', 250, 'common', 'daily_bonus', 1.1, '+10% к ежедневной награде'),
                    ('Кольцо удачи', 'Увеличивает награды из кейсов', 600, 'rare', 'case_bonus', 1.15, '+15% к наградам из кейсов'),
                    ('Браслет везения', 'Увеличивает выигрыши в играх', 450, 'uncommon', 'game_bonus', 1.1, '+10% к выигрышам в играх'),
                    ('Защитный талисман', 'Защищает от краж', 800, 'epic', 'steal_protection', 0.5, '-50% к шансу кражи у вас'),
                    ('Перчатка вора', 'Увеличивает шанс успешной кражи', 700, 'rare', 'steal_bonus', 1.2, '+20% к шансу успешной кражи'),
                ]
                
                for item in default_items:
                    cursor.execute('INSERT INTO items (name, description, value, rarity, buff_type, buff_value, buff_description) VALUES (%s, %s, %s, %s, %s, %s, %s)', item)
                
                print("✅ Стандартные предметы добавлены!")
            
            self.conn.commit()
            print("✅ Начальные данные успешно инициализированы!")
            
        except Exception as e:
            print(f"❌ Ошибка при инициализации данных: {e}")
            self.conn.rollback()

    def get_user(self, user_id):
        """Безопасное получение пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                # Создаем нового пользователя
                cursor.execute('''
                    INSERT INTO users (user_id, balance, inventory) 
                    VALUES (%s, %s, %s)
                ''', (user_id, 100, json.dumps({"cases": {}, "items": {}})))
                self.conn.commit()
                
                # Получаем созданного пользователя
                cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
                user = cursor.fetchone()
            
            return user
            
        except Exception as e:
            print(f"❌ Ошибка в get_user для {user_id}: {e}")
            return (user_id, 100, 0, None, json.dumps({"cases": {}, "items": {}}), datetime.datetime.now())

    def update_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s', (amount, user_id))
        self.conn.commit()
    
    def log_transaction(self, user_id, transaction_type, amount, target_user_id=None, description=""):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, target_user_id, description)
            VALUES (%s, %s, %s, %s, %s)
        ''', (user_id, transaction_type, amount, target_user_id, description))
        self.conn.commit()
    
    def get_cases(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM cases ORDER BY price ASC')
        return cursor.fetchall()
    
    def get_case(self, case_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM cases WHERE id = %s', (case_id,))
        return cursor.fetchone()
    
    def get_items(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM items')
        return cursor.fetchall()
    
    def get_item(self, item_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM items WHERE id = %s', (item_id,))
        return cursor.fetchone()
    
    def get_item_by_name(self, item_name):
        """Безопасное получение предмета по имени"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM items WHERE name = %s', (item_name,))
            item = cursor.fetchone()
            return item
        except Exception as e:
            print(f"❌ Ошибка в get_item_by_name для {item_name}: {e}")
            return None
    
    def add_item_to_inventory(self, user_id, item_name):
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT id FROM items WHERE name = %s', (item_name,))
        item_result = cursor.fetchone()
        
        if not item_result:
            return False
            
        item_id = item_result[0]
        
        cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            inventory_data = json.loads(result[0])
        else:
            inventory_data = {"cases": {}, "items": {}}
            
        if "items" not in inventory_data:
            inventory_data["items"] = {}
            
        item_key = str(item_id)
        if item_key in inventory_data["items"]:
            inventory_data["items"][item_key] += 1
        else:
            inventory_data["items"][item_key] = 1
        
        cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', 
                      (json.dumps(inventory_data), user_id))
        self.conn.commit()
        
        # Обновляем статистику собранных предметов
        self.update_user_stat(user_id, 'items_collected')
        return True
    
    def remove_item_from_inventory(self, user_id, item_name):
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT id FROM items WHERE name = %s', (item_name,))
        item_result = cursor.fetchone()
        
        if not item_result:
            return False
            
        item_id = str(item_result[0])
        
        cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return False
            
        inventory_data = json.loads(result[0])
        
        if item_id in inventory_data.get("items", {}):
            if inventory_data["items"][item_id] > 1:
                inventory_data["items"][item_id] -= 1
            else:
                del inventory_data["items"][item_id]
            
            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', 
                          (json.dumps(inventory_data), user_id))
            self.conn.commit()
            return True
        return False

    def add_case_to_inventory(self, user_id, case_id, case_name, source="gifted"):
        cursor = self.conn.cursor()
        cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            inventory = json.loads(result[0])
        else:
            inventory = {"cases": {}, "items": {}}
        
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
        
        cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', (json.dumps(inventory), user_id))
        self.conn.commit()
    
    def get_user_inventory(self, user_id):
        """Безопасное получение инвентаря пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                try:
                    return json.loads(result[0])
                except json.JSONDecodeError:
                    return {"cases": {}, "items": {}}
            return {"cases": {}, "items": {}}
        except Exception as e:
            print(f"❌ Ошибка в get_user_inventory для {user_id}: {e}")
            return {"cases": {}, "items": {}}

    def remove_case_from_inventory(self, user_id, case_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
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
            
            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', (json.dumps(inventory), user_id))
            self.conn.commit()
            return True
        return False

    def update_user_stat(self, user_id, stat_name, increment=1):
        """Обновляет статистику пользователя"""
        try:
            cursor = self.conn.cursor()
            
            # Проверяем существование записи статистики
            cursor.execute('SELECT 1 FROM user_stats WHERE user_id = %s', (user_id,))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO user_stats (user_id) VALUES (%s)', (user_id,))
            
            # Обновляем статистику
            cursor.execute(f'''
                UPDATE user_stats SET {stat_name} = {stat_name} + %s 
                WHERE user_id = %s
            ''', (increment, user_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка в update_user_stat: {e}")
            return False
    
    def get_user_buffs(self, user_id):
        """Безопасное получение бафов пользователя"""
        try:
            inventory = self.get_user_inventory(user_id)
            buffs = {}
            
            for item_id, count in inventory.get("items", {}).items():
                try:
                    if not item_id.isdigit():
                        continue
                        
                    item_data = self.get_item(int(item_id))
                    if item_data and len(item_data) > 6 and item_data[5]:  # buff_type
                        buff_type = item_data[5]
                        buff_value = item_data[6] if len(item_data) > 6 else 1.0
                        
                        # Берем самый сильный баф каждого типа
                        if buff_type not in buffs or buff_value > buffs[buff_type]['value']:
                            buffs[buff_type] = {
                                'value': buff_value,
                                'description': item_data[7] if len(item_data) > 7 else "Бонус",
                                'item_name': item_data[1] if len(item_data) > 1 else "Предмет"
                            }
                except (ValueError, IndexError) as e:
                    print(f"⚠️ Ошибка обработки предмета {item_id}: {e}")
                    continue
            
            return buffs
        except Exception as e:
            print(f"❌ Ошибка в get_user_buffs для {user_id}: {e}")
            return {}
    
    def apply_buff_to_amount(self, user_id, base_amount, buff_type):
        """Применяет баф к сумме, если он есть у пользователя"""
        buffs = self.get_user_buffs(user_id)
        if buff_type in buffs:
            return int(base_amount * buffs[buff_type]['value'])
        return base_amount
    
    def apply_buff_to_chance(self, user_id, base_chance, buff_type):
        """Применяет баф к шансу, если он есть у пользователя"""
        buffs = self.get_user_buffs(user_id)
        if buff_type in buffs:
            return base_chance * buffs[buff_type]['value']
        return base_chance

    def get_item_name_by_id(self, item_id):
        """Получить название предмета по ID"""
        try:
            if not item_id or not str(item_id).isdigit():
                return f"Предмет ID:{item_id}"
                
            item_data = self.get_item(int(item_id))
            if item_data and len(item_data) > 1 and item_data[1]:
                return item_data[1]
            return f"Предмет ID:{item_id}"
        except Exception as e:
            print(f"❌ Ошибка получения названия предмета {item_id}: {e}")
            return f"Предмет ID:{item_id}"

# Создаем экземпляр базы данных
try:
    db = Database()
    print("✅ База данных успешно инициализирована!")
except Exception as e:
    print(f"💥 Критическая ошибка при инициализации базы данных: {e}")
    traceback.print_exc()
    exit(1)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_user_data_safe(user_data):
    """Безопасное извлечение данных пользователя из кортежа"""
    if not user_data:
        return {
            'user_id': 0,
            'balance': 100,
            'daily_streak': 0,
            'last_daily': None,
            'inventory': '{"cases": {}, "items": {}}',
            'created_at': datetime.datetime.now()
        }
    
    try:
        return {
            'user_id': user_data[0] if len(user_data) > 0 else 0,
            'balance': user_data[1] if len(user_data) > 1 else 100,
            'daily_streak': user_data[2] if len(user_data) > 2 else 0,
            'last_daily': user_data[3] if len(user_data) > 3 else None,
            'inventory': user_data[4] if len(user_data) > 4 else '{"cases": {}, "items": {}}',
            'created_at': user_data[5] if len(user_data) > 5 else datetime.datetime.now()
        }
    except (IndexError, TypeError) as e:
        print(f"⚠️ Ошибка в get_user_data_safe: {e}")
        return {
            'user_id': 0,
            'balance': 100,
            'daily_streak': 0,
            'last_daily': None,
            'inventory': '{"cases": {}, "items": {}}',
            'created_at': datetime.datetime.now()
        }

def get_reward(case):
    """Получить случайную награду из кейса"""
    rewards = case['rewards']
    rand = random.random()
    cumulative_chance = 0
    
    for reward in rewards:
        cumulative_chance += reward['chance']
        if rand <= cumulative_chance:
            return reward
    return rewards[-1]

async def process_reward(user, reward, case):
    """Обработать награду и выдать пользователю"""
    try:
        if reward['type'] == 'coins':
            amount = random.randint(reward['amount'][0], reward['amount'][1])
            
            # Применяем бафы к награде
            amount = db.apply_buff_to_amount(user.id, amount, 'case_bonus')
            amount = db.apply_buff_to_amount(user.id, amount, 'multiplier')
            amount = db.apply_buff_to_amount(user.id, amount, 'all_bonus')
            
            db.update_balance(user.id, amount)
            db.log_transaction(user.id, 'case_reward', amount, description=f"Кейс: {case['name']}")
            
            return f"🎉 Вы выиграли {amount} {EMOJIS['coin']}!\n{reward['description']}"
            
        elif reward['type'] == 'special_item':
            item_name = reward['name']
            success = db.add_item_to_inventory(user.id, item_name)
            
            if success:
                return f"🎁 Вы получили предмет: **{item_name}**!\n{reward['description']}"
            else:
                return f"❌ Не удалось выдать предмет {item_name}"
                
        elif reward['type'] == 'bonus':
            # Временный бонус (в реальной реализации нужно хранить в отдельной таблице)
            return f"🌟 Вы получили временный бонус: {reward['description']}"
            
        else:
            return f"❓ Неизвестный тип награды: {reward}"
            
    except Exception as e:
        print(f"❌ Ошибка обработки награды: {e}")
        return "❌ Произошла ошибка при обработке награды"

# ========== КЛАССЫ VIEW ==========
class ImprovedCasesView(View):
    def __init__(self, pages, author_id):
        super().__init__(timeout=120)
        self.pages = pages
        self.current_page = 0
        self.total_pages = len(pages)
        self.author_id = author_id
        self.update_buttons()

    def update_buttons(self):
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)

    @discord.ui.button(label='⬅️ Назад', style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Это не ваша пагинация!", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='➡️ Вперед', style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Это не ваша пагинация!", ephemeral=True)
            return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self):
        page_cases = self.pages[self.current_page]
        embed = discord.Embed(
            title=f"🎁 Доступные кейсы (Страница {self.current_page + 1}/{self.total_pages})",
            description="Нажмите на кнопку 'Открыть' чтобы купить и открыть кейс",
            color=0xff69b4
        )
        
        for case in page_cases:
            case_id = case[0]
            case_name = case[1]
            case_price = case[2]
            
            embed.add_field(
                name=f"{case_name} (ID: {case_id})",
                value=f"Цена: {case_price} {EMOJIS['coin']}",
                inline=False
            )
        
        return embed

class CaseView(View):
    def __init__(self, case_id, author_id):
        super().__init__(timeout=60)
        self.case_id = case_id
        self.author_id = author_id

    @discord.ui.button(label='🎁 Открыть кейс', style=discord.ButtonStyle.primary)
    async def open_case(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Это не ваш кейс!", ephemeral=True)
            return
        
        try:
            case_data = db.get_case(self.case_id)
            if not case_data:
                await interaction.response.send_message("❌ Кейс не найден!", ephemeral=True)
                return
            
            user_data = db.get_user(interaction.user.id)
            user_safe = get_user_data_safe(user_data)
            
            case_price = case_data[2]
            if user_safe['balance'] < case_price:
                await interaction.response.send_message("❌ Недостаточно монет для открытия кейса!", ephemeral=True)
                return
            
            # Спин анимация
            embed = discord.Embed(title="🎰 Открытие кейса...", color=0xffd700)
            await interaction.response.edit_message(embed=embed, view=None)
            
            for i in range(3):
                await asyncio.sleep(1)
                embed.description = "🎁" * (i + 1)
                await interaction.edit_original_response(embed=embed)
            
            # Списание средств
            db.update_balance(interaction.user.id, -case_price)
            db.log_transaction(interaction.user.id, 'case_purchase', -case_price, description=f"Покупка кейса: {case_data[1]}")
            
            # Определение награды
            case = {
                'name': case_data[1],
                'price': case_data[2],
                'rewards': json.loads(case_data[3])
            }
            
            reward = get_reward(case)
            reward_text = await process_reward(interaction.user, reward, case)
            
            # Обновляем статистику
            db.update_user_stat(interaction.user.id, 'cases_opened')
            
            embed = discord.Embed(
                title=f"🎉 {case['name']} открыт!",
                description=reward_text,
                color=0x00ff00
            )
            embed.add_field(name="💸 Стоимость", value=f"{case_price} {EMOJIS['coin']}", inline=True)
            
            await interaction.edit_original_response(embed=embed)
            
        except Exception as e:
            print(f"❌ Ошибка при открытии кейса: {e}")
            error_embed = discord.Embed(
                title="❌ Ошибка",
                description="Произошла ошибка при открытии кейса",
                color=0xff0000
            )
            await interaction.edit_original_response(embed=error_embed)

class CoinFlipView(View):
    def __init__(self, author_id, bet):
        super().__init__(timeout=30)
        self.author_id = author_id
        self.bet = bet

    @discord.ui.button(label='🪙 Орел', style=discord.ButtonStyle.primary)
    async def heads(self, interaction: discord.Interaction, button: Button):
        await self.flip_coin(interaction, 'heads')

    @discord.ui.button(label='🪙 Решка', style=discord.ButtonStyle.primary)
    async def tails(self, interaction: discord.Interaction, button: Button):
        await self.flip_coin(interaction, 'tails')

    async def flip_coin(self, interaction: discord.Interaction, choice):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        # Анимация подбрасывания
        embed = discord.Embed(title="🪙 Монета подбрасывается...", color=0xffd700)
        await interaction.response.edit_message(embed=embed, view=None)
        
        for i in range(3):
            await asyncio.sleep(0.5)
            embed.description = "🌀" * (i + 1)
            await interaction.edit_original_response(embed=embed)
        
        await asyncio.sleep(1)
        
        # Результат
        result = random.choice(['heads', 'tails'])
        result_emoji = '🪙 Орел' if result == 'heads' else '🪙 Решка'
        
        if choice == result:
            base_winnings = self.bet
            # Применяем бафы к выигрышу
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'coinflip_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings)
            db.log_transaction(interaction.user.id, 'coinflip_win', winnings, description="Победа в coinflip")
            db.update_user_stat(interaction.user.id, 'coinflip_wins')
            
            result_text = f"🎉 Победа! Выигрыш: {winnings} {EMOJIS['coin']}"
            color = 0x00ff00
        else:
            # Применяем баф защиты от проигрышей
            loss = db.apply_buff_to_amount(interaction.user.id, self.bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'coinflip_loss', -loss, description="Проигрыш в coinflip")
            
            result_text = f"❌ Проигрыш! Потеряно: {loss} {EMOJIS['coin']}"
            color = 0xff0000
        
        embed = discord.Embed(
            title=f"🪙 CoinFlip - Ставка: {self.bet} {EMOJIS['coin']}",
            description=f"**Результат:** {result_emoji}\n**Ваш выбор:** {'Орел' if choice == 'heads' else 'Решка'}\n\n{result_text}",
            color=color
        )
        
        await interaction.edit_original_response(embed=embed)

# ========== КОМАНДЫ ==========
def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        is_admin = interaction.user.id in ADMIN_IDS
        if not is_admin:
            await interaction.response.send_message(
                "❌ У вас нет прав для использования этой команды!",
                ephemeral=True
            )
        return is_admin
    return app_commands.check(predicate)

# Базовые команды
@bot.tree.command(name="test", description="Тестовая команда для проверки работы")
async def test_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✅ Тестовая команда работает!",
        description="Если вы видите это сообщение, значит команды синхронизированы правильно!",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ping", description="Проверить пинг бота")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Понг!",
        description=f"Задержка бота: {round(bot.latency * 1000)}мс",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sync", description="Синхронизировать команды (админ)")
@is_admin()
async def sync_commands(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
        
        synced = await bot.tree.sync()
        
        embed = discord.Embed(
            title="✅ Синхронизация завершена",
            description=f"Синхронизировано {len(synced)} команд",
            color=0x00ff00
        )
        
        if synced:
            commands_list = "\n".join([f"• `/{cmd.name}`" for cmd in synced])
            embed.add_field(name="Синхронизированные команды:", value=commands_list, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Ошибка синхронизации",
            description=f"```{e}```",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

# Экономические команды
@bot.tree.command(name="balance", description="Показать ваш баланс")
@app_commands.describe(user="Пользователь, чей баланс показать (опционально)")
async def balance(interaction: discord.Interaction, user: discord.Member = None):
    try:
        user = user or interaction.user
        user_data = db.get_user(user.id)
        user_safe = get_user_data_safe(user_data)
        
        embed = discord.Embed(
            title=f"{EMOJIS['coin']} Баланс {user.display_name}",
            color=0xffd700
        )
        embed.add_field(name="Баланс", value=f"{user_safe['balance']} {EMOJIS['coin']}", inline=True)
        embed.add_field(name="Ежедневная серия", value=f"{user_safe['daily_streak']} дней", inline=True)
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде balance: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка",
            description="Произошла ошибка при получении данных.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="daily", description="Получить ежедневную награду")
async def daily(interaction: discord.Interaction):
    try:
        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)
        
        last_daily_str = user_safe['last_daily']
        daily_streak = user_safe['daily_streak']
        
        last_daily = None
        if last_daily_str:
            try:
                last_daily = datetime.datetime.fromisoformat(last_daily_str)
            except (ValueError, TypeError):
                last_daily = None
        
        now = datetime.datetime.now()
        
        if last_daily and (now - last_daily).days < 1:
            await interaction.response.send_message("❌ Вы уже получали ежедневную награду сегодня!", ephemeral=True)
            return
        
        streak = daily_streak + 1 if last_daily and (now - last_daily).days == 1 else 1
        base_reward = 100
        streak_bonus = streak * 10
        reward = base_reward + streak_bonus
        
        # Применяем бафы к награде
        reward = db.apply_buff_to_amount(interaction.user.id, reward, 'daily_bonus')
        reward = db.apply_buff_to_amount(interaction.user.id, reward, 'multiplier')
        reward = db.apply_buff_to_amount(interaction.user.id, reward, 'all_bonus')
        
        db.update_balance(interaction.user.id, reward)
        cursor = db.conn.cursor()
        cursor.execute('UPDATE users SET daily_streak = %s, last_daily = %s WHERE user_id = %s', 
                       (streak, now.isoformat(), interaction.user.id))
        db.conn.commit()
        db.log_transaction(interaction.user.id, 'daily', reward)
        db.update_user_stat(interaction.user.id, 'daily_claimed')
        
        embed = discord.Embed(
            title=f"{EMOJIS['daily']} Ежедневная награда",
            description=f"Награда: {reward} {EMOJIS['coin']}\nСерия: {streak} дней\nБонус за серию: +{streak_bonus} {EMOJIS['coin']}",
            color=0x00ff00
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде daily: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка",
            description="Не удалось получить ежедневную награду.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# Команды кейсов
@bot.tree.command(name="cases", description="Показать список доступных кейсов")
async def cases_list(interaction: discord.Interaction):
    try:
        cases = db.get_cases()
        
        if not cases:
            await interaction.response.send_message("❌ Кейсы не найдены!", ephemeral=True)
            return
        
        # Разбиваем на страницы по 3 кейса
        pages = []
        current_page = []
        
        for i, case in enumerate(cases):
            if i > 0 and i % 3 == 0:
                pages.append(current_page)
                current_page = []
            current_page.append(case)
        
        if current_page:
            pages.append(current_page)
        
        view = ImprovedCasesView(pages, interaction.user.id)
        embed = view.create_embed()
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        print(f"❌ Ошибка в команде cases: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке кейсов!", ephemeral=True)

@bot.tree.command(name="open_case", description="Открыть кейс")
@app_commands.describe(case_id="ID кейса для открытия")
async def open_case(interaction: discord.Interaction, case_id: int):
    try:
        case_data = db.get_case(case_id)
        if not case_data:
            await interaction.response.send_message("❌ Кейс с таким ID не найден!", ephemeral=True)
            return
        
        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)
        
        case_price = case_data[2]
        if user_safe['balance'] < case_price:
            await interaction.response.send_message("❌ Недостаточно монет для открытия этого кейса!", ephemeral=True)
            return
        
        view = CaseView(case_id, interaction.user.id)
        embed = discord.Embed(
            title=f"🎁 {case_data[1]}",
            description=f"Стоимость: {case_price} {EMOJIS['coin']}\n\nНажмите кнопку ниже чтобы открыть кейс!",
            color=0xff69b4
        )
        
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        print(f"❌ Ошибка в команде open_case: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при открытии кейса!", ephemeral=True)

# Мини-игры
@bot.tree.command(name="coinflip", description="Подбросить монету на ставку (50/50 шанс)")
@app_commands.describe(bet="Ставка в монетах")
async def coinflip(interaction: discord.Interaction, bet: int):
    user_data = db.get_user(interaction.user.id)
    user_safe = get_user_data_safe(user_data)
    
    if user_safe['balance'] < bet:
        await interaction.response.send_message("❌ Недостаточно монет!", ephemeral=True)
        return
    
    if bet <= 0:
        await interaction.response.send_message("❌ Ставка должна быть положительной!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"🪙 Подбрасывание монеты",
        description=f"Ставка: {bet} {EMOJIS['coin']}\nВыберите сторону монеты:",
        color=0xffd700
    )
    
    view = CoinFlipView(interaction.user.id, bet)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="slots", description="Играть в игровые автоматы")
@app_commands.describe(bet="Ставка в монетах")
async def slots(interaction: discord.Interaction, bet: int):
    try:
        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)
        
        if user_safe['balance'] < bet:
            await interaction.response.send_message("❌ Недостаточно монет!", ephemeral=True)
            return
    
        symbols = ['🍒', '🍋', '🍊', '🍇', '🔔', '💎', '7️⃣']
        
        # Анимация вращения
        embed = discord.Embed(title="🎰 Игровые автоматы", description="Вращение...", color=0xff69b4)
        await interaction.response.send_message(embed=embed)
        
        for i in range(3):
            await asyncio.sleep(0.5)
            slot_result = [random.choice(symbols) for _ in range(3)]
            embed.description = f"🎰 | {' | '.join(slot_result)} | 🎰"
            await interaction.edit_original_response(embed=embed)
        
        await asyncio.sleep(1)
        
        # Финальный результат
        final_result = [random.choice(symbols) for _ in range(3)]
        embed.description = f"🎰 | {' | '.join(final_result)} | 🎰"
        
        # Проверка выигрыша
        if final_result[0] == final_result[1] == final_result[2]:
            if final_result[0] == '💎':
                multiplier = 50
            elif final_result[0] == '7️⃣':
                multiplier = 25
            elif final_result[0] == '🔔':
                multiplier = 15
            else:
                multiplier = 8
            
            base_winnings = bet * multiplier
            # Применяем бафы к выигрышу
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'slot_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings)
            db.log_transaction(interaction.user.id, 'slots_win', winnings, description=f"ДЖЕКПОТ в слотах x{multiplier}")
            db.update_user_stat(interaction.user.id, 'slot_wins')
            
            result_text = f"🎉 ДЖЕКПОТ! x{multiplier}\nВыигрыш: {winnings} {EMOJIS['coin']}"
            color = 0x00ff00
        elif final_result[0] == final_result[1] or final_result[1] == final_result[2]:
            multiplier = 3
            base_winnings = bet * multiplier
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'slot_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings)
            db.log_transaction(interaction.user.id, 'slots_win', winnings, description=f"Победа в слотах x{multiplier}")
            
            result_text = f"✅ Два в ряд! x{multiplier}\nВыигрыш: {winnings} {EMOJIS['coin']}"
            color = 0x00ff00
        else:
            # Применяем баф защиты от проигрышей
            loss = db.apply_buff_to_amount(interaction.user.id, bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'slots_loss', -loss, description="Проигрыш в слотах")
            
            result_text = f"❌ Повезет в следующий раз!\nПотеряно: {loss} {EMOJIS['coin']}"
            color = 0xff0000
        
        embed.add_field(name="Результат", value=result_text, inline=False)
        embed.add_field(name="Ставка", value=f"{bet} {EMOJIS['coin']}", inline=True)
        embed.color = color
        
        await interaction.edit_original_response(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде slots: {e}")
        await interaction.response.send_message("❌ Произошла ошибка в слотах!", ephemeral=True)

# Инвентарь и предметы
@bot.tree.command(name="inventory", description="Показать ваш инвентарь")
async def inventory(interaction: discord.Interaction):
    try:
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
                try:
                    case_id = case_key.replace("case_", "")
                    cases_text += f"• {case_info.get('name', 'Неизвестный кейс')} (ID: {case_id}) ×{case_info.get('count', 1)}\n"
                except Exception as e:
                    print(f"⚠️ Ошибка обработки кейса {case_key}: {e}")
                    continue
            embed.add_field(name="🎁 Кейсы", value=cases_text, inline=False)
        else:
            embed.add_field(name="🎁 Кейсы", value="Пусто", inline=False)
        
        # Показываем предметы
        items = inventory_data.get("items", {})
        if items:
            items_text = ""
            for item_id, count in items.items():
                try:
                    item_name = db.get_item_name_by_id(item_id)
                    items_text += f"• {item_name} ×{count}\n"
                except Exception as e:
                    print(f"⚠️ Ошибка обработки предмета {item_id}: {e}")
                    items_text += f"• Предмет ID:{item_id} ×{count}\n"
            
            if items_text:
                embed.add_field(name="📦 Предметы", value=items_text, inline=False)
            else:
                embed.add_field(name="📦 Предметы", value="Пусто", inline=False)
        else:
            embed.add_field(name="📦 Предметы", value="Пусто", inline=False)
        
        # Показываем активные бафы
        buffs = db.get_user_buffs(interaction.user.id)
        if buffs:
            buffs_text = "\n".join([f"• **{buff['item_name']}**: {buff['description']}" for buff in buffs.values()])
            embed.add_field(name="🎯 Активные бафы", value=buffs_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде inventory: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке инвентаря!", ephemeral=True)

@bot.tree.command(name="buffs", description="Показать ваши активные бафы")
async def buffs(interaction: discord.Interaction):
    buffs = db.get_user_buffs(interaction.user.id)
    
    embed = discord.Embed(title="🎯 Ваши активные бафы", color=0x00ff00)
    
    if not buffs:
        embed.description = "У вас пока нет активных бафов. Приобретайте предметы в кейсах!"
        await interaction.response.send_message(embed=embed)
        return
    
    for buff_type, buff_info in buffs.items():
        embed.add_field(
            name=f"✨ {buff_info['item_name']}",
            value=f"**Эффект:** {buff_info['description']}\n**Множитель:** x{buff_info['value']}",
            inline=False
        )
    
    embed.set_footer(text=f"Всего активных бафов: {len(buffs)}")
    await interaction.response.send_message(embed=embed)

# Помощь
@bot.tree.command(name="help", description="Показать информацию о боте и список команд")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Экономический Бот - Помощь",
        description="Добро пожаловать в экономическую игру!",
        color=0x3498db
    )
    
    embed.add_field(
        name="💰 Основные команды",
        value="""**/balance** - Показать баланс
**/daily** - Ежедневная награда
**/inventory** - Инвентарь
**/buffs** - Активные бафы""",
        inline=False
    )
    
    embed.add_field(
        name="🎁 Кейсы",
        value="""**/cases** - Список кейсов
**/open_case** ID - Открыть кейс""",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Игры",
        value="""**/coinflip** ставка - Подбросить монету
**/slots** ставка - Игровые автоматы""",
        inline=False
    )
    
    embed.set_footer(text="Используйте / для просмотра всех команд")
    
    await interaction.response.send_message(embed=embed)

# Обработчик ошибок
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        return
    elif isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message("❌ Команда не найдена!", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Недостаточно прав!", ephemeral=True)
    else:
        print(f"🔴 Необработанная ошибка: {error}")
        try:
            await interaction.response.send_message(
                "❌ Произошла неизвестная ошибка при выполнении команды!",
                ephemeral=True
            )
        except:
            pass

# ========== ЗАПУСК БОТА ==========
if __name__ == "__main__":
    print("🚀 Запуск улучшенного экономического бота...")
    print(f"🔑 Токен: {'✅ Найден' if BOT_TOKEN else '❌ Отсутствует'}")
    print(f"🗄️ База данных: {'✅ Подключена' if DATABASE_URL else '❌ Ошибка'}")
    print(f"👑 Админы: {len(ADMIN_IDS)} пользователей")
    print("=" * 50)
    
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"💥 Критическая ошибка при запуске бота: {e}")
        traceback.print_exc()
