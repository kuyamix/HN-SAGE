# src/main.py
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # <-- Need this import

from src.db import migrate
from src.core.retrieval import init_retrieval
from src.api.routes import router as api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Ensuring schema...")
    migrate()
    init_retrieval()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 1. Include API routes
app.include_router(api_router)

# 2. Mount the static folder (MUST BE AFTER include_router)
STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")