import sqlite3
import json
from datetime import date, timedelta

DB_PATH = "stock_cache.db"

def init_cache():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY, value TEXT, expires TEXT
        )
    """)
    conn.execute("DELETE FROM cache WHERE expires <= ?", (date.today().isoformat(),))
    conn.commit()
    conn.close()

def get_cached(key: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT value FROM cache WHERE key = ? AND expires > ?",
        (key, date.today().isoformat()),
    ).fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

def set_cached(key: str, value: dict, ttl_days: int = 1):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)",
        (key, json.dumps(value, default=str),
         (date.today() + timedelta(days=ttl_days)).isoformat()),
    )
    conn.commit()
    conn.close()
