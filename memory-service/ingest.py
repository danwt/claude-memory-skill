import json
from pathlib import Path
from typing import Iterator
import logging

from db import (
    get_connection,
    insert_conversation,
    get_ingest_state,
    set_ingest_state,
)
from embedder import embed_texts

logger = logging.getLogger(__name__)

ARCHIVE_PATH = Path("/claude-archives")
BATCH_SIZE = 50


def decode_project_path(encoded: str) -> str:
    if encoded.startswith("-"):
        return encoded.replace("-", "/", 1).replace("-", "/")
    return encoded


def parse_jsonl_file(file_path: Path) -> Iterator[dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                logger.debug(
                    "skipping malformed line: file=%s line=%d error=%s",
                    file_path,
                    line_num,
                    e,
                )


def extract_text_content(message: dict) -> str:
    content = message.get("content", [])
    if isinstance(content, str):
        return content
    parts = []
    for item in content:
        if isinstance(item, dict):
            if item.get("type") == "text":
                parts.append(item.get("text", ""))
        elif isinstance(item, str):
            parts.append(item)
    return "\n".join(parts)


def should_index_message(entry: dict) -> bool:
    message = entry.get("message", {})
    role = message.get("role", "")
    if role not in ("user", "assistant"):
        return False
    content = message.get("content", [])
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get("type") in ("tool_use", "tool_result"):
                    return False
    text = extract_text_content(message)
    if len(text.strip()) < 10:
        return False
    return True


def ingest_file(file_path: Path, project_path: str) -> int:
    conn = get_connection()
    state = get_ingest_state(conn, str(file_path))
    file_stat = file_path.stat()

    if state and state["last_modified"] >= file_stat.st_mtime:
        conn.close()
        return 0

    messages_to_insert = []
    session_id = file_path.stem

    for entry in parse_jsonl_file(file_path):
        if not should_index_message(entry):
            continue

        message = entry.get("message", {})
        msg_id = entry.get("uuid", "")
        timestamp = entry.get("timestamp", "")
        role = message.get("role", "")
        text = extract_text_content(message)

        if not msg_id or not text:
            continue

        messages_to_insert.append(
            {
                "id": msg_id,
                "session_id": session_id,
                "project_path": project_path,
                "timestamp": timestamp,
                "role": role,
                "content": text,
                "file_path": str(file_path),
            }
        )

    if not messages_to_insert:
        set_ingest_state(conn, str(file_path), file_stat.st_mtime, 0)
        conn.commit()
        conn.close()
        return 0

    texts = [m["content"] for m in messages_to_insert]
    embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        embeddings.extend(embed_texts(batch))

    for msg, embedding in zip(messages_to_insert, embeddings):
        insert_conversation(
            conn,
            id=msg["id"],
            session_id=msg["session_id"],
            project_path=msg["project_path"],
            timestamp=msg["timestamp"],
            role=msg["role"],
            content=msg["content"],
            file_path=msg["file_path"],
            embedding=embedding,
        )

    set_ingest_state(conn, str(file_path), file_stat.st_mtime, len(messages_to_insert))
    conn.commit()
    conn.close()

    logger.info(
        "ingested file: path=%s messages=%d", file_path, len(messages_to_insert)
    )
    return len(messages_to_insert)


def ingest_all() -> dict:
    if not ARCHIVE_PATH.exists():
        logger.error("archive path does not exist: path=%s", ARCHIVE_PATH)
        return {"error": "Archive path not found", "files": 0, "messages": 0}

    total_files = 0
    total_messages = 0

    for project_dir in ARCHIVE_PATH.iterdir():
        if not project_dir.is_dir():
            continue

        project_path = decode_project_path(project_dir.name)

        for jsonl_file in project_dir.glob("*.jsonl"):
            try:
                count = ingest_file(jsonl_file, project_path)
                total_messages += count
                total_files += 1
            except Exception as e:
                logger.error("failed to ingest file: path=%s error=%s", jsonl_file, e)

    logger.info(
        "ingest complete: files=%d messages=%d", total_files, total_messages
    )
    return {"files": total_files, "messages": total_messages}
