-- migrations/001_v2_schema.sql
-- Upgrades the DB to the multi-source v2 schema.

PRAGMA foreign_keys = ON;

-- 1. Drop old v1 tables if they exist (fresh start for v2)
DROP TABLE IF EXISTS stories;
DROP TABLE IF EXISTS chunks;
DROP TABLE IF EXISTS chunks_fts;

-- 2. Create the new v2 'stories' table (TEXT id for namespaces)
CREATE TABLE stories (
    id TEXT PRIMARY KEY,           -- e.g. 'hn:12345'
    source_id TEXT DEFAULT 'hn',
    native_id TEXT,
    title TEXT,
    url TEXT,
    canonical_url TEXT,
    by TEXT,
    score INTEGER,
    descendants INTEGER,
    time INTEGER,
    text TEXT,
    comments_json TEXT,
    doc_hash TEXT,
    type TEXT,
    domain TEXT,
    story_hash TEXT,
    fetched_at INTEGER,
    updated_at INTEGER,
    extra_json TEXT
);

-- 3. Create the new v2 'chunks' table (TEXT story_id)
CREATE TABLE chunks (
    story_id TEXT REFERENCES stories(id) ON DELETE CASCADE,
    chunk_idx INTEGER,
    chunk_kind TEXT,
    parent_id TEXT,
    depth INTEGER,
    doc TEXT,
    doc_hash TEXT,
    token_count INTEGER,
    PRIMARY KEY (story_id, chunk_idx)
);

-- 4. Create the FTS5 table and triggers
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    doc, content='chunks', content_rowid='rowid', tokenize='porter unicode61'
);

CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, doc) VALUES (new.rowid, new.doc);
END;
CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, doc) VALUES ('delete', old.rowid, old.doc);
END;
CREATE TRIGGER chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, doc) VALUES ('delete', old.rowid, old.doc);
    INSERT INTO chunks_fts(rowid, doc) VALUES (new.rowid, new.doc);
END;

-- 5. Create the chunk_vectors table
CREATE TABLE chunk_vectors (
    faiss_row INTEGER PRIMARY KEY,
    story_id TEXT NOT NULL,
    chunk_idx INTEGER NOT NULL
);