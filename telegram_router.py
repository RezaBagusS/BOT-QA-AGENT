# telegram_router.py
import logging
import traceback
import tempfile # Untuk file sementara
import aiofiles # Untuk file async
from fastapi import APIRouter, Depends, Response, HTTPException
from pydantic import BaseModel
from agent_logic import get_agent_executor, read_pdf_content # Impor tool PDF
from telegram_service import TelegramService, get_telegram_service
from memory_service import BaseMemoryService, get_memory_service
from langchain.agents import AgentExecutor
from config import settings # Impor settings

logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class Chat(BaseModel):
    id: int

class Document(BaseModel): # <<< TAMBAHKAN INI
    file_id: str
    file_name: str | None = None
    mime_type: str | None = None

class Message(BaseModel):
    chat: Chat
    text: str | None = None
    document: Document | None = None # <<< TAMBAHKAN INI

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
    # ... (sama seperti sebelumnya) ...
    welcome_message = "Halo! 👋 Saya adalah QA Agent Anda. Kirim file PDF, gunakan /set_context [teks], atau /help untuk bantuan."
    await service.send_reply(chat_id, welcome_message)

async def handle_help(chat_id: int, service: TelegramService):
    # <<< UPDATE TEXT BANTUAN >>>
    help_text = """
Berikut perintah yang tersedia:
`/start` - Memulai bot.
`/help` - Menampilkan bantuan ini.
`/set_context [teks]` - Mengatur teks PRD sebagai konteks (tempel setelah perintah).
`/show_context` - Menampilkan konteks PRD yang aktif.
`/clear_context` - Menghapus konteks PRD.
`/create_tc [format]` - Membuat test case berdasarkan konteks. Format opsional: `steps` (default) atau `bdd`. Contoh: `/create_tc bdd`

Anda juga bisa langsung mengirim (upload) file PDF untuk dijadikan konteks.
"""
    await service.send_reply(chat_id, help_text)

async def handle_set_context(chat_id: int, text: str, service: TelegramService, memory: BaseMemoryService):
    """Handler untuk /set_context."""
    # Ambil teks setelah '/set_context '
    context_text = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else None
    session_id = str(chat_id)
    if context_text:
        memory.set_context(session_id, context_text)
        await service.send_reply(chat_id, "✅ Konteks berhasil diatur dari teks.")
    else:
        await service.send_reply(chat_id, "⚠️ Format salah. Gunakan: /set_context [tempel teks di sini]")

async def handle_show_context(chat_id: int, service: TelegramService, memory: BaseMemoryService):
    """Handler untuk /show_context."""
    session_id = str(chat_id)
    context = memory.get_context(session_id)
    if context:
        # Tampilkan hanya sebagian kecil konteks
        await service.send_reply(chat_id, f"Konteks saat ini:\n```\n{context[:500]}...\n```")
    else:
        await service.send_reply(chat_id, "ℹ️ Belum ada konteks yang diatur.")

async def handle_clear_context(chat_id: int, service: TelegramService, memory: BaseMemoryService):
    """Handler untuk /clear_context."""
    session_id = str(chat_id)
    memory.set_context(session_id, None) # Hapus konteks
    await service.send_reply(chat_id, "✅ Konteks berhasil dihapus.")

async def handle_create_tc(chat_id: int, text: str, service: TelegramService, memory: BaseMemoryService, agent: AgentExecutor):
    """Handler untuk /create_tc."""
    session_id = str(chat_id)
    context = memory.get_context(session_id)

    if not context:
        await service.send_reply(chat_id, "⚠️ Konteks PRD belum diatur. Kirim PDF atau gunakan `/set_context` dulu.")
        return

    # Tentukan format (default 'steps')
    parts = text.split(maxsplit=1)
    format_choice = parts[1].lower() if len(parts) > 1 and parts[1].lower() in ["steps", "bdd"] else "steps"

    logger.info(f"Meminta pembuatan test case format '{format_choice}' untuk session {session_id}")
    await service.send_typing_action(chat_id)
    history = memory.get_history(session_id)

    try:
        # Minta agen menggunakan tool dengan format dan konteks
        # Kita gabungkan konteks ke input agar agen tahu sumbernya
        agent_input = f"Buatkan test case dalam format '{format_choice}' berdasarkan PRD berikut:\n\n{context}"

        response = await agent.ainvoke({
            "input": agent_input,
            "chat_history": history.messages
        })
        output = response["output"]

        history.add_user_message(text) # Simpan perintah asli
        history.add_ai_message(output)
        memory.save_history(session_id, history)
        await service.send_reply(chat_id, output)

    except Exception as e:
        logger.error(f"Error saat handle_create_tc: {e}", exc_info=True)
        await service.send_reply(chat_id, f"Error: {e}")


# --- Pemetaan Command ---
command_handlers = {
    "/start": handle_start,
    "/help": handle_help,
    "/set_context": handle_set_context,      # <<< Tambah
    "/show_context": handle_show_context,     # <<< Tambah
    "/clear_context": handle_clear_context,    # <<< Tambah
    "/create_tc": handle_create_tc,         # <<< Tambah (akan handle format juga)
}

