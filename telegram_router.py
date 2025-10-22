# telegram_router.py
import logging
import traceback
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from agent_logic import get_agent_executor
from telegram_service import TelegramService, get_telegram_service
from memory_service import BaseMemoryService, get_memory_service
from langchain.agents import AgentExecutor # Untuk type hinting

logger = logging.getLogger(__name__)

# --- Pydantic Models (Bisa dipindah ke models.py jika kompleks) ---
class Chat(BaseModel):
    id: int

class Message(BaseModel):
    chat: Chat
    text: str | None = None

class Update(BaseModel):
    update_id: int
    message: Message | None = None

# --- Router Definition ---
router = APIRouter(
    prefix="/webhook", # Prefix untuk semua route di file ini
    tags=["telegram"]  # Tag untuk dokumentasi API (Swagger UI)
)

# --- Command Handlers ---
async def handle_start(chat_id: int, service: TelegramService):
    """Handler untuk perintah /start."""
    welcome_message = "Halo! 👋 Saya adalah QA Agent Anda. Gunakan /help untuk bantuan."
    await service.send_reply(chat_id, welcome_message)

async def handle_help(chat_id: int, service: TelegramService):
    """Handler untuk perintah /help."""
    help_text = """
Berikut perintah yang tersedia:
`/start` - Memulai bot.
`/help` - Menampilkan bantuan ini.
`/create_tc` - Membuat test case (perlu konteks).
... (tambahkan perintah lain) ...
"""
    await service.send_reply(chat_id, help_text)

# --- Pemetaan Command ke Fungsi Handler ---
# Ini lebih scalable daripada if/elif
command_handlers = {
    "/start": handle_start,
    "/help": handle_help,
    # Tambahkan command lain di sini
}

# --- Webhook Endpoint ---
@router.post("/telegram")
async def handle_telegram_webhook(
    update: Update,
    agent_executor: AgentExecutor = Depends(get_agent_executor), # Inject agent
    telegram_service: TelegramService = Depends(get_telegram_service), # Inject service telegram
    memory_service: BaseMemoryService = Depends(get_memory_service) # Inject service memory
):
    """Endpoint utama yang menerima update dari Telegram."""

    if not update.message or not update.message.text or not update.message.chat:
        logger.debug("Menerima update non-teks atau tanpa chat ID, diabaikan.")
        return Response(status_code=200)

    chat_id = update.message.chat.id
    user_input = update.message.text
    session_id = str(chat_id) # Gunakan chat_id sebagai session ID untuk memori

    logger.info(f"Pesan dari [Chat ID: {chat_id}]: {user_input}")

    # Cek apakah ini command khusus
    handler = command_handlers.get(user_input)
    if handler:
        logger.debug(f"Menjalankan command handler untuk: {user_input}")
        await handler(chat_id, telegram_service)
        return Response(status_code=200)

    # Jika bukan command, proses dengan agen
    logger.debug(f"Memproses input dengan agent untuk session: {session_id}")
    await telegram_service.send_typing_action(chat_id)
    chat_history = memory_service.get_history(session_id)

    try:
        response = await agent_executor.ainvoke({
            "input": user_input,
            "chat_history": chat_history.messages
        })
        output = response["output"]

        # Simpan pesan ke history (implementasi save_history jika perlu)
        chat_history.add_user_message(user_input)
        chat_history.add_ai_message(output)
        memory_service.save_history(session_id, chat_history) # Panggil save (meskipun in-memory tidak melakukan apa-apa)

    except Exception as e:
        logger.error(f"Error dari Agent untuk session {session_id}: {e}", exc_info=True)
        output = f"Maaf, terjadi error: {e}"

    await telegram_service.send_reply(chat_id, output)
    return Response(status_code=200)