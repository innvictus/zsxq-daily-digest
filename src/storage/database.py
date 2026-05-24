"""SQLite database for tracking scraped content and reports."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
    group_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    last_fetch_time TEXT,
    enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS topics (
    topic_id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    author_name TEXT,
    author_id TEXT,
    create_time TEXT NOT NULL,
    fetch_time TEXT NOT NULL,
    comments_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    readings_count INTEGER DEFAULT 0,
    topic_type TEXT,
    files TEXT,
    raw_data TEXT,
    FOREIGN KEY (group_id) REFERENCES groups(group_id)
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT NOT NULL UNIQUE,
    html_content TEXT NOT NULL,
    posts_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_topics_group ON topics(group_id);
CREATE INDEX IF NOT EXISTS idx_topics_create_time ON topics(create_time);
CREATE INDEX IF NOT EXISTS idx_topics_title ON topics(title);
"""


class Database:
    def __init__(self, db_path: str = "data/zsxq.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(DB_SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self):
        """Handle schema migrations for existing databases."""
        # Add files column if it doesn't exist
        cols = [row[1] for row in
                self.conn.execute("PRAGMA table_info(topics)").fetchall()]
        if "files" not in cols:
            self.conn.execute("ALTER TABLE topics ADD COLUMN files TEXT")
            self.conn.commit()

    def ensure_group(self, group_id: str, name: str):
        self.conn.execute(
            "INSERT OR IGNORE INTO groups (group_id, name) VALUES (?, ?)",
            (group_id, name)
        )
        self.conn.commit()

    def update_group_fetch_time(self, group_id: str):
        self.conn.execute(
            "UPDATE groups SET last_fetch_time = ? WHERE group_id = ?",
            (datetime.now().isoformat(), group_id)
        )
        self.conn.commit()

    def topic_exists(self, topic_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM topics WHERE topic_id = ?", (topic_id,)
        ).fetchone()
        return row is not None

    def insert_topic(self, topic: dict):
        raw_data = json.dumps(topic.get("_raw", {}), ensure_ascii=False)
        files_json = json.dumps(topic.get("files", []), ensure_ascii=False)

        self.conn.execute("""
            INSERT OR REPLACE INTO topics
            (topic_id, group_id, title, content, author_name, author_id,
             create_time, fetch_time, comments_count, likes_count,
             readings_count, topic_type, files, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            topic["topic_id"],
            topic.get("group_id", ""),
            topic.get("title", ""),
            topic.get("content", ""),
            topic.get("author_name", ""),
            topic.get("author_id", ""),
            topic.get("create_time", ""),
            datetime.now().isoformat(),
            topic.get("comments_count", 0),
            topic.get("likes_count", 0),
            topic.get("readings_count", 0),
            topic.get("topic_type", ""),
            files_json,
            raw_data,
        ))
        self.conn.commit()

    def insert_topics_batch(self, topics: list[dict]) -> int:
        count = 0
        for topic in topics:
            if not self.topic_exists(topic["topic_id"]):
                self.insert_topic(topic)
                count += 1
        return count

    def get_topics_by_date(self, start: str, end: str,
                           group_id: Optional[str] = None) -> list[dict]:
        query = """
            SELECT t.*, g.name as group_name FROM topics t
            LEFT JOIN groups g ON t.group_id = g.group_id
            WHERE t.create_time >= ? AND t.create_time <= ?
        """
        params = [start, end]
        if group_id:
            query += " AND t.group_id = ?"
            params.append(group_id)
        query += " ORDER BY t.comments_count DESC, t.likes_count DESC"

        rows = self.conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            # Parse files JSON
            try:
                d["files"] = json.loads(d.get("files", "[]") or "[]")
            except (json.JSONDecodeError, TypeError):
                d["files"] = []
            results.append(d)
        return results

    def search_topics(self, keyword: str,
                      group_id: Optional[str] = None,
                      limit: int = 50) -> list[dict]:
        query = """
            SELECT * FROM topics
            WHERE (title LIKE ? OR content LIKE ?)
        """
        params = [f"%{keyword}%", f"%{keyword}%"]
        if group_id:
            query += " AND group_id = ?"
            params.append(group_id)
        query += " ORDER BY create_time DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_report(self, date_str: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM reports WHERE report_date = ?", (date_str,)
        ).fetchone()
        return dict(row) if row else None

    def save_report(self, date_str: str, html_content: str,
                    posts_count: int):
        self.conn.execute("""
            INSERT OR REPLACE INTO reports
            (report_date, html_content, posts_count, created_at)
            VALUES (?, ?, ?, ?)
        """, (date_str, html_content, posts_count, datetime.now().isoformat()))
        self.conn.commit()

    def total_topics(self, group_id: Optional[str] = None) -> int:
        if group_id:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM topics WHERE group_id = ?", (group_id,)
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM topics"
            ).fetchone()
        return row[0] if row else 0

    def close(self):
        self.conn.close()
