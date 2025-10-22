# memory_service.py
from langchain_community.chat_message_histories import ChatMessageHistory
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

# Abstract Base Class (untuk mempermudah penggantian ke DB nanti)
class BaseMemoryService(ABC):
    @abstractmethod
    def get_history(self, session_id: str) -> ChatMessageHistory:
        pass

    @abstractmethod
    def save_history(self, session_id: str, history: ChatMessageHistory):
        # Implementasi penyimpanan (misal ke DB) ada di sini nanti
        pass

# Implementasi In-Memory (seperti yang sekarang)
class InMemoryMemoryService(BaseMemoryService):
    def __init__(self):
        self._store = {}
        logger.info("Menggunakan InMemory Memory Service")

    def get_history(self, session_id: str) -> ChatMessageHistory:
        if session_id not in self._store:
            self._store[session_id] = ChatMessageHistory()
            logger.debug(f"Membuat history baru untuk session: {session_id}")
        return self._store[session_id]

    def save_history(self, session_id: str, history: ChatMessageHistory):
        # Untuk in-memory, tidak perlu save eksplisit karena objeknya sama
        logger.debug(f"History untuk session {session_id} otomatis tersimpan (in-memory)")
        pass

# Dependency function untuk FastAPI
# Kita bisa ganti implementasi (misal PostgresMemoryService) di sini nanti
def get_memory_service() -> BaseMemoryService:
    # Saat ini pakai In-Memory
    return InMemoryMemoryService()