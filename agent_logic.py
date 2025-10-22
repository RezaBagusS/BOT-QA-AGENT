# agent_logic.py

import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ChatMessageHistory

# Muat .env
load_dotenv()

# --- Definisi Tools Anda ---

@tool
def read_pdf_content(file_path: str) -> str:
    """Membaca teks dari file PDF."""
    print(f"--- Membaca file: {file_path} ---")
    try:
        # Asumsikan file PDF ada di folder yang sama
        loader = PyPDFLoader(file_path)
        pages = loader.load_and_split()
        content = "\n".join([page.page_content for page in pages])
        return f"Berhasil membaca {len(pages)} halaman. Konten: {content[:4000]}..."
    except Exception as e:
        return f"Gagal membaca file '{file_path}': {str(e)}"

@tool
def create_testcase(prd_context: str) -> str:
    """Membuat test case baru berdasarkan PRD."""
    print("--- Memanggil create_testcase tool (Gemini) ---")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro-latest", 
        temperature=0.1, 
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Anda adalah QA Engineer senior. Buat test case detail (nama, deskripsi, prekondisi, langkah & hasil) berdasarkan PRD."),
        ("human", "PRD_CONTEXT:\n{context}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"context": prd_context})
    return response.content

# --- Setup Agen (Menggunakan Gemini sebagai "Otak") ---

def get_qa_agent_executor():
    """Menginisialisasi dan mengembalikan agent executor."""
    
    tools = [read_pdf_content, create_testcase]
    
    agent_llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro-latest", 
        temperature=0, 
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    # Model Gemini yang lebih baru menggunakan 'tool_choice'
    # Kita perlu memastikan LLM bisa memanggil tools
    agent_llm = agent_llm.bind_tools(tools)
    
    agent_prompt = ChatPromptTemplate.from_messages([
        ("system", "Anda adalah asisten QA. Selalu gunakan tools jika diperlukan."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(agent_llm, tools, agent_prompt)
    
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True
    )
    return agent_executor