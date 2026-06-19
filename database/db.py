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

    def add_task(self, title, description, deadline_date, deadline_week, reminder_time, chat_id, estimated_duration):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (title, description, deadline_date, deadline_week, reminder_time, chat_id, estimated_duration, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
        return cursor.lastrowid

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
