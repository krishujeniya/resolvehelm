"""Database access layer, schema operations, and storage adapters."""

import json
import logging
import socket
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from app.config import settings

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class BaseDatabase:
    """Abstract interface defining required database operations."""

    def check_health(self) -> bool:
        raise NotImplementedError

    def claim_event(self, message_id: str, max_attempts: int = 3) -> bool:
        raise NotImplementedError

    def complete_event(
        self, message_id: str, result: dict[str, Any] | None = None
    ) -> None:
        raise NotImplementedError

    def fail_event(self, message_id: str, error: str, retryable: bool = False) -> None:
        raise NotImplementedError

    def upsert_ticket(
        self,
        thread_id: str,
        customer: str,
        subject: str,
        category: str = "general",
        status: str = "open",
        proposed_action: str | None = None,
    ) -> str:
        raise NotImplementedError

    def save_message(
        self,
        ticket_id: str,
        message_id: str,
        direction: str,
        sender: str,
        recipient: str,
        body: str,
    ) -> str:
        raise NotImplementedError

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def get_ticket_by_thread(self, thread_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def list_tickets(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_ticket_messages(self, ticket_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def update_ticket(
        self,
        ticket_id: str,
        status: str | None = None,
        assigned_to: str | None = None,
    ) -> bool:
        raise NotImplementedError

    def add_ticket_note(self, ticket_id: str, note: str, author: str) -> str:
        raise NotImplementedError

    def get_ticket_notes(self, ticket_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def list_recent_events(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    def upsert_kb_entry(self, section: str, title: str, content: str) -> str:
        raise NotImplementedError

    def list_kb_sections(self) -> list[str]:
        raise NotImplementedError

    def get_kb_entries(self, section: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_all_kb_entries(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_kb_entry_by_id(self, entry_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def update_kb_entry(self, entry_id: str, title: str, content: str) -> bool:
        raise NotImplementedError


class SQLiteMemoryDatabase(BaseDatabase):
    """Full-featured SQLite implementation for test execution and offline development."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'retrying')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    result TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_events_msg ON events(message_id);

                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL UNIQUE,
                    customer TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    status TEXT NOT NULL CHECK (status IN ('open', 'answered', 'escalated', 'closed', 'resolved')),
                    proposed_action TEXT,
                    assigned_to TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tickets_th ON tickets(thread_id);

                CREATE TABLE IF NOT EXISTS ticket_notes (
                    id TEXT PRIMARY KEY,
                    ticket_id TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                    author TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_ticket_notes_tid ON ticket_notes(ticket_id);

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    ticket_id TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                    message_id TEXT NOT NULL UNIQUE,
                    direction TEXT NOT NULL CHECK (direction IN ('incoming', 'outgoing')),
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_tk ON messages(ticket_id);

                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id TEXT PRIMARY KEY,
                    section TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(section, title)
                );
                CREATE INDEX IF NOT EXISTS idx_kb_sec ON knowledge_base(section);
            """)
            cur = self.conn.cursor()
            cur.execute("PRAGMA table_info(tickets)")
            cols = [r["name"] for r in cur.fetchall()]
            if "assigned_to" not in cols:
                cur.execute("ALTER TABLE tickets ADD COLUMN assigned_to TEXT")

    def check_health(self) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT 1")
            return cur.fetchone()[0] == 1
        except Exception:
            return False

    def claim_event(self, message_id: str, max_attempts: int = 3) -> bool:
        with self.conn:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT id, status, attempts FROM events WHERE message_id = ?",
                (message_id,),
            )
            row = cur.fetchone()

            now = _now_iso()
            if row is None:
                new_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO events (id, message_id, status, attempts, created_at) VALUES (?, ?, 'processing', 1, ?)",
                    (new_id, message_id, now),
                )
                return True

            status = row["status"]
            attempts = row["attempts"]

            if status in ("completed", "processing"):
                return False

            if attempts >= max_attempts:
                return False

            cur.execute(
                "UPDATE events SET status = 'processing', attempts = attempts + 1, error = NULL WHERE message_id = ?",
                (message_id,),
            )
            return True

    def complete_event(
        self, message_id: str, result: dict[str, Any] | None = None
    ) -> None:
        with self.conn:
            res_json = json.dumps(result) if result else None
            self.conn.execute(
                "UPDATE events SET status = 'completed', result = ?, completed_at = ? WHERE message_id = ?",
                (res_json, _now_iso(), message_id),
            )

    def fail_event(self, message_id: str, error: str, retryable: bool = False) -> None:
        with self.conn:
            status = "retrying" if retryable else "failed"
            self.conn.execute(
                "UPDATE events SET status = ?, error = ?, completed_at = ? WHERE message_id = ?",
                (status, error, _now_iso(), message_id),
            )

    def upsert_ticket(
        self,
        thread_id: str,
        customer: str,
        subject: str,
        category: str = "general",
        status: str = "open",
        proposed_action: str | None = None,
    ) -> str:
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("SELECT id FROM tickets WHERE thread_id = ?", (thread_id,))
            row = cur.fetchone()
            now = _now_iso()

            if row:
                ticket_id = row["id"]
                cur.execute(
                    """
                    UPDATE tickets
                    SET customer = ?, subject = ?, category = ?, status = ?, proposed_action = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        customer,
                        subject,
                        category,
                        status,
                        proposed_action,
                        now,
                        ticket_id,
                    ),
                )
                return ticket_id
            else:
                ticket_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO tickets (id, thread_id, customer, subject, category, status, proposed_action, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ticket_id,
                        thread_id,
                        customer,
                        subject,
                        category,
                        status,
                        proposed_action,
                        now,
                        now,
                    ),
                )
                return ticket_id

    def save_message(
        self,
        ticket_id: str,
        message_id: str,
        direction: str,
        sender: str,
        recipient: str,
        body: str,
    ) -> str:
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("SELECT id FROM messages WHERE message_id = ?", (message_id,))
            row = cur.fetchone()
            if row:
                return row["id"]

            msg_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO messages (id, ticket_id, message_id, direction, sender, recipient, body, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg_id,
                    ticket_id,
                    message_id,
                    direction,
                    sender,
                    recipient,
                    body,
                    _now_iso(),
                ),
            )
            return msg_id

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_ticket_by_thread(self, thread_id: str) -> dict[str, Any] | None:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tickets WHERE thread_id = ?", (thread_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_tickets(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM tickets ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_ticket_messages(self, ticket_id: str) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM messages WHERE ticket_id = ? ORDER BY created_at ASC",
            (ticket_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def update_ticket(
        self,
        ticket_id: str,
        status: str | None = None,
        assigned_to: str | None = None,
    ) -> bool:
        with self.conn:
            cur = self.conn.cursor()
            updates = ["updated_at = ?"]
            params = [_now_iso()]
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if assigned_to is not None:
                updates.append("assigned_to = ?")
                params.append(assigned_to)
            params.append(ticket_id)
            cur.execute(
                f"UPDATE tickets SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            return cur.rowcount > 0

    def add_ticket_note(self, ticket_id: str, note: str, author: str) -> str:
        note_id = str(uuid.uuid4())
        with self.conn:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO ticket_notes (id, ticket_id, author, note, created_at) VALUES (?, ?, ?, ?, ?)",
                (note_id, ticket_id, author, note, _now_iso()),
            )
        return note_id

    def get_ticket_notes(self, ticket_id: str) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM ticket_notes WHERE ticket_id = ? ORDER BY created_at DESC",
            (ticket_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def list_recent_events(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM events ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            if d.get("result"):
                try:
                    d["result"] = json.loads(d["result"])
                except Exception:
                    pass
            rows.append(d)
        return rows

    def upsert_kb_entry(self, section: str, title: str, content: str) -> str:
        with self.conn:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT id FROM knowledge_base WHERE section = ? AND title = ?",
                (section, title),
            )
            row = cur.fetchone()
            now = _now_iso()

            if row:
                entry_id = row["id"]
                cur.execute(
                    "UPDATE knowledge_base SET content = ?, updated_at = ? WHERE id = ?",
                    (content, now, entry_id),
                )
                return entry_id
            else:
                entry_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO knowledge_base (id, section, title, content, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (entry_id, section, title, content, now),
                )
                return entry_id

    def list_kb_sections(self) -> list[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT section FROM knowledge_base ORDER BY section ASC")
        return [r["section"] for r in cur.fetchall()]

    def get_kb_entries(self, section: str) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM knowledge_base WHERE section = ? ORDER BY title ASC",
            (section,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_all_kb_entries(self) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM knowledge_base ORDER BY section ASC, title ASC")
        return [dict(r) for r in cur.fetchall()]

    def get_kb_entry_by_id(self, entry_id: str) -> dict[str, Any] | None:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM knowledge_base WHERE id = ?", (entry_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_kb_entry(self, entry_id: str, title: str, content: str) -> bool:
        with self.conn:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE knowledge_base SET title = ?, content = ?, updated_at = ? WHERE id = ?",
                (title, content, _now_iso(), entry_id),
            )
            return cur.rowcount > 0


class PostgresDatabase(BaseDatabase):
    """PostgreSQL / Supabase implementation using psycopg 3 pool."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._pool = None

    def _get_pool(self):
        if self._pool is None:
            from psycopg_pool import ConnectionPool

            # Ensure quick connection timeout to avoid hanging if DB host is unreachable
            conninfo = self.dsn
            if "connect_timeout=" not in conninfo:
                separator = "&" if "?" in conninfo else "?"
                conninfo = f"{conninfo}{separator}connect_timeout=2"

            self._pool = ConnectionPool(conninfo, min_size=1, max_size=10, open=True)
        return self._pool

    def check_health(self) -> bool:
        try:
            with self._get_pool().connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    return cur.fetchone()[0] == 1
        except Exception as e:
            logger.warning("Postgres health check failed: %s", e)
            return False

    def claim_event(self, message_id: str, max_attempts: int = 3) -> bool:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, attempts FROM events WHERE message_id = %s FOR UPDATE",
                    (message_id,),
                )
                row = cur.fetchone()
                if row is None:
                    cur.execute(
                        "INSERT INTO events (message_id, status, attempts) VALUES (%s, 'processing', 1)",
                        (message_id,),
                    )
                    conn.commit()
                    return True

                status, attempts = row
                if status in ("completed", "processing") or attempts >= max_attempts:
                    conn.rollback()
                    return False

                cur.execute(
                    "UPDATE events SET status = 'processing', attempts = attempts + 1, error = NULL WHERE message_id = %s",
                    (message_id,),
                )
                conn.commit()
                return True

    def complete_event(
        self, message_id: str, result: dict[str, Any] | None = None
    ) -> None:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE events SET status = 'completed', result = %s, completed_at = NOW() WHERE message_id = %s",
                    (json.dumps(result) if result else None, message_id),
                )
                conn.commit()

    def fail_event(self, message_id: str, error: str, retryable: bool = False) -> None:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                status = "retrying" if retryable else "failed"
                cur.execute(
                    "UPDATE events SET status = %s, error = %s, completed_at = NOW() WHERE message_id = %s",
                    (status, error, message_id),
                )
                conn.commit()

    def upsert_ticket(
        self,
        thread_id: str,
        customer: str,
        subject: str,
        category: str = "general",
        status: str = "open",
        proposed_action: str | None = None,
    ) -> str:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tickets (thread_id, customer, subject, category, status, proposed_action, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (thread_id) DO UPDATE SET
                        customer = EXCLUDED.customer,
                        subject = EXCLUDED.subject,
                        category = EXCLUDED.category,
                        status = EXCLUDED.status,
                        proposed_action = EXCLUDED.proposed_action,
                        updated_at = NOW()
                    RETURNING id::text;
                    """,
                    (thread_id, customer, subject, category, status, proposed_action),
                )
                ticket_id = cur.fetchone()[0]
                conn.commit()
                return str(ticket_id)

    def save_message(
        self,
        ticket_id: str,
        message_id: str,
        direction: str,
        sender: str,
        recipient: str,
        body: str,
    ) -> str:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (ticket_id, message_id, direction, sender, recipient, body)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (message_id) DO NOTHING
                    RETURNING id::text;
                    """,
                    (ticket_id, message_id, direction, sender, recipient, body),
                )
                row = cur.fetchone()
                if not row:
                    cur.execute(
                        "SELECT id::text FROM messages WHERE message_id = %s",
                        (message_id,),
                    )
                    row = cur.fetchone()
                conn.commit()
                return str(row[0])

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, thread_id, customer, subject, category, status, proposed_action, assigned_to, created_at, updated_at FROM tickets WHERE id = %s",
                    (ticket_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                cols = [c.name for c in cur.description]
                return dict(zip(cols, row))

    def get_ticket_by_thread(self, thread_id: str) -> dict[str, Any] | None:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, thread_id, customer, subject, category, status, proposed_action, assigned_to, created_at, updated_at FROM tickets WHERE thread_id = %s",
                    (thread_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                cols = [c.name for c in cur.description]
                return dict(zip(cols, row))

    def list_tickets(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, thread_id, customer, subject, category, status, proposed_action, assigned_to, created_at, updated_at FROM tickets ORDER BY updated_at DESC LIMIT %s OFFSET %s",
                    (limit, offset),
                )
                cols = [c.name for c in cur.description]
                return [dict(zip(cols, r)) for r in cur.fetchall()]

    def get_ticket_messages(self, ticket_id: str) -> list[dict[str, Any]]:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, ticket_id::text, message_id, direction, sender, recipient, body, created_at FROM messages WHERE ticket_id = %s ORDER BY created_at ASC",
                    (ticket_id,),
                )
                cols = [c.name for c in cur.description]
                return [dict(zip(cols, r)) for r in cur.fetchall()]

    def update_ticket(
        self,
        ticket_id: str,
        status: str | None = None,
        assigned_to: str | None = None,
    ) -> bool:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                updates = ["updated_at = NOW()"]
                params: list[Any] = []
                if status is not None:
                    updates.append("status = %s")
                    params.append(status)
                if assigned_to is not None:
                    updates.append("assigned_to = %s")
                    params.append(assigned_to)
                params.append(ticket_id)
                cur.execute(
                    f"UPDATE tickets SET {', '.join(updates)} WHERE id = %s",
                    params,
                )
                conn.commit()
                return cur.rowcount > 0

    def add_ticket_note(self, ticket_id: str, note: str, author: str) -> str:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ticket_notes (ticket_id, author, note, created_at)
                    VALUES (%s, %s, %s, NOW())
                    RETURNING id::text
                    """,
                    (ticket_id, author, note),
                )
                note_id = cur.fetchone()[0]
                conn.commit()
                return str(note_id)

    def get_ticket_notes(self, ticket_id: str) -> list[dict[str, Any]]:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id::text, ticket_id::text, author, note, created_at
                    FROM ticket_notes
                    WHERE ticket_id = %s
                    ORDER BY created_at DESC
                    """,
                    (ticket_id,),
                )
                cols = [c.name for c in cur.description]
                return [dict(zip(cols, r)) for r in cur.fetchall()]

    def list_recent_events(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, message_id, status, attempts, error, result, created_at, completed_at FROM events ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    (limit, offset),
                )
                cols = [c.name for c in cur.description]
                rows = []
                for r in cur.fetchall():
                    d = dict(zip(cols, r))
                    if isinstance(d.get("result"), str):
                        try:
                            d["result"] = json.loads(d["result"])
                        except Exception:
                            pass
                    rows.append(d)
                return rows

    def upsert_kb_entry(self, section: str, title: str, content: str) -> str:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO knowledge_base (section, title, content, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (section, title) DO UPDATE SET
                        content = EXCLUDED.content,
                        updated_at = NOW()
                    RETURNING id::text;
                    """,
                    (section, title, content),
                )
                res = cur.fetchone()[0]
                conn.commit()
                return str(res)

    def list_kb_sections(self) -> list[str]:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT section FROM knowledge_base ORDER BY section ASC"
                )
                return [r[0] for r in cur.fetchall()]

    def get_kb_entries(self, section: str) -> list[dict[str, Any]]:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, section, title, content, updated_at FROM knowledge_base WHERE section = %s ORDER BY title ASC",
                    (section,),
                )
                cols = [c.name for c in cur.description]
                return [dict(zip(cols, r)) for r in cur.fetchall()]

    def get_all_kb_entries(self) -> list[dict[str, Any]]:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, section, title, content, updated_at FROM knowledge_base ORDER BY section ASC, title ASC"
                )
                cols = [c.name for c in cur.description]
                return [dict(zip(cols, r)) for r in cur.fetchall()]

    def get_kb_entry_by_id(self, entry_id: str) -> dict[str, Any] | None:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, section, title, content, updated_at FROM knowledge_base WHERE id = %s",
                    (entry_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                cols = [c.name for c in cur.description]
                return dict(zip(cols, row))

    def update_kb_entry(self, entry_id: str, title: str, content: str) -> bool:
        with self._get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE knowledge_base SET title = %s, content = %s, updated_at = NOW() WHERE id = %s",
                    (title, content, entry_id),
                )
                affected = cur.rowcount > 0
                conn.commit()
                return affected


# Select repository implementation based on settings and environment
_db_instance: BaseDatabase | None = None


def _is_pg_reachable(dsn: str, timeout: float = 0.5) -> bool:
    """Fast socket check to verify PostgreSQL host/port is reachable before attempting pool connect."""
    try:
        parsed = urlparse(dsn)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def _resolve_sqlite_path(default_path: str = "resolvehelm.db") -> str:
    """Resolve sqlite path, ensuring writable /tmp directory in serverless environments like Vercel."""
    import os
    from pathlib import Path

    if os.environ.get("VERCEL"):
        tmp_path = Path("/tmp/resolvehelm.db")
        if not tmp_path.exists():
            candidate = Path(default_path)
            if not candidate.is_absolute():
                candidate = Path(__file__).resolve().parent.parent / default_path
            if candidate.exists():
                import shutil

                try:
                    shutil.copyfile(candidate, tmp_path)
                except Exception:
                    pass
        return str(tmp_path)
    return default_path


def get_db() -> BaseDatabase:
    """Retrieve database instance."""
    global _db_instance
    if _db_instance is None:
        if settings.APP_ENV == "testing" or settings.DATABASE_URL.startswith(
            "sqlite://"
        ):
            _db_instance = SQLiteMemoryDatabase()
        else:
            sqlite_path = _resolve_sqlite_path("resolvehelm.db")
            if _is_pg_reachable(settings.DATABASE_URL):
                try:
                    pg_db = PostgresDatabase(settings.DATABASE_URL)
                    if pg_db.check_health():
                        _db_instance = pg_db
                    else:
                        logger.info(
                            "Postgres health check failed; using SQLite fallback"
                        )
                        _db_instance = SQLiteMemoryDatabase(sqlite_path)
                except Exception as e:
                    logger.info(
                        "Failed to connect to Postgres (%s); using SQLite fallback", e
                    )
                    _db_instance = SQLiteMemoryDatabase(sqlite_path)
            else:
                logger.info(
                    "Postgres host not reachable; using SQLite fallback (%s)",
                    sqlite_path,
                )
                _db_instance = SQLiteMemoryDatabase(sqlite_path)
    return _db_instance


async def check_db_health() -> bool:
    """Check health asynchronously for FastAPI health probes."""
    return get_db().check_health()
