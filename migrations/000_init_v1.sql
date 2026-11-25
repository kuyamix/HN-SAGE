-- migrations/000_init_v1.sql
-- Creates the base tables (v1) for a fresh install.

CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY, 
    title TEXT, 
    url TEXT, 
    by TEXT, 
    score INTEGER,
    descendants INTEGER, 
    time INTEGER, 
    text TEXT, 
    comments_json TEXT, 
    doc_hash TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    story_id INTEGER, 
    chunk_idx INTEGER, 
    doc TEXT, 
    doc_hash TEXT,
    PRIMARY KEY (story_id, chunk_idx)
);