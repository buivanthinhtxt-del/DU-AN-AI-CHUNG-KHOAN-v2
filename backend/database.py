import sqlite3
import datetime
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = str(BASE_DIR / "antigravity.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            symbol TEXT PRIMARY KEY,
            added_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_watchlist():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT symbol, added_at FROM watchlist ORDER BY added_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [{"symbol": r[0], "added_at": r[1]} for r in rows]

def add_watchlist(symbol: str):
    symbol = symbol.upper()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO watchlist (symbol, added_at)
        VALUES (?, ?)
    ''', (symbol, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def remove_watchlist(symbol: str):
    symbol = symbol.upper()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()
