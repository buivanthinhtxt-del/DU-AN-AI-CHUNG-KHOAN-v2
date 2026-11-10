"""Watchlist — lưu ở PostgreSQL khi có DATABASE_URL, ngược lại SQLite cục bộ antigravity.db."""
import datetime
from pathlib import Path

import db_backend

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = str(BASE_DIR / "antigravity.db")


def init_db():
    with db_backend.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                added_at TEXT
            )
            """
        )


def get_watchlist():
    with db_backend.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT symbol, added_at FROM watchlist ORDER BY added_at DESC").fetchall()
    return [{"symbol": r["symbol"], "added_at": r["added_at"]} for r in rows]


def add_watchlist(symbol: str):
    symbol = symbol.upper()
    with db_backend.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO watchlist (symbol, added_at) VALUES (?, ?)
            ON CONFLICT (symbol) DO UPDATE SET added_at = excluded.added_at
            """,
            (symbol, datetime.datetime.now().isoformat()),
        )


def remove_watchlist(symbol: str):
    symbol = symbol.upper()
    with db_backend.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
