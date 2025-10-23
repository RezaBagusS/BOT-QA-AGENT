# telegram_router.py
import logging
import traceback
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field # <<< BARU
from agent_logic import get_agent_executor 
from telegram_service import TelegramService, get_telegram_service
from memory_service import BaseMemoryService, get_memory_service 
from langchain.agents import AgentExecutor 
from typing import Optional # <<< BARU

logger = logging.getLogger(__name__)

# --- Pydantic Models (Perlu dimodifikasi untuk CallbackQuery) ---
class Chat(BaseModel):
    id: int

class Message(BaseModel):
    message_id: int # <<< BARU: Kita perlu message_id
    chat: Chat
    text: str | None = None

# <<< BARU: Model untuk data CallbackQuery >>>
class CallbackQuery(BaseModel):
    id: str # Ini adalah callback_query_id
    message: Message # Pesan asal tempat tombol diklik
    data: Optional[str] = None # Data dari tombol (misal: "format:bdd")

class Update(BaseModel):
    update_id: int
    message: Optional[Message] = None
    callback_query: Optional[CallbackQuery] = Field(None, alias="callback_query") # <<< BARU

# --- Router Definition (Tidak Berubah) ---
router = APIRouter(
    prefix="/webhook", 
    tags=["telegram"]  
)

# --- MANAJEMEN STATUS (STATE) ---
# Format: { chat_id: {"state": "STATE_NAME", "data": {...}} }
user_states = {}


# --- Command Handlers ---

async def handle_start(chat_id: int, service: TelegramService):
    user_states.pop(chat_id, None) 
    welcome_message = "Halo! 👋 Saya adalah QA Agent Anda. Gunakan /help untuk melihat bantuan yang tersedia."
    await service.send_reply(chat_id, welcome_message)

async def handle_create_case(chat_id: int, service: TelegramService):
    """Handler untuk perintah /create-testcase."""
    user_states[chat_id] = {"state": "WAITING_FOR_FORMAT", "data": {}}
    message = (
        "Baik, mari kita mulai buat test case nya.\n\n"
        "Anda ingin format apa?\n"
    )
    
    # --- LOGIKA KEYBOARD BARU ---
    inline_keyboard = [
        [
            {"text": "📊 Steps", "callback_data": "format:steps"},
            {"text": "🧩 BDD (Gherkin)", "callback_data": "format:bdd"}
        ]
        # Anda bisa menambah baris lain di sini, misal tombol /cancel
        # [
        #    {"text": "❌ Batal", "callback_data": "action:cancel"}
        # ]
    ]
    reply_markup = {"inline_keyboard": inline_keyboard}
    # --- AKHIR LOGIKA KEYBOARD BARU ---

    # Kirim pesan beserta keyboard
    await service.send_reply(chat_id, message, reply_markup)

async def handle_help(chat_id: int, service: TelegramService):
    user_states.pop(chat_id, None)
    help_text = """
Berikut perintah yang tersedia:
/start - Memulai bot.
/help - Menampilkan bantuan ini.
/create-testcase - Memulai proses pembuatan test case.
/cancel - Membatalkan tindakan saat ini.
"""
    await service.send_reply(chat_id, help_text)

async def handle_cancel(chat_id: int, service: TelegramService):
    if chat_id in user_states:
        user_states.pop(chat_id, None)
        message = "Tindakan dibatalkan."
    else:
        message = "Tidak ada tindakan yang sedang berlangsung."
    await service.send_reply(chat_id, message)

command_handlers = {
    "/start": handle_start,
    "/help": handle_help,
    "/create-testcase": handle_create_case,
    "/cancel": handle_cancel
}

