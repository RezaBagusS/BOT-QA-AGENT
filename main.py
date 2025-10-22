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
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Simple QA Bot")

# Cek variabel penting saat startup
logger.info(f"Memuat token Telegram: {'OK' if settings.telegram_bot_token != 'YOUR_FALLBACK_TOKEN' else 'MISSING!'}")
# Hapus log untuk Google API Key

# Sertakan router Telegram
app.include_router(telegram_router)

@app.get("/", tags=["root"])
def read_root():
    """Endpoint root untuk cek status."""
    logger.info("Root endpoint diakses.")
    return {"message": f"Server {app.title} berjalan."}