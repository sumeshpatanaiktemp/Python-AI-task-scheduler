import os
import sqlite3
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "scheduler.db")
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")


class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.ensure_schema()

    def ensure_schema(self):
        with open(SCHEMA_FILE, "r", encoding="utf-8") as schema_file:
            self.conn.executescript(schema_file.read())
        self._migrate_schema()
        self.conn.commit()

    def _migrate_schema(self):
        cursor = self.conn.execute("PRAGMA table_info(tasks)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "chat_id" not in columns:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN chat_id TEXT")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )


    def add_task(self, title, description, deadline_date, deadline_week, reminder_time, chat_id, estimated_duration):
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(id) FROM tasks")
        row = cursor.fetchone()
        next_id = 1 if (row is None or row[0] is None) else int(row[0]) + 1

        cursor.execute(
            """
            INSERT INTO tasks (id, title, description, deadline_date, deadline_week, reminder_time, chat_id, estimated_duration, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_id,
                title,
                description,
                deadline_date,
                deadline_week,
                reminder_time,
                chat_id,
                estimated_duration,
                datetime.utcnow().isoformat(),
            ),
        )
        self.conn.commit()
        return next_id

    def update_task(self, task_id, title, description, deadline_date, deadline_week, reminder_time, chat_id, estimated_duration):
        self.conn.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, deadline_date = ?, deadline_week = ?, reminder_time = ?, chat_id = ?, estimated_duration = ?
            WHERE id = ?
            """,
            (title, description, deadline_date, deadline_week, reminder_time, chat_id, estimated_duration, task_id),
        )
        self.conn.commit()

    def delete_task(self, task_id):
        self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.execute("DELETE FROM schedules WHERE task_id = ?", (task_id,))
        self.conn.commit()

    def get_all_tasks(self):
        cursor = self.conn.execute("SELECT * FROM tasks ORDER BY deadline_date NULLS LAST, deadline_week NULLS LAST, created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_task(self, task_id):
        cursor = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_schedule(self, task_id, day_number, start_time, end_time):
        self.conn.execute(
            "INSERT INTO schedules (task_id, day_number, start_time, end_time, created_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, day_number, start_time, end_time, datetime.utcnow().isoformat()),
        )
        self.conn.commit()

    def clear_schedules(self):
        self.conn.execute("DELETE FROM schedules")
        self.conn.commit()

    def get_schedule(self):
        cursor = self.conn.execute(
            "SELECT schedules.*, tasks.title, tasks.chat_id FROM schedules JOIN tasks ON schedules.task_id = tasks.id ORDER BY day_number, start_time"
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_pending_reminders(self):
        cursor = self.conn.execute("SELECT * FROM tasks WHERE reminder_time IS NOT NULL")
        return [dict(row) for row in cursor.fetchall()]

    def get_setting(self, key, default=None):
        try:
            cursor = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default
        except Exception:
            return default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        self.conn.commit()

    def get_daily_limit(self):
        val = self.get_setting("daily_limit", "6.0")
        try:
            limit = float(val)
            if limit > 24.0:
                limit = 24.0
            return limit
        except Exception:
            return 6.0

    def get_total_duration_for_date(self, date_str, exclude_task_id=None):
        if exclude_task_id is not None:
            cursor = self.conn.execute(
                "SELECT SUM(estimated_duration) FROM tasks WHERE deadline_date = ? AND id != ?",
                (date_str, exclude_task_id),
            )
        else:
            cursor = self.conn.execute(
                "SELECT SUM(estimated_duration) FROM tasks WHERE deadline_date = ?",
                (date_str,),
            )
        row = cursor.fetchone()
        return float(row[0] or 0.0)

    def get_tasks_count_for_date(self, date_str):
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE deadline_date = ?",
            (date_str,),
        )
        row = cursor.fetchone()
        return int(row[0] or 0)

    def get_tasks_for_date(self, date_str):
        cursor = self.conn.execute(
            "SELECT * FROM tasks WHERE deadline_date = ? ORDER BY created_at DESC",
            (date_str,),
        )
        return [dict(row) for row in cursor.fetchall()]