# --- Fungsi untuk menangani File PDF ---
async def handle_pdf_upload(
    chat_id: int,
    document: Document,
    service: TelegramService,
    memory: BaseMemoryService
):
    """Menangani upload file PDF."""
    session_id = str(chat_id)
    logger.info(f"Menerima upload PDF: {document.file_name} (ID: {document.file_id}) dari {chat_id}")
    await service.send_reply(chat_id, f"⏳ Menerima file '{document.file_name}'. Memproses...")
    await service.send_typing_action(chat_id)

    temp_file_path = None
    try:
        # 1. Dapatkan path file dari Telegram
        async with httpx.AsyncClient() as client:
            get_file_resp = await client.get(f"{settings.telegram_api_url}/getFile?file_id={document.file_id}")
            get_file_resp.raise_for_status()
            file_path_tg = get_file_resp.json()["result"]["file_path"]

            # 2. Download file
            download_url = f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path_tg}"
            file_resp = await client.get(download_url)
            file_resp.raise_for_status()

            # 3. Simpan ke file sementara
            # Pastikan direktori /tmp ada dan bisa ditulis di Koyeb (biasanya bisa)
            temp_dir = tempfile.gettempdir()
            # Gunakan file_id untuk nama unik, tambahkan ekstensi .pdf
            temp_file_path = os.path.join(temp_dir, f"{document.file_id}.pdf")

            async with aiofiles.open(temp_file_path, 'wb') as f:
                await f.write(file_resp.content)
            logger.info(f"File PDF disimpan sementara di: {temp_file_path}")

        # 4. Ekstrak teks (LANGSUNG, tanpa agen agar lebih cepat & pasti)
        # Kita bisa panggil fungsi tool langsung
        extracted_text = read_pdf_content.func(temp_file_path) # Panggil fungsi asli dari tool

        if "Berhasil membaca" in extracted_text:
             # Ambil hanya kontennya saja dari pesan sukses tool
             pdf_context = extracted_text.split("Konten:", 1)[1].strip().rsplit("...", 1)[0] # Ambil bagian tengah
             memory.set_context(session_id, pdf_context)
             await service.send_reply(chat_id, f"✅ PDF '{document.file_name}' berhasil diproses dan dijadikan konteks. Anda sekarang bisa menggunakan /create_tc.")
        else:
             # Jika tool gagal, 'extracted_text' berisi pesan errornya
             await service.send_reply(chat_id, f"⚠️ Gagal memproses PDF: {extracted_text}")

    except Exception as e:
        logger.error(f"Error saat menangani upload PDF: {e}", exc_info=True)
        await service.send_reply(chat_id, f"Maaf, terjadi error saat memproses file PDF Anda: {e}")
    finally:
        # 5. Hapus file sementara (PENTING!)
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"File sementara dihapus: {temp_file_path}")
            except OSError as e:
                logger.error(f"Gagal menghapus file sementara {temp_file_path}: {e}")


# --- Webhook Endpoint (Utama) ---
@router.post("/telegram")
async def handle_telegram_webhook(
    update: Update,
    agent_executor: AgentExecutor = Depends(get_agent_executor),
    telegram_service: TelegramService = Depends(get_telegram_service),
    memory_service: BaseMemoryService = Depends(get_memory_service)
):
    """Endpoint utama yang menerima update dari Telegram."""

    if not update.message or not update.message.chat:
        logger.debug("Update tanpa message atau chat ID.")
        return Response(status_code=200)

    chat_id = update.message.chat.id
    session_id = str(chat_id)

    # --- PENANGANAN FILE UPLOAD ---
    if update.message.document and update.message.document.mime_type == 'application/pdf':
        await handle_pdf_upload(chat_id, update.message.document, telegram_service, memory_service)
        return Response(status_code=200)
    # ----------------------------

    # --- PENANGANAN PESAN TEKS ---
    if not update.message.text:
        # Kirim pesan jika bukan teks atau PDF (misal stiker)
        await telegram_service.send_reply(chat_id, "Maaf, saya hanya bisa memproses pesan teks atau file PDF.")
        logger.debug("Menerima pesan non-teks, diabaikan.")
        return Response(status_code=200)

    user_input = update.message.text
    logger.info(f"Pesan teks dari [Chat ID: {chat_id}]: {user_input}")

    # Cek command (ambil kata pertama)
    command = user_input.split()[0]
    handler = command_handlers.get(command)

    if handler:
        logger.debug(f"Menjalankan command handler untuk: {command}")
        # Panggil handler dengan argumen yang relevan
        # Perlu penyesuaian argumen berdasarkan handler
        if command in ["/start", "/help"]:
            await handler(chat_id, telegram_service)
        elif command in ["/set_context"]:
             await handler(chat_id, user_input, telegram_service, memory_service)
        elif command in ["/show_context", "/clear_context"]:
             await handler(chat_id, telegram_service, memory_service)
        elif command in ["/create_tc"]:
             await handler(chat_id, user_input, telegram_service, memory_service, agent_executor)
        # Tambahkan else if untuk command lain jika butuh argumen berbeda

        return Response(status_code=200)

    # Jika bukan command, proses dengan agen
    logger.debug(f"Memproses input umum dengan agent untuk session: {session_id}")
    await telegram_service.send_typing_action(chat_id)
    chat_history = memory_service.get_history(session_id)

    try:
        response = await agent_executor.ainvoke({
            "input": user_input,
            "chat_history": chat_history.messages
        })
        output = response["output"]

        chat_history.add_user_message(user_input)
        chat_history.add_ai_message(output)
        memory_service.save_history(session_id, chat_history)

    except Exception as e:
        logger.error(f"Error dari Agent (input umum) session {session_id}: {e}", exc_info=True)
        output = f"Maaf, terjadi error: {e}"

    await telegram_service.send_reply(chat_id, output)
    return Response(status_code=200)