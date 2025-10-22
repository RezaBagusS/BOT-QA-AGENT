# memory_service.py
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseMemoryService(ABC):
    """
    Struktur dasar untuk memory service.
    Dikosongkan karena tidak ada state yang perlu disimpan untuk /start dan /help.
    """
    pass

class InMemoryMemoryService(BaseMemoryService):
    """
    Implementasi memory service dalam memori.
    Dikosongkan karena tidak ada state yang perlu disimpan.
    """
    def __init__(self):
        logger.info("Menggunakan InMemory Memory Service (Kosong)")
        pass

def get_memory_service() -> BaseMemoryService:
    """Dependency injector untuk memory service."""
    return InMemoryMemoryService()