# config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_FALLBACK_TOKEN")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "YOUR_FALLBACK_KEY")
    telegram_api_url: str = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}"
    model: str = "gemini-2.5-pro"
    # Tambahkan konfigurasi lain jika perlu

    class Config:
        env_file = ".env" # Memastikan .env tetap dibaca jika ada

settings = Settings()