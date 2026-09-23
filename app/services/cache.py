import json
import time
from threading import Lock


class TTLCache:
    """进程内 TTL 缓存。接口与 Redis 对齐，便于面试时讲「可替换成 Redis」。"""

    def __init__(self):
        self._store: dict[str, tuple[float, str]] = {}
        self._lock = Lock()

    def get(self, key: str) -> str | None:
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            exp, value = item
            if exp < now:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: str, ttl: int) -> None:
        with self._lock:
            self._store[key] = (time.time() + ttl, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def get_json(self, key: str):
        raw = self.get(key)
        return json.loads(raw) if raw else None

    def set_json(self, key: str, value, ttl: int) -> None:
        self.set(key, json.dumps(value, ensure_ascii=False), ttl)


cache = TTLCache()
