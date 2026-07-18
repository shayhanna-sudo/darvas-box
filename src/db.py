"""SQLite persistence layer (WAL mode) for Darvas-Bot."""
import sqlite3
import os
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS bars_cache (
    symbol TEXT NOT NULL,
    date   TEXT NOT NULL,
    open   REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS box_state (
    symbol         TEXT PRIMARY KEY,
    state          TEXT NOT NULL,
    top_high       REAL,
    bottom_low     REAL,
    top_count      INTEGER DEFAULT 0,
    bottom_count   INTEGER DEFAULT 0,
    entry_price    REAL,
    stop_price     REAL,
    updated_at     TEXT
);

CREATE TABLE IF NOT EXISTS signals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol        TEXT NOT NULL,
    date          TEXT NOT NULL,
    box_top       REAL, box_bottom REAL,
    entry_price   REAL, stop_price REAL,
    fundamental   TEXT,
    theme         TEXT,
    verdict       TEXT,
    status        TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS positions (
    symbol        TEXT PRIMARY KEY,
    qty           REAL,
    entry_price   REAL,
    stop_price    REAL,
    opened_at     TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol        TEXT NOT NULL,
    alpaca_order_id TEXT,
    order_class   TEXT,
    side          TEXT,
    created_at    TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,
    kind      TEXT NOT NULL,
    symbol    TEXT,
    detail    TEXT
);
"""


def init_db(db_path: str):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


@contextmanager
def get_conn(db_path: str):
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
