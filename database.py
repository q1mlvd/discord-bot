import aiosqlite
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        self.db_path = "data/bot.db"
        os.makedirs("data", exist_ok=True)
    
    async def init_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Основная таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 1000,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    reputation INTEGER DEFAULT 100,
                    daily_claimed TEXT,
                    work_cooldown TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица инвентаря
            await db.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER,
                    item_id TEXT,
                    item_name TEXT,
                    quantity INTEGER DEFAULT 1,
                    rarity TEXT DEFAULT 'common',
                    PRIMARY KEY (user_id, item_id)
                )
            ''')
            
            # Таблица транзакций
            await db.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    type TEXT,
                    description TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица NFT
            await db.execute('''
                CREATE TABLE IF NOT EXISTS nfts (
                    nft_id TEXT PRIMARY KEY,
                    owner_id INTEGER,
                    name TEXT,
                    image_url TEXT,
                    rarity TEXT,
                    attributes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.commit()
    
    async def get_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        'user_id': result[0], 'balance': result[1], 'level': result[2],
                        'xp': result[3], 'reputation': result[4], 'daily_claimed': result[5],
                        'work_cooldown': result[6], 'created_at': result[7]
                    }
                else:
                    # Создаем нового пользователя
                    await db.execute(
                        'INSERT INTO users (user_id) VALUES (?)',
                        (user_id,)
                    )
                    await db.commit()
                    return await self.get_user(user_id)
    
    async def update_balance(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE users SET balance = balance + ? WHERE user_id = ?',
                (amount, user_id)
            )
            await db.commit()
            return await self.get_user(user_id)
