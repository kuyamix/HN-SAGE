# src/core/retrieval.py
import logging
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from src.config import INDEX_PATH, RETRIEVAL_MODE, MMR_LAMBDA, EMBED_MODEL
from src.db import get_db

log = logging.getLogger("core.retrieval")
state = {}

def init_retrieval():
    log.info("Loading embedding model...")
    state["model"] = SentenceTransformer(EMBED_MODEL)

    log.info("Loading FAISS index...")
    state["index"] = faiss.read_index(INDEX_PATH)
    state["all_vectors"] = state["index"].reconstruct_n(0, state["index"].ntotal)

    log.info("Loading chunk_vectors...")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT faiss_row, story_id, chunk_idx FROM chunk_vectors ORDER BY faiss_row"
        ).fetchall()
    state["row_to_pair"] = {r["faiss_row"]: (r["story_id"], r["chunk_idx"]) for r in rows}

    id_to_rowidx = {}
    for row_i, (sid, cidx) in state["row_to_pair"].items():
        id_to_rowidx.setdefault(sid, row_i)
    state["id_to_rowidx"] = id_to_rowidx
    log.info("Retrieval ready: %d vectors", state["index"].ntotal)

def get_story_rows(conn, story_ids):
    if not story_ids: return {}
    qs = ",".join("?" * len(story_ids))
    rows = conn.execute(f"SELECT * FROM stories WHERE id IN ({qs})", story_ids).fetchall()
    return {r["id"]: dict(r) for r in rows}

def to_hit(row, similarity, matched_chunk_idx, matched_doc):
    return {
        "id": row["id"], "title": row["title"], "url": row["url"],
        "by": row["by"], "score": row["score"], "descendants": row.get("descendants", 0),
        "time": row.get("time", 0), "text": row.get("text") or "",
        "comments": json.loads(row.get("comments_json") or "[]"),
        "similarity": round(float(similarity), 3),
        "matched_chunk_idx": matched_chunk_idx,
        "matched_doc": matched_doc,
        "source": row.get("source_id", "hn")  # <--- SOURCE ADDED HERE
    }

def _vector_search(query, k):
    model, index, row_to_pair = state["model"], state["index"], state["row_to_pair"]
    vec = model.encode([query], normalize_embeddings=True).astype("float32")
    k = min(k, index.ntotal)
    scores, idxs = index.search(vec, k)

    best = {}
    with get_db() as conn:
        for score, i in zip(scores[0], idxs[0]):
            if i < 0: continue
            pair = row_to_pair.get(int(i))
            if not pair: continue
            story_id, chunk_idx = pair
            c_row = conn.execute("SELECT doc FROM chunks WHERE story_id=? AND chunk_idx=?", (story_id, chunk_idx)).fetchone()
            doc = c_row["doc"] if c_row else ""
            if story_id not in best or score > best[story_id][0]:
                best[story_id] = (float(score), chunk_idx, doc)
    return best

def _bm25_scores(query, conn, k=30):
    safe = " ".join(t for t in query.split() if t.isalnum() or "-" in t)
    if not safe: return {}
    try:
        rows = conn.execute("""
            SELECT chunks.story_id, bm25(chunks_fts) AS score, chunks.chunk_idx, chunks.doc
            FROM chunks_fts JOIN chunks ON chunks.rowid = chunks_fts.rowid
            WHERE chunks_fts MATCH ? ORDER BY score LIMIT ?
        """, (safe, k)).fetchall()
    except Exception: return {}

    best = {}
    for r in rows:
        s = -float(r["score"])
        sid = r["story_id"]
        if sid not in best or s > best[sid][0]:
            best[sid] = (s, r["chunk_idx"], r["doc"])
    return best

def _mmr_rerank(query_vec, candidate_ids, relevance, k, lambda_=MMR_LAMBDA):
    if not candidate_ids: return []
    vecs, rowidx = state.get("all_vectors"), state.get("id_to_rowidx", {})
    if vecs is None or not rowidx:
        return sorted(candidate_ids, key=lambda s: relevance[s][0], reverse=True)[:k]

    max_rel = max((relevance[s][0] for s in candidate_ids), default=1.0) or 1.0
    selected, remaining = [], list(candidate_ids)
    while remaining and len(selected) < k:
        best_id, best_score = None, -1e9
        for sid in remaining:
            rel = relevance[sid][0] / max_rel
            v = vecs[rowidx[sid]]
            div = max((float(np.dot(v, vecs[rowidx[s]])) for s in selected), default=0.0) if selected else 0.0
            mmr = lambda_ * rel - (1 - lambda_) * div
            if mmr > best_score: best_score, best_id = mmr, sid
        if best_id is None: break
        selected.append(best_id)
        remaining.remove(best_id)
    return selected

def hybrid_search(query, k=5, pool=30):
    qvec = state["model"].encode([query], normalize_embeddings=True).astype("float32")[0]
    with get_db() as conn:
        vec = {} if RETRIEVAL_MODE == "bm25" else _vector_search(query, pool)
        bm = {} if RETRIEVAL_MODE == "vector" else _bm25_scores(query, conn, pool)

        ranks = {}
        for r, sid in enumerate(sorted(vec, key=lambda s: vec[s][0], reverse=True)):
            ranks[sid] = ranks.get(sid, 0.0) + 1.0 / (60 + r + 1)
        for r, sid in enumerate(sorted(bm, key=lambda s: bm[s][0], reverse=True)):
            ranks[sid] = ranks.get(sid, 0.0) + 1.0 / (60 + r + 1)

        candidate_ids = sorted(ranks, key=ranks.get, reverse=True)[:pool]
        relevance = {}
        for sid in candidate_ids:
            relevance[sid] = vec[sid] if sid in vec else bm[sid]

        top_ids = _mmr_rerank(qvec, candidate_ids, relevance, k)
        rows = get_story_rows(conn, top_ids)
        
        hits = []
        for sid in top_ids:
            if sid not in rows: continue
            score, c_idx, doc = relevance[sid]
            hits.append(to_hit(rows[sid], score, c_idx, doc))
        return hits