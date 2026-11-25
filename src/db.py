# src/db.py
"""Shared DB connection + migration runner."""
import sqlite3
import logging
from src.config import DB_PATH, MIGRATIONS_DIR

log = logging.getLogger("hn_db")

def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn

def get_db():
    return _connect()

def current_version(conn) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]

def _set_version(conn, v: int):
    conn.execute(f"PRAGMA user_version = {int(v)}")

def _check_table_exists(conn, table_name):
    return conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", 
        (table_name,)
    ).fetchone()[0] > 0

def migrate(target: int | None = None):
    """Apply pending migrations in order. Idempotent (tracked by user_version)."""
    conn = _connect()
    try:
        cur = current_version(conn)
        
        # If it's a brand new DB file, initialize it to version -1 so migration 000 runs
        if cur == 0 and not _check_table_exists(conn, "stories"):
            cur = -1
            
        if target is None:
            target = _discover_latest()
        if cur >= target:
            log.info("DB already at version %d", cur)
            return cur

        for v in range(cur + 1, target + 1):
            f = _find_migration(v)
            if f is None:
                raise RuntimeError(f"No migration file for version {v}")
            log.info("Applying migration %s", f.name)
            conn.executescript(f.read_text())
            _set_version(conn, v)
            conn.commit()
        log.info("DB migrated to version %d", target)
        return target
    finally:
        conn.close()

def _discover_latest() -> int:
    if not MIGRATIONS_DIR.exists():
        return 0
    vs = []
    for f in MIGRATIONS_DIR.glob("*.sql"):
        try:
            vs.append(int(f.name.split("_", 1)[0]))
        except ValueError:
            continue
    return max(vs) if vs else 0

def _find_migration(v: int):
    for f in MIGRATIONS_DIR.glob(f"{v:03d}_*.sql"):
        return f
    return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate()