# main.py

import os
import httpx 
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from dotenv import load_dotenv
from agent_logic import get_qa_agent_executor
from langchain_core.messages import HumanMessage, AIMessage
# --- GANTI IMPORT INI ---
# from langchain.memory import ChatMessageHistory 
from langchain_community.chat_message_histories import ChatMessageHistory # <<< BARU

# --- Setup Awal ---
load_dotenv()
app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

agent_executor = get_qa_agent_executor()
chat_memory_store = {}

def get_chat_history(chat_id: int) -> ChatMessageHistory:
    if chat_id not in chat_memory_store:
        chat_memory_store[chat_id] = ChatMessageHistory()
    return chat_memory_store[chat_id]

# --- Model Data ---
class Chat(BaseModel):
    id: int

class Message(BaseModel):
    chat: Chat
    text: str | None = None

class Update(BaseModel):
    update_id: int
    message: Message | None = None # Jadikan message opsional

# --- Fungsi Helper ---
async def send_telegram_reply(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={"chat_id": chat_id, "text": text}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"Error saat mengirim balasan: {e.response.text}") # Tampilkan detail error
        except Exception as e:
            print(f"Error tak terduga saat mengirim balasan: {e}")

# --- Endpoint Server ---
@app.get("/")
def read_root():
    return {"message": "Server QA Agent (Gemini) berjalan."}

@app.post("/webhook/telegram")
async def handle_telegram_webhook(update: Update):
    """ Endpoint utama yang menerima update dari Telegram. """
    
    # 1. Validasi Update (Lebih Aman)
    if not update.message or not update.message.text or not update.message.chat:
        print("Menerima update tanpa pesan teks atau chat ID, diabaikan.")
        return Response(status_code=200) 

    chat_id = update.message.chat.id
    user_input = update.message.text
    print(f"Menerima pesan dari [Chat ID: {chat_id}]: {user_input}")

    # --- TAMBAHKAN PENANGANAN /start DI SINI ---
    if user_input == "/start":
        welcome_message = "Halo! 👋 Saya adalah QA Agent Anda. Kirimkan saya perintah atau nama file PDF untuk diproses."
        await send_telegram_reply(chat_id, welcome_message)
        return Response(status_code=200) # Selesai, tidak perlu ke agen
    # ------------------------------------------

    # 2. Ambil memori chat (Hanya jika bukan /start)
    chat_history = get_chat_history(chat_id)
    
    # 3. Kirim ke Agen LangChain
    try:
        # Kirim notifikasi "sedang mengetik..."
        async with httpx.AsyncClient() as client:
           await client.post(f"{TELEGRAM_API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})

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
        # Tambahkan traceback untuk detail error
        import traceback
        traceback.print_exc() 
        output = f"Maaf, terjadi error saat memproses permintaan Anda: {e}"

    # 5. Kirim balasan ke Telegram
    await send_telegram_reply(chat_id, output)
    
    # 6. Balas Telegram bahwa kita sudah terima
    return Response(status_code=200)