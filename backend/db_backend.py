"""
Lớp lưu trữ dùng chung (Storage Backend) — SQLite cục bộ hoặc PostgreSQL đám mây.

- Nếu biến môi trường DATABASE_URL (postgres://... hoặc postgresql://...) được đặt,
  mọi dữ liệu bền vững (Điểm Công Huân, biên bản Quân Cơ, lịch sử dự báo, watchlist,
  kết quả chấm điểm hằng ngày) sẽ được ghi vào Postgres (vd: Neon free tier),
  nên KHÔNG bị mất khi container Render Free ngủ/khởi động lại.
- Nếu không có DATABASE_URL, hệ thống tiếp tục dùng SQLite cục bộ như trước.

Mã SQL trong các module dùng placeholder kiểu SQLite ("?"); lớp này tự chuyển sang "%s"
cho Postgres. Chỉ dùng cú pháp chung cho cả 2 dialect: ON CONFLICT ... DO NOTHING/UPDATE,
RETURNING (SQLite >= 3.35).
"""

from __future__ import annotations

import atexit
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Sequence

logger = logging.getLogger("db_backend")

_pool = None
_pool_lock = threading.Lock()


def database_url() -> str:
    return (os.getenv("DATABASE_URL") or "").strip()


def postgres_enabled() -> bool:
    url = database_url()
    return url.startswith("postgres://") or url.startswith("postgresql://")


def use_postgres(db_path: Optional[str | Path] = None) -> bool:
    """Postgres chỉ được dùng khi không chỉ định db_path tường minh (tests luôn truyền db_path SQLite)."""
    return db_path is None and postgres_enabled()


def dialect(db_path: Optional[str | Path] = None) -> str:
    return "postgres" if use_postgres(db_path) else "sqlite"


def autoincrement_pk(db_path: Optional[str | Path] = None) -> str:
    """Khai báo cột khóa chính tự tăng tương thích từng dialect."""
    if use_postgres(db_path):
        return "id BIGSERIAL PRIMARY KEY"
    return "id INTEGER PRIMARY KEY AUTOINCREMENT"


def _normalize_value(v: Any) -> Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def _normalize_row(row: Any) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {k: _normalize_value(v) for k, v in dict(row).items()}


class Cursor:
    """Cursor tối giản thống nhất giữa sqlite3 và psycopg; hàng trả về luôn là dict."""

    def __init__(self, raw_cursor: Any, is_pg: bool):
        self._raw = raw_cursor
        self._is_pg = is_pg

    def execute(self, sql: str, params: Sequence[Any] = ()) -> "Cursor":
        if self._is_pg:
            sql = sql.replace("?", "%s")
        self._raw.execute(sql, tuple(params))
        return self

    def fetchone(self) -> Optional[Dict[str, Any]]:
        return _normalize_row(self._raw.fetchone())

    def fetchall(self) -> list[Dict[str, Any]]:
        return [_normalize_row(r) for r in self._raw.fetchall()]

    @property
    def rowcount(self) -> int:
        return self._raw.rowcount


class Connection:
    def __init__(self, raw_conn: Any, is_pg: bool, pool: Any = None):
        self._raw = raw_conn
        self.is_pg = is_pg
        self._pool = pool
        self._closed = False

    def close(self) -> None:
        """Đóng SQLite / trả kết nối Postgres về pool (rollback phần chưa commit)."""
        if self._closed:
            return
        self._closed = True
        if self._pool is not None:
            try:
                self._raw.rollback()
            except Exception:
                pass
            self._pool.putconn(self._raw)
        else:
            self._raw.close()

    def cursor(self) -> Cursor:
        return Cursor(self._raw.cursor(), self.is_pg)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Cursor:
        return self.cursor().execute(sql, params)

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()


def _get_pool():
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is None:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            _pool = ConnectionPool(
                conninfo=database_url(),
                min_size=0,
                max_size=int(os.getenv("DB_POOL_MAX", "4")),
                kwargs={"row_factory": dict_row, "autocommit": False},
                # Neon/Render hay đóng kết nối nhàn rỗi -> kiểm tra trước khi cấp phát
                check=ConnectionPool.check_connection,
                open=True,
            )
            logger.info("[db_backend] Đã khởi tạo pool kết nối PostgreSQL.")
            atexit.register(close_pool)
    return _pool


def close_pool() -> None:
    """Đóng pool Postgres (gọi khi FastAPI shutdown / thoát tiến trình)."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.close()
            except Exception:
                pass
            _pool = None


def open_connection(sqlite_path: str | Path, db_path: Optional[str | Path] = None) -> Connection:
    """Mở kết nối thủ công (người gọi tự commit()/close())."""
    if use_postgres(db_path):
        pool = _get_pool()
        return Connection(pool.getconn(), True, pool)
    target = Path(db_path) if db_path else Path(sqlite_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(str(target), timeout=30.0)
    raw.row_factory = sqlite3.Row
    return Connection(raw, False)


@contextmanager
def connect(sqlite_path: str | Path, db_path: Optional[str | Path] = None) -> Iterator[Connection]:
    """
    Mở kết nối:
      - Postgres (pool) nếu DATABASE_URL được đặt và db_path là None.
      - SQLite tại db_path (nếu có) hoặc sqlite_path mặc định.
    Tự commit khi thoát bình thường, rollback khi có ngoại lệ.
    """
    conn = open_connection(sqlite_path, db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def storage_info() -> Dict[str, Any]:
    """Thông tin chẩn đoán (không lộ mật khẩu) cho /api/health."""
    if postgres_enabled():
        url = database_url()
        host = url.split("@")[-1].split("/")[0] if "@" in url else "?"
        return {"backend": "postgres", "host": host, "persistent": True}
    return {"backend": "sqlite", "persistent": False,
            "note": "Không có DATABASE_URL — dữ liệu sẽ mất khi container khởi động lại."}
