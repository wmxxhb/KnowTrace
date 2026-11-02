import redis
import json
from typing import List, Dict, Any
from src.settings import settings
from src.utils.logger import logger

class MemorySystem:
    def __init__(self):
        from src.services.local_backend import LocalMemory
        self.redis_client = LocalMemory() if settings.LOCAL_MODE else redis.from_url(settings.REDIS_URL)
        self.ttl = settings.SHORT_TERM_MEMORY_TTL
        self.history_limit = settings.MEMORY_HISTORY_LIMIT

    # --- Short Term Memory (Redis) ---
    
    def get_short_term_memory(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Retrieve recent conversation history from Redis."""
        key = f"session:{session_id}:history"
        try:
            # Redis lrange: 0 to limit-1 (limit elements)
            # If limit is 0, return empty
            if limit <= 0:
                return []
                
            data = self.redis_client.lrange(key, 0, limit - 1)
            # Redis stores most recent at head (lpush), so we need to reverse to get chronological order
            # Wait, lpush puts new at index 0. So index 0 is newest.
            # If we want context: "User: hi", "Assistant: hello", we want oldest first.
            # lrange(0, -1) gives [newest, ..., oldest] if lpush used.
            # Let's check add_short_term_memory: lpush.
            # So lrange returns [newest, 2nd newest, ...].
            # We should reverse it for context.
            
            messages = [json.loads(d) for d in data]
            messages.reverse() 
            return messages
        except Exception as e:
            logger.error(f"Error getting short term memory: {e}")
            raise

    def add_short_term_memory(self, session_id: str, role: str, content: str):
        """Add a new message to short term memory."""
        key = f"session:{session_id}:history"
        message = {"role": role, "content": content}
        try:
            self.redis_client.lpush(key, json.dumps(message))
            self.redis_client.ltrim(key, 0, self.history_limit - 1)
            self.redis_client.expire(key, self.ttl)
        except Exception as e:
            logger.error(f"Error adding short term memory: {e}")
            raise

    def clear_short_term_memory(self, session_id: str):
        """Clear session history."""
        key = f"session:{session_id}:history"
        self.redis_client.delete(key)
