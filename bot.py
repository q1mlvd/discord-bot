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

# Класс CustomBot должен быть определен ПЕРВЫМ
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
                print("🔍 Проверка зарегистрированных команд...")
                commands = self.tree.get_commands()
                print(f"🔍 Команд в дереве: {len(commands)}")
                for cmd in commands:
                    print(f"   - {cmd.name}: {cmd.description}")
                
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")
            traceback.print_exc()

# Получение переменных окружения
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
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# СОЗДАЕМ ЭКЗЕМПЛЯР БОТА ЗДЕСЬ
bot = CustomBot(command_prefix='!', intents=intents, help_command=None)

# Конфигурация
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

# Улучшенная система достижений
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

# Безопасный доступ к данным пользователя
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

# Исправленный класс Database для PostgreSQL
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
        """Инициализация начальных данных с УЛУЧШЕННЫМИ КЕЙСАМИ"""
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
                    ('⚡ Быстрый кейс', 75, json.dumps([
                        {'type': 'coins', 'amount': [30, 80], 'chance': 0.7, 'description': 'Быстрые монеты'},
                        {'type': 'coins', 'amount': [81, 180], 'chance': 0.2, 'description': 'Быстрая хорошая сумма'},
                        {'type': 'special_item', 'name': 'Перчатка вора', 'chance': 0.1, 'description': 'Увеличивает шанс кражи на 20%'}
                    ])),
                    ('📦 Средний кейс', 150, json.dumps([
                        {'type': 'coins', 'amount': [50, 100], 'chance': 0.4, 'description': 'Надежная сумма монет'},
                        {'type': 'coins', 'amount': [101, 250], 'chance': 0.3, 'description': 'Отличная сумма монет'},
                        {'type': 'special_item', 'name': 'Золотой амулет', 'chance': 0.15, 'description': 'Увеличивает ежедневную награду на 20%'},
                        {'type': 'coins', 'amount': [251, 500], 'chance': 0.1, 'description': 'Отличный выигрыш'},
                        {'type': 'bonus', 'multiplier': 1.2, 'duration': 12, 'chance': 0.05, 'description': 'Временный бонус x1.2 на 12 часов'}
                    ])),
                    ('💎 Большой кейс', 500, json.dumps([
                        {'type': 'coins', 'amount': [200, 400], 'chance': 0.6, 'description': 'Солидная сумма'},
                        {'type': 'coins', 'amount': [401, 1000], 'chance': 0.25, 'description': 'Очень хорошая сумма'},
                        {'type': 'special_item', 'name': 'Золотой ключ', 'chance': 0.08, 'description': 'Особый предмет'},
                        {'type': 'bonus', 'multiplier': 1.5, 'duration': 24, 'chance': 0.07, 'description': 'Временный бонус x1.5 на 24 часа'}
                    ])),
                    ('👑 Элитный кейс', 1000, json.dumps([
                        {'type': 'coins', 'amount': [500, 1000], 'chance': 0.3, 'description': 'Элитные монеты'},
                        {'type': 'coins', 'amount': [-300, -100], 'chance': 0.2, 'description': 'Неудача (потеря монет)'},
                        {'type': 'special_item', 'name': 'Древний артефакт', 'chance': 0.15, 'description': 'Мощный множитель наград'},
                        {'type': 'bonus', 'multiplier': 2.0, 'duration': 48, 'chance': 0.1, 'description': 'Временный бонус x2.0 на 48 часов'},
                        {'type': 'coins', 'amount': [1001, 3000], 'chance': 0.15, 'description': 'Элитный выигрыш'},
                        {'type': 'coins', 'amount': [3001, 6000], 'chance': 0.1, 'description': 'Элитный джекпот'}
                    ])),
                    ('🔮 Секретный кейс', 2000, json.dumps([
                        {'type': 'coins', 'amount': [800, 1500], 'chance': 0.3, 'description': 'Секретные монеты'},
                        {'type': 'coins', 'amount': [-1000, -500], 'chance': 0.15, 'description': 'Секретный риск'},
                        {'type': 'special_item', 'name': 'Мифический предмет', 'chance': 0.15, 'description': 'Легендарный множитель наград'},
                        {'type': 'bonus', 'multiplier': 3.0, 'duration': 72, 'chance': 0.1, 'description': 'Временный бонус x3.0 на 72 часа'},
                        {'type': 'coins', 'amount': [1501, 3000], 'chance': 0.15, 'description': 'Секретная удача'},
                        {'type': 'coins', 'amount': [4001, 7000], 'chance': 0.15, 'description': 'Секретный клад'}
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
                    ('Магический свиток', 'Увеличивает выигрыш в рулетке', 550, 'rare', 'roulette_bonus', 1.25, '+25% к выигрышу в рулетке'),
                    ('Кристалл маны', 'Умножает все награды', 1000, 'epic', 'multiplier', 1.3, 'x1.3 к любым наградам'),
                    ('Древний артефакт', 'Мощный множитель наград', 2000, 'legendary', 'multiplier', 1.5, 'x1.5 к любым наградам'),
                    ('Мифический предмет', 'Легендарный множитель наград', 5000, 'mythic', 'multiplier', 2.0, 'x2.0 к любым наградам'),
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
            # Возвращаем кортеж с безопасными значениями по умолчанию
            return (user_id, 100, 0, None, json.dumps({"cases": {}, "items": {}}), datetime.datetime.now())

    def get_user_safe(self, user_id):
        """Алиас для get_user для совместимости"""
        return self.get_user(user_id)
    
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
            # Если предмет не найден, создаем его без бафа
            cursor.execute('INSERT INTO items (name, description, value, rarity) VALUES (%s, %s, %s, %s) RETURNING id', 
                          (item_name, 'Автоматически созданный предмет', 100, 'common'))
            item_id = cursor.fetchone()[0]
        else:
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

    def get_user_inventory_safe(self, user_id):
        """Безопасное получение инвентаря с обработкой ошибок"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                try:
                    inventory_data = json.loads(result[0])
                    # Проверяем структуру инвентаря
                    if not isinstance(inventory_data, dict):
                        inventory_data = {"cases": {}, "items": {}}
                    if "cases" not in inventory_data:
                        inventory_data["cases"] = {}
                    if "items" not in inventory_data:
                        inventory_data["items"] = {}
                    return inventory_data
                except json.JSONDecodeError:
                    return {"cases": {}, "items": {}}
            return {"cases": {}, "items": {}}
        except Exception as e:
            print(f"❌ Ошибка в get_user_inventory_safe: {e}")
            return {"cases": {}, "items": {}}
    
    def get_all_items_safe(self):
        """Безопасное получение всех предметов"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM items')
            return cursor.fetchall()
        except Exception as e:
            print(f"❌ Ошибка в get_all_items_safe: {e}")
            return []
    
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
        """Обновляет статистику пользователя и проверяет достижения"""
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
            
            # Проверяем достижения
            return self.check_achievements(user_id)
        except Exception as e:
            print(f"❌ Ошибка в update_user_stat: {e}")
            return []
    
    def check_achievements(self, user_id):
        """Проверяет и выдает достижения пользователю"""
        try:
            cursor = self.conn.cursor()
            
            # Получаем статистику пользователя
            cursor.execute('SELECT * FROM user_stats WHERE user_id = %s', (user_id,))
            stats = cursor.fetchone()
            
            if not stats:
                return []
            
            # Получаем баланс пользователя
            user_data = self.get_user(user_id)
            balance = user_data[1] if len(user_data) > 1 else 0
            
            # Получаем инвентарь для проверки уникальных предметов
            inventory = self.get_user_inventory(user_id)
            unique_items = len(inventory.get("items", {}))
            
            # Получаем уже полученные достижения
            cursor.execute('SELECT achievement_id FROM achievements WHERE user_id = %s', (user_id,))
            user_achievements = [row[0] for row in cursor.fetchall()]
            
            # Проверяем каждое достижение
            achievements_to_add = []
            
            # Достижения по балансу
            if 'rich' not in user_achievements and balance >= 10000:
                achievements_to_add.append('rich')
            if 'millionaire' not in user_achievements and balance >= 100000:
                achievements_to_add.append('millionaire')
            
            # Достижения по кейсам
            if 'case_opener' not in user_achievements and stats[1] >= 50:  # cases_opened
                achievements_to_add.append('case_opener')
            if 'case_master' not in user_achievements and stats[1] >= 200:
                achievements_to_add.append('case_master')
            
            # Достижения по играм
            if 'gambler' not in user_achievements and stats[5] >= 25:  # roulette_wins
                achievements_to_add.append('gambler')
            if 'thief' not in user_achievements and stats[3] >= 20:  # steals_successful
                achievements_to_add.append('thief')
            if 'duel_master' not in user_achievements and stats[2] >= 25:  # duels_won
                achievements_to_add.append('duel_master')
            if 'slot_king' not in user_achievements and stats[6] >= 1:  # slot_wins (джекпот)
                achievements_to_add.append('slot_king')
            if 'blackjack_pro' not in user_achievements and stats[7] >= 10:  # blackjack_wins
                achievements_to_add.append('blackjack_pro')
            if 'coinflip_champ' not in user_achievements and stats[8] >= 30:  # coinflip_wins
                achievements_to_add.append('coinflip_champ')
            
            # Другие достижения
            if 'trader' not in user_achievements and stats[11] >= 15:  # market_sales
                achievements_to_add.append('trader')
            if 'gifter' not in user_achievements and stats[12] >= 10:  # gifts_sent
                achievements_to_add.append('gifter')
            if 'veteran' not in user_achievements and stats[9] >= 30:  # daily_claimed
                achievements_to_add.append('veteran')
            if 'lucky' not in user_achievements and stats[13] >= 3:  # consecutive_wins
                achievements_to_add.append('lucky')
            if 'item_collector' not in user_achievements and unique_items >= 10:
                achievements_to_add.append('item_collector')
            if 'buff_master' not in user_achievements and self.get_active_buffs_count(user_id) >= 5:
                achievements_to_add.append('buff_master')
            
            # Добавляем новые достижения и выдаем награды
            for achievement_id in achievements_to_add:
                cursor.execute('INSERT INTO achievements (user_id, achievement_id) VALUES (%s, %s)', 
                              (user_id, achievement_id))
                
                # Выдаем награду за достижение
                reward = ACHIEVEMENTS[achievement_id]['reward']
                self.update_balance(user_id, reward)
                self.log_transaction(user_id, 'achievement_reward', reward, description=f"Достижение: {ACHIEVEMENTS[achievement_id]['name']}")
            
            self.conn.commit()
            
            return achievements_to_add
        except Exception as e:
            print(f"❌ Ошибка в check_achievements: {e}")
            return []

    def get_item_name_by_id(self, item_id):
        """Получить название предмета по ID"""
        try:
            if not item_id or not str(item_id).isdigit():
                return f"Предмет ID:{item_id}"
                
            item_data = self.get_item(int(item_id))
            if item_data and len(item_data) > 1 and item_data[1]:
                return item_data[1]  # название предмета
            return f"Предмет ID:{item_id}"
        except Exception as e:
            print(f"❌ Ошибка получения названия предмета {item_id}: {e}")
            return f"Предмет ID:{item_id}"

    def update_consecutive_wins(self, user_id, win=True):
        """Обновляет счетчик последовательных побед"""
        cursor = self.conn.cursor()
        
        if win:
            cursor.execute('''
                UPDATE user_stats 
                SET consecutive_wins = consecutive_wins + 1, last_win_time = CURRENT_TIMESTAMP
                WHERE user_id = %s
            ''', (user_id,))
        else:
            cursor.execute('''
                UPDATE user_stats 
                SET consecutive_wins = 0
                WHERE user_id = %s
            ''', (user_id,))
        
        self.conn.commit()
    
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
    
    def get_active_buffs_count(self, user_id):
        """Возвращает количество активных уникальных бафов"""
        buffs = self.get_user_buffs(user_id)
        return len(buffs)
    
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
    
    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY balance DESC')
        return cursor.fetchall()
    
    def get_all_transactions(self, limit=50):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM transactions ORDER BY timestamp DESC LIMIT %s', (limit,))
        return cursor.fetchall()
    
    def get_all_items(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM items')
        return cursor.fetchall()

    def get_user_quests(self, user_id):
        """Получить квесты пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT quest_id, progress, completed FROM quests WHERE user_id = %s', (user_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"❌ Ошибка в get_user_quests: {e}")
            return []
    
    def add_user_quest(self, user_id, quest_id):
        """Добавить квест пользователю"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO quests (user_id, quest_id, progress, completed) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, quest_id) DO NOTHING
            ''', (user_id, quest_id, 0, False))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка в add_user_quest: {e}")
            return False
    
    def update_quest_progress(self, user_id, quest_id, progress, completed=False):
        """Обновить прогресс квеста"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE quests SET progress = %s, completed = %s 
                WHERE user_id = %s AND quest_id = %s
            ''', (progress, completed, user_id, quest_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка в update_quest_progress: {e}")
            return False

# Создаем экземпляр базы данных
try:
    db = Database()
    print("✅ База данных успешно инициализирована!")
    
    # Проверяем, что кейсы загружаются
    test_cases = db.get_cases()
    print(f"🔍 Тест: загружено {len(test_cases)} кейсов после инициализации")
    
except Exception as e:
    print(f"💥 Критическая ошибка при инициализации базы данных: {e}")
    traceback.print_exc()
    exit(1)

# Событие подключения для отладки
@bot.event
async def on_connect():
    print(f"🔗 Бот подключился к Discord")
    commands_count = len(bot.tree.get_commands())
    print(f"📊 Зарегистрировано команд в коде: {commands_count}")
    
    if commands_count == 0:
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: Нет зарегистрированных команд!")
        print("🔍 Проверьте:")
        print("   - Декораторы @bot.tree.command")
        print("   - Отсутствие ошибок в определении команд")
        print("   - Правильность импортов")

# Простая тестовая команда для проверки
@bot.tree.command(name="test", description="Тестовая команда для проверки работы")
async def test_command(interaction: discord.Interaction):
    """Простая тестовая команда для проверки синхронизации"""
    embed = discord.Embed(
        title="✅ Тестовая команда работает!",
        description="Если вы видите это сообщение, значит команды синхронизированы правильно!",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Улучшенная функция проверки прав администратора
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

# Обработчик ошибок для команд
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        return
    elif isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message("❌ Команда не найдена!", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Недостаточно прав!", ephemeral=True)
    elif isinstance(error, IndexError):
        print(f"🔴 IndexError в команде: {error}")
        error_embed = discord.Embed(
            title="❌ Ошибка данных",
            description="Произошла ошибка при обработке данных. Администратор уведомлен.",
            color=0xff0000
        )
        try:
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        except:
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    else:
        print(f"🔴 Необработанная ошибка: {error}")
        try:
            await interaction.response.send_message(
                "❌ Произошла неизвестная ошибка при выполнении команды!",
                ephemeral=True
            )
        except:
            try:
                await interaction.followup.send(
                    "❌ Произошла неизвестная ошибка при выполнении команды!",
                    ephemeral=True
                )
            except:
                pass

# Классы View для различных команд
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
            title=f"📦 Список кейсов (Страница {self.current_page + 1}/{self.total_pages})",
            color=0xff69b4
        )

        for case in page_cases:
            case_id = case[0]
            case_name = case[1]
            case_price = case[2]
            case_rewards = json.loads(case[3])

            embed.add_field(
                name=f"{case_name} (ID: {case_id})",
                value=f"Цена: {case_price} {EMOJIS['coin']}",
                inline=False
            )

        return embed

class CaseView(View):
    def __init__(self, case_id, user_id):
        super().__init__(timeout=60)
        self.case_id = case_id
        self.user_id = user_id

    @discord.ui.button(label='Открыть кейс', style=discord.ButtonStyle.primary)
    async def open_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваш кейс!", ephemeral=True)
            return

        case_data = db.get_case(self.case_id)
        if not case_data:
            await interaction.response.send_message("❌ Кейс не найден!", ephemeral=True)
            return

        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)

        case_price = case_data[2]
        if user_safe['balance'] < case_price:
            await interaction.response.send_message("❌ Недостаточно монет!", ephemeral=True)
            return

        # Спин анимация
        embed = discord.Embed(title="🎰 Открытие кейса...", color=0xffd700)
        await interaction.response.edit_message(embed=embed, view=None)

        for i in range(3):
            await asyncio.sleep(1)
            embed.description = "🎁" * (i + 1)
            await interaction.edit_original_response(embed=embed)

        # Определение награды
        case = {
            'name': case_data[1],
            'price': case_data[2],
            'rewards': json.loads(case_data[3])
        }
        
        # Функции для работы с наградами
        def get_reward(case):
            rewards = case['rewards']
            rand = random.random()
            current = 0
            for reward in rewards:
                current += reward['chance']
                if rand <= current:
                    return reward
            return rewards[0]

        async def process_reward(user, reward, case):
            user_id = user.id
            if reward['type'] == 'coins':
                amount = random.randint(reward['amount'][0], reward['amount'][1])
                # Применяем бафы
                amount = db.apply_buff_to_amount(user_id, amount, 'case_bonus')
                amount = db.apply_buff_to_amount(user_id, amount, 'multiplier')
                amount = db.apply_buff_to_amount(user_id, amount, 'all_bonus')
                db.update_balance(user_id, amount)
                db.log_transaction(user_id, 'case_reward', amount, description=f"Кейс: {case['name']}")
                return f"Монеты: {amount} {EMOJIS['coin']}"

            elif reward['type'] == 'special_item':
                item_name = reward['name']
                db.add_item_to_inventory(user_id, item_name)
                return f"Предмет: {item_name}"

            elif reward['type'] == 'bonus':
                amount = case['price'] * reward['multiplier']
                db.update_balance(user_id, amount)
                db.log_transaction(user_id, 'case_bonus', amount, description=f"Бонус из кейса: {case['name']}")
                return f"Бонус: {amount} {EMOJIS['coin']} (x{reward['multiplier']})"

            else:
                return "Ничего"

        reward = get_reward(case)
        reward_text = await process_reward(interaction.user, reward, case)

        # Списание средств
        db.update_balance(interaction.user.id, -case_price)
        db.log_transaction(interaction.user.id, 'case_purchase', -case_price, description=case['name'])

        # Обновляем статистику открытия кейсов
        db.update_user_stat(interaction.user.id, 'cases_opened')

        embed = discord.Embed(
            title=f"🎉 {case['name']} открыт!",
            description=reward_text,
            color=0x00ff00
        )
        embed.add_field(name="Стоимость", value=f"{case_price} {EMOJIS['coin']}", inline=True)
        await interaction.edit_original_response(embed=embed)

class CoinFlipView(View):
    def __init__(self, user_id, bet):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bet = bet

    @discord.ui.button(label='Орёл', style=discord.ButtonStyle.primary)
    async def heads(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        await self.process_coinflip(interaction, 'heads')

    @discord.ui.button(label='Решка', style=discord.ButtonStyle.primary)
    async def tails(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        await self.process_coinflip(interaction, 'tails')

    async def process_coinflip(self, interaction: discord.Interaction, choice):
        # Анимация подбрасывания
        embed = discord.Embed(title="🪙 Монета подбрасывается...", color=0xffd700)
        await interaction.response.edit_message(embed=embed, view=None)
        
        for i in range(3):
            await asyncio.sleep(1)
            embed.description = "⏳" * (i + 1)
            await interaction.edit_original_response(embed=embed)
        
        await asyncio.sleep(1)
        
        # Результат
        result = random.choice(['heads', 'tails'])
        if choice == result:
            base_winnings = self.bet * 2
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'coinflip_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings - self.bet)  # Чистый выигрыш
            db.log_transaction(interaction.user.id, 'coinflip_win', winnings - self.bet)
            db.update_user_stat(interaction.user.id, 'coinflip_wins')
            db.update_consecutive_wins(interaction.user.id, True)
            
            result_text = f"🎉 Победа! Вы выиграли {winnings - self.bet} {EMOJIS['coin']} (чистыми)"
            color = 0x00ff00
        else:
            # Применяем баф защиты от проигрышей
            loss = db.apply_buff_to_amount(interaction.user.id, self.bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'coinflip_loss', -loss)
            db.update_consecutive_wins(interaction.user.id, False)
            
            result_text = f"❌ Проигрыш! Вы потеряли {loss} {EMOJIS['coin']}"
            color = 0xff0000
        
        embed = discord.Embed(
            title=f"🪙 CoinFlip - Ставка: {self.bet} {EMOJIS['coin']}",
            description=f"Ваш выбор: {choice}\nРезультат: {result}\n\n{result_text}",
            color=color
        )
        await interaction.edit_original_response(embed=embed)

class BlackjackView(View):
    def __init__(self, user_id, bet):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bet = bet
        self.player_cards = []
        self.dealer_cards = []
        self.game_over = False
        
        # Начальная раздача
        self.player_cards = [self.draw_card(), self.draw_card()]
        self.dealer_cards = [self.draw_card(), self.draw_card()]

    def draw_card(self):
        return random.randint(1, 11)

    def calculate_score(self, cards):
        score = sum(cards)
        # Обработка тузов
        if score > 21 and 11 in cards:
            cards[cards.index(11)] = 1
            score = sum(cards)
        return score

    def create_embed(self):
        player_score = self.calculate_score(self.player_cards)
        dealer_score = self.calculate_score(self.dealer_cards)
        
        embed = discord.Embed(title="🃏 Блэкджек", color=0x2ecc71)
        embed.add_field(
            name="Ваши карты",
            value=f"{' '.join(['🂠' for _ in self.player_cards])} (Очки: {player_score})",
            inline=False
        )
        embed.add_field(
            name="Карты дилера", 
            value=f"{' '.join(['🂠' for _ in self.dealer_cards])} (Очки: {dealer_score})",
            inline=False
        )
        embed.add_field(name="Ставка", value=f"{self.bet} {EMOJIS['coin']}", inline=True)
        
        if self.game_over:
            if player_score > 21:
                embed.description = "💥 Перебор! Вы проиграли."
                embed.color = 0xff0000
            elif dealer_score > 21:
                embed.description = "🎉 Дилер перебрал! Вы выиграли."
                embed.color = 0x00ff00
            elif player_score > dealer_score:
                embed.description = "🎉 Вы выиграли!"
                embed.color = 0x00ff00
            elif player_score < dealer_score:
                embed.description = "❌ Вы проиграли."
                embed.color = 0xff0000
            else:
                embed.description = "🤝 Ничья!"
                embed.color = 0xffff00
        else:
            embed.description = "Выберите действие:"
            
        return embed

    @discord.ui.button(label='Взять карту', style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Игра уже завершена!", ephemeral=True)
            return
        
        self.player_cards.append(self.draw_card())
        player_score = self.calculate_score(self.player_cards)
        
        if player_score > 21:
            self.game_over = True
            # Применяем баф защиты от проигрышей
            loss = db.apply_buff_to_amount(interaction.user.id, self.bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'blackjack_loss', -loss)
            db.update_consecutive_wins(interaction.user.id, False)
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Остановиться', style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Игра уже завершена!", ephemeral=True)
            return
        
        # Ход дилера
        while self.calculate_score(self.dealer_cards) < 17:
            self.dealer_cards.append(self.draw_card())
        
        self.game_over = True
        player_score = self.calculate_score(self.player_cards)
        dealer_score = self.calculate_score(self.dealer_cards)
        
        # Определение победителя
        if player_score > 21:
            # Уже обработано в hit
            pass
        elif dealer_score > 21 or player_score > dealer_score:
            base_winnings = self.bet * 2
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'blackjack_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings - self.bet)
            db.log_transaction(interaction.user.id, 'blackjack_win', winnings - self.bet)
            db.update_user_stat(interaction.user.id, 'blackjack_wins')
            db.update_consecutive_wins(interaction.user.id, True)
        elif player_score < dealer_score:
            loss = db.apply_buff_to_amount(interaction.user.id, self.bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'blackjack_loss', -loss)
            db.update_consecutive_wins(interaction.user.id, False)
        # Ничья - деньги возвращаются
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class DuelView(View):
    def __init__(self, challenger_id, target_id, bet):
        super().__init__(timeout=30)
        self.challenger_id = challenger_id
        self.target_id = target_id
        self.bet = bet

    @discord.ui.button(label='Принять дуэль', style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ Это не ваш вызов на дуэль!", ephemeral=True)
            return
        
        # Проверяем балансы еще раз
        challenger_data = db.get_user(self.challenger_id)
        challenger_safe = get_user_data_safe(challenger_data)
        target_data = db.get_user(self.target_id)
        target_safe = get_user_data_safe(target_data)
        
        if challenger_safe['balance'] < self.bet or target_safe['balance'] < self.bet:
            await interaction.response.send_message("❌ У одного из участников недостаточно монет!", ephemeral=True)
            return
        
        # Определяем победителя с учетом бафов
        challenger_buffs = db.get_user_buffs(self.challenger_id)
        target_buffs = db.get_user_buffs(self.target_id)
        
        challenger_win_chance = 0.5
        target_win_chance = 0.5
        
        # Применяем бафы дуэлей
        if 'duel_bonus' in challenger_buffs:
            challenger_win_chance *= challenger_buffs['duel_bonus']['value']
        if 'duel_bonus' in target_buffs:
            target_win_chance *= target_buffs['duel_bonus']['value']
        
        # Нормализуем шансы
        total = challenger_win_chance + target_win_chance
        challenger_win_chance /= total
        target_win_chance /= total
        
        # Определяем победителя
        if random.random() < challenger_win_chance:
            winner_id = self.challenger_id
            loser_id = self.target_id
        else:
            winner_id = self.target_id
            loser_id = self.challenger_id
        
        # Передача монет
        base_winnings = self.bet * 2
        winnings = db.apply_buff_to_amount(winner_id, base_winnings, 'game_bonus')
        winnings = db.apply_buff_to_amount(winner_id, winnings, 'multiplier')
        winnings = db.apply_buff_to_amount(winner_id, winnings, 'all_bonus')
        
        db.update_balance(winner_id, winnings - self.bet)  # Чистый выигрыш
        db.update_balance(loser_id, -self.bet)
        
        db.log_transaction(winner_id, 'duel_win', winnings - self.bet, loser_id, "Победа в дуэли")
        db.log_transaction(loser_id, 'duel_loss', -self.bet, winner_id, "Поражение в дуэли")
        
        db.update_user_stat(winner_id, 'duels_won')
        db.update_consecutive_wins(winner_id, True)
        db.update_consecutive_wins(loser_id, False)
        
        winner = bot.get_user(winner_id)
        loser = bot.get_user(loser_id)
        
        embed = discord.Embed(
            title="⚔️ Дуэль завершена!",
            description=f"Победитель: {winner.mention}\nПроигравший: {loser.mention}",
            color=0x00ff00
        )
        embed.add_field(name="Ставка", value=f"{self.bet} {EMOJIS['coin']}", inline=True)
        embed.add_field(name="Выигрыш", value=f"{winnings - self.bet} {EMOJIS['coin']} (чистыми)", inline=True)
        
        # Показываем влияние бафов
        buffs_info = ""
        if challenger_buffs or target_buffs:
            if challenger_buffs:
                buffs_info += f"**{bot.get_user(self.challenger_id).display_name}**: " + ", ".join([f"{buff['item_name']}" for buff in challenger_buffs.values()]) + "\n"
            if target_buffs:
                buffs_info += f"**{bot.get_user(self.target_id).display_name}**: " + ", ".join([f"{buff['item_name']}" for buff in target_buffs.values()])
            embed.add_field(name="🎯 Влияние бафов", value=buffs_info, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label='Отклонить дуэль', style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ Это не ваш вызов на дуэль!", ephemeral=True)
            return
        
        challenger = bot.get_user(self.challenger_id)
        embed = discord.Embed(
            title="⚔️ Дуэль отклонена",
            description=f"{interaction.user.mention} отклонил вызов от {challenger.mention}",
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=None)

# Классы для пагинации
class ItemsPaginatedView(View):
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
        page_items = self.pages[self.current_page]
        embed = discord.Embed(
            title=f"📦 Все доступные предметы (Страница {self.current_page + 1}/{self.total_pages})",
            description="**Предметы автоматически активируются при получении и дают постоянные баффы!**",
            color=0x3498db
        )
        
        for item in page_items:
            try:
                item_id = item[0] if len(item) > 0 else "N/A"
                item_name = item[1] if len(item) > 1 else "Неизвестный предмет"
                item_description = item[2] if len(item) > 2 else "Описание отсутствует"
                item_value = item[3] if len(item) > 3 else 0
                item_rarity = item[4] if len(item) > 4 else "common"
                buff_type = item[5] if len(item) > 5 else None
                buff_value = item[6] if len(item) > 6 else 1.0
                buff_description = item[7] if len(item) > 7 else "Без особого эффекта"
                
                rarity_emoji = {
                    'common': '⚪',
                    'uncommon': '🟢', 
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟠',
                    'mythic': '🟡'
                }.get(item_rarity, '⚪')
                
                effect_details = self.get_effect_details(buff_type, buff_value, buff_description)
                
                field_value = f"**Описание:** {item_description}\n"
                field_value += f"**Эффект:** {effect_details}\n"
                field_value += f"**Ценность:** {item_value} {EMOJIS['coin']}\n"
                field_value += f"**Редкость:** {rarity_emoji} {item_rarity.capitalize()}"
                
                embed.add_field(
                    name=f"{item_name} (ID: {item_id})",
                    value=field_value,
                    inline=False
                )
                
            except Exception as e:
                print(f"⚠️ Ошибка обработки предмета {item}: {e}")
                continue
        
        embed.set_footer(text="💡 Предметы можно получить из кейсов или купить на маркетплейсе")
        return embed

    def get_effect_details(self, buff_type, buff_value, buff_description):
        if not buff_type:
            return "Без особого эффекта"
        
        effect_map = {
            'daily_bonus': f"📅 Увеличивает ежедневную награду в {buff_value}x раза",
            'case_bonus': f"🎁 Увеличивает награды из кейсов в {buff_value}x раза", 
            'game_bonus': f"🎮 Увеличивает выигрыши в играх в {buff_value}x раза",
            'steal_protection': f"🛡️ Уменьшает шанс кражи у вас в {buff_value}x раза",
            'steal_bonus': f"🦹 Увеличивает шанс успешной кражи в {buff_value}x раза",
            'roulette_bonus': f"🎰 Увеличивает выигрыш в рулетке в {buff_value}x раза",
            'multiplier': f"✨ Умножает все награды в {buff_value}x раза",
            'coinflip_bonus': f"🪙 Увеличивает выигрыш в coinflip в {buff_value}x раза",
            'blackjack_bonus': f"🃏 Увеличивает выигрыш в блэкджеке в {buff_value}x раза",
            'slot_bonus': f"🎰 Увеличивает выигрыш в слотах в {buff_value}x раза",
            'loss_protection': f"💎 Уменьшает проигрыши в {buff_value}x раза",
            'quest_bonus': f"🗺️ Увеличивает награды за квесты в {buff_value}x раза",
            'all_bonus': f"🌟 Увеличивает все награды в {buff_value}x раза",
            'transfer_bonus': f"💸 Уменьшает комиссию переводов в {buff_value}x раза",
            'duel_bonus': f"⚔️ Увеличивает шанс победы в дуэлях в {buff_value}x раза",
            'xp_bonus': f"📚 Увеличивает получаемый опыт в {buff_value}x раза",
            'steal_chance': f"🎯 Увеличивает шанс кражи в {buff_value}x раза"
        }
        
        return effect_map.get(buff_type, buff_description)

class MyItemsPaginatedView(View):
    def __init__(self, pages, author_id):
        super().__init__(timeout=120)
        self.pages = pages
        self.current_page = 0
        self.total_pages = len(pages)
        self.author_id = author_id
        self.author_name = "Пользователь"
        self.update_buttons()
        
        try:
            user = bot.get_user(author_id)
            if user:
                self.author_name = user.display_name
        except:
            pass

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
        page_items = self.pages[self.current_page]
        embed = discord.Embed(
            title=f"🎒 Инвентарь {self.author_name} (Страница {self.current_page + 1}/{self.total_pages})",
            description="**Активные предметы автоматически дают бонусы! Самый сильный предмет каждого типа действует.**",
            color=0x3498db
        )
        
        user = bot.get_user(self.author_id)
        self.author_name = user.display_name if user else "Пользователь"
        
        for item_data, count in page_items:
            try:
                item_name = item_data[1] if len(item_data) > 1 else "Неизвестный предмет"
                item_description = item_data[2] if len(item_data) > 2 else "Описание отсутствует"
                item_rarity = item_data[4] if len(item_data) > 4 else "common"
                buff_description = item_data[7] if len(item_data) > 7 else "Без особого эффекта"
                
                rarity_emoji = {
                    'common': '⚪',
                    'uncommon': '🟢', 
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟠',
                    'mythic': '🟡'
                }.get(item_rarity, '⚪')
                
                field_value = f"**Количество:** ×{count}\n"
                field_value += f"**Описание:** {item_description}\n"
                field_value += f"**Эффект:** {buff_description}\n"
                field_value += f"**Редкость:** {rarity_emoji} {item_rarity.capitalize()}"
                
                embed.add_field(
                    name=f"{item_name}",
                    value=field_value,
                    inline=False
                )
                
            except Exception as e:
                print(f"⚠️ Ошибка обработки предмета в инвентаре: {e}")
                continue
        
        try:
            buffs = db.get_user_buffs(self.author_id)
            if buffs:
                buffs_text = "\n".join([f"• **{buff['item_name']}**: {buff['description']}" for buff in buffs.values()])
                embed.add_field(
                    name="🎯 Активные бафы (самые сильные)",
                    value=buffs_text,
                    inline=False
                )
        except Exception as e:
            print(f"⚠️ Ошибка получения бафов: {e}")
        
        embed.set_footer(text="💡 Предметы можно продать на маркетплейсе или использовать для улучшения")
        return embed

# КОМАНДЫ БОТА

# Экономические команды
@bot.tree.command(name="balance", description="Показать ваш баланс")
@app_commands.describe(user="Пользователь, чей баланс показать (опционально)")
async def balance(interaction: discord.Interaction, user: discord.Member = None):
    try:
        user = user or interaction.user
        user_data = db.get_user(user.id)
        user_safe = get_user_data_safe(user_data)
        
        cursor = db.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM achievements WHERE user_id = %s', (user.id,))
        achievements_result = cursor.fetchone()
        achievements_count = achievements_result[0] if achievements_result else 0
        
        buffs = {}
        try:
            buffs = db.get_user_buffs(user.id)
        except Exception as e:
            print(f"⚠️ Ошибка получения бафов для пользователя {user.id}: {e}")
        
        embed = discord.Embed(
            title=f"{EMOJIS['coin']} Баланс {user.display_name}",
            color=0xffd700
        )
        embed.add_field(name="Баланс", value=f"{user_safe['balance']} {EMOJIS['coin']}", inline=True)
        embed.add_field(name="Ежедневная серия", value=f"{user_safe['daily_streak']} дней", inline=True)
        embed.add_field(name="Достижения", value=f"{achievements_count}/{len(ACHIEVEMENTS)}", inline=True)
        
        if buffs:
            buffs_text = "\n".join([f"• {buff['item_name']}: {buff['description']}" for buff in buffs.values()])
            embed.add_field(name="🎯 Активные бафы", value=buffs_text, inline=False)
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Критическая ошибка в команде balance: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка",
            description="Произошла ошибка при получении данных. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="daily", description="Получить ежедневную награду")
async def daily(interaction: discord.Interaction):
    try:
        user_data = db.get_user_safe(interaction.user.id)
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
            await interaction.response.send_message("Вы уже получали ежедневную награду сегодня!", ephemeral=True)
            return
        
        streak = daily_streak + 1 if last_daily and (now - last_daily).days == 1 else 1
        base_reward = 100
        streak_bonus = streak * 10
        reward = base_reward + streak_bonus
        
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
        
        try:
            new_achievements = db.check_achievements(interaction.user.id)
            if new_achievements:
                achievements_text = "\n".join([f"🎉 {ACHIEVEMENTS[ach_id]['name']} (+{ACHIEVEMENTS[ach_id]['reward']} {EMOJIS['coin']})" for ach_id in new_achievements])
                embed.add_field(name="Новые достижения!", value=achievements_text, inline=False)
        except Exception as e:
            print(f"⚠️ Ошибка проверки достижений: {e}")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде daily: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка",
            description="Не удалось получить ежедневную награду. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# Команды кейсов
@bot.tree.command(name="cases", description="Показать список доступных кейсов")
async def cases_list(interaction: discord.Interaction):
    try:
        cases = db.get_cases()
        
        if not cases:
            await interaction.response.send_message("Кейсы не найдены!", ephemeral=True)
            return
        
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

@bot.tree.command(name="admin_boost_chances", description="Повысить шансы во всех кейсах на 3-5% (админ)")
@is_admin()
async def admin_boost_chances(interaction: discord.Interaction):
    try:
        cursor = db.conn.cursor()
        cursor.execute('DELETE FROM cases')
        
        boosted_cases = [
            ('📦 Малый кейс', 50, json.dumps([
                {'type': 'coins', 'amount': [10, 40], 'chance': 0.77, 'description': 'Небольшая сумма монет'},
                {'type': 'coins', 'amount': [41, 100], 'chance': 0.18, 'description': 'Средняя сумма монет'},
                {'type': 'coins', 'amount': [101, 300], 'chance': 0.05, 'description': 'Хорошая сумма монет'}
            ])),
            ('📦 Средний кейс', 150, json.dumps([
                {'type': 'coins', 'amount': [50, 120], 'chance': 0.66, 'description': 'Надежная сумма монет'},
                {'type': 'coins', 'amount': [121, 300], 'chance': 0.2, 'description': 'Отличная сумма монет'},
                {'type': 'special_item', 'name': 'Магический свиток', 'chance': 0.09, 'description': 'Увеличивает выигрыш в рулетке на 25%'},
                {'type': 'coins', 'amount': [301, 800], 'chance': 0.05, 'description': 'Отличный выигрыш'}
            ]))
        ]
        
        for case in boosted_cases:
            cursor.execute('INSERT INTO cases (name, price, rewards) VALUES (%s, %s, %s)', case)
        
        db.conn.commit()
        
        embed = discord.Embed(
            title="✅ Шансы увеличены!",
            description="Во всех кейсах шансы на хорошие награды увеличены на 3-5%, а на плохие уменьшены",
            color=0x00ff00
        )
        embed.add_field(
            name="📊 Основные изменения",
            value="• **Предметы**: +3-5% шанс\n• **Бонусы**: +3% шанс\n• **Минусы**: -3-5% шанс\n• **Монеты**: баланс смещен в сторону средних/больших сумм",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка при увеличении шансов: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка",
            description=f"Не удалось увеличить шансы: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# МИНИ-ИГРЫ
@bot.tree.command(name="coinflip", description="Подбросить монету на ставку (50/50 шанс)")
@app_commands.describe(bet="Ставка в монетах")
async def coinflip(interaction: discord.Interaction, bet: int):
    user_data = db.get_user(interaction.user.id)
    user_safe = get_user_data_safe(user_data)
    
    if user_safe['balance'] < bet:
        await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"🪙 Подбрасывание монеты",
        description=f"Ставка: {bet} {EMOJIS['coin']}\nВыберите сторону монеты:",
        color=0xffd700
    )
    
    view = CoinFlipView(interaction.user.id, bet)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="blackjack", description="Сыграть в блэкджек")
@app_commands.describe(bet="Ставка в монетах")
async def blackjack(interaction: discord.Interaction, bet: int):
    user_data = db.get_user(interaction.user.id)
    user_safe = get_user_data_safe(user_data)
    
    if user_safe['balance'] < bet:
        await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
        return
    
    if bet <= 0:
        await interaction.response.send_message("Ставка должна быть положительной!", ephemeral=True)
        return
    
    view = BlackjackView(interaction.user.id, bet)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="slots", description="Играть в игровые автоматы")
@app_commands.describe(bet="Ставка в монетах")
async def slots(interaction: discord.Interaction, bet: int):
    try:
        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)
        
        if user_safe['balance'] < bet:
            await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
            return
    
        symbols = ['🍒', '🍋', '🍊', '🍇', '🔔', '💎', '7️⃣']
        
        embed = discord.Embed(title="🎰 Игровые автоматы", description="Вращение...", color=0xff69b4)
        await interaction.response.send_message(embed=embed)
        
        for i in range(3):
            await asyncio.sleep(0.5)
            slot_result = [random.choice(symbols) for _ in range(3)]
            embed.description = f"🎰 | {' | '.join(slot_result)} | 🎰"
            await interaction.edit_original_response(embed=embed)
        
        await asyncio.sleep(1)
        
        final_result = []
        if random.random() < 0.4:
            winning_symbol = random.choice(symbols)
            if random.random() < 0.1:
                final_result = [winning_symbol, winning_symbol, winning_symbol]
            else:
                final_result = [winning_symbol, winning_symbol, random.choice(symbols)]
                random.shuffle(final_result)
        else:
            final_result = [random.choice(symbols) for _ in range(3)]
        
        embed.description = f"🎰 | {' | '.join(final_result)} | 🎰"
        
        if final_result[0] == final_result[1] == final_result[2]:
            if final_result[0] == '💎':
                multiplier = 50
                db.update_user_stat(interaction.user.id, 'slot_wins')
            elif final_result[0] == '7️⃣':
                multiplier = 25
            elif final_result[0] == '🔔':
                multiplier = 15
            else:
                multiplier = 8
            
            base_winnings = bet * multiplier
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'slot_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings)
            db.log_transaction(interaction.user.id, 'slots_win', winnings, description=f"ДЖЕКПОТ в слотах x{multiplier}")
            db.update_consecutive_wins(interaction.user.id, True)
            
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
            db.update_consecutive_wins(interaction.user.id, True)
            
            result_text = f"✅ Два в ряд! x{multiplier}\nВыигрыш: {winnings} {EMOJIS['coin']}"
            color = 0x00ff00
        else:
            loss = db.apply_buff_to_amount(interaction.user.id, bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'slots_loss', -loss, description="Проигрыш в слотах")
            db.update_consecutive_wins(interaction.user.id, False)
            
            result_text = f"❌ Повезет в следующий раз!\nПотеряно: {loss} {EMOJIS['coin']}"
            color = 0xff0000
        
        embed.add_field(name="Результат", value=result_text, inline=False)
        embed.add_field(name="Ставка", value=f"{bet} {EMOJIS['coin']}", inline=True)
        embed.color = color
        
        await interaction.edit_original_response(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде slots: {e}")
        await interaction.response.send_message("❌ Произошла ошибка в слотах!", ephemeral=True)

@bot.tree.command(name="roulette", description="Сыграть в рулетку")
@app_commands.describe(bet="Ставка в монетах")
async def roulette(interaction: discord.Interaction, bet: int):
    try:
        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)
        
        if user_safe['balance'] < bet:
            await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
            return
        
        winning_number = random.randint(0, 36)
        user_number = random.randint(0, 36)
        
        embed = discord.Embed(title="🎰 Рулетка вращается...", color=0xffd700)
        await interaction.response.send_message(embed=embed)
        
        for i in range(3):
            await asyncio.sleep(1)
            embed.description = "⏳" * (i + 1)
            await interaction.edit_original_response(embed=embed)
        
        await asyncio.sleep(1)
        
        if user_number == winning_number:
            multiplier = 35
            base_winnings = bet * multiplier
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'roulette_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings)
            db.log_transaction(interaction.user.id, 'roulette_win', winnings, description="Победа в рулетке")
            db.update_user_stat(interaction.user.id, 'roulette_wins')
            db.update_consecutive_wins(interaction.user.id, True)
            
            result_text = f"🎉 ДЖЕКПОТ! Ваше число: {user_number}\nВыпало: {winning_number}\nВыигрыш: {winnings} {EMOJIS['coin']} (x{multiplier})"
            color = 0x00ff00
        else:
            loss = db.apply_buff_to_amount(interaction.user.id, bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'roulette_loss', -loss, description="Проигрыш в рулетке")
            db.update_consecutive_wins(interaction.user.id, False)
            
            result_text = f"💀 Проигрыш! Ваше число: {user_number}\nВыпало: {winning_number}\nПотеряно: {loss} {EMOJIS['coin']}"
            color = 0xff0000
        
        embed = discord.Embed(
            title=f"🎰 Рулетка - Ставка: {bet} {EMOJIS['coin']}",
            description=result_text,
            color=color
        )
        await interaction.edit_original_response(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде roulette: {e}")
        await interaction.response.send_message("❌ Произошла ошибка в рулетке!", ephemeral=True)

# ДУЭЛЬ
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
    user_safe = get_user_data_safe(user_data)
    
    if user_safe['balance'] < bet:
        await interaction.response.send_message("У вас недостаточно монет для дуэли!", ephemeral=True)
        return
    
    target_data = db.get_user(user.id)
    target_safe = get_user_data_safe(target_data)
    
    if target_safe['balance'] < bet:
        await interaction.response.send_message(f"У {user.mention} недостаточно монет для дуэли!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"{EMOJIS['duel']} Вызов на дуэль!",
        description=f"{interaction.user.mention} вызывает {user.mention} на дуэль!",
        color=0xff0000
    )
    embed.add_field(name="Ставка", value=f"{bet} {EMOJIS['coin']}", inline=True)
    
    challenger_buffs = db.get_user_buffs(interaction.user.id)
    target_buffs = db.get_user_buffs(user.id)
    
    if challenger_buffs or target_buffs:
        buffs_text = ""
        if challenger_buffs:
            buffs_text += f"**{interaction.user.display_name}**: " + ", ".join([f"{buff['item_name']}" for buff in challenger_buffs.values()]) + "\n"
        if target_buffs:
            buffs_text += f"**{user.display_name}**: " + ", ".join([f"{buff['item_name']}" for buff in target_buffs.values()])
        embed.add_field(name="🎯 Активные бафы", value=buffs_text, inline=False)
    
    embed.add_field(name="Время на ответ", value="30 секунд", inline=True)
    embed.set_footer(text="Победитель забирает всю ставку!")
    
    view = DuelView(interaction.user.id, user.id, bet)
    await interaction.response.send_message(embed=embed, view=view)

# КРАЖА
@bot.tree.command(name="steal", description="Попытаться украсть монеты у другого пользователя (КД 30 мин)")
@app_commands.describe(user="Пользователь, у которого крадем")
@app_commands.checks.cooldown(1, 1800.0, key=lambda i: (i.guild_id, i.user.id))
async def steal(interaction: discord.Interaction, user: discord.Member):
    if user.id == interaction.user.id:
        await interaction.response.send_message("Нельзя красть у себя!", ephemeral=True)
        return
    
    thief_data = db.get_user(interaction.user.id)
    thief_safe = get_user_data_safe(thief_data)
    target_data = db.get_user(user.id)
    target_safe = get_user_data_safe(target_data)
    
    if thief_safe['balance'] < 10:
        await interaction.response.send_message("Нужно минимум 10 монет для кражи!", ephemeral=True)
        return
    
    if target_safe['balance'] < 10:
        await interaction.response.send_message("У цели недостаточно монет для кражи!", ephemeral=True)
        return
    
    max_steal = min(int(target_safe['balance'] * 0.2), 1000)
    min_steal = max(int(target_safe['balance'] * 0.05), 10)
    
    if max_steal < min_steal:
        amount = min_steal
    else:
        amount = random.randint(min_steal, max_steal)
    
    base_success_chance = 0.3
    success_chance = db.apply_buff_to_chance(interaction.user.id, base_success_chance, 'steal_chance')
    success_chance = db.apply_buff_to_chance(interaction.user.id, success_chance, 'steal_bonus')
    
    target_protection = db.apply_buff_to_chance(user.id, 1.0, 'steal_protection')
    success_chance = success_chance * (1 - target_protection)
    
    if random.random() <= success_chance:
        stolen_amount = db.apply_buff_to_amount(interaction.user.id, amount, 'multiplier')
        stolen_amount = db.apply_buff_to_amount(interaction.user.id, stolen_amount, 'all_bonus')
        
        db.update_balance(interaction.user.id, stolen_amount)
        db.update_balance(user.id, -amount)
        db.log_transaction(interaction.user.id, 'steal', stolen_amount, user.id, "Успешная кража")
        db.update_user_stat(interaction.user.id, 'steals_successful')
        db.update_consecutive_wins(interaction.user.id, True)
        
        embed = discord.Embed(
            title=f"{EMOJIS['steal']} Успешная кража!",
            description=f"{interaction.user.mention} украл {stolen_amount} {EMOJIS['coin']} у {user.mention}!",
            color=0x00ff00
        )
        embed.add_field(name="Шанс успеха", value=f"{success_chance*100:.1f}%")
    else:
        penalty = min(amount // 2, 100)
        actual_penalty = db.apply_buff_to_amount(interaction.user.id, penalty, 'loss_protection')
        
        db.update_balance(interaction.user.id, -actual_penalty)
        db.log_transaction(interaction.user.id, 'steal_fail', -actual_penalty, user.id, "Неудачная кража")
        db.update_user_stat(interaction.user.id, 'steals_failed')
        db.update_consecutive_wins(interaction.user.id, False)
        
        embed = discord.Embed(
            title=f"{EMOJIS['lose']} Кража провалилась!",
            description=f"{interaction.user.mention} оштрафован на {actual_penalty} {EMOJIS['coin']}!",
            color=0xff0000
        )
        embed.add_field(name="Шанс успеха", value=f"{success_chance*100:.1f}%")
    
    await interaction.response.send_message(embed=embed)

@steal.error
async def steal_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        
        await interaction.response.send_message(
            f"❌ Следующую кражу можно совершить через {minutes} минут {seconds:02d} секунд",
            ephemeral=True
        )
    else:
        raise error

# ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ
@bot.tree.command(name="items", description="Показать все доступные предметы с эффектами")
async def items_list(interaction: discord.Interaction):
    try:
        items = db.get_all_items_safe()
        
        if not items:
            await interaction.response.send_message("❌ Предметы не найдены!", ephemeral=True)
            return
        
        items_per_page = 5
        pages = []
        
        for i in range(0, len(items), items_per_page):
            page_items = items[i:i + items_per_page]
            pages.append(page_items)
        
        view = ItemsPaginatedView(pages, interaction.user.id)
        embed = view.create_embed()
        
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        print(f"❌ Ошибка в команде items: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке предметов!", ephemeral=True)

@bot.tree.command(name="myitems", description="Показать ваши предметы с эффектами")
async def my_items(interaction: discord.Interaction):
    try:
        inventory = db.get_user_inventory_safe(interaction.user.id)
        
        items = inventory.get("items", {})
        if not items:
            embed = discord.Embed(
                title=f"📦 Предметы {interaction.user.display_name}",
                description="У вас пока нет предметов. Открывайте кейсы или покупайте на маркетплейсе!",
                color=0x3498db
            )
            await interaction.response.send_message(embed=embed)
            return
        
        user_items = []
        for item_id, count in items.items():
            try:
                if item_id.isdigit():
                    item_data = db.get_item(int(item_id))
                    if item_data:
                        user_items.append((item_data, count))
            except Exception as e:
                print(f"⚠️ Ошибка обработки предмета {item_id}: {e}")
                continue
        
        if not user_items:
            embed = discord.Embed(
                title=f"📦 Предметы {interaction.user.display_name}",
                description="Не удалось загрузить информацию о ваших предметах.",
                color=0x3498db
            )
            await interaction.response.send_message(embed=embed)
            return
        
        items_per_page = 5
        pages = []
        
        for i in range(0, len(user_items), items_per_page):
            page_items = user_items[i:i + items_per_page]
            pages.append(page_items)
        
        view = MyItemsPaginatedView(pages, interaction.user.id)
        embed = view.create_embed()
        
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        print(f"❌ Ошибка в команде myitems: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке предметов!", ephemeral=True)

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
    sender_safe = get_user_data_safe(sender_data)
    
    if sender_safe['balance'] < amount:
        await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
        return
    
    transfer_amount = db.apply_buff_to_amount(interaction.user.id, amount, 'transfer_bonus')
    
    db.update_balance(interaction.user.id, -transfer_amount)
    db.update_balance(user.id, amount)
    db.log_transaction(interaction.user.id, 'transfer', -transfer_amount, user.id, f"Перевод {user.name}")
    db.log_transaction(user.id, 'transfer', amount, interaction.user.id, f"Получено от {interaction.user.name}")
    
    embed = discord.Embed(
        title=f"{EMOJIS['coin']} Перевод средств",
        description=f"{interaction.user.mention} → {user.mention}",
        color=0x00ff00
    )
    embed.add_field(name="Сумма", value=f"{amount} {EMOJIS['coin']}")
    if transfer_amount < amount:
        embed.add_field(name="Комиссия", value=f"-{amount - transfer_amount} {EMOJIS['coin']} (баф)")
    
    await interaction.response.send_message(embed=embed)

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
    user_safe = get_user_data_safe(user_data)
    
    if user_safe['balance'] < case_data[2]:
        await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
        return
    
    db.get_user(user.id)
    
    db.update_balance(interaction.user.id, -case_data[2])
    db.add_case_to_inventory(user.id, case_id, case_data[1], "gifted")
    db.log_transaction(interaction.user.id, 'gift_case', -case_data[2], user.id, f"Подарок: {case_data[1]}")
    db.update_user_stat(interaction.user.id, 'gifts_sent')
    
    embed = discord.Embed(
        title="🎁 Кейс в подарок!",
        description=f"{interaction.user.mention} подарил {case_data[1]} пользователю {user.mention}!",
        color=0xff69b4
    )
    embed.add_field(name="💼 Получатель", value=f"Кейс добавлен в инвентарь {user.mention}")
    embed.add_field(name="📦 Кейс", value=f"{case_data[1]}")
    embed.add_field(name="💰 Стоимость", value=f"{case_data[2]} {EMOJIS['coin']}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="openmycase", description="Открыть кейс из вашего инвентаря")
@app_commands.describe(case_id="ID кейса из инвентаря")
async def openmycase(interaction: discord.Interaction, case_id: int):
    db.get_user(interaction.user.id)
    
    inventory_data = db.get_user_inventory(interaction.user.id)
    case_key = f"case_{case_id}"
    
    if case_key not in inventory_data.get("cases", {}):
        await interaction.response.send_message("У вас нет такого кейса в инвентаре!", ephemeral=True)
        return
    
    case_data = db.get_case(case_id)
    if not case_data:
        await interaction.response.send_message("Кейс не найден в базе данных!", ephemeral=True)
        return
    
    db.remove_case_from_inventory(interaction.user.id, case_id)
    
    case = {
        'name': case_data[1],
        'price': case_data[2],
        'rewards': json.loads(case_data[3])
    }
    
    embed = discord.Embed(title="🎰 Открытие кейса...", color=0xffd700)
    await interaction.response.send_message(embed=embed)
    
    for i in range(3):
        await asyncio.sleep(1)
        embed.description = "🎁" * (i + 1)
        await interaction.edit_original_response(embed=embed)
    
    def get_reward(case):
        rewards = case['rewards']
        rand = random.random()
        current = 0
        for reward in rewards:
            current += reward['chance']
            if rand <= current:
                return reward
        return rewards[0]

    async def process_reward(user, reward, case):
        user_id = user.id
        if reward['type'] == 'coins':
            amount = random.randint(reward['amount'][0], reward['amount'][1])
            amount = db.apply_buff_to_amount(user_id, amount, 'case_bonus')
            amount = db.apply_buff_to_amount(user_id, amount, 'multiplier')
            amount = db.apply_buff_to_amount(user_id, amount, 'all_bonus')
            db.update_balance(user_id, amount)
            db.log_transaction(user_id, 'case_reward', amount, description=f"Кейс: {case['name']}")
            return f"Монеты: {amount} {EMOJIS['coin']}"

        elif reward['type'] == 'special_item':
            item_name = reward['name']
            db.add_item_to_inventory(user_id, item_name)
            return f"Предмет: {item_name}"

        elif reward['type'] == 'bonus':
            amount = case['price'] * reward['multiplier']
            db.update_balance(user_id, amount)
            db.log_transaction(user_id, 'case_bonus', amount, description=f"Бонус из кейса: {case['name']}")
            return f"Бонус: {amount} {EMOJIS['coin']} (x{reward['multiplier']})"

        else:
            return "Ничего"

    reward = get_reward(case)
    reward_text = await process_reward(interaction.user, reward, case)
    
    db.update_user_stat(interaction.user.id, 'cases_opened')
    
    embed = discord.Embed(
        title=f"🎉 {case['name']} открыт!",
        description=reward_text,
        color=0x00ff00
    )
    embed.set_footer(text="Кейс из инвентаря")
    
    await interaction.edit_original_response(embed=embed)

@bot.tree.command(name="market", description="Взаимодействие с маркетплейсом")
@app_commands.describe(action="Действие на маркетплейсе", item_name="Название предмета", price="Цена")
@app_commands.choices(action=[
    app_commands.Choice(name="📋 Список товаров", value="list"),
    app_commands.Choice(name="💰 Продать предмет", value="sell"),
    app_commands.Choice(name="🛒 Купить предмет", value="buy")
])
async def market(interaction: discord.Interaction, action: app_commands.Choice[str], item_name: str = None, price: int = None):
    try:
        if action.value == "list":
            cursor = db.conn.cursor()
            cursor.execute('SELECT id, seller_id, item_name, price FROM market LIMIT 10')
            items = cursor.fetchall()
            
            embed = discord.Embed(title="🏪 Маркетплейс", color=0x00ff00)
            
            if not items:
                embed.description = "На маркетплейсе пока нет товаров."
            else:
                for item in items:
                    item_id = item[0] if len(item) > 0 else "N/A"
                    seller_id = item[1] if len(item) > 1 else None
                    item_name_db = item[2] if len(item) > 2 else "Неизвестный предмет"
                    item_price = item[3] if len(item) > 3 else 0
                    
                    seller = bot.get_user(seller_id) if seller_id else None
                    
                    buff_info = ""
                    try:
                        item_data = db.get_item_by_name(item_name_db)
                        if item_data and len(item_data) > 7 and item_data[7]:
                            buff_info = f" - {item_data[7]}"
                    except Exception as e:
                        print(f"⚠️ Ошибка получения информации о предмете {item_name_db}: {e}")
                    
                    embed.add_field(
                        name=f"#{item_id} {item_name_db}{buff_info}",
                        value=f"Цена: {item_price} {EMOJIS['coin']}\nПродавец: {seller.name if seller else 'Неизвестно'}",
                        inline=False
                    )
            
            await interaction.response.send_message(embed=embed)
        
        elif action.value == "sell":
            if not item_name or not price:
                await interaction.response.send_message("Укажите название предмета и цену!", ephemeral=True)
                return
            
            if price <= 0:
                await interaction.response.send_message("Цена должна быть положительной!", ephemeral=True)
                return
            
            inventory = db.get_user_inventory(interaction.user.id)
            item_found = False
            
            for item_id, count in inventory.get("items", {}).items():
                try:
                    item_data = db.get_item(int(item_id))
                    if item_data and len(item_data) > 1 and item_data[1] == item_name:
                        item_found = True
                        break
                except (ValueError, IndexError) as e:
                    print(f"⚠️ Ошибка обработки предмета {item_id}: {e}")
                    continue
            
            if not item_found:
                await interaction.response.send_message("❌ У вас нет этого предмета в инвентаре.", ephemeral=True)
                return
            
            cursor = db.conn.cursor()
            cursor.execute('INSERT INTO market (seller_id, item_name, price) VALUES (%s, %s, %s)', 
                          (interaction.user.id, item_name, price))
            db.conn.commit()
            db.update_user_stat(interaction.user.id, 'market_sales')
            
            db.remove_item_from_inventory(interaction.user.id, item_name)
            
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
            
            try:
                item_id = int(item_name)
            except ValueError:
                await interaction.response.send_message("ID предмета должен быть числом!", ephemeral=True)
                return
            
            cursor = db.conn.cursor()
            cursor.execute('SELECT id, seller_id, item_name, price FROM market WHERE id = %s', (item_id,))
            item = cursor.fetchone()
            
            if not item:
                await interaction.response.send_message("Предмет не найден!", ephemeral=True)
                return
            
            market_item_id = item[0] if len(item) > 0 else None
            seller_id = item[1] if len(item) > 1 else None
            market_item_name = item[2] if len(item) > 2 else "Неизвестный предмет"
            item_price = item[3] if len(item) > 3 else 0
            
            if not seller_id:
                await interaction.response.send_message("Ошибка: продавец не найден!", ephemeral=True)
                return
            
            user_data = db.get_user(interaction.user.id)
            user_safe = get_user_data_safe(user_data)
            
            if user_safe['balance'] < item_price:
                await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
                return
            
            db.update_balance(interaction.user.id, -item_price)
            db.update_balance(seller_id, item_price)
            
            db.add_item_to_inventory(interaction.user.id, market_item_name)
            
            cursor.execute('DELETE FROM market WHERE id = %s', (market_item_id,))
            db.conn.commit()
            
            db.log_transaction(interaction.user.id, 'market_buy', -item_price, seller_id, f"Покупка: {market_item_name}")
            db.log_transaction(seller_id, 'market_sell', item_price, interaction.user.id, f"Продажа: {market_item_name}")
            
            buff_info = ""
            try:
                item_data = db.get_item_by_name(market_item_name)
                if item_data and len(item_data) > 7 and item_data[7]:
                    buff_info = f"\n**Эффект:** {item_data[7]}"
            except Exception as e:
                print(f"⚠️ Ошибка получения бафа предмета {market_item_name}: {e}")
            
            embed = discord.Embed(
                title="🏪 Покупка совершена!",
                description=f"Вы купили **{market_item_name}** за {item_price} {EMOJIS['coin']}{buff_info}",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)
    
    except Exception as e:
        print(f"❌ Критическая ошибка в команде market: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка маркетплейса",
            description="Произошла ошибка при выполнении команды. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="inventory", description="Показать ваш инвентарь")
async def inventory(interaction: discord.Interaction):
    try:
        inventory_data = db.get_user_inventory_safe(interaction.user.id)
        
        embed = discord.Embed(
            title=f"🎒 Инвентарь {interaction.user.display_name}",
            color=0x3498db
        )
        
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
        
        buffs = db.get_user_buffs(interaction.user.id)
        if buffs:
            buffs_text = "\n".join([f"• **{buff['item_name']}**: {buff['description']}" for buff in buffs.values()])
            embed.add_field(name="🎯 Активные бафы", value=buffs_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде inventory: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке инвентаря!", ephemeral=True)

# КВЕСТЫ И ДОСТИЖЕНИЯ
@bot.tree.command(name="quest", description="Получить случайный квест")
@app_commands.checks.cooldown(1, 10800.0)
async def quest_command(interaction: discord.Interaction):
    try:
        if not QUESTS:
            await interaction.response.send_message("❌ В системе пока нет доступных квестов!", ephemeral=True)
            return
        
        quest_id, quest_data = random.choice(list(QUESTS.items()))
        
        success = db.add_user_quest(interaction.user.id, quest_id)
        
        if success:
            base_reward = quest_data['reward']
            reward = db.apply_buff_to_amount(interaction.user.id, base_reward, 'quest_bonus')
            reward = db.apply_buff_to_amount(interaction.user.id, reward, 'multiplier')
            reward = db.apply_buff_to_amount(interaction.user.id, reward, 'all_bonus')
            
            embed = discord.Embed(
                title=f"{EMOJIS['quest']} Новый квест!",
                description=quest_data['description'],
                color=0x00ff00
            )
            embed.add_field(name="Награда", value=f"{reward} {EMOJIS['coin']}")
            embed.set_footer(text="Используйте /quests чтобы посмотреть ваши квесты")
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Не удалось выдать квест! Возможно, он у вас уже есть.", ephemeral=True)
            
    except Exception as e:
        print(f"❌ Ошибка в команде quest: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка получения квеста",
            description="Произошла ошибка при получении квеста. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@quest_command.error
async def quest_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        hours = int(error.retry_after // 3600)
        minutes = int((error.retry_after % 3600) // 60)
        
        await interaction.response.send_message(
            f"❌ Следующий квест можно получить через {hours} часов {minutes} минут",
            ephemeral=True
        )
    else:
        raise error

@bot.tree.command(name="quests", description="Показать ваши активные квесты")
async def show_quests(interaction: discord.Interaction):
    try:
        user_quests = db.get_user_quests(interaction.user.id)
        
        embed = discord.Embed(title=f"{EMOJIS['quest']} Ваши квесты", color=0x9b59b6)
        
        if not user_quests:
            embed.description = "У вас пока нет активных квестов. Используйте `/quest` чтобы получить новый!"
            await interaction.response.send_message(embed=embed)
            return
        
        completed_quests = 0
        for quest_row in user_quests:
            quest_id = quest_row[0] if len(quest_row) > 0 else None
            progress = quest_row[1] if len(quest_row) > 1 else 0
            completed = quest_row[2] if len(quest_row) > 2 else False
            
            if quest_id and quest_id in QUESTS:
                quest_data = QUESTS[quest_id]
                status = "✅" if completed else f"📊 Прогресс: {progress}%"
                embed.add_field(
                    name=f"{status} {quest_data['name']}",
                    value=f"{quest_data['description']}\nНаграда: {quest_data['reward']} {EMOJIS['coin']}",
                    inline=False
                )
                if completed:
                    completed_quests += 1
        
        embed.set_footer(text=f"Завершено: {completed_quests}/{len(user_quests)}")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде quests: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка загрузки квестов",
            description="Произошла ошибка при загрузке ваших квестов. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="achievements", description="Показать ваши достижения")
async def show_achievements(interaction: discord.Interaction):
    try:
        cursor = db.conn.cursor()
        cursor.execute('SELECT achievement_id FROM achievements WHERE user_id = %s', (interaction.user.id,))
        user_achievements_result = cursor.fetchall()
        
        user_achievements = []
        for row in user_achievements_result:
            if row and len(row) > 0:
                user_achievements.append(row[0])
        
        embed = discord.Embed(title="🏅 Ваши достижения", color=0xffd700)
        
        unlocked_count = 0
        achievements_list = []
        
        for achievement_id, achievement in ACHIEVEMENTS.items():
            status = "✅" if achievement_id in user_achievements else "❌"
            if achievement_id in user_achievements:
                unlocked_count += 1
                
            achievements_list.append(
                f"{status} **{achievement['name']}**\n{achievement['description']}\nНаграда: {achievement['reward']} {EMOJIS['coin']}\n"
            )
        
        if achievements_list:
            pages = []
            current_page = ""
            
            for achievement in achievements_list:
                if len(current_page) + len(achievement) > 2000:
                    pages.append(current_page)
                    current_page = achievement
                else:
                    current_page += achievement
            
            if current_page:
                pages.append(current_page)
            
            if len(pages) == 1:
                embed.description = pages[0]
                await interaction.response.send_message(embed=embed)
            else:
                class AchievementsPaginatedView(View):
                    def __init__(self, pages, author_id, unlocked_count, total_count):
                        super().__init__(timeout=120)
                        self.pages = pages
                        self.current_page = 0
                        self.total_pages = len(pages)
                        self.author_id = author_id
                        self.unlocked_count = unlocked_count
                        self.total_count = total_count
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
                        embed = discord.Embed(
                            title=f"🏅 Ваши достижения (Страница {self.current_page + 1}/{self.total_pages})",
                            description=self.pages[self.current_page],
                            color=0xffd700
                        )
                        embed.set_footer(text=f"Разблокировано: {self.unlocked_count}/{self.total_count}")
                        return embed
                
                view = AchievementsPaginatedView(pages, interaction.user.id, unlocked_count, len(ACHIEVEMENTS))
                embed = view.create_embed()
                await interaction.response.send_message(embed=embed, view=view)
        else:
            embed.description = "У вас пока нет достижений. Продолжайте играть, чтобы их получить!"
            embed.set_footer(text="Используйте команды бота для получения достижений")
            await interaction.response.send_message(embed=embed)
            
    except Exception as e:
        print(f"❌ Ошибка в команде achievements: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка загрузки достижений",
            description="Произошла ошибка при загрузке ваших достижений. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="stats", description="Показать вашу статистику")
async def stats(interaction: discord.Interaction):
    cursor = db.conn.cursor()
    cursor.execute('SELECT * FROM user_stats WHERE user_id = %s', (interaction.user.id,))
    stats_data = cursor.fetchone()
    
    if not stats_data:
        cursor.execute('INSERT INTO user_stats (user_id) VALUES (%s)', (interaction.user.id,))
        db.conn.commit()
        cursor.execute('SELECT * FROM user_stats WHERE user_id = %s', (interaction.user.id,))
        stats_data = cursor.fetchone()
    
    buffs = db.get_user_buffs(interaction.user.id)
    
    embed = discord.Embed(title="📊 Ваша статистика", color=0x3498db)
    
    embed.add_field(
        name="🎮 Игровая статистика",
        value=f"**Кейсы открыто:** {stats_data[1]}\n"
              f"**Дуэлей выиграно:** {stats_data[2]}\n"
              f"**Успешных краж:** {stats_data[3]}\n"
              f"**Неудачных краж:** {stats_data[4]}",
        inline=False
    )
    
    embed.add_field(
        name="🎰 Статистика игр",
        value=f"**Побед в рулетке:** {stats_data[5]}\n"
              f"**Побед в слотах:** {stats_data[6]}\n"
              f"**Побед в блэкджеке:** {stats_data[7]}\n"
              f"**Побед в coinflip:** {stats_data[8]}",
        inline=False
    )
    
    embed.add_field(
        name="📈 Другая статистика",
        value=f"**Ежедневных наград:** {stats_data[9]}\n"
              f"**Всего заработано:** {stats_data[10]} {EMOJIS['coin']}\n"
              f"**Продаж на маркете:** {stats_data[11]}\n"
              f"**Подарков отправлено:** {stats_data[12]}\n"
              f"**Предметов собрано:** {stats_data[14]}",
        inline=False
    )
    
    if buffs:
        buffs_text = "\n".join([f"• **{buff['item_name']}**: {buff['description']}" for buff in buffs.values()])
        embed.add_field(name="🎯 Активные бафы", value=buffs_text, inline=False)
    
    await interaction.response.send_message(embed=embed)

# ЛИДЕРБОРДЫ
@bot.tree.command(name="leaderboard", description="Показать таблицу лидеров")
@app_commands.describe(type="Тип лидерборда")
@app_commands.choices(type=[
    app_commands.Choice(name="💰 Баланс", value="balance"),
    app_commands.Choice(name="🏆 Победы", value="wins"),
    app_commands.Choice(name="🦹 Кражи", value="steals"),
    app_commands.Choice(name="🎁 Кейсы", value="cases"),
    app_commands.Choice(name="🏅 Достижения", value="achievements"),
    app_commands.Choice(name="📦 Предметы", value="items")
])
async def leaderboard(interaction: discord.Interaction, type: app_commands.Choice[str]):
    cursor = db.conn.cursor()
    
    if type.value == 'balance':
        cursor.execute('SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10')
        title = "💰 Лидеры по балансу"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, balance) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{balance} {EMOJIS['coin']}",
                inline=False
            )
    
    elif type.value == 'wins':
        cursor.execute('''
            SELECT user_id, 
                   (COALESCE(roulette_wins, 0) + COALESCE(duels_won, 0) + COALESCE(slot_wins, 0) + 
                    COALESCE(blackjack_wins, 0) + COALESCE(coinflip_wins, 0)) as total_wins 
            FROM user_stats 
            ORDER BY total_wins DESC LIMIT 10
        ''')
        title = "🏆 Лидеры по победам"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, wins) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{wins} побед",
                inline=False
            )
    
    elif type.value == 'steals':
        cursor.execute('SELECT user_id, steals_successful FROM user_stats ORDER BY steals_successful DESC LIMIT 10')
        title = "🦹 Лидеры по кражам"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, steals) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{steals} краж",
                inline=False
            )
    
    elif type.value == 'cases':
        cursor.execute('SELECT user_id, cases_opened FROM user_stats ORDER BY cases_opened DESC LIMIT 10')
        title = "🎁 Лидеры по кейсам"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, cases) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{cases} кейсов",
                inline=False
            )
    
    elif type.value == 'achievements':
        cursor.execute('''
            SELECT user_id, COUNT(*) as achievement_count 
            FROM achievements 
            GROUP BY user_id 
            ORDER BY achievement_count DESC LIMIT 10
        ''')
        title = "🏅 Лидеры по достижениям"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, achievements_count) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{achievements_count} достижений",
                inline=False
            )
    
    elif type.value == 'items':
        cursor.execute('SELECT user_id, items_collected FROM user_stats ORDER BY items_collected DESC LIMIT 10')
        title = "📦 Лидеры по предметам"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, items) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{items} предметов",
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)

# АДМИН-КОМАНДЫ
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
        item_data = db.get_item_by_name(item_name)
        if not item_data:
            all_items = db.get_all_items()
            item_list = "\n".join([f"• {item[1]}" for item in all_items[:10]])
            if len(all_items) > 10:
                item_list += f"\n• ... и ещё {len(all_items) - 10} предметов"
            
            embed = discord.Embed(
                title="❌ Предмет не найден",
                description=f"Доступные предметы:\n{item_list}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        db.add_item_to_inventory(user.id, item_name)
        
        embed = discord.Embed(
            title="⚙️ Админ действие",
            description=f"Предмет '{item_name}' выдан пользователю {user.mention}",
            color=0x00ff00
        )
        buff_description = item_data[7] if len(item_data) > 7 and item_data[7] else "Нет бафа"
        embed.add_field(name="Эффект", value=buff_description)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_createcase", description="Создать новый кейс (админ)")
@app_commands.describe(name="Название кейса", price="Цена кейса", rewards_json="Награды в формате JSON")
@is_admin()
async def admin_createcase(interaction: discord.Interaction, name: str, price: int, rewards_json: str):
    try:
        rewards = json.loads(rewards_json)
        cursor = db.conn.cursor()
        cursor.execute('INSERT INTO cases (name, price, rewards) VALUES (%s, %s, %s) RETURNING id', 
                      (name, price, json.dumps(rewards)))
        case_id = cursor.fetchone()[0]
        db.conn.commit()
        
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

@bot.tree.command(name="admin_viewtransactions", description="Просмотр транзакций (админ)")
@app_commands.describe(user="Пользователь (опционально)")
@is_admin()
async def admin_viewtransactions(interaction: discord.Interaction, user: discord.Member = None):
    try:
        cursor = db.conn.cursor()
        
        if user:
            cursor.execute('SELECT * FROM transactions WHERE user_id = %s OR target_user_id = %s ORDER BY timestamp DESC LIMIT 10', (user.id, user.id))
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

# КОМАНДА ПОМОЩИ
@bot.tree.command(name="help", description="Показать информацию о боте и список команд")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Экономический Бот - Помощь",
        description="Добро пожаловать в экономическую игру! Этот бот предоставляет полную систему экономики с кейсами, мини-играми, маркетплейсом, достижениями и системой бафов.",
        color=0x3498db
    )
    
    embed.add_field(
        name="📊 О боте",
        value="• Внутренняя валюта: монеты 🪙\n• Ежедневные бонусы 📅\n• Система кейсов 🎁\n• Маркетплейс 🏪\n• Мини-игры 🎰\n• Достижения 🏅\n• Система бафов 🎯",
        inline=False
    )
    
    embed.add_field(
        name="💰 Экономические команды",
        value="""**/balance** [пользователь] - Показать баланс и активные бафы
**/daily** - Получить ежедневную награду (учитывает бафы)
**/pay** @пользователь сумма - Перевести монеты
**/inventory** - Показать инвентарь и активные бафы
**/stats** - Показать статистику""",
        inline=False
    )
    
    embed.add_field(
        name="🎁 Команды кейсов",
        value="""**/cases** - Список доступных кейсов
**/open_case** ID_кейса - Купить и открыть кейс
**/openmycase** ID_кейса - Открыть кейс из инвентаря
**/giftcase** @пользователь ID_кейса - Подарить кейс""",
        inline=False
    )
    
    embed.add_field(
        name="🏪 Маркетплейс",
        value="""**/market** list - Список товаров
**/market** sell название_предмета цена - Продать предмет
**/market** buy ID_товара - Купить товар (баф сохраняется)""",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Мини-игры",
        value="""**/roulette** ставка - Игра в рулетку (учитывает бафы)
**/slots** ставка - Игровые автоматы (учитывает бафы)
**/blackjack** ставка - Игра в блэкджек (учитывает бафы)
**/coinflip** ставка - Подбрасывание монеты (50/50, учитывает бафы)
**/duel** @пользователь ставка - Дуэль с игроком (учитывает бафы)
**/quest** - Получить случайный квест (КД 3 часа)
**/steal** @пользователь - Попытаться украсть монеты (учитывает бафы, КД 30 мин)""",
        inline=False
    )
    
    embed.add_field(
        name="🏅 Достижения и лидерборды",
        value="""**/leaderboard** balance - Лидеры по балансу
**/leaderboard** wins - Лидеры по победам
**/leaderboard** steals - Лидеры по кражам
**/leaderboard** cases - Лидеры по кейсам
**/leaderboard** achievements - Лидеры по достижениям
**/leaderboard** items - Лидеры по предметам
**/achievements** - Ваши достижения""",
        inline=False
    )
    
    if interaction.user.id in ADMIN_IDS:
        embed.add_field(
            name="⚙️ Админ-команды",
            value="""**/admin_addcoins** @пользователь сумма - Добавить монеты
**/admin_removecoins** @пользователь сумма - Забрать монеты
**/admin_giveitem** @пользователь предмет - Выдать предмет
**/admin_createcase** название цена JSON_наград - Создать кейс
**/admin_viewtransactions** [@пользователь] - Просмотр транзакций""",
            inline=False
        )
    
    embed.set_footer(text="Используйте / для просмотра всех команд")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buffs", description="Показать ваши активные бафы")
async def buffs(interaction: discord.Interaction):
    buffs = db.get_user_buffs(interaction.user.id)
    
    embed = discord.Embed(title="🎯 Ваши активные бафы", color=0x00ff00)
    
    if not buffs:
        embed.description = "У вас пока нет активных бафов. Приобретайте предметы в кейсах или на маркетплейсе!"
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

@bot.tree.command(name="ping", description="Проверить пинг бота")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Понг!",
        description=f"Задержка бота: {round(bot.latency * 1000)}мс",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="recover", description="Восстановить данные пользователя (если есть проблемы)")
async def recover_data(interaction: discord.Interaction):
    user_data = db.get_user(interaction.user.id)
    
    inventory = db.get_user_inventory(interaction.user.id)
    if not isinstance(inventory, dict):
        cursor = db.conn.cursor()
        cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', 
                      (json.dumps({"cases": {}, "items": {}}), interaction.user.id))
        db.conn.commit()
    
    embed = discord.Embed(
        title="🔧 Восстановление данных",
        description="Ваши данные были проверены и восстановлены при необходимости!",
        color=0x00ff00
    )
    embed.add_field(name="Баланс", value=f"{user_data[1]} {EMOJIS['coin']}", inline=True)
    embed.add_field(name="Ежедневная серия", value=f"{user_data[2]} дней", inline=True)
    
    await interaction.response.send_message(embed=embed)

# AUTОCOMPLETE ДЛЯ ПРЕДМЕТОВ В МАРКЕТЕ
@market.autocomplete('item_name')
async def market_item_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    try:
        inventory = db.get_user_inventory_safe(interaction.user.id)
        items = inventory.get("items", {})
        item_choices = []
        
        for item_id, count in items.items():
            try:
                item_name = db.get_item_name_by_id(item_id)
                if current.lower() in item_name.lower():
                    item_choices.append(
                        app_commands.Choice(
                            name=f"{item_name} (x{count})",
                            value=item_name
                        )
                    )
            except Exception as e:
                continue
        
        return item_choices[:25]
    
    except Exception as e:
        print(f"❌ Ошибка в autocomplete: {e}")
        return []

# Команда для принудительной синхронизации
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

# ЗАПУСК БОТА
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
