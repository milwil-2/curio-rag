# Global configuration loaded from environment
from dotenv import load_dotenv
import os

load_dotenv()

# Embedding + ingestion
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
LANCE_PATH = os.getenv("LANCE_PATH", "./data/lance")
DB_PATH = os.getenv("DB_PATH")

# Local LLM (Ollama) — used by curio ask CLI
MODEL_NAME = os.getenv("LLM_MODEL")
LLM_MODEL = os.getenv("LLM_MODEL")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

# Cloud LLM (Gemini) — used by web demo
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Vector DB (Qdrant Cloud) — used by both CLI and web demo
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "chunks")
