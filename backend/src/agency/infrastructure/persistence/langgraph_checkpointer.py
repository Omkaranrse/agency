"""SQLite checkpointer infrastructure for durable LangGraph workflows."""

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

DEFAULT_CHECKPOINT_DB_PATH = "data/checkpoints.db"


class SqliteCheckpointerManager:
    """Manages SQLite checkpointer lifecycles and stable thread persistence."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is not None:
            self.db_path = str(db_path)
        elif "AGENCY_CHECKPOINT_DB" in os.environ:
            self.db_path = os.environ["AGENCY_CHECKPOINT_DB"]
        elif "AGENCY_CHECKPOINT_DB_PATH" in os.environ:
            self.db_path = os.environ["AGENCY_CHECKPOINT_DB_PATH"]
        else:
            self.db_path = DEFAULT_CHECKPOINT_DB_PATH

        # Ensure parent directory exists for file-based SQLite databases
        if self.db_path != ":memory:" and not self.db_path.startswith("file:"):
            Path(self.db_path).resolve().parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_checkpointer(self) -> Generator[SqliteSaver, None, None]:
        """Yield an initialized SqliteSaver checkpointer with managed lifetime."""
        if self.db_path == ":memory:":
            conn = sqlite3.connect(":memory:", check_same_thread=False)
            saver = SqliteSaver(conn)
            saver.setup()
            try:
                yield saver
            finally:
                conn.close()
        else:
            with SqliteSaver.from_conn_string(self.db_path) as saver:
                yield saver


def create_in_memory_checkpointer() -> SqliteSaver:
    """Create a standalone in-memory checkpointer primarily used for unit testing."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    return saver
