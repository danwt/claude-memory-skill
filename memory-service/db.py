import sqlite3
import sqlite_vec
import struct
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path("/app/data/memory.db")
EMBEDDING_DIM = 384


def serialize_float32(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            project_path TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            file_path TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_session
        ON conversations(session_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
        ON conversations(timestamp)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_project
        ON conversations(project_path)
    """)

    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts
        USING fts5(
            content,
            content_rowid='rowid',
            tokenize='porter unicode61'
        )
    """)

    cursor.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS conversations_vec
        USING vec0(
            id TEXT PRIMARY KEY,
            embedding float[{EMBEDDING_DIM}]
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingest_state (
            file_path TEXT PRIMARY KEY,
            last_modified REAL NOT NULL,
            last_position INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    logger.info("database initialized: path=%s", DB_PATH)


def insert_conversation(
    conn: sqlite3.Connection,
    id: str,
    session_id: str,
    project_path: str,
    timestamp: str,
    role: str,
    content: str,
    file_path: str,
    embedding: list[float],
) -> None:
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO conversations
        (id, session_id, project_path, timestamp, role, content, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (id, session_id, project_path, timestamp, role, content, file_path),
    )

    cursor.execute(
        """
        INSERT OR REPLACE INTO conversations_fts (rowid, content)
        VALUES (
            (SELECT rowid FROM conversations WHERE id = ?),
            ?
        )
        """,
        (id, content),
    )

    cursor.execute(
        """
        INSERT OR REPLACE INTO conversations_vec (id, embedding)
        VALUES (?, ?)
        """,
        (id, serialize_float32(embedding)),
    )


def fts_search(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.id, c.session_id, c.project_path, c.timestamp, c.role, c.content,
               bm25(conversations_fts) as score
        FROM conversations_fts fts
        JOIN conversations c ON c.rowid = fts.rowid
        WHERE conversations_fts MATCH ?
        ORDER BY score
        LIMIT ?
        """,
        (query, limit),
    )
    return [dict(row) for row in cursor.fetchall()]


def vec_search(
    conn: sqlite3.Connection, embedding: list[float], limit: int = 20
) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT v.id, v.distance, c.session_id, c.project_path, c.timestamp,
               c.role, c.content
        FROM conversations_vec v
        JOIN conversations c ON c.id = v.id
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT ?
        """,
        (serialize_float32(embedding), limit),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_session_context(
    conn: sqlite3.Connection, session_id: str, around_id: Optional[str] = None
) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, session_id, project_path, timestamp, role, content
        FROM conversations
        WHERE session_id = ?
        ORDER BY timestamp
        """,
        (session_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_ingest_state(conn: sqlite3.Connection, file_path: str) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_modified, last_position FROM ingest_state WHERE file_path = ?",
        (file_path,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def set_ingest_state(
    conn: sqlite3.Connection, file_path: str, last_modified: float, last_position: int
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO ingest_state (file_path, last_modified, last_position)
        VALUES (?, ?, ?)
        """,
        (file_path, last_modified, last_position),
    )


def get_stats(conn: sqlite3.Connection) -> dict:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM conversations")
    total = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(DISTINCT session_id) as count FROM conversations")
    sessions = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(DISTINCT project_path) as count FROM conversations")
    projects = cursor.fetchone()["count"]
    return {"total_messages": total, "sessions": sessions, "projects": projects}
