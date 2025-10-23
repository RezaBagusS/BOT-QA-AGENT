# main.py
import logging
from fastapi import FastAPI
from telegram_router import router as telegram_router # Impor router telegram
from config import settings # Impor konfigurasi

# Konfigurasi logging dasar
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler() # Output ke console
        # Anda bisa menambahkan FileHandler di sini jika perlu
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="QA Agent Bot")

# Cek variabel penting saat startup
logger.info(f"Memuat token Telegram: {'OK' if settings.telegram_bot_token != 'YOUR_FALLBACK_TOKEN' else 'MISSING!'}")
logger.info(f"Memuat Google API Key: {'OK' if settings.google_api_key != 'YOUR_FALLBACK_KEY' else 'MISSING!'}")

# Sertakan router Telegram
app.include_router(telegram_router)

@app.get("/", tags=["root"])
def read_root():
    """Endpoint root untuk cek status."""
    logger.info("Root endpoint diakses.")
    return {"message": f"Server {app.title} (Gemini) berjalan."}

# Anda bisa menambahkan event startup/shutdown jika perlu
# @app.on_event("startup")
# async def startup_event():
#     logger.info("Aplikasi FastAPI dimulai...")

# @app.on_event("shutdown")
# async def shutdown_event():
#     logger.info("Aplikasi FastAPI dimatikan...")