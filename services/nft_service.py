import random

class NFTService:
    def __init__(self):
        self.nft_collection = {}
        self.next_id = 1
    
    async def generate_nft(self, user_id: int):
        """Генерация NFT для пользователя"""
        nft_id = self.next_id
        self.next_id += 1
        
        rarities = ["Common", "Rare", "Epic", "Legendary"]
        rarity = random.choices(rarities, weights=[70, 20, 8, 2])[0]
        
        nft = {
            'id': nft_id,
            'owner': user_id,
            'name': f"NFT #{nft_id}",
            'rarity': rarity,
            'value': random.randint(100, 5000),
            'created': datetime.now()
        }
        
        self.nft_collection[nft_id] = nft
        return nft
    
    async def get_user_nfts(self, user_id: int):
        return [nft for nft in self.nft_collection.values() if nft['owner'] == user_id]

nft_service = NFTService()
