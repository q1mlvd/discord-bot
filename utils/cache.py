import time

class Cache:
    def __init__(self):
        self.data = {}
        self.expire_times = {}
    
    def set(self, key: str, value, expire: int = 3600):
        self.data[key] = value
        self.expire_times[key] = time.time() + expire
    
    def get(self, key: str):
        if key in self.data and time.time() < self.expire_times.get(key, 0):
            return self.data[key]
        else:
            if key in self.data:
                del self.data[key]
                del self.expire_times[key]
            return None
    
    def delete(self, key: str):
        if key in self.data:
            del self.data[key]
            del self.expire_times[key]

cache = Cache()
