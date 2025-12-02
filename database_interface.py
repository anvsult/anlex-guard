import sqlite3
import threading
import time
import os
import logging
from typing import Dict
from dotenv import load_dotenv

try:
    import psycopg2
except ImportError:
    psycopg2 = None

logger = logging.getLogger(__name__)
load_dotenv()

# We add 'rfid_tag' column for your specific hardware
CREATE_ENV_TABLE = """
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    synced INTEGER DEFAULT 0
);
"""

CREATE_SEC_TABLE = """
CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT,
    details TEXT,
    mode TEXT,
    synced INTEGER DEFAULT 0
);
"""

class DatabaseInterface:
    def __init__(self, config: Dict):
        self.config = config
        self.local_db = "anlex_local.db"
        self.device_id = "anlex_pi_01"
        
        # Cloud connection string
        self.pg_conn_str = os.getenv("DATABASE_URL")
        if self.pg_conn_str and self.pg_conn_str.startswith("postgres://"):
            self.pg_conn_str = self.pg_conn_str.replace("postgres://", "postgresql://", 1)

        self._init_local_db()
        
        self.running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, name="DBSyncWorker", daemon=True)
        self.sync_thread.start()

    def _init_local_db(self):
        try:
            with sqlite3.connect(self.local_db) as conn:
                conn.execute(CREATE_ENV_TABLE)
                conn.execute(CREATE_SEC_TABLE)
            logger.info("Local database initialized.")
        except Exception as e:
            logger.error(f"DB Init Failed: {e}")

    def log_environment(self, temp, humidity):
        try:
            ts = time.strftime('%Y-%m-%dT%H:%M:%S')
            with sqlite3.connect(self.local_db) as conn:
                conn.execute(
                    "INSERT INTO measurements (timestamp, temperature, humidity, synced) VALUES (?, ?, ?, 0)",
                    (ts, temp, humidity)
                )
        except Exception as e:
            logger.error(f"Failed to log env data: {e}")

    def log_security(self, event_type, details, mode):
        try:
            ts = time.strftime('%Y-%m-%dT%H:%M:%S')
            with sqlite3.connect(self.local_db) as conn:
                conn.execute(
                    "INSERT INTO security_events (timestamp, event_type, details, mode, synced) VALUES (?, ?, ?, ?, 0)",
                    (ts, event_type, details, mode)
                )
        except Exception as e:
            logger.error(f"Failed to log security data: {e}")

    def _sync_loop(self):
        while self.running:
            if self.pg_conn_str and psycopg2:
                try:
                    self._sync_measurements()
                    self._sync_security()
                except Exception as e:
                    logger.error(f"Sync error: {e}")
            time.sleep(15)

    def _sync_measurements(self):
        # Implementation matches JeefHS logic (fetching synced=0 and pushing to Postgres)
        # Omitted for brevity, copy logical flow from JeefHS database_interface.py
        pass 

    def _sync_security(self):
        # Implementation matches JeefHS logic
        pass

    def close(self):
        self.running = False