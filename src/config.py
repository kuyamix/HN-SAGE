# src/config.py
import os
from pathlib import Path

# Base project directory (HCKR folder)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database & Index Paths
DB_PATH = os.getenv("HN_DB", str(DATA_DIR / "hn.db"))
INDEX_PATH = os.getenv("HN_INDEX", str(DATA_DIR / "hn.faiss"))
IDS_PATH = os.getenv("HN_IDS", str(DATA_DIR / "ids.json"))
MIGRATIONS_DIR = BASE_DIR / "migrations"

# Model Settings
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

# LLM Provider Toggle
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama") # 'ollama' or 'openai'

# Local Ollama Settings
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Cloud API Settings (DeepSeek / OpenAI)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# Ingestion Settings
INGEST_LIMIT = int(os.getenv("INGEST_LIMIT", "300"))
COMMENTS_PER_STORY = int(os.getenv("COMMENTS_PER_STORY", "10"))
HN_DEPTH = int(os.getenv("HN_COMMENT_DEPTH", "1"))
PRUNE_REBUILD_THRESHOLD = float(os.getenv("PRUNE_REBUILD_THRESHOLD", "0.05"))

# Retrieval Settings
RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "hybrid")
MMR_LAMBDA = float(os.getenv("MMR_LAMBDA", "0.5"))