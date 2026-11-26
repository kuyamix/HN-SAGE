# src/ingest/sources/hackernews.py
import os
import time
import logging
import requests

from src.config import INGEST_LIMIT, COMMENTS_PER_STORY, HN_DEPTH
from src.ingest.sources.base import RawDoc, RawComment
from src.ingest.orchestrator import html_to_text, ingest_docs

BASE = "https://hacker-news.firebaseio.com/v0"
log = logging.getLogger("ingest.hn")

def fetch_json(url: str):
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_comments(story: dict) -> list[RawComment]:
    out: list[RawComment] = []
    queue = [(k, None, 0) for k in (story.get("kids") or [])[:COMMENTS_PER_STORY]]
    while queue and len(out) < COMMENTS_PER_STORY:
        kid, parent, d = queue.pop(0)
        try: 
            c = fetch_json(f"{BASE}/item/{kid}.json")
        except: 
            continue
        if not c or c.get("deleted") or c.get("dead"): 
            continue
        text = html_to_text(c.get("text", ""))
        if not text: 
            continue
        out.append(RawComment(
            id=str(c["id"]), 
            parent_id=str(parent) if parent else None, 
            by=c.get("by", ""), 
            text=text, 
            depth=d
        ))
        if d + 1 < HN_DEPTH:
            for sub in (c.get("kids") or [])[:2]:
                queue.append((sub, c["id"], d + 1))
    return out

class HackerNewsAdapter:
    id = "hn"

    def fetch_ids(self, limit: int) -> list[str]:
        log.info(f"Fetching topstories ids…")
        ids = fetch_json(f"{BASE}/topstories.json")[:limit]
        return [str(i) for i in ids]

    def fetch_doc(self, native_id: str) -> RawDoc | None:
        try: 
            item = fetch_json(f"{BASE}/item/{native_id}.json")
        except: 
            return None
        if not item or not item.get("title"): 
            return None
        
        return RawDoc(
            source_id="hn",
            native_id=str(item["id"]),
            kind="story",
            title=item["title"],
            url=item.get("url", ""),
            author=item.get("by", ""),
            score=item.get("score", 0),
            num_comments=item.get("descendants", 0),
            published_at=item.get("time", 0),
            text=html_to_text(item.get("text", "")),
            extra={"feed": item.get("type", "story")},
            comments=fetch_comments(item),
        )

def run_hn_ingest(limit=20):
    """Reusable function for background tasks and CLI."""
    adapter = HackerNewsAdapter()
    ids = adapter.fetch_ids(limit)
    docs = []
    for native_id in ids:
        doc = adapter.fetch_doc(native_id)
        if doc:
            docs.append(doc)
        time.sleep(0.05)
    
    if docs:
        ingest_docs(docs)
        return len(docs)
    return 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log.info("Starting HN ingestion...")
    count = run_hn_ingest(limit=INGEST_LIMIT)
    log.info(f"Finished ingesting {count} HN docs.")