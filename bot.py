import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import json
import random
import asyncio
import datetime
import aiohttp
from typing import Dict, List, Optional
import traceback

# Попробуем разные варианты импорта PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("✅ psycopg2 импортирован успешно")
except ImportError:
    print("❌ psycopg2 не установлен, устанавливаем...")
    os.system("pip install psycopg2-binary")
    import psycopg2
    from psycopg2.extras import RealDictCursor

# ПОЛУЧЕНИЕ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
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

if not BOT_TOKEN:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: DISCORD_BOT_TOKEN не установлен!")
    exit(1)

if not DATABASE_URL:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: DATABASE_URL не установлен!")
    exit(1)

# Настройки бота
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

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
    'Браслет везения': {'type': 'game_bonus', 'value': 1.1, 'description': '+10% к выигрышам в игран'},
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

# УЛУЧШЕННАЯ СИСТЕМА КВЕСТОВ
QUESTS = {
    'daily_rich': {'name': 'Ежедневный богач', 'description': 'Получите 3 ежедневных награды подряд', 'reward': 500, 'type': 'daily_streak', 'target': 3},
    'gambling_king': {'name': 'Король азарта', 'description': 'Выиграйте 5,000 монет в азартных играх', 'reward': 1000, 'type': 'gambling_win', 'target': 5000},
    'case_hunter': {'name': 'Охотник за кейсами', 'description': 'Откройте 10 кейсов любого типа', 'reward': 800, 'type': 'cases_opened', 'target': 10},
    'market_expert': {'name': 'Эксперт рынка', 'description': 'Продайте 3 предмета на маркетплейсе', 'reward': 600, 'type': 'market_sales', 'target': 3},
    'duel_champion': {'name': 'Чемпион дуэлей', 'description': 'Выиграйте 5 дуэлей', 'reward': 750, 'type': 'duels_won', 'target': 5},
    'item_collector_quest': {'name': 'Коллекционер', 'description': 'Соберите 3 разных магических предмета', 'reward': 900, 'type': 'unique_items', 'target': 3},
    'thief_apprentice': {'name': 'Ученик вора', 'description': 'Успешно украдите монеты 5 раз', 'reward': 700, 'type': 'steals_successful', 'target': 5},
    'gambler_novice': {'name': 'Новичок в азарте', 'description': 'Выиграйте в рулетку 3 раза', 'reward': 550, 'type': 'roulette_wins', 'target': 3},
    'generous_soul': {'name': 'Щедрая душа', 'description': 'Подарите 3 кейса другим игрокам', 'reward': 650, 'type': 'gifts_sent', 'target': 3},
    'blackjack_beginner': {'name': 'Начинающий в блэкджеке', 'description': 'Выиграйте в блэкджек 2 раза', 'reward': 450, 'type': 'blackjack_wins', 'target': 2},
    'slot_enthusiast': {'name': 'Энтузиаст слотов', 'description': 'Выиграйте в слотах 5 раз', 'reward': 500, 'type': 'slot_wins', 'target': 5},
    'coinflip_pro': {'name': 'Профи в подбрасывании', 'description': 'Выиграйте в coinflip 7 раз', 'reward': 600, 'type': 'coinflip_wins', 'target': 7}
}

