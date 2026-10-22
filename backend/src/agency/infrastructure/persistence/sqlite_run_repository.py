"""SQLite implementation of RunRepositoryPort for durable aggregate persistence."""

import sqlite3
from pathlib import Path

from agency.application.errors import RepositoryError
from agency.application.ports.run_repository import RunRepositoryPort
from agency.domain.entities.run import Run
from agency.domain.enums import RunState


class SqliteRunRepository(RunRepositoryPort):
    """Thread-safe SQLite persistent repository store for Run aggregates."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:" and not self.db_path.startswith("file:"):
            Path(self.db_path).resolve().parent.mkdir(parents=True, exist_ok=True)

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
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    data_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_created_at "
                "ON runs(created_at, run_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_state ON runs(state)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_state_created_at "
                "ON runs(state, created_at, run_id)"
            )
            conn.commit()

    def save(self, run: Run) -> None:
        """Persist or update a Run aggregate."""
        try:
            data_json = run.model_dump_json()
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO runs (run_id, state, created_at, data_json)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                        state = excluded.state,
                        data_json = excluded.data_json
                    """,
                    (
                        run.run_id,
                        run.state.value
                        if hasattr(run.state, "value")
                        else str(run.state),
                        run.created_at.isoformat(),
                        data_json,
                    ),
                )
                conn.commit()
        except Exception as exc:
            raise RepositoryError(
                f"Failed to persist run '{run.run_id}': {exc}"
            ) from exc

    def get_by_id(self, run_id: str) -> Run | None:
        """Retrieve a Run aggregate by unique identifier."""
        try:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT data_json FROM runs WHERE run_id = ?",
                    (run_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return Run.model_validate_json(row["data_json"])
        except Exception as exc:
            raise RepositoryError(f"Failed to retrieve run '{run_id}': {exc}") from exc

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        state: RunState | None = None,
    ) -> list[Run]:
        """Return a deterministic, paginated slice of stored runs."""
        if limit < 1 or limit > 100:
            raise RepositoryError(
                f"Invalid limit '{limit}'. Limit must be between 1 and 100."
            )
        if offset < 0:
            raise RepositoryError(f"Invalid offset '{offset}'. Offset must be >= 0.")

        try:
            with self._get_connection() as conn:
                if state is not None:
                    state_val = state.value if hasattr(state, "value") else str(state)
                    cur = conn.execute(
                        """
                        SELECT data_json FROM runs
                        WHERE state = ?
                        ORDER BY created_at ASC, run_id ASC
                        LIMIT ? OFFSET ?
                        """,
                        (state_val, limit, offset),
                    )
                else:
                    cur = conn.execute(
                        """
                        SELECT data_json FROM runs
                        ORDER BY created_at ASC, run_id ASC
                        LIMIT ? OFFSET ?
                        """,
                        (limit, offset),
                    )
                rows = cur.fetchall()
                return [Run.model_validate_json(row["data_json"]) for row in rows]
        except Exception as exc:
            raise RepositoryError(f"Failed to list runs: {exc}") from exc

    def count(self, state: RunState | None = None) -> int:
        """Return the count of stored runs."""
        try:
            with self._get_connection() as conn:
                if state is not None:
                    state_val = state.value if hasattr(state, "value") else str(state)
                    cur = conn.execute(
                        "SELECT COUNT(*) as count FROM runs WHERE state = ?",
                        (state_val,),
                    )
                else:
                    cur = conn.execute("SELECT COUNT(*) as count FROM runs")
                row = cur.fetchone()
                return int(row["count"]) if row else 0
        except Exception as exc:
            raise RepositoryError(f"Failed to count runs: {exc}") from exc

    def clear(self) -> None:
        """Clear all stored runs."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM runs")
                conn.commit()
        except Exception as exc:
            raise RepositoryError(f"Failed to clear runs: {exc}") from exc
