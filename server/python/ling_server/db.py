"""SQLite 索引 schema 与小工具。"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    status      TEXT NOT NULL,
    deadline    TEXT,
    notes       TEXT,
    source      TEXT,
    updated_at  TEXT NOT NULL,
    raw_hash    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reminders (
    id          TEXT PRIMARY KEY,
    task_id     TEXT NOT NULL,
    fire_at     TEXT NOT NULL,
    state       TEXT NOT NULL,
    last_error  TEXT
);
CREATE INDEX IF NOT EXISTS idx_reminders_state_fire ON reminders(state, fire_at);

CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    payload     TEXT NOT NULL,
    state       TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_state_created ON events(state, created_at);

CREATE TABLE IF NOT EXISTS workdir_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def set_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO workdir_state(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_state(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM workdir_state WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None
