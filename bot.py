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
        cursor.execute('SELECT * FROM cases')
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
            balance = user_data[1]
            
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
            ''', (user_id, quest_id, 0, 0))
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
                    completed INTEGER DEFAULT 0,
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
        """Инициализация начальных данных"""
        try:
            cursor = self.conn.cursor()
            
            # Проверяем, есть ли уже кейсы
            cursor.execute('SELECT COUNT(*) FROM cases')
            if cursor.fetchone()[0] == 0:
                print("🔄 Добавление стандартных кейсов...")
                
                default_cases = [
                    ('📦 Начинающий кейс', 25, json.dumps([
                        {'type': 'coins', 'amount': [10, 30], 'chance': 0.6},
                        {'type': 'coins', 'amount': [31, 80], 'chance': 0.3},
                        {'type': 'coins', 'amount': [81, 150], 'chance': 0.1}
                    ])),
                    ('📦 Малый кейс', 50, json.dumps([
                        {'type': 'coins', 'amount': [20, 50], 'chance': 0.5},
                        {'type': 'coins', 'amount': [51, 120], 'chance': 0.3},
                        {'type': 'coins', 'amount': [121, 250], 'chance': 0.15},
                        {'type': 'special_item', 'name': 'Серебряный амулет', 'chance': 0.05}
                    ])),
                    ('📦 Средний кейс', 150, json.dumps([
                        {'type': 'coins', 'amount': [50, 100], 'chance': 0.4},
                        {'type': 'coins', 'amount': [101, 250], 'chance': 0.3},
                        {'type': 'special_item', 'name': 'Золотой амулет', 'chance': 0.15},
                        {'type': 'coins', 'amount': [251, 500], 'chance': 0.1},
                        {'type': 'bonus', 'multiplier': 1.2, 'duration': 12, 'chance': 0.05}
                    ])),
                    ('💎 Большой кейс', 500, json.dumps([
                        {'type': 'coins', 'amount': [150, 300], 'chance': 0.35},
                        {'type': 'coins', 'amount': [301, 600], 'chance': 0.25},
                        {'type': 'special_item', 'name': 'Кольцо удачи', 'chance': 0.15},
                        {'type': 'bonus', 'multiplier': 1.5, 'duration': 24, 'chance': 0.1},
                        {'type': 'coins', 'amount': [601, 1000], 'chance': 0.1},
                        {'type': 'special_item', 'name': 'Браслет везения', 'chance': 0.05}
                    ])),
                    ('👑 Элитный кейс', 1000, json.dumps([
                        {'type': 'coins', 'amount': [300, 600], 'chance': 0.3},
                        {'type': 'coins', 'amount': [-200, -100], 'chance': 0.1},
                        {'type': 'special_item', 'name': 'Защитный талисман', 'chance': 0.2},
                        {'type': 'bonus', 'multiplier': 2.0, 'duration': 48, 'chance': 0.15},
                        {'type': 'coins', 'amount': [601, 1500], 'chance': 0.15},
                        {'type': 'coins', 'amount': [1501, 3000], 'chance': 0.1}
                    ])),
                    ('🔮 Секретный кейс', 2000, json.dumps([
                        {'type': 'coins', 'amount': [500, 1000], 'chance': 0.25},
                        {'type': 'coins', 'amount': [-500, -200], 'chance': 0.1},
                        {'type': 'special_item', 'name': 'Магический свиток', 'chance': 0.2},
                        {'type': 'bonus', 'multiplier': 3.0, 'duration': 72, 'chance': 0.15},
                        {'type': 'coins', 'amount': [1001, 2500], 'chance': 0.15},
                        {'type': 'coins', 'amount': [2501, 5000], 'chance': 0.1},
                        {'type': 'custom_role', 'chance': 0.05}
                    ])),
                    ('⚡ Быстрый кейс', 75, json.dumps([
                        {'type': 'coins', 'amount': [30, 80], 'chance': 0.7},
                        {'type': 'coins', 'amount': [81, 180], 'chance': 0.2},
                        {'type': 'special_item', 'name': 'Перчатка вора', 'chance': 0.1}
                    ])),
                    ('🎭 Загадочный кейс', 300, json.dumps([
                        {'type': 'coins', 'amount': [50, 200], 'chance': 0.3},
                        {'type': 'coins', 'amount': [-150, -50], 'chance': 0.2},
                        {'type': 'coins', 'amount': [201, 500], 'chance': 0.2},
                        {'type': 'special_item', 'name': 'Кристалл маны', 'chance': 0.15},
                        {'type': 'coins', 'amount': [501, 1200], 'chance': 0.1},
                        {'type': 'bonus', 'multiplier': 1.8, 'duration': 36, 'chance': 0.05}
                    ])),
                    ('🌟 Звездный кейс', 750, json.dumps([
                        {'type': 'coins', 'amount': [200, 400], 'chance': 0.4},
                        {'type': 'coins', 'amount': [401, 800], 'chance': 0.25},
                        {'type': 'special_item', 'name': 'Счастливая монета', 'chance': 0.15},
                        {'type': 'bonus', 'multiplier': 1.7, 'duration': 24, 'chance': 0.1},
                        {'type': 'coins', 'amount': [801, 2000], 'chance': 0.08},
                        {'type': 'special_item', 'name': 'Карточный шулер', 'chance': 0.02}
                    ])),
                    ('🐉 Драконий кейс', 1500, json.dumps([
                        {'type': 'coins', 'amount': [400, 800], 'chance': 0.35},
                        {'type': 'coins', 'amount': [801, 1600], 'chance': 0.2},
                        {'type': 'special_item', 'name': 'Слот-мастер', 'chance': 0.15},
                        {'type': 'bonus', 'multiplier': 2.2, 'duration': 48, 'chance': 0.1},
                        {'type': 'coins', 'amount': [1601, 3500], 'chance': 0.1},
                        {'type': 'special_item', 'name': 'Щит богатства', 'chance': 0.05},
                        {'type': 'coins', 'amount': [3501, 7000], 'chance': 0.05}
                    ])),
                    ('🔥 Огненный кейс', 600, json.dumps([
                        {'type': 'coins', 'amount': [150, 350], 'chance': 0.5},
                        {'type': 'coins', 'amount': [351, 700], 'chance': 0.25},
                        {'type': 'special_item', 'name': 'Флакон зелья', 'chance': 0.15},
                        {'type': 'bonus', 'multiplier': 1.6, 'duration': 18, 'chance': 0.1}
                    ])),
                    ('❄️ Ледяной кейс', 600, json.dumps([
                        {'type': 'coins', 'amount': [150, 350], 'chance': 0.5},
                        {'type': 'coins', 'amount': [351, 700], 'chance': 0.25},
                        {'type': 'special_item', 'name': 'Зелье удачи', 'chance': 0.15},
                        {'type': 'bonus', 'multiplier': 1.6, 'duration': 18, 'chance': 0.1}
                    ])),
                    ('🌙 Лунный кейс', 1200, json.dumps([
                        {'type': 'coins', 'amount': [300, 600], 'chance': 0.4},
                        {'type': 'coins', 'amount': [601, 1200], 'chance': 0.25},
                        {'type': 'special_item', 'name': 'Руна богатства', 'chance': 0.15},
                        {'type': 'bonus', 'multiplier': 1.8, 'duration': 36, 'chance': 0.1},
                        {'type': 'coins', 'amount': [1201, 2500], 'chance': 0.08},
                        {'type': 'special_item', 'name': 'Тотем защиты', 'chance': 0.02}
                    ])),
                    ('⚗️ Алхимический кейс', 800, json.dumps([
                        {'type': 'coins', 'amount': [200, 500], 'chance': 0.45},
                        {'type': 'coins', 'amount': [501, 1000], 'chance': 0.25},
                        {'type': 'special_item', 'name': 'Ожерелье мудрости', 'chance': 0.2},
                        {'type': 'bonus', 'multiplier': 1.7, 'duration': 24, 'chance': 0.1}
                    ])),
                    ('🏹 Охотничий кейс', 400, json.dumps([
                        {'type': 'coins', 'amount': [100, 300], 'chance': 0.6},
                        {'type': 'coins', 'amount': [301, 600], 'chance': 0.25},
                        {'type': 'special_item', 'name': 'Плащ тени', 'chance': 0.1},
                        {'type': 'bonus', 'multiplier': 1.4, 'duration': 12, 'chance': 0.05}
                    ]))
                ]
                
                for case in default_cases:
                    cursor.execute('INSERT INTO cases (name, price, rewards) VALUES (%s, %s, %s)', case)
                
                print("✅ Стандартные кейсы добавлены!")
            
            # Проверяем, есть ли уже предметы
            cursor.execute('SELECT COUNT(*) FROM items')
            if cursor.fetchone()[0] == 0:
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
                    ('Счастливая монета', 'Увеличивает выигрыш в coinflip', 400, 'uncommon', 'coinflip_bonus', 1.2, '+20% к выигрышу в coinflip'),
                    ('Карточный шулер', 'Увеличивает выигрыш в блэкджеке', 650, 'rare', 'blackjack_bonus', 1.15, '+15% к выигрышу в блэкджеке'),
                    ('Слот-мастер', 'Увеличивает выигрыш в слотах', 750, 'rare', 'slot_bonus', 1.25, '+25% к выигрышу в слотах'),
                    ('Щит богатства', 'Уменьшает проигрыши', 900, 'epic', 'loss_protection', 0.8, '-20% к проигрышам'),
                    ('Флакон зелья', 'Увеличивает награды за квесты', 350, 'uncommon', 'quest_bonus', 1.2, '+20% к наградам за квесты'),
                    ('Зелье удачи', 'Небольшой бонус ко всем наградам', 300, 'common', 'all_bonus', 1.1, '+10% ко всем наградам'),
                    ('Руна богатства', 'Уменьшает комиссию переводов', 500, 'rare', 'transfer_bonus', 0.9, '-10% к комиссии переводов'),
                    ('Тотем защиты', 'Увеличивает шанс победы в дуэлях', 850, 'epic', 'duel_bonus', 1.2, '+20% к шансу победы в дуэлях'),
                    ('Ожерелье мудрости', 'Увеличивает получаемый опыт', 600, 'rare', 'xp_bonus', 1.15, '+15% к опыту'),
                    ('Плащ тени', 'Увеличивает шанс кражи', 550, 'uncommon', 'steal_chance', 1.15, '+15% к шансу кражи')
                ]
                
                for item in default_items:
                    cursor.execute('INSERT INTO items (name, description, value, rarity, buff_type, buff_value, buff_description) VALUES (%s, %s, %s, %s, %s, %s, %s)', item)
                
                print("✅ Стандартные предметы добавлены!")
            
            self.conn.commit()
            print("✅ Начальные данные успешно инициализированы!")
            
        except Exception as e:
            print(f"❌ Ошибка при инициализации данных: {e}")
            self.conn.rollback()

# Создаем экземпляр базы данных
try:
    db = Database()
    print("✅ База данных успешно инициализирована!")
except Exception as e:
    print(f"💥 Критическая ошибка при инициализации базы данных: {e}")
    exit(1)

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
        return f"Монеты: {amount} {EMOJIS['coin']}"
    
    elif reward['type'] == 'custom_role':
        await create_custom_role_webhook(user)
        return "🎭 Кастомная роль! (Создан запрос в канале администрации)"
    
    elif reward['type'] == 'special_item':
        db.add_item_to_inventory(user.id, reward['name'])
        return f"📦 Особый предмет: {reward['name']}"
    
    elif reward['type'] == 'bonus':
        return f"🚀 Бонус x{reward['multiplier']} на {reward['duration']}ч"
    
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
        
        # Обновляем статистику открытия кейсов
        db.update_user_stat(self.user_id, 'cases_opened')
        
        # Выдача награды
        reward_text = await process_reward(interaction.user, reward, case)
        
        embed = discord.Embed(
            title=f"🎉 {case['name']} открыт!",
            description=reward_text,
            color=0x00ff00
        )
        embed.set_footer(text=f"Стоимость: {case['price']} {EMOJIS['coin']}")
        
        await interaction.edit_original_response(embed=embed)

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
        
        # Определяем победителя с учетом бафов
        base_challenger_chance = 0.5
        base_target_chance = 0.5
        
        # Применяем бафы к шансам
        challenger_buff = db.apply_buff_to_chance(self.challenger_id, 1.0, 'duel_bonus')
        target_buff = db.apply_buff_to_chance(self.target_id, 1.0, 'duel_bonus')
        
        challenger_chance = base_challenger_chance * challenger_buff
        target_chance = base_target_chance * target_buff
        
        # Нормализуем шансы
        total = challenger_chance + target_chance
        challenger_chance /= total
        target_chance /= total
        
        # Определяем победителя
        winner_id = random.choices([self.challenger_id, self.target_id], 
                                 weights=[challenger_chance, target_chance])[0]
        loser_id = self.target_id if winner_id == self.challenger_id else self.challenger_id
        
        # Выдаем выигрыш с учетом бафов
        base_winnings = self.bet * 2
        winnings = db.apply_buff_to_amount(winner_id, base_winnings, 'game_bonus')
        winnings = db.apply_buff_to_amount(winner_id, winnings, 'multiplier')
        winnings = db.apply_buff_to_amount(winner_id, winnings, 'all_bonus')
        
        db.update_balance(winner_id, winnings)
        
        # Логируем и обновляем статистику
        db.log_transaction(winner_id, 'duel_win', winnings, loser_id, "Победа в дуэли")
        db.log_transaction(loser_id, 'duel_loss', -self.bet, winner_id, "Проигрыш в дуэли")
        db.update_user_stat(winner_id, 'duels_won')
        db.update_consecutive_wins(winner_id, True)
        db.update_consecutive_wins(loser_id, False)
        
        winner = bot.get_user(winner_id)
        loser = bot.get_user(loser_id)
        
        embed = discord.Embed(
            title=f"{EMOJIS['duel']} Результат дуэли",
            description=f"**Победитель:** {winner.mention}\n**Проигравший:** {loser.mention}",
            color=0x00ff00
        )
        embed.add_field(name="Выигрыш", value=f"{winnings} {EMOJIS['coin']}")
        embed.add_field(name="Шанс победы", value=f"{challenger_chance*100:.1f}% / {target_chance*100:.1f}%")
        
        await interaction.edit_original_response(embed=embed)

class CoinFlipView(View):
    def __init__(self, user_id, bet):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.bet = bet
        self.choice_made = False
    
    @discord.ui.button(label='🦅 Орёл', style=discord.ButtonStyle.primary)
    async def heads(self, interaction: discord.Interaction, button: Button):
        await self.process_choice(interaction, 'heads')
    
    @discord.ui.button(label='💰 Решка', style=discord.ButtonStyle.primary)
    async def tails(self, interaction: discord.Interaction, button: Button):
        await self.process_choice(interaction, 'tails')
    
    async def process_choice(self, interaction: discord.Interaction, choice):
        if self.choice_made:
            return
        
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Эта игра не для вас!", ephemeral=True)
            return
        
        self.choice_made = True
        
        # Подбрасываем монету
        result = random.choice(['heads', 'tails'])
        win = choice == result
        
        # Анимация
        embed = discord.Embed(title="🪙 Монета в воздухе...", color=0xffd700)
        await interaction.response.edit_message(embed=embed, view=None)
        
        for i in range(3):
            await asyncio.sleep(0.5)
            embed.description = "🌀" * (i + 1)
            await interaction.edit_original_response(embed=embed)
        
        await asyncio.sleep(1)
        
        if win:
            base_winnings = int(self.bet * 1.8)  # 80% прибыль
            # Применяем бафы к выигрышу
            winnings = db.apply_buff_to_amount(self.user_id, base_winnings, 'coinflip_bonus')
            winnings = db.apply_buff_to_amount(self.user_id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(self.user_id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(self.user_id, winnings, 'all_bonus')
            
            db.update_balance(self.user_id, winnings)
            db.log_transaction(self.user_id, 'coinflip_win', winnings, description="Победа в coinflip")
            db.update_user_stat(self.user_id, 'coinflip_wins')
            db.update_consecutive_wins(self.user_id, True)
            
            result_text = f"ПОБЕДА! Выпало: {'🦅 Орёл' if result == 'heads' else '💰 Решка'}\nВыигрыш: {winnings} {EMOJIS['coin']}"
            color = 0x00ff00
        else:
            # Применяем баф защиты от проигрышей
            loss = db.apply_buff_to_amount(self.user_id, self.bet, 'loss_protection')
            db.update_balance(self.user_id, -loss)
            db.log_transaction(self.user_id, 'coinflip_loss', -loss, description="Проигрыш в coinflip")
            db.update_consecutive_wins(self.user_id, False)
            
            result_text = f"ПРОИГРЫШ! Выпало: {'🦅 Орёл' if result == 'heads' else '💰 Решка'}\nПотеряно: {loss} {EMOJIS['coin']}"
            color = 0xff0000
        
        embed = discord.Embed(
            title=f"🪙 Результат подбрасывания монеты",
            description=f"Ваш выбор: {'🦅 Орёл' if choice == 'heads' else '💰 Решка'}\n{result_text}",
            color=color
        )
        embed.add_field(name="Ставка", value=f"{self.bet} {EMOJIS['coin']}")
        
        await interaction.edit_original_response(embed=embed)

class BlackjackView(View):
    def __init__(self, user_id, bet):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bet = bet
        self.user_cards = []
        self.dealer_cards = []
        self.game_over = False
        
        # Начальная раздача
        self.user_cards = [self.draw_card(), self.draw_card()]
        self.dealer_cards = [self.draw_card(), self.draw_card()]
    
    def draw_card(self):
        return random.randint(1, 11)  # 11 - это туз
    
    def calculate_score(self, cards):
        score = sum(cards)
        aces = cards.count(11)
        
        # Обработка тузов
        while score > 21 and aces > 0:
            score -= 10
            aces -= 1
        
        return score
    
    def create_embed(self):
        user_score = self.calculate_score(self.user_cards)
        dealer_score = self.calculate_score([self.dealer_cards[0]])  # Показываем только одну карту дилера
        
        embed = discord.Embed(title="🃏 Блэкджек", color=0x2ecc71)
        
        # Отображаем карты пользователя
        user_cards_display = ' '.join([f'`{card}`' for card in self.user_cards])
        embed.add_field(
            name="Ваши карты",
            value=f"{user_cards_display} (Очки: {user_score})",
            inline=False
        )
        
        # Отображаем карты дилера (только первую видна)
        dealer_cards_display = f'`{self.dealer_cards[0]}` ' + ' '.join(['`?`' for _ in range(len(self.dealer_cards)-1)])
        embed.add_field(
            name="Карты дилера", 
            value=f"{dealer_cards_display} (Очки: {dealer_score}+)",
            inline=False
        )
        
        embed.add_field(name="Ставка", value=f"{self.bet} {EMOJIS['coin']}", inline=True)
        
        return embed
    
    @discord.ui.button(label='Взять карту', style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: Button):
        if self.game_over:
            await interaction.response.send_message("Игра уже завершена!", ephemeral=True)
            return
        
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Эта игра не для вас!", ephemeral=True)
            return
        
        # Добавляем карту
        self.user_cards.append(self.draw_card())
        user_score = self.calculate_score(self.user_cards)
        
        # Проверяем перебор
        if user_score > 21:
            # Отключаем кнопки перед завершением игры
            for item in self.children:
                item.disabled = True
            
            embed = self.create_embed()
            embed.add_field(name="Результат", value="Перебор! Вы проиграли.", inline=False)
            embed.color = 0xff0000
            
            await interaction.response.edit_message(embed=embed, view=self)
            await self.end_game(interaction, "перебор")
        else:
            # Просто обновляем сообщение с новыми картами
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='Остановиться', style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: Button):
        if self.game_over:
            await interaction.response.send_message("Игра уже завершена!", ephemeral=True)
            return
        
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Эта игра не для вас!", ephemeral=True)
            return
        
        # Отключаем кнопки
        for item in self.children:
            item.disabled = True
        
        # Дилер берет карты пока не наберет 17 или больше
        dealer_turn_embed = self.create_embed()
        dealer_turn_embed.add_field(name="Действие", value="Дилер берет карты...", inline=False)
        await interaction.response.edit_message(embed=dealer_turn_embed, view=self)
        
        # Даем немного времени для отображения
        await asyncio.sleep(1)
        
        while self.calculate_score(self.dealer_cards) < 17:
            self.dealer_cards.append(self.draw_card())
            # Обновляем сообщение после каждой карты дилера
            dealer_turn_embed = self.create_embed()
            dealer_turn_embed.add_field(name="Действие", value="Дилер берет карты...", inline=False)
            await interaction.edit_original_response(embed=dealer_turn_embed)
            await asyncio.sleep(1)
        
        await self.end_game(interaction, "stand")
    
    async def end_game(self, interaction: discord.Interaction, reason):
        self.game_over = True
        user_score = self.calculate_score(self.user_cards)
        dealer_score = self.calculate_score(self.dealer_cards)
        
        # Определяем победителя
        if reason == "перебор":
            result = "lose"
            result_text = "Перебор! Вы проиграли."
        elif user_score > dealer_score or dealer_score > 21:
            result = "win"
            result_text = "Вы выиграли!"
        elif user_score == dealer_score:
            result = "push"
            result_text = "Ничья!"
        else:
            result = "lose"
            result_text = "Дилер выиграл."
        
        # Обработка выигрыша
        if result == "win":
            base_winnings = int(self.bet * 2)
            # Применяем бафы к выигрышу
            winnings = db.apply_buff_to_amount(self.user_id, base_winnings, 'blackjack_bonus')
            winnings = db.apply_buff_to_amount(self.user_id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(self.user_id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(self.user_id, winnings, 'all_bonus')
            
            db.update_balance(self.user_id, winnings)
            db.log_transaction(self.user_id, 'blackjack_win', winnings, description="Победа в блэкджеке")
            db.update_user_stat(self.user_id, 'blackjack_wins')
            db.update_consecutive_wins(self.user_id, True)
            color = 0x00ff00
        elif result == "push":
            # Возвращаем ставку при ничье
            db.update_balance(self.user_id, self.bet)
            color = 0xffff00
        else:
            # Применяем баф защиты от проигрышей
            loss = db.apply_buff_to_amount(self.user_id, self.bet, 'loss_protection')
            db.update_balance(self.user_id, -loss)
            db.log_transaction(self.user_id, 'blackjack_loss', -loss, description="Проигрыш в блэкджеке")
            db.update_consecutive_wins(self.user_id, False)
            color = 0xff0000
        
        # Создаем финальное embed
        embed = discord.Embed(title="🃏 Результат блэкджека", color=color)
        
        # Отображаем все карты пользователя
        user_cards_display = ' '.join([f'`{card}`' for card in self.user_cards])
        embed.add_field(
            name="Ваши карты",
            value=f"{user_cards_display} (Очки: {user_score})",
            inline=False
        )
        
        # Отображаем все карты дилера
        dealer_cards_display = ' '.join([f'`{card}`' for card in self.dealer_cards])
        embed.add_field(
            name="Карты дилера",
            value=f"{dealer_cards_display} (Очки: {dealer_score})",
            inline=False
        )
        
        embed.add_field(name="Результат", value=result_text, inline=False)
        
        if result == "win":
            embed.add_field(name="Выигрыш", value=f"{winnings} {EMOJIS['coin']}", inline=True)
        elif result == "push":
            embed.add_field(name="Результат", value="Ставка возвращена", inline=True)
        else:
            embed.add_field(name="Потеряно", value=f"{loss} {EMOJIS['coin']}", inline=True)
        
        # Обновляем сообщение с финальным результатом
        await interaction.edit_original_response(embed=embed, view=None)

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

# КОМАНДЫ БОТА

# Экономические команды
@bot.tree.command(name="balance", description="Показать ваш баланс")
@app_commands.describe(user="Пользователь, чей баланс показать (опционально)")
async def balance(interaction: discord.Interaction, user: discord.Member = None):
    try:
        user = user or interaction.user
        user_data = db.get_user(user.id)
        
        # БЕЗОПАСНОЕ ПОЛУЧЕНИЕ ДАННЫХ С ПРОВЕРКОЙ ИНДЕКСОВ
        balance_amount = user_data[1] if len(user_data) > 1 else 100
        daily_streak = user_data[2] if len(user_data) > 2 else 0
        inventory_json = user_data[4] if len(user_data) > 4 else '{"cases": {}, "items": {}}'
        
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
        embed.add_field(name="Баланс", value=f"{balance_amount} {EMOJIS['coin']}", inline=True)
        embed.add_field(name="Ежедневная серия", value=f"{daily_streak} дней", inline=True)
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

@bot.tree.command(name="daily", description="Получить ежедневную награду")
async def daily(interaction: discord.Interaction):
    try:
        user_data = db.get_user_safe(interaction.user.id)
        
        # БЕЗОПАСНЫЙ ДОСТУП К ДАННЫМ
        last_daily_str = user_data[3] if len(user_data) > 3 else None
        daily_streak = user_data[2] if len(user_data) > 2 else 0
        
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


@bot.tree.command(name="items", description="Показать все доступные предметы")
async def items_list(interaction: discord.Interaction):
    try:
        items = db.get_all_items_safe()
        
        embed = discord.Embed(title="📦 Все доступные предметы", color=0x3498db)
        
        for item in items:
            try:
                rarity_emoji = {
                    'common': '⚪',
                    'uncommon': '🟢', 
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟠',
                    'mythic': '🟡'
                }.get(item[4] if len(item) > 4 else 'common', '⚪')
                
                buff_info = f"**Баф:** {item[7]}\n" if len(item) > 7 and item[7] else ""
                embed.add_field(
                    name=f"{rarity_emoji} {item[1]}",
                    value=f"{item[2]}\n{buff_info}**Цена:** {item[3]} {EMOJIS['coin']}",
                    inline=False
                )
            except Exception as e:
                print(f"⚠️ Ошибка обработки предмета {item}: {e}")
                continue
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде items: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке предметов!", ephemeral=True)

@bot.tree.command(name="myitems", description="Показать ваши предметы")
async def my_items(interaction: discord.Interaction):
    try:
        inventory = db.get_user_inventory_safe(interaction.user.id)
        
        embed = discord.Embed(title=f"📦 Предметы {interaction.user.display_name}", color=0x3498db)
        
        items = inventory.get("items", {})
        if not items:
            embed.description = "У вас пока нет предметов. Открывайте кейсы или покупайте на маркетплейсе!"
            await interaction.response.send_message(embed=embed)
            return
        
        for item_id, count in items.items():
            try:
                if item_id.isdigit():
                    item_data = db.get_item(int(item_id))
                    if item_data:
                        rarity_emoji = {
                            'common': '⚪',
                            'uncommon': '🟢', 
                            'rare': '🔵',
                            'epic': '🟣',
                            'legendary': '🟠',
                            'mythic': '🟡'
                        }.get(item_data[4] if len(item_data) > 4 else 'common', '⚪')
                        
                        buff_info = f"\n**Эффект:** {item_data[7]}" if len(item_data) > 7 and item_data[7] else ""
                        embed.add_field(
                            name=f"{rarity_emoji} {item_data[1]} ×{count}",
                            value=f"{item_data[2]}{buff_info}",
                            inline=True
                        )
            except Exception as e:
                print(f"⚠️ Ошибка обработки предмета {item_id}: {e}")
                continue
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде myitems: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке предметов!", ephemeral=True)
@bot.tree.command(name="admin_giveitem", description="Выдать предмет пользователю (админ)")
@app_commands.describe(user="Пользователь", item_name="Название предмета")
@is_admin()
async def admin_giveitem(interaction: discord.Interaction, user: discord.Member, item_name: str):
    try:
        # Проверяем существование предмета
        item_data = db.get_item_by_name(item_name)
        if not item_data:
            # Показываем список доступных предметов
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
        embed.add_field(name="Эффект", value=item_data[7] if item_data[7] else "Нет бафа")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

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
    
    # Применяем баф к комиссии (если есть)
    transfer_amount = db.apply_buff_to_amount(interaction.user.id, amount, 'transfer_bonus')
    
    db.update_balance(interaction.user.id, -transfer_amount)
    db.update_balance(user.id, amount)  # Получатель получает полную сумму
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

# Команды кейсов
@bot.tree.command(name="cases", description="Показать список доступных кейсов")
async def cases_list(interaction: discord.Interaction):
    try:
        cases = db.get_cases()
        
        if not cases:
            await interaction.response.send_message("Кейсы не найдены!", ephemeral=True)
            return
        
        # Разбиваем на страницы по 5 кейсов
        pages = []
        current_page = []
        
        for i, case in enumerate(cases):
            if i > 0 and i % 5 == 0:
                pages.append(current_page)
                current_page = []
            current_page.append(case)
        
        if current_page:
            pages.append(current_page)
        
        view = CasesView(pages, interaction.user.id)
        embed = view.create_embed()
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        print(f"❌ Ошибка в команде cases: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке кейсов!", ephemeral=True)
    
class CasesView(View):
    def __init__(self, pages, author_id):
        super().__init__(timeout=60)
        self.pages = pages
        self.current_page = 0
        self.total_pages = len(pages)
        self.author_id = author_id

    @discord.ui.button(label='⬅️ Назад', style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Это не ваша пагинация!", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='➡️ Вперед', style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Это не ваша пагинация!", ephemeral=True)
            return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self):
        page_cases = self.pages[self.current_page]
        embed = discord.Embed(
            title=f"🎁 Доступные кейсы (Страница {self.current_page + 1}/{self.total_pages})", 
            color=0xff69b4
        )
        
        for case in page_cases:
            rewards = json.loads(case[3])
            rewards_desc = "\n".join([f"• {r['type']} ({r['chance']*100:.1f}%)" for r in rewards[:3]])
            if len(rewards) > 3:
                rewards_desc += f"\n• ... и ещё {len(rewards) - 3} наград"
            embed.add_field(
                name=f"{case[1]} - {case[2]} {EMOJIS['coin']} (ID: {case[0]})",
                value=rewards_desc,
                inline=False
            )
        
        return embed

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

@bot.tree.command(name="inventory", description="Показать ваш инвентарь")
async def inventory(interaction: discord.Interaction):
    try:
        inventory_data = db.get_user_inventory_safe(interaction.user.id)
        
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
                    if item_id.isdigit():
                        item_data = db.get_item(int(item_id))
                        if item_data:
                            item_name = item_data[1]
                            buff_desc = f" - {item_data[7]}" if len(item_data) > 7 and item_data[7] else ""
                            items_text += f"• {item_name}{buff_desc} ×{count}\n"
                        else:
                            items_text += f"• Предмет ID:{item_id} ×{count}\n"
                    else:
                        items_text += f"• {item_id} ×{count}\n"
                except Exception as e:
                    print(f"⚠️ Ошибка обработки предмета {item_id}: {e}")
                    items_text += f"• Предмет ID:{item_id} ×{count}\n"
            embed.add_field(name="📦 Предметы", value=items_text, inline=False)
        else:
            embed.add_field(name="📦 Предметы", value="Пусто", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде inventory: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке инвентаря!", ephemeral=True)
    
    # Показываем активные бафы
    buffs = db.get_user_buffs(interaction.user.id)
    if buffs:
        buffs_text = "\n".join([f"• **{buff['item_name']}**: {buff['description']}" for buff in buffs.values()])
        embed.add_field(name="🎯 Активные бафы", value=buffs_text, inline=False)
    
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
    
    # Обновляем статистику открытия кейсов
    db.update_user_stat(interaction.user.id, 'cases_opened')
    
    embed = discord.Embed(
        title=f"🎉 {case['name']} открыт!",
        description=reward_text,
        color=0x00ff00
    )
    embed.set_footer(text="Кейс из инвентаря")
    
    await interaction.edit_original_response(embed=embed)

# Команды маркетплейса
@bot.tree.command(name="market", description="Взаимодействие с маркетплейсом")
@app_commands.describe(action="Действие на маркетплейсе", item_name="Название предмета (для покупки/продажи)", price="Цена (для продажи)")
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
                    # БЕЗОПАСНЫЙ ДОСТУП К ДАННЫМ
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
                await interaction.response.send_message("У вас нет такого предмета в инвентаре!", ephemeral=True)
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
            
            # БЕЗОПАСНЫЙ ДОСТУП К ДАННЫМ ТОВАРА
            market_item_id = item[0] if len(item) > 0 else None
            seller_id = item[1] if len(item) > 1 else None
            market_item_name = item[2] if len(item) > 2 else "Неизвестный предмет"
            item_price = item[3] if len(item) > 3 else 0
            
            if not seller_id:
                await interaction.response.send_message("Ошибка: продавец не найден!", ephemeral=True)
                return
            
            user_data = db.get_user(interaction.user.id)
            user_balance = user_data[1] if len(user_data) > 1 else 0
            
            if user_balance < item_price:
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

# МИНИ-ИГРЫ

@bot.tree.command(name="roulette", description="Сыграть в рулетку")
@app_commands.describe(bet="Ставка в монетах")
async def roulette(interaction: discord.Interaction, bet: int):
    try:
        user_data = db.get_user(interaction.user.id)
        
        if user_data[1] < bet:
            await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
            return
        
        winning_number = random.randint(0, 36)
        user_number = random.randint(0, 36)
        
        # Анимация вращения
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
            
            result = f"🎉 ДЖЕКПОТ! Ваше число: {user_number}\nВыпало: {winning_number}\nВыигрыш: {winnings} {EMOJIS['coin']} (x{multiplier})"
            color = 0x00ff00
        else:
            loss = db.apply_buff_to_amount(interaction.user.id, bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'roulette_loss', -loss, description="Проигрыш в рулетке")
            db.update_consecutive_wins(interaction.user.id, False)
            
            result = f"💀 Проигрыш! Ваше число: {user_number}\nВыпало: {winning_number}\nПотеряно: {loss} {EMOJIS['coin']}"
            color = 0xff0000
        
        embed = discord.Embed(
            title=f"🎰 Рулетка - Ставка: {bet} {EMOJIS['coin']}",
            description=result,
            color=color
        )
        await interaction.edit_original_response(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде roulette: {e}")
        await interaction.response.send_message("❌ Произошла ошибка в рулетке!", ephemeral=True)

@bot.tree.command(name="coinflip", description="Подбросить монету на ставку (50/50 шанс)")
@app_commands.describe(bet="Ставка в монетах")
async def coinflip(interaction: discord.Interaction, bet: int):
    user_data = db.get_user(interaction.user.id)
    
    if user_data[1] < bet:
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
    
    if user_data[1] < bet:
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
        # ИСПОЛЬЗУЕМ БЕЗОПАСНЫЙ МЕТОД ПОЛУЧЕНИЯ ПОЛЬЗОВАТЕЛЯ
        user_data = db.get_user(interaction.user.id)
        balance = user_data[1] if len(user_data) > 1 else 100
        
        if balance < bet:
            await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
            return
    
    except Exception as e:
        print(f"❌ Ошибка в команде slots при проверке баланса: {e}")
        error_embed = discord.Embed(
            title="🎰 Ошибка слотов",
            description="Произошла ошибка при проверке баланса. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    # Символы для слотов
    symbols = ['🍒', '🍋', '🍊', '🍇', '🔔', '💎', '7️⃣']
    
    # Анимация вращения
    embed = discord.Embed(title="🎰 Игровые автоматы", description="Вращение...", color=0xff69b4)
    message = await interaction.response.send_message(embed=embed)
    
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
            # Джекпот
            multiplier = 100
            db.update_user_stat(interaction.user.id, 'slot_wins')
        elif final_result[0] == '7️⃣':
            multiplier = 50
        elif final_result[0] == '🔔':
            multiplier = 20
        else:
            multiplier = 5
        
        base_winnings = bet * multiplier
        # Применяем бафы к выигрышу
        winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'slot_bonus')
        winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
        winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
        winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
        
        db.update_balance(interaction.user.id, winnings)
        db.log_transaction(interaction.user.id, 'slots_win', winnings, description=f"Победа в слотах x{multiplier}")
        db.update_consecutive_wins(interaction.user.id, True)
        
        result_text = f"ДЖЕКПОТ! x{multiplier}\nВыигрыш: {winnings} {EMOJIS['coin']}"
        color = 0x00ff00
    elif final_result[0] == final_result[1] or final_result[1] == final_result[2]:
        # Два одинаковых символа
        base_winnings = bet * 2
        # Применяем бафы к выигрышу
        winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'slot_bonus')
        winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
        winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
        winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
        
        db.update_balance(interaction.user.id, winnings)
        db.log_transaction(interaction.user.id, 'slots_win', winnings, description="Победа в слотах x2")
        db.update_consecutive_wins(interaction.user.id, True)
        
        result_text = f"Два в ряд! x2\nВыигрыш: {winnings} {EMOJIS['coin']}"
        color = 0x00ff00
    else:
        # Применяем баф защиты от проигрышей
        loss = db.apply_buff_to_amount(interaction.user.id, bet, 'loss_protection')
        db.update_balance(interaction.user.id, -loss)
        db.log_transaction(interaction.user.id, 'slots_loss', -loss, description="Проигрыш в слотах")
        db.update_consecutive_wins(interaction.user.id, False)
        
        result_text = f"Повезет в следующий раз!\nПотеряно: {loss} {EMOJIS['coin']}"
        color = 0xff0000
    
    embed.add_field(name="Результат", value=result_text, inline=False)
    embed.add_field(name="Ставка", value=f"{bet} {EMOJIS['coin']}", inline=True)
    embed.color = color
    
    await interaction.edit_original_response(embed=embed)

# ДУЭЛЬ С УЧЕТОМ БАФОВ
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
    
    # Показываем бафы участников
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

# КРАЖА С УЧЕТОМ БАФОВ
@bot.tree.command(name="steal", description="Попытаться украсть монеты у другого пользователя (КД 30 мин)")
@app_commands.describe(user="Пользователь, у которого крадем")
@app_commands.checks.cooldown(1, 1800.0, key=lambda i: (i.guild_id, i.user.id))
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
    
    base_success_chance = 0.3
    # Применяем бафы к шансу кражи
    success_chance = db.apply_buff_to_chance(interaction.user.id, base_success_chance, 'steal_chance')
    success_chance = db.apply_buff_to_chance(interaction.user.id, success_chance, 'steal_bonus')
    
    # Применяем баф защиты цели
    target_protection = db.apply_buff_to_chance(user.id, 1.0, 'steal_protection')
    success_chance = success_chance * (1 - target_protection)
    
    if random.random() <= success_chance:
        # Применяем бафы к украденной сумме
        stolen_amount = db.apply_buff_to_amount(interaction.user.id, amount, 'multiplier')
        stolen_amount = db.apply_buff_to_amount(interaction.user.id, stolen_amount, 'all_bonus')
        
        db.update_balance(interaction.user.id, stolen_amount)
        db.update_balance(user.id, -amount)  # Цель теряет оригинальную сумму
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
        # Применяем баф защиты от проигрышей к штрафу
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

# Обработчик кд для /steal
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

# КВЕСТЫ И ДОСТИЖЕНИЯ
@bot.tree.command(name="quest", description="Получить случайный квест")
@app_commands.checks.cooldown(1, 10800.0)  # 3 часа КД
async def quest(interaction: discord.Interaction):
    try:
        # Получаем случайный квест
        quest_id, quest_data = random.choice(list(QUESTS.items()))
        
        # Добавляем квест пользователю
        if db.add_user_quest(interaction.user.id, quest_id):
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
            await interaction.response.send_message("❌ Не удалось выдать квест!", ephemeral=True)
            
    except Exception as e:
        print(f"❌ Ошибка в команде quest: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при получении квеста!", ephemeral=True)
@bot.tree.command(name="achievements", description="Показать ваши достижения")
async def achievements(interaction: discord.Interaction):
    cursor = db.conn.cursor()
    cursor.execute('SELECT achievement_id FROM achievements WHERE user_id = %s', (interaction.user.id,))
    user_achievements = [row[0] for row in cursor.fetchall()]
    
    embed = discord.Embed(title="🏅 Ваши достижения", color=0xffd700)
    
    unlocked_count = 0
    for achievement_id, achievement in ACHIEVEMENTS.items():
        status = "✅" if achievement_id in user_achievements else "❌"
        if achievement_id in user_achievements:
            unlocked_count += 1
            
        embed.add_field(
            name=f"{status} {achievement['name']}",
            value=f"{achievement['description']}\nНаграда: {achievement['reward']} {EMOJIS['coin']}",
            inline=False
        )
    
    embed.set_footer(text=f"Разблокировано: {unlocked_count}/{len(ACHIEVEMENTS)}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stats", description="Показать вашу статистику")
async def stats(interaction: discord.Interaction):
    cursor = db.conn.cursor()
    cursor.execute('SELECT * FROM user_stats WHERE user_id = %s', (interaction.user.id,))
    stats_data = cursor.fetchone()
    
    if not stats_data:
        # Создаем запись статистики если её нет
        cursor.execute('INSERT INTO user_stats (user_id) VALUES (%s)', (interaction.user.id,))
        db.conn.commit()
        cursor.execute('SELECT * FROM user_stats WHERE user_id = %s', (interaction.user.id,))
        stats_data = cursor.fetchone()
    
    # Получаем активные бафы
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
    
    # Показываем активные бафы
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

@bot.tree.command(name="admin_database", description="Просмотр содержимого базы данных (админ)")
@app_commands.describe(table="Таблица для просмотра")
@app_commands.choices(table=[
    app_commands.Choice(name="👥 Пользователи", value="users"),
    app_commands.Choice(name="💰 Транзакции", value="transactions"),
    app_commands.Choice(name="🎁 Кейсы", value="cases"),
    app_commands.Choice(name="📦 Предметы", value="items"),
    app_commands.Choice(name="🏪 Маркет", value="market"),
    app_commands.Choice(name="📊 Статистика", value="stats")
])
@is_admin()
async def admin_database(interaction: discord.Interaction, table: app_commands.Choice[str]):
    try:
        if table.value == "users":
            users = db.get_all_users()
            embed = discord.Embed(title="👥 База данных: Пользователи", color=0x3498db)
            
            for user in users[:10]:
                embed.add_field(
                    name=f"ID: {user[0]}",
                    value=f"Баланс: {user[1]} {EMOJIS['coin']}\nСерия: {user[2]} дней",
                    inline=False
                )
            
            if len(users) > 10:
                embed.set_footer(text=f"Показано 10 из {len(users)} пользователей")
                
        elif table.value == "transactions":
            transactions = db.get_all_transactions(10)
            embed = discord.Embed(title="💰 База данных: Транзакции", color=0x3498db)
            
            for trans in transactions:
                embed.add_field(
                    name=f"#{trans[0]} {trans[2]}",
                    value=f"Сумма: {trans[3]} {EMOJIS['coin']}\nID пользователя: {trans[1]}\nОписание: {trans[5]}",
                    inline=False
                )
                
        elif table.value == "cases":
            cases = db.get_cases()
            embed = discord.Embed(title="🎁 База данных: Кейсы", color=0x3498db)
            
            for case in cases:
                embed.add_field(
                    name=f"#{case[0]} {case[1]}",
                    value=f"Цена: {case[2]} {EMOJIS['coin']}",
                    inline=False
                )
                
        elif table.value == "items":
            items = db.get_all_items()
            embed = discord.Embed(title="📦 База данных: Предметы", color=0x3498db)
            
            for item in items:
                buff_info = f" | {item[7]}" if item[7] else ""
                embed.add_field(
                    name=f"#{item[0]} {item[1]}",
                    value=f"Цена: {item[3]} {EMOJIS['coin']}\nРедкость: {item[4]}{buff_info}",
                    inline=False
                )
                
        elif table.value == "market":
            cursor = db.conn.cursor()
            cursor.execute('SELECT * FROM market LIMIT 10')
            market_items = cursor.fetchall()
            
            embed = discord.Embed(title="🏪 База данных: Маркет", color=0x3498db)
            
            for item in market_items:
                embed.add_field(
                    name=f"#{item[0]} {item[2]}",
                    value=f"Цена: {item[3]} {EMOJIS['coin']}\nПродавец ID: {item[1]}",
                    inline=False
                )
        
        elif table.value == "stats":
            cursor = db.conn.cursor()
            cursor.execute('SELECT * FROM user_stats ORDER BY total_earned DESC LIMIT 10')
            stats = cursor.fetchall()
            
            embed = discord.Embed(title="📊 База данных: Статистика", color=0x3498db)
            
            for stat in stats:
                user = bot.get_user(stat[0])
                name = user.display_name if user else f"User#{stat[0]}"
                embed.add_field(
                    name=f"{name}",
                    value=f"Кейсы: {stat[1]}, Заработано: {stat[10]} {EMOJIS['coin']}",
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

@bot.tree.command(name="admin_init_db", description="Принудительно инициализировать базу данных (админ)")
@is_admin()
async def admin_init_db(interaction: discord.Interaction):
    try:
        db.create_tables()
        embed = discord.Embed(
            title="✅ База данных инициализирована",
            description="Все таблицы успешно созданы!",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Ошибка инициализации БД",
            description=f"Ошибка: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# КОМАНДА ПОМОЩИ
@bot.tree.command(name="help", description="Показать информацию о боте и список команд")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Экономический Бот - Помощь",
        description="Добро пожаловать в экономическую игру! Этот бот предоставляет полную систему экономики с кейсами, мини-играми, маркетплейсом, достижениями и системой бафов.",
        color=0x3498db
    )
    
    # Основная информация о боте
    embed.add_field(
        name="📊 О боте",
        value="• Внутренняя валюта: монеты 🪙\n• Ежедневные бонусы 📅\n• Система кейсов 🎁\n• Маркетплейс 🏪\n• Мини-игры 🎰\n• Достижения 🏅\n• Система бафов 🎯",
        inline=False
    )
    
    # Экономические команды
    embed.add_field(
        name="💰 Экономические команды",
        value="""**/balance** [пользователь] - Показать баланс и активные бафы
**/daily** - Получить ежедневную награду (учитывает бафы)
**/pay** @пользователь сумма - Перевести монеты
**/inventory** - Показать инвентарь и активные бафы
**/stats** - Показать статистику""",
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
**/market** buy ID_товара - Купить товар (баф сохраняется)""",
        inline=False
    )
    
    # Мини-игры
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
    
    # Достижения и лидерборды
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
**/admin_database** таблица - Просмотр базы данных
**/admin_broadcast** сообщение - Отправить объявление
**/admin_reset_market** Очистить маркетплейс
**/admin_init_db** - Принудительно инициализировать БД""",
            inline=False
        )
    
    embed.set_footer(text="Используйте / для просмотра всех команд")
    
    await interaction.response.send_message(embed=embed)

# СИСТЕМА КВЕСТОВ И ПРОГРЕССА
@bot.tree.command(name="quests", description="Показать ваши активные квесты")
async def quests(interaction: discord.Interaction):
    try:
        user_quests = db.get_user_quests(interaction.user.id)
        
        embed = discord.Embed(title=f"{EMOJIS['quest']} Ваши квесты", color=0x9b59b6)
        
        if not user_quests:
            embed.description = "У вас пока нет активных квестов. Используйте `/quest` чтобы получить новый!"
            await interaction.response.send_message(embed=embed)
            return
        
        completed_quests = 0
        for quest_row in user_quests:
            quest_id, progress, completed = quest_row
            if quest_id in QUESTS:
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
        await interaction.response.send_message("❌ Произошла ошибка при загрузке квестов!", ephemeral=True)

# КОМАНДА ПЕРЕЗАГРУЗКИ БАФОВ
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

# СИСТЕМА УВЕДОМЛЕНИЙ О ДОСТИЖЕНИЯХ
async def notify_achievement(channel, user, achievement_id):
    achievement = ACHIEVEMENTS[achievement_id]
    embed = discord.Embed(
        title="🏆 Новое достижение!",
        description=f"Поздравляем {user.mention} с получением достижения!",
        color=0xffd700
    )
    embed.add_field(name=achievement['name'], value=achievement['description'], inline=False)
    embed.add_field(name="Награда", value=f"{achievement['reward']} {EMOJIS['coin']}", inline=True)
    
    try:
        await channel.send(embed=embed)
    except:
        pass  # Игнорируем ошибки отправки

# СИСТЕМА ВРЕМЕННЫХ БОНУСОВ
active_bonuses = {}

class BonusSystem:
    @staticmethod
    def add_bonus(user_id, bonus_type, multiplier, duration_hours):
        expiry = datetime.datetime.now() + datetime.timedelta(hours=duration_hours)
        if user_id not in active_bonuses:
            active_bonuses[user_id] = {}
        active_bonuses[user_id][bonus_type] = {
            'multiplier': multiplier,
            'expiry': expiry
        }
    
    @staticmethod
    def get_bonus_multiplier(user_id, bonus_type):
        if user_id not in active_bonuses or bonus_type not in active_bonuses[user_id]:
            return 1.0
        
        bonus = active_bonuses[user_id][bonus_type]
        if datetime.datetime.now() > bonus['expiry']:
            del active_bonuses[user_id][bonus_type]
            if not active_bonuses[user_id]:
                del active_bonuses[user_id]
            return 1.0
        
        return bonus['multiplier']
    
    @staticmethod
    def cleanup_expired():
        current_time = datetime.datetime.now()
        expired_users = []
        
        for user_id, bonuses in active_bonuses.items():
            expired_bonuses = []
            for bonus_type, bonus in bonuses.items():
                if current_time > bonus['expiry']:
                    expired_bonuses.append(bonus_type)
            
            for bonus_type in expired_bonuses:
                del bonuses[bonus_type]
            
            if not bonuses:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del active_bonuses[user_id]

# ЗАДАЧА ДЛЯ ОЧИСТКИ ПРОСРОЧЕННЫХ БОНУСОВ
@tasks.loop(minutes=30)
async def cleanup_bonuses():
    BonusSystem.cleanup_expired()

# КОМАНДА ДЛЯ ПРОВЕРКИ ВРЕМЕННЫХ БОНУСОВ
@bot.tree.command(name="activebonuses", description="Показать активные временные бонусы")
async def active_bonuses_cmd(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if user_id not in active_bonuses or not active_bonuses[user_id]:
        embed = discord.Embed(
            title="⏰ Активные бонусы",
            description="У вас нет активных временных бонусов.",
            color=0xffff00
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(title="⏰ Ваши активные бонусы", color=0x00ff00)
    
    for bonus_type, bonus in active_bonuses[user_id].items():
        time_left = bonus['expiry'] - datetime.datetime.now()
        hours_left = max(0, int(time_left.total_seconds() // 3600))
        minutes_left = max(0, int((time_left.total_seconds() % 3600) // 60))
        
        embed.add_field(
            name=f"✨ {bonus_type.upper()} бонус",
            value=f"Множитель: x{bonus['multiplier']}\nОсталось: {hours_left}ч {minutes_left}м",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="admin_reset_market", description="Очистить маркетплейс (админ)")
@is_admin()
async def admin_reset_market(interaction: discord.Interaction):
    try:
        cursor = db.conn.cursor()
        cursor.execute('DELETE FROM market')
        db.conn.commit()
        
        embed = discord.Embed(
            title="🔄 Маркетплейс очищен",
            description="Все товары удалены с маркетплейса.",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Ошибка очистки маркетплейса",
            description=f"Ошибка: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="debug_market", description="Проверить структуру маркетплейса (админ)")
@is_admin()
async def debug_market(interaction: discord.Interaction):
    try:
        cursor = db.conn.cursor()
        
        # Проверяем структуру таблицы
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'market'
        """)
        columns = cursor.fetchall()
        
        # Проверяем существующие записи
        cursor.execute('SELECT * FROM market LIMIT 5')
        items = cursor.fetchall()
        
        embed = discord.Embed(title="🐛 Отладка маркетплейса", color=0x3498db)
        
        # Показываем структуру таблицы
        columns_info = "\n".join([f"• {col[0]} ({col[1]}) - nullable: {col[2]}" for col in columns])
        embed.add_field(name="📊 Структура таблицы", value=columns_info, inline=False)
        
        # Показываем примеры записей
        if items:
            items_info = ""
            for item in items:
                items_info += f"• {item}\n"
            embed.add_field(name="📝 Примеры записей", value=items_info, inline=False)
        else:
            embed.add_field(name="📝 Записи", value="Таблица пуста", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Ошибка отладки",
            description=f"Ошибка: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# СИСТЕМА ВОССТАНОВЛЕНИЯ ДАННЫХ
@bot.tree.command(name="recover", description="Восстановить данные пользователя (если есть проблемы)")
async def recover_data(interaction: discord.Interaction):
    # Создаем запись пользователя если её нет
    user_data = db.get_user(interaction.user.id)
    
    # Восстанавливаем инвентарь если он поврежден
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

# ОБРАБОТЧИКИ СОБЫТИЙ БОТА
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user.name} успешно запущен!')
    print(f'🔗 ID бота: {bot.user.id}')
    print(f'🌐 Количество серверов: {len(bot.guilds)}')
    
    # Запускаем фоновые задачи
    cleanup_bonuses.start()
    
    # Синхронизация команд
    try:
        synced = await bot.tree.sync()
        print(f'✅ Успешно синхронизировано {len(synced)} команд')
    except Exception as e:
        print(f'❌ Ошибка синхронизации команд: {e}')
    
    # Устанавливаем статус бота
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="экономику сервера | /help"
    )
    await bot.change_presence(activity=activity)
    
    # ИСПРАВЛЕНИЕ: Проверяем тип канала перед отправкой
    try:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel and hasattr(channel, 'send') and isinstance(channel, (discord.TextChannel, discord.Thread)):
            embed = discord.Embed(
                title="🟢 Бот запущен",
                description=f"Бот {bot.user.mention} успешно запущен и готов к работе!",
                color=0x00ff00,
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Серверов", value=len(bot.guilds), inline=True)
            embed.add_field(name="Пинг", value=f"{round(bot.latency * 1000)}мс", inline=True)
            embed.add_field(name="Версия", value="2.0", inline=True)
            await channel.send(embed=embed)
        else:
            print(f"⚠️ Канал с ID {LOG_CHANNEL_ID} не найден или недоступен для отправки сообщений")
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения о запуске: {e}")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    try:
        # Пропускаем обработку, если это не команда
        if not interaction.type == discord.InteractionType.application_command:
            return
            
        # Логируем использование команд
        print(f"🔹 Команда: {interaction.data.get('name')} | Пользователь: {interaction.user} | Сервер: {interaction.guild}")
        
    except Exception as e:
        print(f"❌ Ошибка в on_interaction: {e}")

# Добавьте обработку timeout для View
@bot.event
async def on_error(event, *args, **kwargs):
    print(f"❌ Ошибка в событии {event}: {args} {kwargs}")

@bot.event
async def on_guild_join(guild):
    print(f'✅ Бот добавлен на сервер: {guild.name} (ID: {guild.id})')
    
    # Отправляем приветственное сообщение
    try:
        system_channel = guild.system_channel
        if system_channel and system_channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="🎮 Добро пожаловать в экономическую игру!",
                description="Спасибо за добавление бота на ваш сервер!",
                color=0x3498db
            )
            embed.add_field(
                name="🚀 Начало работы",
                value="Используйте `/help` для просмотра всех команд\n`/balance` чтобы проверить баланс\n`/daily` для получения ежедневной награды",
                inline=False
            )
            embed.add_field(
                name="🎯 Основные возможности",
                value="• Полная экономическая система\n• Система кейсов с наградами\n• Мини-игры и дуэли\n• Маркетплейс для торговли\n• Достижения и квесты\n• Система бафов от предметов",
                inline=False
            )
            embed.set_footer(text="Для помощи используйте /help или /commands")
            
            await system_channel.send(embed=embed)
    except Exception as e:
        print(f"❌ Ошибка отправки приветственного сообщения: {e}")
    
    # Логируем в лог-канал
    try:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="✅ Бот добавлен на новый сервер",
                description=f"Сервер: **{guild.name}**\nID: `{guild.id}`\nУчастников: {guild.member_count}",
                color=0x00ff00,
                timestamp=datetime.datetime.now()
            )
            await channel.send(embed=embed)
    except Exception as e:
        print(f"❌ Ошибка логирования добавления на сервер: {e}")

@bot.event
async def on_guild_remove(guild):
    print(f'❌ Бот удален с сервера: {guild.name} (ID: {guild.id})')
    
    # Логируем в лог-канал
    try:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="❌ Бот удален с сервера",
                description=f"Сервер: **{guild.name}**\nID: `{guild.id}`",
                color=0xff0000,
                timestamp=datetime.datetime.now()
            )
            await channel.send(embed=embed)
    except Exception as e:
        print(f"❌ Ошибка логирования удаления с сервера: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        await ctx.send(f"❌ Эта команда на перезарядке! Попробуйте через {minutes}м {seconds}с", delete_after=10)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас недостаточно прав для использования этой команды!", delete_after=10)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Команда не найдена! Используйте `/help` для списка команд", delete_after=10)
    else:
        print(f"❌ Необработанная ошибка: {error}")

# КОМАНДА ДЛЯ ПРОВЕРКИ ПИНГА
@bot.tree.command(name="ping", description="Проверить пинг бота")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Понг!",
        description=f"Задержка бота: {round(bot.latency * 1000)}мс",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="debug_db", description="Проверить состояние базы данных (отладка)")
@is_admin()
async def debug_db(interaction: discord.Interaction):
    try:
        cursor = db.conn.cursor()
        
        # Проверяем таблицу пользователей
        cursor.execute('SELECT COUNT(*) FROM users')
        users_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM user_stats')
        stats_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM achievements')
        achievements_count = cursor.fetchone()[0]
        
        embed = discord.Embed(title="🐛 Отладка Базы Данных", color=0x3498db)
        embed.add_field(name="👥 Пользователей", value=users_count, inline=True)
        embed.add_field(name="📊 Записей статистики", value=stats_count, inline=True)
        embed.add_field(name="🏅 Достижений", value=achievements_count, inline=True)
        
        # Проверяем текущего пользователя
        user_data = db.get_user_safe(interaction.user.id)
        embed.add_field(
            name="🔍 Ваши данные", 
            value=f"Баланс: {user_data[1]}\nСерия: {user_data[2]}\nДлина кортежа: {len(user_data)}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Ошибка отладки",
            description=f"Ошибка: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="admin_fix_user", description="Исправить данные пользователя (админ)")
@app_commands.describe(user="Пользователь для исправления")
@is_admin()
async def admin_fix_user(interaction: discord.Interaction, user: discord.Member):
    try:
        cursor = db.conn.cursor()
        
        # Создаем или обновляем пользователя
        cursor.execute('''
            INSERT INTO users (user_id, balance, daily_streak, inventory) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                balance = COALESCE(EXCLUDED.balance, 100),
                daily_streak = COALESCE(EXCLUDED.daily_streak, 0),
                inventory = COALESCE(EXCLUDED.inventory, '{"cases": {}, "items": {}}')
        ''', (user.id, 100, 0, json.dumps({"cases": {}, "items": {}})))
        
        # Создаем запись статистики если её нет
        cursor.execute('''
            INSERT INTO user_stats (user_id) 
            VALUES (%s)
            ON CONFLICT (user_id) DO NOTHING
        ''', (user.id,))
        
        db.conn.commit()
        
        embed = discord.Embed(
            title="🔧 Данные пользователя исправлены",
            description=f"Данные пользователя {user.mention} были успешно исправлены!",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Ошибка исправления",
            description=f"Ошибка: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# ЗАПУСК БОТА
if __name__ == "__main__":
    print("🚀 Запуск экономического бота...")
    print(f"🔑 Токен: {'✅ Найден' if BOT_TOKEN else '❌ Отсутствует'}")
    print(f"🗄️ База данных: {'✅ Подключена' if DATABASE_URL else '❌ Ошибка'}")
    print(f"👑 Админы: {len(ADMIN_IDS)} пользователей")
    print("=" * 50)
    
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"💥 Критическая ошибка при запуске бота: {e}")
        traceback.print_exc()
        print("🔄 Попытка перезапуска через 5 секунд...")
        import time
        time.sleep(5)
        # Попробуем перезапустить бота
        try:
            bot.run(BOT_TOKEN)
        except Exception as e2:
            print(f"💥 Повторная критическая ошибка: {e2}")
            traceback.print_exc()





