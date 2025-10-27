import redis
import os
from typing import Optional

class RedisConnection:
    _instance: Optional['RedisConnection'] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisConnection, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self._client = redis.from_url(
                redis_url,
                decode_responses=True,
                health_check_interval=30
            )
    
    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self.__init__()
        return self._client
    
    def ping(self) -> bool:
        """Test Redis connection"""
        try:
            return self._client.ping()
        except Exception:
            return False
    
    def close(self):
        """Close Redis connection"""
        if self._client:
            self._client.close()
            self._client = None

# Global instance
redis_conn = RedisConnection()

def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    return redis_conn.client