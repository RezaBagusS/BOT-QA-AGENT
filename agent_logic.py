# agent_logic.py

import os
import logging
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings # <<< Gunakan config terpusat

# Setup logging dasar (bisa dikonfigurasi lebih lanjut di main.py)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv() # Load .env jika belum

# --- Definisi Tools ---
@tool
def read_pdf_content(file_path: str) -> str:
    # ... (kode tool sama) ...
    logger.info(f"Mencoba membaca file: {file_path}")
    try:
        # ... (sama)
        return f"Berhasil membaca {len(pages)} halaman. Konten: {content[:1000]}..." # Potong lebih pendek untuk log
    except Exception as e:
        logger.error(f"Gagal membaca file '{file_path}': {e}", exc_info=True) # Tambah exc_info
        return f"Gagal membaca file '{file_path}': {str(e)}"

@tool
def create_testcase(prd_context: str) -> str:
    # ... (kode tool sama) ...
    logger.info("Memanggil tool create_testcase")
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro-latest",
            temperature=0.1,
            google_api_key=settings.google_api_key # <<< Ambil dari config
        )
        # ... (prompt sama) ...
        response = chain.invoke({"context": prd_context})
        return response.content
    except Exception as e:
        logger.error(f"Error di tool create_testcase: {e}", exc_info=True)
        return "Maaf, terjadi error saat membuat test case."


# --- Setup Agen ---
def get_qa_agent_executor():
    """Menginisialisasi dan mengembalikan agent executor."""
    logger.info("Menginisialisasi QA Agent Executor...")
    if not settings.google_api_key or settings.google_api_key == "YOUR_FALLBACK_KEY":
         logger.error("GOOGLE_API_KEY tidak ditemukan atau belum diatur!")
         # Sebaiknya raise error di sini agar aplikasi tidak jalan tanpa key
         raise ValueError("GOOGLE_API_KEY is not set correctly.")

    tools = [read_pdf_content, create_testcase]

    agent_llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro-latest",
        temperature=0,
        google_api_key=settings.google_api_key # <<< Ambil dari config
    )
    agent_llm = agent_llm.bind_tools(tools)

    agent_prompt = ChatPromptTemplate.from_messages([
        ("system", "Anda adalah asisten QA. Selalu gunakan tools jika diperlukan. Jawab dengan ringkas."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(agent_llm, tools, agent_prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True, # Biarkan verbose untuk debugging
        handle_parsing_errors=True # Lebih robust
    )
    logger.info("QA Agent Executor berhasil diinisialisasi.")
    return agent_executor

# --- Dependency untuk FastAPI ---
# Buat instance agent sekali saja saat startup
agent_executor_instance = get_qa_agent_executor()

def get_agent_executor():
    return agent_executor_instance