# Безопасный доступ к данным пользователя
def get_user_data_safe(user_data):
    """Безопасное извлечение данных пользователя из кортежа"""
    return {
        'user_id': user_data[0] if len(user_data) > 0 else 0,
        'balance': user_data[1] if len(user_data) > 1 else 100,
        'daily_streak': user_data[2] if len(user_data) > 2 else 0,
        'last_daily': user_data[3] if len(user_data) > 3 else None,
        'inventory': user_data[4] if len(user_data) > 4 else '{"cases": {}, "items": {}}',
        'created_at': user_data[5] if len(user_data) > 5 else datetime.datetime.now()
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
    
    def create_case(self, name, price, rewards):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO cases (name, price, rewards) VALUES (%s, %s, %s) RETURNING id', 
                      (name, price, json.dumps(rewards)))
        case_id = cursor.fetchone()[0]
        self.conn.commit()
        return case_id
    
    def update_case(self, case_id, name, price, rewards):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE cases SET name = %s, price = %s, rewards = %s WHERE id = %s', 
                      (name, price, json.dumps(rewards), case_id))
        self.conn.commit()
    
    def delete_case(self, case_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM cases WHERE id = %s', (case_id,))
        self.conn.commit()
    
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
            cursor.execute('SELECT quest_id, progress, completed, assigned_at FROM quests WHERE user_id = %s', (user_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"❌ Ошибка в get_user_quests: {e}")
            return []
    
    def add_user_quest(self, user_id, quest_id):
        """Добавить квест пользователю"""
        try:
            cursor = self.conn.cursor()
            # Используем 0 вместо False для совместимости с типом integer
            cursor.execute('''
                INSERT INTO quests (user_id, quest_id, progress, completed, assigned_at) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, quest_id) DO NOTHING
            ''', (user_id, quest_id, 0, 0, datetime.datetime.now().isoformat()))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка в add_user_quest: {e}")
            return False
    
    def update_quest_progress(self, user_id, quest_id, progress, completed=False):
        """Обновить прогресс квеста"""
        try:
            cursor = self.conn.cursor()
            # Преобразуем boolean в integer для совместимости
            completed_int = 1 if completed else 0
            cursor.execute('''
                UPDATE quests SET progress = %s, completed = %s 
                WHERE user_id = %s AND quest_id = %s
            ''', (progress, completed_int, user_id, quest_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка в update_quest_progress: {e}")
            return False

    def get_user_active_quest(self, user_id):
        """Получить активный квест пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT quest_id, progress, completed, assigned_at FROM quests WHERE user_id = %s AND completed = 0', (user_id,))
            return cursor.fetchone()
        except Exception as e:
            print(f"❌ Ошибка в get_user_active_quest: {e}")
            return None

    def check_quest_completion(self, user_id, quest_type, current_value):
        """Проверяет выполнение квеста и обновляет прогресс"""
        try:
            cursor = self.conn.cursor()
            
            # Получаем активный квест пользователя
            active_quest = self.get_user_active_quest(user_id)
            if not active_quest:
                return False
                
            quest_id, progress, completed, assigned_at = active_quest
            
            if quest_id not in QUESTS:
                return False
                
            quest_data = QUESTS[quest_id]
            
            # Проверяем тип квеста
            if quest_data.get('type') != quest_type:
                return False
                
            target = quest_data.get('target', 0)
            new_progress = min(current_value, target)
            progress_percent = int((new_progress / target) * 100) if target > 0 else 0
            
            # Обновляем прогресс
            cursor.execute('''
                UPDATE quests SET progress = %s 
                WHERE user_id = %s AND quest_id = %s
            ''', (progress_percent, user_id, quest_id))
            
            # Проверяем завершение
            if new_progress >= target:
                cursor.execute('''
                    UPDATE quests SET completed = 1 
                    WHERE user_id = %s AND quest_id = %s
                ''', (user_id, quest_id))
                
                # Выдаем награду
                reward = quest_data['reward']
                reward = self.apply_buff_to_amount(user_id, reward, 'quest_bonus')
                reward = self.apply_buff_to_amount(user_id, reward, 'multiplier')
                reward = self.apply_buff_to_amount(user_id, reward, 'all_bonus')
                
                self.update_balance(user_id, reward)
                self.log_transaction(user_id, 'quest_reward', reward, description=f"Квест: {quest_data['name']}")
                
                self.conn.commit()
                return True
            
            self.conn.commit()
            return False
            
        except Exception as e:
            print(f"❌ Ошибка в check_quest_completion: {e}")
            return False

    def can_get_new_quest(self, user_id):
        """Проверяет, может ли пользователь получить новый квест"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT assigned_at FROM quests WHERE user_id = %s ORDER BY assigned_at DESC LIMIT 1', (user_id,))
            result = cursor.fetchone()
            
            if not result:
                return True
                
            last_quest_time = result[0]
            if isinstance(last_quest_time, str):
                last_quest_time = datetime.datetime.fromisoformat(last_quest_time)
                
            time_since_last_quest = datetime.datetime.now() - last_quest_time
            return time_since_last_quest.total_seconds() >= 3600  # 1 час
            
        except Exception as e:
            print(f"❌ Ошибка в can_get_new_quest: {e}")
            return True

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
        
        # Таблица квестов - ИСПРАВЛЕНО: используем INTEGER вместо BOOLEAN
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quests (
                user_id BIGINT,
                quest_id TEXT,
                progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                assigned_at TIMESTAMP,
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
        
        # Инициализация начальных данных - ВЫЗЫВАЕМ ПРАВИЛЬНЫЙ МЕТОД
        self._initialize_default_data()
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        self.conn.rollback()
        raise

def _initialize_default_data(self):
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
        
        self.conn.commit()
        print("✅ Начальные данные успешно инициализированы!")
        
    except Exception as e:
        print(f"❌ Ошибка при инициализации данных: {e}")
        self.conn.rollback()

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
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            webhook = await channel.create_webhook(name=f"Role-{user.name}")
            message = f"🎉 <@{user.id}> Поздравляю, вам выпала кастом роль на 2 дня, администратор <@{ADMIN_USER_ID}> скоро вам ответит и вы выберете свою роль"
            await webhook.send(
                content=message,
                username="Case System",
                avatar_url=bot.user.avatar.url if bot.user.avatar else None
            )
            await webhook.delete()
            return True
    except Exception as e:
        print(f"Ошибка создания вебхука для роли: {e}")
    return False

async def process_reward(user, reward, case):
    if reward['type'] == 'coins':
        amount = random.randint(reward['amount'][0], reward['amount'][1])
        # Применяем бафы к награде из кейса
        amount = db.apply_buff_to_amount(user.id, amount, 'case_bonus')
        amount = db.apply_buff_to_amount(user.id, amount, 'multiplier')
        amount = db.apply_buff_to_amount(user.id, amount, 'all_bonus')
        
        db.update_balance(user.id, amount)
        db.log_transaction(user.id, 'case_reward', amount, description=f"Награда из {case['name']}")
        return f"💰 {amount} {EMOJIS['coin']} - {reward.get('description', 'Монеты')}"
    
    elif reward['type'] == 'custom_role':
        await create_custom_role_webhook(user)
        return "🎭 Кастомная роль! (Создан запрос в канале администрации)"
    
    elif reward['type'] == 'special_item':
        db.add_item_to_inventory(user.id, reward['name'])
        return f"📦 {reward['name']} - {reward.get('description', 'Особый предмет')}"
    
    elif reward['type'] == 'bonus':
        return f"🚀 Бонус x{reward['multiplier']} на {reward['duration']}ч - {reward.get('description', 'Временный бонус')}"
    
    elif reward['type'] == 'role':
        return f"👑 Роль: {reward['name']} на {reward['duration']}ч"
    
    return "Неизвестная награда"

# КЛАССЫ ДЛЯ МИНИ-ИГР

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
        user_safe = get_user_data_safe(user_data)
        
        if user_safe['balance'] < case['price']:
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
        
        # Обновляем статистику открытия кейсов
        db.update_user_stat(self.user_id, 'cases_opened')
        
        # Проверяем квесты
        db.check_quest_completion(self.user_id, 'cases_opened', user_safe['balance'])
        
        # Выдача награды
        reward_text = await process_reward(interaction.user, reward, case)
        
        embed = discord.Embed(
            title=f"🎉 {case['name']} открыт!",
            description=reward_text,
            color=0x00ff00
        )
        embed.set_footer(text=f"Стоимость: {case['price']} {EMOJIS['coin']}")
        
        await interaction.edit_original_response(embed=embed)

# УЛУЧШЕННАЯ ПАГИНАЦИЯ ДЛЯ КЕЙСОВ
class ImprovedCasesView(View):
    def __init__(self, pages, author_id):
        super().__init__(timeout=120)
        self.pages = pages
        self.current_page = 0
        self.total_pages = len(pages)
        self.author_id = author_id
        self.update_buttons()

    def update_buttons(self):
        """Обновляет состояние кнопок"""
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
            color=0xff69b4
        )
        
        for case in page_cases:
            try:
                rewards = json.loads(case[3])
                
                # Полное описание наград
                rewards_desc = ""
                for reward in rewards:
                    chance_percent = reward['chance'] * 100
                    if reward['type'] == 'coins':
                        if reward['amount'][0] < 0:
                            rewards_desc += f"• 💀 Потеря: {abs(reward['amount'][0])}-{abs(reward['amount'][1])} монет ({chance_percent:.1f}%)\n"
                        else:
                            rewards_desc += f"• 💰 Монеты: {reward['amount'][0]}-{reward['amount'][1]} ({chance_percent:.1f}%)\n"
                    elif reward['type'] == 'special_item':
                        rewards_desc += f"• 🎁 {reward['name']} ({chance_percent:.1f}%)\n"
                    elif reward['type'] == 'bonus':
                        rewards_desc += f"• ⭐ Бонус x{reward['multiplier']} ({chance_percent:.1f}%)\n"
                    elif reward['type'] == 'custom_role':
                        rewards_desc += f"• 👑 Кастомная роль ({chance_percent:.1f}%)\n"
                
                embed.add_field(
                    name=f"{case[1]} - {case[2]} {EMOJIS['coin']} (ID: {case[0]})",
                    value=rewards_desc,
                    inline=False
                )
            except Exception as e:
                print(f"⚠️ Ошибка обработки кейса {case[0]}: {e}")
                continue
        
        return embed

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

@bot.tree.command(name="debug_cases", description="Отладочная информация о кейсах")
async def debug_cases(interaction: discord.Interaction):
    global db
    try:
        cases = db.get_cases()
        embed = discord.Embed(title="🔧 Отладочная информация о кейсах", color=0xff9900)
        embed.add_field(name="Всего кейсов в базе", value=len(cases), inline=False)
        embed.add_field(name="Тип db", value=str(type(db)), inline=False)
        
        case_details = []
        for i, case in enumerate(cases[:10]):  # Показываем первые 10 кейсов
            case_details.append(f"{i+1}. ID: {case[0]}, Name: {case[1]}, Price: {case[2]}")
        
        if case_details:
            embed.add_field(name="Кейсы (первые 10)", value="\n".join(case_details), inline=False)
        else:
            embed.add_field(name="Кейсы", value="Нет кейсов в базе", inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка отладки: {e}", ephemeral=True)

# КОМАНДЫ БОТА

# Экономические команды
@bot.tree.command(name="balance", description="Показать ваш баланс")
@app_commands.describe(user="Пользователь, чей баланс показать (опционально)")
async def balance(interaction: discord.Interaction, user: discord.Member = None):
    try:
        user = user or interaction.user
        user_data = db.get_user(user.id)
        user_safe = get_user_data_safe(user_data)
        
        # Получаем статистику достижений
        cursor = db.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM achievements WHERE user_id = %s', (user.id,))
        achievements_result = cursor.fetchone()
        achievements_count = achievements_result[0] if achievements_result else 0
        
        # Получаем активные бафы
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
        
        # Показываем активные бафы
        if buffs:
            buffs_text = "\n".join([f"• {buff['item_name']}: {buff['description']}" for buff in buffs.values()])
            embed.add_field(name="🎯 Активные бафы", value=buffs_text, inline=False)
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        elif user.default_avatar:
            embed.set_thumbnail(url=user.default_avatar.url)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Критическая ошибка в команде balance: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка",
            description="Произошла ошибка при получении данных. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# УЛУЧШЕННАЯ КОМАНДА CASES С ПАГИНАЦИЕЙ И ПОЛНЫМ ОПИСАНИЕМ
# Добавьте это в начало команды cases
@bot.tree.command(name="cases", description="Показать список доступных кейсов с полным описанием")
async def cases_list(interaction: discord.Interaction):
    global db  # Добавляем глобальное объявление
    try:
        cases = db.get_cases()  # Теперь db должна быть доступна
        
        if not cases:
            await interaction.response.send_message("Кейсы не найдены!", ephemeral=True)
            return
        
        # Разбиваем на страницы по 3 кейса (из-за полного описания)
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

# УЛУЧШЕННАЯ СИСТЕМА КВЕСТОВ
@bot.tree.command(name="quest", description="Получить случайный квест (перезарядка 1 час)")
async def quest(interaction: discord.Interaction):
    try:
        # Проверяем, может ли пользователь получить новый квест
        if not db.can_get_new_quest(interaction.user.id):
            await interaction.response.send_message(
                "❌ Вы можете получить новый квест только через 1 час после получения предыдущего!",
                ephemeral=True
            )
            return
        
        # Проверяем, есть ли активный квест
        active_quest = db.get_user_active_quest(interaction.user.id)
        if active_quest:
            quest_id, progress, completed, assigned_at = active_quest
            if quest_id in QUESTS:
                quest_data = QUESTS[quest_id]
                await interaction.response.send_message(
                    f"❌ У вас уже есть активный квест: **{quest_data['name']}**\n"
                    f"📊 Прогресс: {progress}%\n"
                    f"Используйте `/quests` чтобы посмотреть детали.",
                    ephemeral=True
                )
                return
        
        # Выдаем случайный квест
        available_quests = list(QUESTS.keys())
        if not available_quests:
            await interaction.response.send_message("❌ Нет доступных квестов!", ephemeral=True)
            return
        
        quest_id = random.choice(available_quests)
        quest_data = QUESTS[quest_id]
        
        if db.add_user_quest(interaction.user.id, quest_id):
            embed = discord.Embed(
                title=f"{EMOJIS['quest']} Новый квест получен!",
                description=quest_data['description'],
                color=0x00ff00
            )
            embed.add_field(name="Награда", value=f"{quest_data['reward']} {EMOJIS['coin']}")
            embed.add_field(name="Тип", value=quest_data.get('type', 'Неизвестно'))
            embed.set_footer(text="Используйте /quests чтобы посмотреть ваши квесты")
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Не удалось выдать квест!", ephemeral=True)
            
    except Exception as e:
        print(f"❌ Ошибка в команде quest: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при получении квеста!", ephemeral=True)

@bot.tree.command(name="quests", description="Показать ваши активные и завершенные квесты")
async def quests(interaction: discord.Interaction):
    try:
        user_quests = db.get_user_quests(interaction.user.id)
        
        embed = discord.Embed(title=f"{EMOJIS['quest']} Ваши квесты", color=0x9b59b6)
        
        if not user_quests:
            embed.description = "У вас пока нет квестов. Используйте `/quest` чтобы получить новый!"
            await interaction.response.send_message(embed=embed)
            return
        
        active_quests = []
        completed_quests = []
        
        for quest_row in user_quests:
            quest_id, progress, completed, assigned_at = quest_row
            if quest_id in QUESTS:
                quest_data = QUESTS[quest_id]
                quest_info = {
                    'name': quest_data['name'],
                    'description': quest_data['description'],
                    'progress': progress,
                    'reward': quest_data['reward'],
                    'completed': completed
                }
                
                if completed == 1:
                    completed_quests.append(quest_info)
                else:
                    active_quests.append(quest_info)
        
        # Показываем активные квесты
        if active_quests:
            embed.add_field(
                name="📊 Активные квесты",
                value="",
                inline=False
            )
            for quest in active_quests:
                embed.add_field(
                    name=f"🔄 {quest['name']} - {quest['progress']}%",
                    value=f"{quest['description']}\nНаграда: {quest['reward']} {EMOJIS['coin']}",
                    inline=False
                )
        
        # Показываем завершенные квесты
        if completed_quests:
            embed.add_field(
                name="✅ Завершенные квесты",
                value="",
                inline=False
            )
            for quest in completed_quests:
                embed.add_field(
                    name=f"✅ {quest['name']}",
                    value=f"{quest['description']}\nПолучено: {quest['reward']} {EMOJIS['coin']}",
                    inline=False
                )
        
        if not active_quests and not completed_quests:
            embed.description = "У вас пока нет квестов. Используйте `/quest` чтобы получить новый!"
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде quests: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке квестов!", ephemeral=True)

# УЛУЧШЕННАЯ КОМАНДА MARKET С AUTocomplete
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
                    
                    # Получаем информацию о бафе предмета безопасно
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
            
            # Проверяем, есть ли предмет в инвентаре
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
            
            # Убираем предмет из инвентаря
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
            
            # Покупка предмета
            db.update_balance(interaction.user.id, -item_price)
            db.update_balance(seller_id, item_price)
            
            # Добавляем предмет покупателю
            db.add_item_to_inventory(interaction.user.id, market_item_name)
            
            cursor.execute('DELETE FROM market WHERE id = %s', (market_item_id,))
            db.conn.commit()
            
            db.log_transaction(interaction.user.id, 'market_buy', -item_price, seller_id, f"Покупка: {market_item_name}")
            db.log_transaction(seller_id, 'market_sell', item_price, interaction.user.id, f"Продажа: {market_item_name}")
            
            # Получаем информацию о бафе купленного предмета
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

# Создаем экземпляр базы данных
try:
    db = Database()
    print("✅ База данных успешно инициализирована!")
    
    # Принудительно инициализируем данные
    print("🔄 Принудительная инициализация данных...")
    db._initialize_default_data()
    
    # Проверяем, что кейсы загружаются
    test_cases = db.get_cases()
    print(f"🔍 Тест: загружено {len(test_cases)} кейсов после инициализации")
    
except Exception as e:
    print(f"💥 Критическая ошибка при инициализации базы данных: {e}")
    traceback.print_exc()
    exit(1)

    # Создаем заглушку для db чтобы избежать ошибок
    class DummyDB:
        def get_cases(self):
            return []
        def get_user(self, user_id):
            return (user_id, 100, 0, None, '{"cases": {}, "items": {}}', datetime.datetime.now())
        # Добавьте другие методы по мере необходимости
    db = DummyDB()

# AUTОCOMPLETE ДЛЯ ПРЕДМЕТОВ В МАРКЕТЕ
@market.autocomplete('item_name')
async def market_item_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
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
        
        return item_choices[:25]  # Discord ограничивает до 25选项
    
    except Exception as e:
        print(f"❌ Ошибка в autocomplete: {e}")
        return []

# ДОБАВЛЯЕМ ПРОВЕРКУ КВЕСТОВ В ДРУГИЕ КОМАНДЫ

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
        
        # Проверяем квесты
        db.check_quest_completion(interaction.user.id, 'daily_streak', streak)
        
        embed = discord.Embed(
            title=f"{EMOJIS['daily']} Ежедневная награда",
            description=f"Награда: {reward} {EMOJIS['coin']}\nСерия: {streak} дней\nБонус за серию: +{streak_bonus} {EMOJIS['coin']}",
            color=0x00ff00
        )
        
        # Проверяем достижения после получения награды
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

# ДОБАВЛЯЕМ ПРОВЕРКУ КВЕСТОВ В ДУЭЛИ
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
    
    # Создаем представление для дуэли (упрощенная версия)
    embed = discord.Embed(
        title=f"{EMOJIS['duel']} Вызов на дуэль!",
        description=f"{interaction.user.mention} вызывает {user.mention} на дуэль!",
        color=0xff0000
    )
    embed.add_field(name="Ставка", value=f"{bet} {EMOJIS['coin']}", inline=True)
    embed.add_field(name="Время на ответ", value="30 секунд", inline=True)
    embed.set_footer(text="Победитель забирает всю ставку!")
    
    # В реальной реализации здесь должна быть полноценная система дуэлей
    # Для простоты просто сообщим, что дуэль начата
    await interaction.response.send_message(
        f"⚔️ Дуэль между {interaction.user.mention} и {user.mention} начата!\n"
        f"Ставка: {bet} {EMOJIS['coin']}\n\n"
        f"*В реальной реализации здесь была бы полноценная система дуэлей*"
    )
    
    # Имитируем результат дуэли (50/50 шанс)
    await asyncio.sleep(2)
    
    winner = interaction.user if random.random() > 0.5 else user
    loser = user if winner == interaction.user else interaction.user
    
    # Выдаем выигрыш
    winnings = bet * 2
    winnings = db.apply_buff_to_amount(winner.id, winnings, 'game_bonus')
    winnings = db.apply_buff_to_amount(winner.id, winnings, 'multiplier')
    winnings = db.apply_buff_to_amount(winner.id, winnings, 'all_bonus')
    
    db.update_balance(winner.id, winnings - bet)  # Чистый выигрыш
    db.update_balance(loser.id, -bet)
    
    db.log_transaction(winner.id, 'duel_win', winnings - bet, loser.id, "Победа в дуэли")
    db.log_transaction(loser.id, 'duel_loss', -bet, winner.id, "Проигрыш в дуэли")
    
    # Обновляем статистику
    db.update_user_stat(winner.id, 'duels_won')
    db.update_consecutive_wins(winner.id, True)
    db.update_consecutive_wins(loser.id, False)
    
    # Проверяем квесты
    cursor = db.conn.cursor()
    cursor.execute('SELECT duels_won FROM user_stats WHERE user_id = %s', (winner.id,))
    duels_won = cursor.fetchone()
    if duels_won:
        db.check_quest_completion(winner.id, 'duels_won', duels_won[0])
    
    result_embed = discord.Embed(
        title=f"{EMOJIS['duel']} Результат дуэли",
        description=f"**Победитель:** {winner.mention}\n**Проигравший:** {loser.mention}",
        color=0x00ff00
    )
    result_embed.add_field(name="Выигрыш", value=f"{winnings - bet} {EMOJIS['coin']}", inline=True)
    
    await interaction.followup.send(embed=result_embed)

@bot.tree.command(name="admin_update_cases", description="[ADMIN] Принудительно обновить кейсы")
@is_admin()
async def admin_update_cases(interaction: discord.Interaction):
    try:
        # Очищаем таблицу кейсов и добавляем заново
        cursor = db.conn.cursor()
        cursor.execute('DELETE FROM cases')
        db.conn.commit()
        
        # Инициализируем данные
        db._initialize_default_data()
        
        # Проверяем результат
        cases = db.get_cases()
        
        embed = discord.Embed(title="🔄 Кейсы обновлены", color=0x00ff00)
        embed.add_field(name="Добавлено кейсов", value=len(cases), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

@bot.tree.command(name="debug_database", description="Глубокая отладка базы данных")
async def debug_database(interaction: discord.Interaction):
    try:
        cursor = db.conn.cursor()
        
        # Проверяем существование таблицы cases
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'cases'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        # Получаем информацию о таблице
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'cases'
        """)
        columns = cursor.fetchall()
        
        # Получаем все кейсы
        cases = db.get_cases()
        
        embed = discord.Embed(title="🔧 Отладка базы данных", color=0xff9900)
        embed.add_field(name="Таблица cases существует", value="✅ Да" if table_exists else "❌ Нет", inline=False)
        embed.add_field(name="Колонки таблицы", value="\n".join([f"{col[0]}: {col[1]}" for col in columns]), inline=False)
        embed.add_field(name="Количество кейсов", value=len(cases), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка отладки: {e}", ephemeral=True)

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





