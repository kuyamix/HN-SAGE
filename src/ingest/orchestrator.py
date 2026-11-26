# src/ingest/orchestrator.py
import hashlib, json, logging, os, re, time
from html.parser import HTMLParser
import faiss
from sentence_transformers import SentenceTransformer

from src.config import INDEX_PATH, IDS_PATH, EMBED_MODEL, PRUNE_REBUILD_THRESHOLD
from src.db import get_db, migrate
from src.ingest.sources.base import RawDoc

log = logging.getLogger("ingest.orchestrator")

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, data): self.parts.append(data)
    def text(self): return re.sub(r"\s+", " ", "".join(self.parts)).strip()

def html_to_text(html: str) -> str:
    if not html: return ""
    p = _HTMLStripper()
    try: p.feed(html)
    except: return ""
    return p.text()

def doc_hash(doc: str) -> str:
    return hashlib.sha256(doc.encode("utf-8")).hexdigest()

def chunk_doc(doc: RawDoc) -> list[dict]:
    chunks = []
    body = f"Title: {doc.title}\n\n{doc.text}".strip()
    chunks.append({
        "doc_id": f"{doc.source_id}:{doc.native_id}", 
        "chunk_idx": 0, "chunk_kind": "title", "parent_id": None, "depth": 0, 
        "doc": body, "hash": doc_hash(body)
    })
    for j, c in enumerate(doc.comments, 1):
        text = f"Title: {doc.title} (Comment by {c.by}): {c.text}"
        chunks.append({
            "doc_id": f"{doc.source_id}:{doc.native_id}", 
            "chunk_idx": j, "chunk_kind": "comment", "parent_id": c.parent_id, 
            "depth": c.depth, "doc": text, "hash": doc_hash(text)
        })
    return chunks

def ingest_docs(docs: list[RawDoc]):
    migrate()
    if not docs: return
    model = SentenceTransformer(EMBED_MODEL)

    with get_db() as conn:
        # Upsert stories
        rows = []
        for d in docs:
            rows.append((
                f"{d.source_id}:{d.native_id}", d.source_id, d.native_id,
                d.title, d.url, d.url, d.author, d.score, d.num_comments, d.published_at,
                d.text, json.dumps([c.__dict__ for c in d.comments]),
                "", d.kind, "", doc_hash(f"{d.title}|{d.text}"), int(time.time()), int(time.time()), None
            ))
        conn.executemany("""
            INSERT OR REPLACE INTO stories 
            (id, source_id, native_id, title, url, canonical_url, by, score, descendants, time, text, comments_json, doc_hash, type, domain, story_hash, fetched_at, updated_at, extra_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows)

        # Chunks
        all_chunks = []
        for d in docs: all_chunks.extend(chunk_doc(d))
        
        existing = {(r["story_id"], r["chunk_idx"]): r["doc_hash"] for r in conn.execute("SELECT story_id, chunk_idx, doc_hash FROM chunks")}
        to_embed = [c for c in all_chunks if existing.get((c["doc_id"], c["chunk_idx"])) != c["hash"]]

        if not to_embed:
            log.info("No new chunks to embed.")
            # Even if no new chunks, ensure the index file exists
            if not os.path.exists(INDEX_PATH):
                log.warning("FAISS index missing but chunks exist. Forcing rebuild.")
                force_build_index()
            return

        # Insert chunks
        conn.executemany(
            "INSERT OR REPLACE INTO chunks (story_id, chunk_idx, chunk_kind, parent_id, depth, doc, doc_hash) VALUES (?,?,?,?,?,?,?)",
            [(c["doc_id"], c["chunk_idx"], c["chunk_kind"], c["parent_id"], c["depth"], c["doc"], c["hash"]) for c in to_embed]
        )
        conn.commit()

        # Embed
        log.info(f"Embedding {len(to_embed)} chunks...")
        vecs = model.encode([c["doc"] for c in to_embed], normalize_embeddings=True, batch_size=32).astype("float32")

        # Append or create FAISS
        if os.path.exists(INDEX_PATH):
            index = faiss.read_index(INDEX_PATH)
            start_row = index.ntotal
        else:
            index = faiss.IndexFlatIP(vecs.shape[1])
            start_row = 0

        index.add(vecs)
        # Atomic save to prevent corruption
        tmp_path = INDEX_PATH + ".tmp"
        faiss.write_index(index, tmp_path)
        os.replace(tmp_path, INDEX_PATH)

        conn.executemany(
            "INSERT INTO chunk_vectors (faiss_row, story_id, chunk_idx) VALUES (?,?,?)",
            [(start_row + i, c["doc_id"], c["chunk_idx"]) for i, c in enumerate(to_embed)]
        )
        conn.commit()
        log.info("Ingest complete.")

def force_build_index():
    """Builds FAISS from scratch using whatever is in the SQLite database."""
    log.info("Forcing FAISS index build from database...")
    model = SentenceTransformer(EMBED_MODEL)
    
    with get_db() as conn:
        rows = conn.execute("SELECT story_id, chunk_idx, doc FROM chunks ORDER BY story_id, chunk_idx").fetchall()
    
    if not rows:
        log.warning("No chunks in database. Run the ingest script first.")
        return

    docs = [r["doc"] for r in rows]
    log.info(f"Embedding {len(docs)} chunks...")
    vecs = model.encode(docs, normalize_embeddings=True, batch_size=32).astype("float32")
    
    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)
    
    # Atomic save
    tmp_path = INDEX_PATH + ".tmp"
    faiss.write_index(index, tmp_path)
    os.replace(tmp_path, INDEX_PATH)
    
    with get_db() as conn:
        conn.execute("DELETE FROM chunk_vectors")
        conn.executemany(
            "INSERT INTO chunk_vectors (faiss_row, story_id, chunk_idx) VALUES (?,?,?)",
            [(i, r["story_id"], r["chunk_idx"]) for i, r in enumerate(rows)]
        )
        conn.commit()
    
    log.info(f"Successfully built FAISS index with {len(docs)} vectors at {INDEX_PATH}")