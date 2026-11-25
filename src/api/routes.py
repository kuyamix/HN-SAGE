# src/api/routes.py
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from src.core import retrieval, llm
from src.config import RETRIEVAL_MODE, OLLAMA_MODEL, LLM_MODEL, LLM_PROVIDER
from src.db import get_db

router = APIRouter()

@router.get("/health")
def health():
    with get_db() as conn:
        n_docs = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
        n_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    
    active_model = OLLAMA_MODEL if LLM_PROVIDER == "ollama" else LLM_MODEL
    return {
        "ok": True, 
        "mode": RETRIEVAL_MODE, 
        "vectors": retrieval.state["index"].ntotal,
        "story_rows": n_docs, 
        "chunk_rows": n_chunks, 
        "llm_model": f"{LLM_PROVIDER}/{active_model}" # Shows e.g. "ollama/llama3.2"
    }

@router.get("/search")
def search(q: str, k: int = Query(10, ge=1, le=30)):
    return retrieval.hybrid_search(q, k=k)

@router.get("/ask/stream")
def ask_stream(q: str, k: int = Query(8, ge=1, le=30)):
    hits = retrieval.hybrid_search(q, k=k)
    return StreamingResponse(llm.stream_llm_response(q, hits), media_type="application/x-ndjson")