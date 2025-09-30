import discord

class MusicService:
    def __init__(self):
        self.queues = {}
        self.now_playing = {}
    
    async def add_to_queue(self, guild_id: int, track: str):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        self.queues[guild_id].append(track)
        return len(self.queues[guild_id])
    
    async def skip_track(self, guild_id: int):
        if guild_id in self.queues and self.queues[guild_id]:
            self.queues[guild_id].pop(0)
            return True
        return False

music_service = MusicService()
