# telegram_router.py
import logging
import traceback
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from agent_logic import get_agent_executor 
from telegram_service import TelegramService, get_telegram_service
from memory_service import BaseMemoryService, get_memory_service 
from langchain.agents import AgentExecutor 
from typing import Optional, Dict, Any # <<< Pastikan Dict dan Any di-import
from state_service import StateService, get_state_service # <<< Service Redis Anda

logger = logging.getLogger(__name__)

# --- Pydantic Models (Tidak Berubah) ---
class Chat(BaseModel):
    id: int

class Message(BaseModel):
    message_id: int 
    chat: Chat
    text: str | None = None

class CallbackQuery(BaseModel):
    id: str 
    message: Message 
    data: Optional[str] = None 

class Update(BaseModel):
    update_id: int
    message: Optional[Message] = None
    callback_query: Optional[CallbackQuery] = Field(None, alias="callback_query")

# --- Router Definition (Tidak Berubah) ---
router = APIRouter(
    prefix="/webhook", 
    tags=["telegram"]  
)

# --- Pemetaan Teks Tombol (Tetap Digunakan) ---
button_text_to_command = {
    "🚀 Buat Test Case": "/create-testcase",
    "❓ Bantuan": "/help",
    "❌ Batalkan Aksi": "/cancel"
}

# --- Webhook Endpoint (Logika Handler Di-refactor) ---
@router.post("/telegram")
async def handle_telegram_webhook(
    update: Update,
    agent_executor: AgentExecutor = Depends(get_agent_executor), 
    telegram_service: TelegramService = Depends(get_telegram_service),
    memory_service: BaseMemoryService = Depends(get_memory_service),
    state_service: StateService = Depends(get_state_service) # <<< Service Redis di-inject
):
    """Endpoint utama yang menerima update dari Telegram."""

    # --- 1: Menangani Klik Tombol Inline (CallbackQuery) ---
    if update.callback_query:
        callback_id = update.callback_query.id
        data = update.callback_query.data
        chat_id = update.callback_query.message.chat.id
        message_id = update.callback_query.message.message_id

        await telegram_service.answer_callback_query(callback_id)

        if data and data.startswith("format:"):
            chosen_format = data.split(":", 1)[1]
            
            # --- REFACTOR: Simpan state ke Redis ---
            new_state = {
                "state": "WAITING_FOR_PRD",
                "data": {"format": chosen_format}
            }
            state_service.save_state(chat_id, new_state)
            logger.info(f"State disimpan ke Redis untuk chat {chat_id}: {new_state}")
            # --- SELESAI REFACTOR ---

            new_text = (f"👍 Format `{chosen_format}` dipilih.\n\n")
            next_text = ("Sekarang, silakan kirimkan **deskripsi PRD** Anda.")
            await telegram_service.edit_message_text(chat_id, message_id, new_text)
            await telegram_service.send_reply(chat_id, next_text)
        
        elif data == "action:cancel":
            # --- REFACTOR: Hapus state dari Redis ---
            state_service.clear_state(chat_id)
            # --- SELESAI REFACTOR ---
            await telegram_service.edit_message_text(chat_id, message_id, "Tindakan dibatalkan.")

        return Response(status_code=200)

    # --- 2: Menangani Pesan Teks (Message) ---
    if not update.message or not update.message.text or not update.message.chat:
        logger.debug("Menerima update non-teks atau non-callback, diabaikan.")
        return Response(status_code=200)

    chat_id = update.message.chat.id
    user_input = update.message.text.strip()
    session_id = str(chat_id) 

    logger.info(f"Pesan teks dari [Chat ID: {chat_id}]: {user_input}")

    # Terjemahkan teks tombol ke command
    command_to_run = button_text_to_command.get(user_input, user_input)

    # --- REFACTOR: Logika Command Handler dipindah ke sini ---
    # Karena 'state_service' sudah di-inject di sini.

    if command_to_run == "/start":
        state_service.clear_state(chat_id) 
        welcome_message = "Halo! 👋 Saya adalah QA Agent Anda. Silakan pilih tindakan dari menu di bawah."
        reply_keyboard = [
            [ {"text": "🚀 Buat Test Case"} ], 
            [ {"text": "❓ Bantuan"}, {"text": "❌ Batalkan Aksi"} ]
        ]
        reply_markup = {"keyboard": reply_keyboard, "resize_keyboard": True, "selective": True}
        await telegram_service.send_reply(chat_id, welcome_message, reply_markup=reply_markup)
        return Response(status_code=200)

    if command_to_run == "/help":
        state_service.clear_state(chat_id)
        help_text = """
Berikut perintah yang tersedia:
/start - Memulai bot.
/help - Menampilkan bantuan ini.
/create-testcase - Memulai proses pembuatan test case.
/cancel - Membatalkan tindakan saat ini.
"""
        await telegram_service.send_reply(chat_id, help_text)
        return Response(status_code=200)

    if command_to_run == "/cancel":
        state_service.clear_state(chat_id)
        await telegram_service.send_reply(chat_id, "Tindakan dibatalkan.")
        return Response(status_code=200)

    if command_to_run == "/create-testcase":
        # Atur state ke "WAITING_FOR_FORMAT" di Redis
        new_state = {"state": "WAITING_FOR_FORMAT", "data": {}}
        state_service.save_state(chat_id, new_state)
        logger.info(f"State /create-testcase disimpan ke Redis untuk chat {chat_id}")
        
        message = (
            "Baik, mari kita mulai buat test case nya.\n\n"
            "Anda ingin format apa?\n"
        )
        inline_keyboard = [
            [
                {"text": "📊 Steps", "callback_data": "format:steps"},
                {"text": "🧩 BDD (Gherkin)", "callback_data": "format:bdd"}
            ]
        ]
        reply_markup = {"inline_keyboard": inline_keyboard}
        await telegram_service.send_reply(chat_id, message, reply_markup=reply_markup)
        return Response(status_code=200)

    # --- SELESAI REFACTOR HANDLER ---

    # 3. Jika bukan command, cek status dari Redis
    # --- REFACTOR: Ambil state dari Redis ---
    current_state_data = state_service.get_state(chat_id)
    logger.info(f"Mencari state di Redis untuk {chat_id}, ditemukan: {current_state_data is not None}")
    # --- SELESAI REFACTOR ---

    if not current_state_data:
        logger.warn(f"Menerima chat biasa (non-command) dari {chat_id}, diabaikan.")
        unknown_message = (
            "Maaf, saya tidak mengerti. 😕\n"
            "Gunakan tombol di bawah atau /help untuk melihat daftar perintah."
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
        
        # --- REFACTOR: Hapus state dari Redis ---
        state_service.clear_state(chat_id)
        # --- SELESAI REFACTOR ---

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
    
    # ... (Tambahkan penanganan untuk state 'WAITING_FOR_FORMAT' jika diperlukan,
    # meskipun saat ini ditangani oleh /create-testcase) ...

    # Fallback jika ada state yang tidak dikenal
    logger.error(f"State tidak dikenal: {state_name} untuk chat_id {chat_id}")
    # --- REFACTOR: Hapus state dari Redis ---
    state_service.clear_state(chat_id)
    # --- SELESAI REFACTOR ---
    await telegram_service.send_reply(chat_id, "Terjadi kesalahan state. Silakan coba lagi.")
    return Response(status_code=200)