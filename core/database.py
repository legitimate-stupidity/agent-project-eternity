import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.config import ConfigManager

class DatabaseManager:
    """Handles all SQLite interactions for the Ingestor/Processor task queue."""
    def __init__(self, config: ConfigManager):
        self.db_path = Path(config.get("database_config", "sqlite_db_path"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # We only call init_db from the 'init' command
        # to avoid wiping data on every run.
        if not self.db_path.exists():
            self.init_db(config)

    def get_conn(self) -> sqlite3.Connection:
        """Returns a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self, config: ConfigManager = None):
        """Destructively wipes and recreates the database schema."""
        drop_script = """
        DROP TABLE IF EXISTS raw_content;
        DROP TABLE IF EXISTS crawl_targets;
        """
        
        schema = """
        CREATE TABLE IF NOT EXISTS crawl_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', -- pending, active, completed, failed
            last_crawled_timestamp DATETIME
        );

        CREATE TABLE IF NOT EXISTS raw_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER,
            url TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', -- pending, processed, failed
            creation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(target_id) REFERENCES crawl_targets(id) ON DELETE SET NULL
        );
        """
        
        with self.get_conn() as conn:
            conn.executescript(drop_script)
            conn.executescript(schema)
            
            # Seed initial crawl targets from config
            if config:
                targets = config.get("services", "ingestor", "crawl_targets", default=[])
                if targets:
                    conn.executemany(
                        "INSERT OR IGNORE INTO crawl_targets (url) VALUES (?)",
                        [(url,) for url in targets]
                    )
            conn.commit()

    def add_crawl_target(self, url: str):
        """Adds a new URL to the crawl list."""
        with self.get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO crawl_targets (url) VALUES (?)", (url,))
            conn.commit()
    
    def get_next_crawl_target(self) -> Optional[Dict[str, Any]]:
        """Gets the oldest pending crawl target."""
        query = "SELECT * FROM crawl_targets WHERE status = 'pending' ORDER BY last_crawled_timestamp ASC, id ASC LIMIT 1"
        with self.get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
        return dict(result) if result else None
    
    def update_crawl_target_status(self, target_id: int, status: str):
        """Updates the status and timestamp of a crawl target."""
        with self.get_conn() as conn:
            conn.execute(
                "UPDATE crawl_targets SET status = ?, last_crawled_timestamp = CURRENT_TIMESTAMP WHERE id = ?",
                (status, target_id)
            )
            conn.commit()

    def add_raw_content(self, target_id: int, url: str, raw_text: str):
        """Adds fetched raw text to the processing queue."""
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO raw_content (target_id, url, raw_text) VALUES (?, ?, ?)",
                (target_id, url, raw_text)
            )
            conn.commit()

    def get_next_raw_content(self) -> Optional[Dict[str, Any]]:
        """Gets the oldest pending raw content for processing."""
        query = "SELECT * FROM raw_content WHERE status = 'pending' ORDER BY creation_timestamp ASC LIMIT 1"
        with self.get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
        return dict(result) if result else None

    def update_raw_content_status(self, content_id: int, status: str):
        """Updates the status of a raw content chunk."""
        with self.get_conn() as conn:
            conn.execute(
                "UPDATE raw_content SET status = ? WHERE id = ?",
                (status, content_id)
            )
            conn.commit()
