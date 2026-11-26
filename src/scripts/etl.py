# src/scripts/etl.py
import sqlite3
import logging
from datetime import datetime, timezone
from src.config import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("etl")

def run_etl():
    log.info("Starting ETL pipeline...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 1. EXTRACT: Read from Operational DB
    log.info("Extracting stories from operational database...")
    stories = conn.execute("SELECT * FROM stories").fetchall()
    log.info(f"Extracted {len(stories)} rows.")

    # 2. TRANSFORM & LOAD: Dimensions
    for s in stories:
        # Dimension: Time
        dt = datetime.fromtimestamp(s["time"], tz=timezone.utc)
        time_key = int(dt.strftime("%Y%m%d"))
        conn.execute("""
            INSERT OR IGNORE INTO dw_dim_time (time_key, year, month, day) 
            VALUES (?, ?, ?, ?)
        """, (time_key, dt.year, dt.month, dt.day))

        # Dimension: Source
        source_name = s["source_id"] or "hn"
        conn.execute("INSERT OR IGNORE INTO dw_dim_source (source_name) VALUES (?)", (source_name,))
        source_id = conn.execute("SELECT source_key FROM dw_dim_source WHERE source_name = ?", (source_name,)).fetchone()[0]

        # Dimension: Author
        author = s["by"] or "unknown"
        conn.execute("INSERT OR IGNORE INTO dw_dim_author (username) VALUES (?)", (author,))
        author_id = conn.execute("SELECT author_key FROM dw_dim_author WHERE username = ?", (author,)).fetchone()[0]

        # 3. LOAD: Fact Table
        conn.execute("""
            INSERT OR REPLACE INTO dw_fact_stories 
            (story_id, source_key, author_key, time_key, title, score, num_comments)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (s["id"], source_id, author_id, time_key, s["title"], s["score"], s["descendants"]))

    conn.commit()
    conn.close()
    log.info("ETL pipeline completed successfully. Warehouse is updated.")

if __name__ == "__main__":
    run_etl()