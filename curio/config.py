# Global Constraints
from dotenv import load_dotenv
import os

load_dotenv()
MODEL_NAME = os.getenv("LLM_MODEL")

LANCE_PATH = os.getenv("LANCE_PATH")
DB_PATH = os.getenv("DB_PATH")
EMBED_MODEL = os.getenv("EMBED_MODEL")
LLM_MODEL = os.getenv("LLM_MODEL") # change phase 3
OLLAMA_URL = os.getenv("OLLAMA_URL")
