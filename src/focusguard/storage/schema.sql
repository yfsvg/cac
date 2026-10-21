-- Draft schema; not applied anywhere yet.

CREATE TABLE IF NOT EXISTS app_rules (
    app_id      TEXT PRIMARY KEY,
    app_name    TEXT NOT NULL,
    verdict     TEXT NOT NULL CHECK (verdict IN ('productive', 'unproductive', 'unknown')),
    is_browser  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS site_rules (
    site_root   TEXT PRIMARY KEY,
    verdict     TEXT NOT NULL CHECK (verdict IN ('productive', 'unproductive', 'unknown')),
    source      TEXT NOT NULL DEFAULT 'user',  -- 'user' or 'ai'
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS schedules (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    weekdays    TEXT NOT NULL,                 -- comma-separated 0-6
    start_time  TEXT NOT NULL,                 -- HH:MM
    end_time    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    app_id      TEXT NOT NULL,
    window_title TEXT,
    site_root   TEXT,
    verdict     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS goals (
    id          INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    target_minutes INTEGER,
    period      TEXT NOT NULL DEFAULT 'daily'  -- 'daily' or 'weekly'
);
