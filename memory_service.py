# memory_service.py
from langchain_community.chat_message_histories import ChatMessageHistory
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseMemoryService(ABC):
    @abstractmethod
    def get_history(self, session_id: str) -> ChatMessageHistory:
        pass

    @abstractmethod
    def save_history(self, session_id: str, history: ChatMessageHistory):
        pass

    # <<< TAMBAHKAN INI >>>
    @abstractmethod
    def set_context(self, session_id: str, context: str | None):
        """Menyimpan atau menghapus konteks PRD untuk sesi."""
        pass

    @abstractmethod
    def get_context(self, session_id: str) -> str | None:
        """Mengambil konteks PRD aktif untuk sesi."""
        pass
    # <<<----------------->

class InMemoryMemoryService(BaseMemoryService):
    def __init__(self):
        self._store = {}
        self._context_store = {} # <<< TAMBAHKAN INI
        logger.info("Menggunakan InMemory Memory Service")

    def get_history(self, session_id: str) -> ChatMessageHistory:
        # ... (kode get_history sama)
        if session_id not in self._store:
            self._store[session_id] = ChatMessageHistory()
        return self._store[session_id]

    def save_history(self, session_id: str, history: ChatMessageHistory):
        # ... (kode save_history sama)
        pass

    # <<< TAMBAHKAN IMPLEMENTASI INI >>>
    def set_context(self, session_id: str, context: str | None):
        if context:
            self._context_store[session_id] = context
            logger.info(f"Konteks diatur untuk session: {session_id}")
        elif session_id in self._context_store:
            del self._context_store[session_id]
            logger.info(f"Konteks dihapus untuk session: {session_id}")

    def get_context(self, session_id: str) -> str | None:
        return self._context_store.get(session_id)
    # <<<----------------------------->

def get_memory_service() -> BaseMemoryService:
    return InMemoryMemoryService()