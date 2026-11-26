# src/main.py
import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config import DB_PATH, INDEX_PATH
from src.db import migrate, get_db
from src.core.retrieval import init_retrieval
from src.api.routes import router as api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("main")

async def auto_ingest_loop():
    """Background task to fetch new stories every hour."""
    from src.ingest.sources.hackernews import run_hn_ingest
    from src.ingest.sources.lobsters import run_lobsters_ingest
    
    while True:
        try:
            log.info("Background Task: Fetching latest stories...")
            # Run in threadpool so it doesn't block the async event loop
            await asyncio.to_thread(run_hn_ingest, 20)
            await asyncio.to_thread(run_lobsters_ingest, 10)
            
            # Reload the FAISS index into memory so the new vectors are searchable!
            init_retrieval() 
            log.info("Background Task: Ingestion complete. Index reloaded.")
            
        except Exception as e:
            log.error(f"Background Task Error: {e}")
            
        # Sleep for 1 hour (3600 seconds)
        await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Ensuring schema...")
    migrate()
    
    # Check if DB is empty (e.g. on a fresh Render deploy)
    with get_db() as conn:
        story_count = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
    
    if story_count == 0:
        log.warning("Database is empty! Bootstrapping initial data...")
        from src.ingest.sources.hackernews import run_hn_ingest
        # Fetch just 10 stories to get the app working immediately
        await asyncio.to_thread(run_hn_ingest, 10)
        log.info("Bootstrap complete.")
        
    log.info("Loading retrieval engine...")
    try:
        init_retrieval()
    except Exception as e:
        log.error(f"Could not load FAISS index: {e}")
    
    # Start the background loop
    task = asyncio.create_task(auto_ingest_loop())
    
    yield
    
    # Cleanup
    task.cancel()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)

STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")