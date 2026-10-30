"""SQLite persistence for synthetic student records, tickets, and memory."""
from __future__ import annotations
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("STUDENT_AGENT_DB", "student_support.sqlite3"))

@contextmanager
def connect(path: str | Path | None = None):
    db = sqlite3.connect(str(path or DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db(path: str | Path | None = None) -> None:
    with connect(path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS students(
          student_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, programme TEXT NOT NULL,
          semester INTEGER NOT NULL, fee_amount REAL NOT NULL, amount_paid REAL NOT NULL,
          payment_status TEXT NOT NULL, scholarship_status TEXT NOT NULL,
          scholarship_eligibility TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tickets(
          ticket_id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(student_id),
          category TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memories(
          memory_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL REFERENCES students(student_id),
          fact TEXT NOT NULL, category TEXT NOT NULL, created_at TEXT NOT NULL,
          UNIQUE(student_id, fact));
        CREATE TABLE IF NOT EXISTS conversation_messages(
          id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL, session_id TEXT NOT NULL,
          role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit_events(
          event_id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, correlation_id TEXT NOT NULL,
          requester_id TEXT, action TEXT NOT NULL, target_id TEXT, decision TEXT NOT NULL,
          reason TEXT NOT NULL, approval_required INTEGER NOT NULL DEFAULT 0,
          approver_id TEXT, approval_status TEXT, execution_status TEXT NOT NULL,
          result_summary TEXT, duration_ms REAL);
        CREATE TABLE IF NOT EXISTS pending_actions(
          action_id TEXT PRIMARY KEY, requester_id TEXT NOT NULL, target_id TEXT NOT NULL,
          field_name TEXT NOT NULL, proposed_value TEXT NOT NULL, action_hash TEXT NOT NULL,
          status TEXT NOT NULL, created_at TEXT NOT NULL, decided_at TEXT, approver_id TEXT);
        CREATE TABLE IF NOT EXISTS login_events(
          event_id TEXT PRIMARY KEY, username TEXT NOT NULL, role TEXT NOT NULL,
          student_id TEXT, logged_in_at TEXT NOT NULL);
        """)
        columns = {row[1] for row in db.execute("PRAGMA table_info(students)")}
        if "contact_email" not in columns:
            db.execute("ALTER TABLE students ADD COLUMN contact_email TEXT NOT NULL DEFAULT ''")
