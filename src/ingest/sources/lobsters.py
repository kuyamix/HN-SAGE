# src/ingest/sources/lobsters.py
import time
import logging
import requests
from datetime import datetime

from src.ingest.sources.base import RawDoc, RawComment
from src.ingest.orchestrator import html_to_text, ingest_docs

BASE = "https://lobste.rs"
HEADERS = {"User-Agent": "HN-Sage/1.0 (RAG Demo)"}
log = logging.getLogger("ingest.lobsters")

class LobstersAdapter:
    id = "lobsters"

    def fetch_ids(self, limit: int) -> list[str]:
        log.info("Fetching hottest ids from Lobsters…")
        r = requests.get(f"{BASE}/hottest.json", headers=HEADERS, timeout=10)
        r.raise_for_status()
        # Lobsters returns the full story list in one go. We just grab the short_ids.
        return [s["short_id"] for s in r.json()[:limit]]

    def fetch_doc(self, native_id: str) -> RawDoc | None:
        try:
            r = requests.get(f"{BASE}/s/{native_id}.json", headers=HEADERS, timeout=10)
            if r.status_code != 200:
                return None
            s = r.json()
            
            comments = self._flatten_comments(s.get("comments", []))
            
            # Lobsters uses ISO 8601 strings for dates. We convert to Unix timestamp.
            dt = datetime.fromisoformat(s["created_at"].replace("Z", "+00:00"))
            
            return RawDoc(
                source_id="lobsters",
                native_id=s["short_id"],
                kind="story",
                title=s["title"],
                url=s.get("url") or s.get("comments_url", ""),
                author=s.get("submitter_user", ""),
                score=s.get("score", 0),
                num_comments=s.get("comment_count", 0),
                published_at=int(dt.timestamp()),
                text=html_to_text(s.get("description", "")),
                extra={"tags": s.get("tags", [])},
                comments=comments[:5], # Keep top 5 to match HN
            )
        except Exception as e:
            log.warning(f"Failed to fetch Lobsters doc {native_id}: {e}")
            return None

    def _flatten_comments(self, tree, depth=0, out=None):
        """Lobsters comments are nested JSON. We flatten them into a list."""
        if out is None: out = []
        for c in tree:
            if c.get("commenting_user"):
                out.append(RawComment(
                    id=c["short_id"],
                    parent_id=None,
                    by=c["commenting_user"],
                    text=html_to_text(c.get("comment", "")),
                    depth=depth,
                ))
            self._flatten_comments(c.get("comments", []), depth+1, out)
        return out


# --- Add this block so you can run it directly ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    
    adapter = LobstersAdapter()
    ids = adapter.fetch_ids(limit=50)
    
    docs = []
    for i, native_id in enumerate(ids, 1):
        log.info(f"Fetching Lobsters doc {i}/{len(ids)}...")
        doc = adapter.fetch_doc(native_id)
        if doc:
            docs.append(doc)
        time.sleep(0.5) # Be polite to their API
        
    log.info(f"Handing {len(docs)} Lobsters docs to orchestrator...")
    ingest_docs(docs)
    log.info("Lobsters ingestion complete!")