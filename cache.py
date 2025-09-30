import redis
import json
import asyncio
from datetime import timedelta

class RedisCache:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    async def set_cache(self, key: str, value, expire: int = 3600):
        """Кэширование данных"""
        try:
            self.redis_client.setex(key, timedelta(seconds=expire), json.dumps(value))
        except Exception as e:
            print(f"Redis error: {e}")
    
    async def get_cache(self, key: str):
        """Получение данных из кэша"""
        try:
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Redis error: {e}")
            return None
    
    async def delete_cache(self, key: str):
        """Удаление из кэша"""
        try:
            self.redis_client.delete(key)
        except Exception as e:
            print(f"Redis error: {e}")
    
    # Кэш для экономики
    async def cache_user_balance(self, user_id: int, balance: int):
        await self.set_cache(f"user_balance:{user_id}", balance, 300)
    
    async def get_cached_balance(self, user_id: int):
        return await self.get_cache(f"user_balance:{user_id}")
    
    # Кэш для крипты
    async def cache_crypto_prices(self, prices: dict):
        await self.set_cache("crypto_prices", prices, 60)  # Обновляем каждую минуту
    
    async def get_cached_crypto_prices(self):
        return await self.get_cache("crypto_prices")
