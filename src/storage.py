import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

_DB_PATH = "auto_friend.db"
_LOCK = threading.Lock()


@contextmanager
def connect():
    with _LOCK:
        conn = sqlite3.connect(_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db():
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                platform_user_id TEXT NOT NULL,
                username TEXT,
                consent INTEGER DEFAULT 0,
                paused INTEGER DEFAULT 0,
                last_contact_at TEXT,
                daily_msg_count INTEGER DEFAULT 0,
                last_reset_date TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_platform_uid
                ON users(platform, platform_user_id);

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                direction TEXT NOT NULL, -- 'in' or 'out'
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS followups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                due_at TEXT NOT NULL,
                reason TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


@dataclass
class User:
    id: int
    platform: str
    platform_user_id: str
    username: Optional[str]
    consent: bool
    paused: bool
    last_contact_at: Optional[str]
    daily_msg_count: int
    last_reset_date: Optional[str]


def upsert_user(platform: str, platform_user_id: str, username: Optional[str]) -> User:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO users(platform, platform_user_id, username)
            VALUES(?,?,?)
            ON CONFLICT(platform, platform_user_id) DO UPDATE SET username=excluded.username
            """,
            (platform, platform_user_id, username),
        )
        row = conn.execute(
            "SELECT id, platform, platform_user_id, username, consent, paused, last_contact_at, daily_msg_count, last_reset_date FROM users WHERE platform=? AND platform_user_id=?",
            (platform, platform_user_id),
        ).fetchone()
        return User(*row)


def get_user_by_platform_id(platform: str, platform_user_id: str) -> Optional[User]:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, platform, platform_user_id, username, consent, paused, last_contact_at, daily_msg_count, last_reset_date FROM users WHERE platform=? AND platform_user_id=?",
            (platform, platform_user_id),
        ).fetchone()
        return User(*row) if row else None


def get_user_by_id(user_id: int) -> Optional[User]:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, platform, platform_user_id, username, consent, paused, last_contact_at, daily_msg_count, last_reset_date FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        return User(*row) if row else None


def set_consent(user_id: int, consent: bool):
    with connect() as conn:
        conn.execute("UPDATE users SET consent=? WHERE id=?", (1 if consent else 0, user_id))


def set_paused(user_id: int, paused: bool):
    with connect() as conn:
        conn.execute("UPDATE users SET paused=? WHERE id=?", (1 if paused else 0, user_id))


def record_message(user_id: int, direction: str, content: str):
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages(user_id, direction, content, created_at) VALUES(?,?,?,?)",
            (user_id, direction, content, datetime.utcnow().isoformat()),
        )
        # increment daily count for outbound
        if direction == 'out':
            user = conn.execute("SELECT daily_msg_count, last_reset_date FROM users WHERE id=?", (user_id,)).fetchone()
            daily_msg_count, last_reset_date = user
            today = datetime.utcnow().date().isoformat()
            if last_reset_date != today:
                daily_msg_count = 0
            daily_msg_count += 1
            conn.execute(
                "UPDATE users SET daily_msg_count=?, last_reset_date=?, last_contact_at=? WHERE id=?",
                (daily_msg_count, today, datetime.utcnow().isoformat(), user_id),
            )
        else:
            conn.execute(
                "UPDATE users SET last_contact_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), user_id),
            )


def get_recent_messages(user_id: int, limit: int = 20) -> List[Tuple[str, str, str]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT direction, content, created_at FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return list(reversed(rows))


def schedule_followup(user_id: int, due_at_iso: str, reason: str):
    with connect() as conn:
        conn.execute(
            "INSERT INTO followups(user_id, due_at, reason) VALUES(?,?,?)",
            (user_id, due_at_iso, reason),
        )


def due_followups(now_iso: str) -> List[Dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, user_id, due_at, reason FROM followups WHERE due_at<=? ORDER BY due_at ASC",
            (now_iso,),
        ).fetchall()
        return [
            {"id": r[0], "user_id": r[1], "due_at": r[2], "reason": r[3]} for r in rows
        ]


def delete_followup(followup_id: int):
    with connect() as conn:
        conn.execute("DELETE FROM followups WHERE id=?", (followup_id,))


def reset_daily_counts_if_needed():
    with connect() as conn:
        today = datetime.utcnow().date().isoformat()
        conn.execute(
            "UPDATE users SET daily_msg_count=0, last_reset_date=? WHERE last_reset_date IS NULL OR last_reset_date<>?",
            (today, today),
        )


def delete_user(user_id: int):
    with connect() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
