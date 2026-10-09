from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import PROJECT_ROOT
from typing import Any


class MemoryStore:
    """Tiny long-term memory layer for auditable client insight summaries."""

    def __init__(self, path: str) -> None:
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = PROJECT_ROOT / resolved
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(resolved)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS client_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_client_insights_client ON client_insights(client_id, created_at DESC)"
            )

    def save_insight(
        self, client_id: str, risk_level: str, summary: str, payload: dict[str, Any]
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO client_insights(client_id, created_at, risk_level, summary, payload) VALUES (?, ?, ?, ?, ?)",
                (
                    client_id,
                    datetime.now(timezone.utc).isoformat(),
                    risk_level,
                    summary,
                    json.dumps(payload, default=str),
                ),
            )

    def recent_insights(self, client_id: str, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT created_at, risk_level, summary, payload FROM client_insights WHERE client_id = ? ORDER BY created_at DESC LIMIT ?",
                (client_id, limit),
            ).fetchall()
        return [
            {
                "created_at": row["created_at"],
                "risk_level": row["risk_level"],
                "summary": row["summary"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]