# --- Webhook Endpoint (Dimodifikasi Total) ---
@router.post("/telegram")
async def handle_telegram_webhook(
    update: Update,
    agent_executor: AgentExecutor = Depends(get_agent_executor), 
    telegram_service: TelegramService = Depends(get_telegram_service),
    memory_service: BaseMemoryService = Depends(get_memory_service)
):
    """Endpoint utama yang menerima update dari Telegram."""

    # --- LOGIKA BARU 1: Menangani Klik Tombol (CallbackQuery) ---
    if update.callback_query:
        # Ambil data penting dari callback
        callback_id = update.callback_query.id
        data = update.callback_query.data
        chat_id = update.callback_query.message.chat.id
        message_id = update.callback_query.message.message_id

        # Segera jawab callback agar tombol tidak loading
        await telegram_service.answer_callback_query(callback_id)

        # Cek data apa yang dikirim tombol
        if data and data.startswith("format:"):
            chosen_format = data.split(":", 1)[1] # "steps" atau "bdd"
            
            # Update state pengguna
            user_states[chat_id] = {
                "state": "WAITING_FOR_PRD",
                "data": {"format": chosen_format}
            }

            # Edit pesan asli (yang ada tombolnya) menjadi pesan instruksi berikutnya
            new_text = (
                f"👍 Format `{chosen_format}` dipilih.\n\n"
                "Sekarang, silakan kirimkan **deskripsi PRD** Anda."
            )
            await telegram_service.edit_message_text(chat_id, message_id, new_text)
        
        # (Tambahan) Anda bisa menangani callback "action:cancel" di sini
        elif data == "action:cancel":
            user_states.pop(chat_id, None)
            await telegram_service.edit_message_text(chat_id, message_id, "Tindakan dibatalkan.")

        return Response(status_code=200)

    # --- LOGIKA BARU 2: Menangani Pesan Teks (Seperti sebelumnya) ---
    if not update.message or not update.message.text or not update.message.chat:
        logger.debug("Menerima update non-teks atau non-callback, diabaikan.")
        return Response(status_code=200)

    chat_id = update.message.chat.id
    user_input = update.message.text.strip()
    session_id = str(chat_id) 

    logger.info(f"Pesan teks dari [Chat ID: {chat_id}]: {user_input}")

    # 1. Cek apakah ini command
    handler = command_handlers.get(user_input)
    if handler:
        logger.debug(f"Menjalankan command handler untuk: {user_input}")
        await handler(chat_id, telegram_service)
        return Response(status_code=200)

    # 2. Jika bukan command, cek apakah user punya status
    current_state_data = user_states.get(chat_id)
    if not current_state_data:
        # 3. Jika bukan command dan tidak ada status, ini adalah chat biasa.
        logger.warn(f"Menerima chat biasa (non-command) dari {chat_id}, diabaikan.")
        unknown_message = (
            "Maaf, saya tidak mengerti. 😕\n"
            "Saya hanya merespons perintah. Gunakan /help untuk melihat daftar perintah."
        )
        await telegram_service.send_reply(chat_id, unknown_message)
        return Response(status_code=200)
    
    # --- Ada Status Aktif, Proses Sesuai State ---
    state_name = current_state_data.get("state")

    # --- STATE : Menunggu Input PRD ---
    if state_name == "WAITING_FOR_PRD":
        logger.debug(f"Memproses PRD dari {chat_id} dengan agent.")
        await telegram_service.send_typing_action(chat_id)
        
        saved_format = current_state_data.get("data", {}).get("format", "steps")
        prd_text = user_input
        
        user_states.pop(chat_id, None) 

        prompt_input = f"""
        Buatkan saya test case dengan format '{saved_format}' berdasarkan PRD berikut.

        PRD:
        {prd_text}
        """

        try:
            response = await agent_executor.ainvoke({
                "input": prompt_input,
                "chat_history": []
            })
            output = response["output"]

        except Exception as e:
            logger.error(f"Error dari Agent untuk session {session_id}: {e}", exc_info=True)
            output = f"Maaf, terjadi error saat memproses PRD: {e}"

        await telegram_service.send_reply(chat_id, output)
        return Response(status_code=200)

    # Fallback jika ada state yang tidak dikenal
    logger.error(f"State tidak dikenal: {state_name} untuk chat_id {chat_id}")
    user_states.pop(chat_id, None)
    await telegram_service.send_reply(chat_id, "Terjadi kesalahan state. Silakan coba lagi.")
    return Response(status_code=200)