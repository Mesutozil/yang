from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


class StateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_items (
                id TEXT PRIMARY KEY,
                ctime INTEGER NOT NULL,
                notified_at TEXT
            )
            """
        )
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM seen_items").fetchone()
        return int(row[0]) if row else 0

    def is_empty(self) -> bool:
        return self.count() == 0

    def has_seen(self, item_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM seen_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        return row is not None

    def mark_seen(self, item_id: str, ctime: int, notified: bool = False) -> None:
        notified_at = datetime.now().isoformat() if notified else None
        self._conn.execute(
            """
            INSERT OR IGNORE INTO seen_items (id, ctime, notified_at)
            VALUES (?, ?, ?)
            """,
            (item_id, ctime, notified_at),
        )
        if notified:
            self._conn.execute(
                """
                UPDATE seen_items SET notified_at = ? WHERE id = ?
                """,
                (notified_at, item_id),
            )
        self._conn.commit()

    def seed_items(self, items: list[tuple[str, int]]) -> None:
        for item_id, ctime in items:
            self.mark_seen(item_id, ctime, notified=False)

    def cleanup_old(self, days: int = 7) -> int:
        cutoff = int((datetime.now() - timedelta(days=days)).timestamp())
        cursor = self._conn.execute(
            "DELETE FROM seen_items WHERE ctime < ?",
            (cutoff,),
        )
        self._conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        self._conn.close()
