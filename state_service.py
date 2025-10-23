# state_service.py
import redis
import json
import logging
from config import settings # Asumsi Anda punya config.py
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class StateService:
    def __init__(self, client: redis.Redis):
        self.client = client
        # Atur prefix agar tidak bentrok jika Redis dipakai hal lain
        self.prefix = "bot:state:"
        # Atur expiry time (misal 1 jam) agar state tidak menumpuk
        self.expire_seconds = 3600 

    def _get_key(self, chat_id: int) -> str:
        return f"{self.prefix}{chat_id}"

    def save_state(self, chat_id: int, state_data: Dict[str, Any]):
        """Menyimpan state dictionary sebagai JSON string ke Redis."""
        try:
            key = self._get_key(chat_id)
            # Redis menyimpan string, jadi kita ubah dict ke JSON
            self.client.set(key, json.dumps(state_data), ex=self.expire_seconds)
            logger.debug(f"State disimpan ke Redis untuk {chat_id}")
        except Exception as e:
            logger.error(f"Gagal menyimpan state ke Redis: {e}")

    def get_state(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Mengambil state dari Redis dan mengubahnya kembali ke dict."""
        try:
            key = self._get_key(chat_id)
            data = self.client.get(key)
            if data:
                # Ubah JSON string kembali ke dictionary Python
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Gagal mengambil state dari Redis: {e}")
            return None

    def clear_state(self, chat_id: int):
        """Menghapus state dari Redis."""
        try:
            key = self._get_key(chat_id)
            self.client.delete(key)
            logger.debug(f"State dihapus dari Redis untuk {chat_id}")
        except Exception as e:
            logger.error(f"Gagal menghapus state dari Redis: {e}")

# --- Dependency untuk FastAPI ---

# Buat satu koneksi pool saat startup (lebih efisien)
# Pastikan REDIS_URL ada di settings/environment
try:
    redis_pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
    logger.info("Koneksi Redis Pool berhasil dibuat.")
except Exception as e:
    logger.error(f"GAGAL KONEK KE REDIS POOL: {e}")
    redis_pool = None # Aplikasi akan error jika ini gagal

def get_state_service():
    if not redis_pool:
        raise Exception("Redis pool tidak terinisialisasi.")

    client = redis.Redis(connection_pool=redis_pool)
    yield StateService(client)
    # client.close() # Tidak perlu close jika pakai pool