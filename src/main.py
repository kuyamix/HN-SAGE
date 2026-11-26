# src/main.py
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config import DB_PATH, INDEX_PATH
from src.db import migrate
from src.core.retrieval import init_retrieval
from src.api.routes import router as api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Ensuring schema...")
    migrate()
    
    # Check if DB exists and has data
    import os
    if not os.path.exists(INDEX_PATH) or not os.path.exists(DB_PATH):
        log.warning("Database or Index missing! Initializing empty schema.")
    
    log.info("Loading retrieval engine...")
    try:
        init_retrieval()
    except Exception as e:
        log.error(f"Could not load FAISS index: {e}")
        log.error("The app will start, but search will fail until data is ingested.")
    
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)

STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")