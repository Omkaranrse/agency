"""SQLite-backed persistent implementation of EventFeedPort for SSE and replay."""

import asyncio
import json
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from agency.application.ports.event_feed import EventEnvelope, EventFeedPort
from agency.domain.events import DomainEvent

logger = logging.getLogger(__name__)

# Keys stripped from event payloads for safety
SENSITIVE_KEYS = {"api_key", "secret", "token", "password", "authorization"}


def _sanitize_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively strip sensitive keys and raw credentials from event payloads."""
    clean: dict[str, Any] = {}
    for k, v in data.items():
        if k.lower() in SENSITIVE_KEYS:
            continue
        if isinstance(v, dict):
            clean[k] = _sanitize_payload(v)
        elif isinstance(v, list):
            clean[k] = [
                _sanitize_payload(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            clean[k] = v
    return clean


class SqliteEventFeed(EventFeedPort):
    """SQLite-backed event feed supporting durable cursor replay and live fan-out."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:" and not self.db_path.startswith("file:"):
            Path(self.db_path).resolve().parent.mkdir(parents=True, exist_ok=True)

        self._subscribers: dict[str, set[asyncio.Queue[EventEnvelope]]] = defaultdict(
            set
        )
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        if self.db_path != ":memory:" and not self.db_path.startswith("file::memory:"):
            conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -64000;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS domain_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_run_id_id "
                "ON domain_events(run_id, id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_lookup "
                "ON domain_events(run_id, event_id)"
            )
            conn.commit()

    def record_event(self, event: DomainEvent) -> EventEnvelope:
        """Persist a domain event to SQLite and fan out to active subscriber queues."""
        raw_payload = event.model_dump(mode="json")
        clean_payload = _sanitize_payload(raw_payload)

        envelope = EventEnvelope(
            event_id=event.event_id,
            run_id=event.run_id,
            event_type=type(event).__name__,
            occurred_at=event.occurred_at,
            payload=clean_payload,
        )

        occurred_str = envelope.occurred_at.isoformat()
        payload_str = json.dumps(clean_payload)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO domain_events (
                    event_id, run_id, event_type, occurred_at, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    envelope.event_id,
                    envelope.run_id,
                    envelope.event_type,
                    occurred_str,
                    payload_str,
                ),
            )
            conn.commit()

        # Fan-out to in-memory active subscriber queues
        subscribers = list(self._subscribers.get(event.run_id, set()))
        for queue in subscribers:
            try:
                queue.put_nowait(envelope)
            except asyncio.QueueFull:
                logger.warning(
                    "Event queue full for subscriber on run '%s'", event.run_id
                )

        return envelope

    def get_events(
        self,
        run_id: str,
        after_id: str | None = None,
        limit: int = 100,
    ) -> list[EventEnvelope]:
        """Fetch historical events for a run occurring strictly after after_id."""
        with self._get_connection() as conn:
            after_row_id: int | None = None
            if after_id:
                cur = conn.execute(
                    "SELECT id FROM domain_events WHERE run_id = ? AND event_id = ?",
                    (run_id, after_id),
                )
                row = cur.fetchone()
                if row:
                    after_row_id = int(row["id"])

            if after_row_id is not None:
                cur = conn.execute(
                    """
                    SELECT event_id, run_id, event_type, occurred_at, payload_json
                    FROM domain_events
                    WHERE run_id = ? AND id > ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (run_id, after_row_id, limit),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT event_id, run_id, event_type, occurred_at, payload_json
                    FROM domain_events
                    WHERE run_id = ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (run_id, limit),
                )

            rows = cur.fetchall()
            envelopes: list[EventEnvelope] = []
            for r in rows:
                envelopes.append(
                    EventEnvelope(
                        event_id=r["event_id"],
                        run_id=r["run_id"],
                        event_type=r["event_type"],
                        occurred_at=datetime.fromisoformat(r["occurred_at"]),
                        payload=json.loads(r["payload_json"]),
                    )
                )
            return envelopes

    def subscribe(self, run_id: str) -> asyncio.Queue[EventEnvelope]:
        """Create a live event subscription queue for a run."""
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=500)
        self._subscribers[run_id].add(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[EventEnvelope]) -> None:
        """Remove a subscription queue and free resources."""
        if run_id in self._subscribers and queue in self._subscribers[run_id]:
            self._subscribers[run_id].discard(queue)
            if not self._subscribers[run_id]:
                del self._subscribers[run_id]
