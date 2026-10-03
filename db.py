import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


STATUSES = ("open", "in_progress", "done")
PRIORITIES = ("low", "normal", "high")
TRANSITIONS = {
    "open": {"in_progress"},
    "in_progress": {"done", "open"},
    "done": {"in_progress"},
}


class ValidationError(Exception):
    pass


class NotFoundError(Exception):
    pass


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TaskStore:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    priority TEXT NOT NULL CHECK(priority IN ('low', 'normal', 'high')),
                    status TEXT NOT NULL CHECK(status IN ('open', 'in_progress', 'done')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER NOT NULL REFERENCES tasks(id),
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=5)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_tasks(self):
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
            return [dict(row) for row in rows]

    def create_task(self, title, priority):
        if not isinstance(title, str) or not 3 <= len(title.strip()) <= 120:
            raise ValidationError("Title must be 3-120 characters.")
        if priority not in PRIORITIES:
            raise ValidationError("Priority must be low, normal, or high.")
        timestamp = now_utc()
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO tasks (title, priority, status, created_at, updated_at) VALUES (?, ?, 'open', ?, ?)",
                (title.strip(), priority, timestamp, timestamp),
            )
            task_id = cursor.lastrowid
            connection.execute(
                "INSERT INTO events (task_id, from_status, to_status, created_at) VALUES (?, NULL, 'open', ?)",
                (task_id, timestamp),
            )
            return dict(connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())

    def transition(self, task_id, new_status):
        if new_status not in STATUSES:
            raise ValidationError("Status must be open, in_progress, or done.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            task = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if task is None:
                raise NotFoundError("Task not found.")
            if new_status not in TRANSITIONS[task["status"]]:
                raise ValidationError(f"Cannot move from {task['status']} to {new_status}.")
            timestamp = now_utc()
            connection.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (new_status, timestamp, task_id),
            )
            connection.execute(
                "INSERT INTO events (task_id, from_status, to_status, created_at) VALUES (?, ?, ?, ?)",
                (task_id, task["status"], new_status, timestamp),
            )
            return dict(connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())

    def events(self, task_id):
        with self._connect() as connection:
            if connection.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone() is None:
                raise NotFoundError("Task not found.")
            rows = connection.execute(
                "SELECT id, from_status, to_status, created_at FROM events WHERE task_id = ? ORDER BY id",
                (task_id,),
            ).fetchall()
            return [dict(row) for row in rows]
