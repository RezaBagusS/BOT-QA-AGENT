# telegram_router.py
import logging
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
# Hapus import yang tidak perlu: agent_logic, memory_service, dll.
from telegram_service import TelegramService, get_telegram_service

logger = logging.getLogger(__name__)

# --- Pydantic Models (Disederhanakan) ---
class Chat(BaseModel):
    id: int

class Message(BaseModel):
    message_id: int
    chat: Chat
    text: str | None = None
    # Hapus 'document' and 'reply_to_message'

class Update(BaseModel):
    update_id: int
    message: Message | None = None

# --- Router Definition ---
router = APIRouter(
    prefix="/webhook",
    tags=["telegram"]
)

# --- Command Handlers ---
async def handle_start(chat_id: int, service: TelegramService):
    """Handler untuk /start."""
    welcome_message = "Halo! 👋 Saya adalah bot sederhana. Gunakan /help untuk bantuan."
    await service.send_reply(chat_id, welcome_message)

async def handle_help(chat_id: int, service: TelegramService):
    """Handler untuk /help."""
    help_text = """
Berikut perintah yang tersedia:
`/start` - Memulai bot.
`/help` - Menampilkan bantuan ini.
"""
    await service.send_reply(chat_id, help_text)

# --- Hapus handler: handle_set_context, handle_show_context, handle_clear_context, handle_create_tc ---

# --- Pemetaan Command (Disederhanakan) ---
command_handlers = {
    "/start": handle_start,
    "/help": handle_help,
}

# --- Hapus Fungsi: handle_pdf_upload ---


# --- Webhook Endpoint (Utama Disederhanakan) ---
@router.post("/telegram")
async def handle_telegram_webhook(
    update: Update,
    # Hapus dependency agent_executor dan memory_service
    telegram_service: TelegramService = Depends(get_telegram_service)
):
    """Endpoint utama yang menerima update dari Telegram."""

    if not update.message or not update.message.chat or not update.message.text:
        # Abaikan update tanpa pesan teks
        logger.debug("Update diabaikan (bukan pesan teks).")
        return Response(status_code=200)

    chat_id = update.message.chat.id
    user_input = update.message.text
    logger.info(f"Pesan teks dari [Chat ID: {chat_id}]: {user_input}")

    # --- Hapus Penanganan File Upload ---

    # Cek command (ambil kata pertama)
    command = user_input.split()[0]
    handler = command_handlers.get(command)

    if handler:
        logger.debug(f"Menjalankan command handler untuk: {command}")
        # Panggil handler sederhana
        await handler(chat_id, telegram_service)
    else:
        # Jika bukan command yang dikenali, abaikan atau kirim balasan default
        logger.debug(f"Perintah tidak dikenali: {command}")
        # Opsional: Kirim balasan untuk perintah tidak dikenal
        # await telegram_service.send_reply(chat_id, "Maaf, perintah tidak dikenali. Gunakan /help.")
        pass # Saat ini, kita abaikan saja

    # --- Hapus logika 'else' (proses dengan agen) ---

    return Response(status_code=200)