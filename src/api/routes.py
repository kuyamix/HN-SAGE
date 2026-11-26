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
        "llm_model": f"{LLM_PROVIDER}/{active_model}"
    }

@router.get("/search")
def search(q: str, k: int = Query(10, ge=1, le=30)):
    return retrieval.hybrid_search(q, k=k)

@router.get("/ask/stream")
def ask_stream(q: str, k: int = Query(8, ge=1, le=30)):
    hits = retrieval.hybrid_search(q, k=k)
    return StreamingResponse(llm.stream_llm_response(q, hits), media_type="application/x-ndjson")

@router.get("/analytics")
def analytics():
    """Analytics endpoint querying the Data Warehouse."""
    with get_db() as conn:
        # 1. Stories by Source
        source_counts = conn.execute("""
            SELECT ds.source_name, COUNT(*) as count
            FROM dw_fact_stories f
            JOIN dw_dim_source ds ON f.source_key = ds.source_key
            GROUP BY ds.source_name
        """).fetchall()

        # 2. Top Authors by Total Score
        top_authors = conn.execute("""
            SELECT da.username, SUM(f.score) as total_score, COUNT(*) as stories
            FROM dw_fact_stories f
            JOIN dw_dim_author da ON f.author_key = da.author_key
            GROUP BY da.username
            ORDER BY total_score DESC
            LIMIT 5
        """).fetchall()

        # 3. Activity over Time (Last 6 months)
        activity = conn.execute("""
            SELECT dt.year, dt.month, COUNT(*) as count
            FROM dw_fact_stories f
            JOIN dw_dim_time dt ON f.time_key = dt.time_key
            GROUP BY dt.year, dt.month
            ORDER BY dt.year DESC, dt.month DESC
            LIMIT 6
        """).fetchall()

    return {
        "sources": [dict(r) for r in source_counts],
        "top_authors": [dict(r) for r in top_authors],
        "activity": [dict(r) for r in activity]
    }