import discord
import random
from datetime import datetime

class EconomyService:
    def __init__(self):
        self.user_balances = {}
        self.transaction_history = []
    
    async def get_balance(self, user_id: int):
        return self.user_balances.get(user_id, 1000)
    
    async def transfer(self, from_user: int, to_user: int, amount: int):
        if self.user_balances.get(from_user, 1000) < amount:
            return False, "Недостаточно средств"
        
        self.user_balances[from_user] = self.user_balances.get(from_user, 1000) - amount
        self.user_balances[to_user] = self.user_balances.get(to_user, 1000) + amount
        
        self.transaction_history.append({
            'from': from_user,
            'to': to_user, 
            'amount': amount,
            'time': datetime.now()
        })
        
        return True, "Перевод выполнен"

economy_service = EconomyService()
