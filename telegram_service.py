# telegram_service.py
import httpx
import logging
from config import settings
from typing import Dict, Any, Optional # <<< BARU: Untuk type hinting

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client
        self.api_url = settings.telegram_api_url

    async def send_reply(
        self, 
        chat_id: int, 
        text: str, 
        reply_markup: Optional[Dict[str, Any]] = None # <<< BARU: Tambah parameter
    ):
        """Mengirim balasan teks ke pengguna, bisa dengan keyboard."""
        
        # --- LOGIKA BARU ---
        json_payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            json_payload["reply_markup"] = reply_markup
        # --- AKHIR LOGIKA BARU ---

        try:
            response = await self.http_client.post(
                f"{self.api_url}/sendMessage",
                json=json_payload # <<< BARU: Gunakan payload yang sudah disusun
            )
            response.raise_for_status()
            logger.info(f"Balasan terkirim ke Chat ID: {chat_id}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP saat mengirim balasan ke {chat_id}: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Error tak terduga saat mengirim balasan ke {chat_id}: {e}")

    # <<< FUNGSI BARU UNTUK JAWAB CALLBACK (MENGHILANGKAN LOADING) >>>
    async def answer_callback_query(self, callback_query_id: str):
        """Memberi tahu Telegram bahwa callback telah diterima."""
        try:
            await self.http_client.post(
                f"{self.api_url}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id}
            )
        except Exception as e:
            logger.warning(f"Gagal menjawab callback query {callback_query_id}: {e}")

    # <<< FUNGSI BARU UNTUK MENGEDIT PESAN (MENGHAPUS KEYBOARD) >>>
    async def edit_message_text(
        self, 
        chat_id: int, 
        message_id: int, 
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None # Bisa juga ganti keyboard
    ):
        """Mengedit pesan yang sudah ada (misal: menghapus keyboard)."""
        json_payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
        if reply_markup:
            json_payload["reply_markup"] = reply_markup

        try:
            response = await self.http_client.post(
                f"{self.api_url}/editMessageText",
                json=json_payload
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Gagal mengedit pesan {message_id} di chat {chat_id}: {e}")

    async def send_typing_action(self, chat_id: int):
        """Mengirim aksi 'sedang mengetik'."""
        try:
            await self.http_client.post(
                f"{self.api_url}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"}
            )
        except Exception as e:
            logger.warning(f"Gagal mengirim typing action ke {chat_id}: {e}")

# Dependency function (Tidak berubah)
async def get_telegram_service():
    async with httpx.AsyncClient() as client:
        yield TelegramService(client)