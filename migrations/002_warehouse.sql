-- migrations/002_warehouse.sql
-- Data Warehouse: Star Schema
-- Grain: One row per story.

CREATE TABLE IF NOT EXISTS dw_dim_source (
    source_key INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS dw_dim_author (
    author_key INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS dw_dim_time (
    time_key INTEGER PRIMARY KEY, -- Format: YYYYMMDD
    year INTEGER,
    month INTEGER,
    day INTEGER
);

CREATE TABLE IF NOT EXISTS dw_fact_stories (
    story_id TEXT PRIMARY KEY,
    source_key INTEGER,
    author_key INTEGER,
    time_key INTEGER,
    title TEXT,
    score INTEGER,
    num_comments INTEGER,
    FOREIGN KEY(source_key) REFERENCES dw_dim_source(source_key),
    FOREIGN KEY(author_key) REFERENCES dw_dim_author(author_key),
    FOREIGN KEY(time_key) REFERENCES dw_dim_time(time_key)
);