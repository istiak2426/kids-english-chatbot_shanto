"""SQLite persistence (one JSON row per child). Swap for Postgres/Redis in production."""
import json, os, sqlite3, threading
from .curriculum import ChildState

DB = os.getenv("DB_PATH", "buddy.db")
_lock = threading.Lock()
_conn = sqlite3.connect(DB, check_same_thread=False)
_conn.execute("CREATE TABLE IF NOT EXISTS child (id TEXT PRIMARY KEY, data TEXT)")


def load(child_id: str) -> ChildState:
    with _lock:
        row = _conn.execute("SELECT data FROM child WHERE id=?", (child_id,)).fetchone()
    return ChildState.from_dict(json.loads(row[0])) if row else ChildState(child_id=child_id)


def save(state: ChildState):
    with _lock:
        _conn.execute("INSERT OR REPLACE INTO child VALUES (?,?)", (state.child_id, json.dumps(state.to_dict())))
        _conn.commit()
