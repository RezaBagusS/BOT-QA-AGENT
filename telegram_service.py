# telegram_service.py
import httpx
import logging
from config import settings

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client
        self.api_url = settings.telegram_api_url

    async def send_reply(self, chat_id: int, text: str):
        """Mengirim balasan teks ke pengguna."""
        try:
            response = await self.http_client.post(
                f"{self.api_url}/sendMessage",
                json={"chat_id": chat_id, "text": text}
            )
            response.raise_for_status()
            logger.info(f"Balasan terkirim ke Chat ID: {chat_id}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP saat mengirim balasan ke {chat_id}: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Error tak terduga saat mengirim balasan ke {chat_id}: {e}")

    async def send_typing_action(self, chat_id: int):
        """Mengirim aksi 'sedang mengetik'."""
        try:
            await self.http_client.post(
                f"{self.api_url}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"}
            )
        except Exception as e:
            logger.warning(f"Gagal mengirim typing action ke {chat_id}: {e}")

# Dependency function untuk FastAPI
async def get_telegram_service():
    async with httpx.AsyncClient() as client:
        yield TelegramService(client)