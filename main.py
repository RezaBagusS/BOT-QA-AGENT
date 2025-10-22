# main.py

import os
import httpx # Untuk mengirim pesan kembali ke Telegram
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel # Untuk validasi data dari Telegram
from dotenv import load_dotenv

# Impor "otak" agen kita
from agent_logic import get_qa_agent_executor
from langchain_core.messages import HumanMessage, AIMessage
from langchain.memory import ChatMessageHistory

# --- Setup Awal ---
load_dotenv()
app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Inisialisasi Agen (hanya sekali saat startup)
agent_executor = get_qa_agent_executor()

# Manajemen Memori (Sederhana)
# NOTE: Ini akan reset setiap server restart. Untuk produksi, gunakan database.
chat_memory_store = {}

def get_chat_history(chat_id: int) -> ChatMessageHistory:
    """Mengambil atau membuat memori chat untuk pengguna."""
    if chat_id not in chat_memory_store:
        chat_memory_store[chat_id] = ChatMessageHistory()
    return chat_memory_store[chat_id]

# --- Model Data (Validasi Pydantic) ---
# Ini memastikan data yang masuk dari Telegram sesuai format

class Chat(BaseModel):
    id: int

class Message(BaseModel):
    chat: Chat
    text: str | None = None # Pesan bisa saja bukan teks (stiker, dll)

class Update(BaseModel):
    update_id: int
    message: Message

# --- Fungsi Helper ---

async def send_telegram_reply(chat_id: int, text: str):
    """Mengirim balasan teks ke pengguna via Telegram API."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={"chat_id": chat_id, "text": text}
            )
            response.raise_for_status() # Cek jika ada error HTTP
        except httpx.HTTPStatusError as e:
            print(f"Error saat mengirim balasan: {e}")

# --- Endpoint Server ---

@app.get("/")
def read_root():
    return {"message": "Server QA Agent (Gemini) berjalan."}

@app.post("/webhook/telegram")
async def handle_telegram_webhook(update: Update):
    """
    Endpoint utama yang menerima update dari Telegram.
    """
    # 1. Cek apakah ada pesan teks
    if not update.message or not update.message.text:
        return Response(status_code=200) # Abaikan update non-teks

    chat_id = update.message.chat.id
    user_input = update.message.text
    print(f"Menerima pesan dari [Chat ID: {chat_id}]: {user_input}")
    
    # 2. Ambil memori chat
    chat_history = get_chat_history(chat_id)
    
    # 3. Kirim ke Agen LangChain (gunakan 'ainvoke' untuk async)
    try:
        response = await agent_executor.ainvoke({
            "input": user_input,
            "chat_history": chat_history.messages
        })
        
        output = response["output"]
        
        # 4. Simpan ke memori
        chat_history.add_user_message(user_input)
        chat_history.add_ai_message(output)

    except Exception as e:
        print(f"Error dari Agent: {e}")
        output = f"Maaf, terjadi error: {e}"

    # 5. Kirim balasan ke Telegram
    await send_telegram_reply(chat_id, output)
    
    # 6. Balas Telegram bahwa kita sudah terima
    return Response(status_code=200)