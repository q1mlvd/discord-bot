import aiohttp
import asyncio

class CryptoService:
    def __init__(self):
        self.prices = {}
    
    async def update_prices(self):
        """Обновление курсов с Binance"""
        try:
            async with aiohttp.ClientSession() as session:
                coins = ['BTCUSDT', 'ETHUSDT', 'DOGEUSDT']
                for coin in coins:
                    async with session.get(f'https://api.binance.com/api/v3/ticker/price?symbol={coin}') as resp:
                        data = await resp.json()
                        self.prices[coin.replace('USDT', '')] = float(data['price'])
        except Exception as e:
            print(f"Ошибка обновления курсов: {e}")
    
    async def get_portfolio_value(self, user_crypto: dict):
        total = 0
        for coin, amount in user_crypto.items():
            if coin in self.prices:
                total += amount * self.prices[coin]
        return total

crypto_service = CryptoService()
