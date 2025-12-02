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
        self.pg_conn_str = os.getenv("NEON_DATABASE_URL")
        if self.pg_conn_str and self.pg_conn_str.startswith("postgres://"):
            self.pg_conn_str = self.pg_conn_str.replace("postgres://", "postgresql://", 1)

        # Whether we should attempt direct Postgres writes
        self.use_pg = bool(self.pg_conn_str and psycopg2)

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

    def _pg_connect(self):
        """Return a psycopg2 connection using the configured DATABASE_URL.

        Tries to connect with sslmode='require' first (Neon typically requires TLS),
        then falls back to a plain connect if that fails.
        """
        if not self.pg_conn_str:
            raise RuntimeError("No DATABASE_URL configured")
        if not psycopg2:
            raise RuntimeError("psycopg2 not installed")

        try:
            return psycopg2.connect(self.pg_conn_str, sslmode='require')
        except Exception:
            return psycopg2.connect(self.pg_conn_str)

    def log_environment(self, temp, humidity):
        ts = time.strftime('%Y-%m-%dT%H:%M:%S')

        # Try direct Postgres insert if configured
        if self.use_pg:
            try:
                pg = self._pg_connect()
                with pg:
                    with pg.cursor() as cur:
                        cur.execute(
                            "INSERT INTO measurements (timestamp, temperature, humidity) VALUES (%s, %s, %s)",
                            (ts, temp, humidity)
                        )
                try:
                    pg.close()
                except Exception:
                    pass
                logger.debug("Logged environment data to Postgres")
                return
            except Exception as e:
                logger.warning(f"Postgres insert failed, falling back to local SQLite: {e}")

        # Fallback to local sqlite (acts as buffer for later sync)
        try:
            with sqlite3.connect(self.local_db) as conn:
                conn.execute(
                    "INSERT INTO measurements (timestamp, temperature, humidity, synced) VALUES (?, ?, ?, 0)",
                    (ts, temp, humidity)
                )
        except Exception as e:
            logger.error(f"Failed to log env data to local DB: {e}")

    def log_security(self, event_type, details, mode):
        ts = time.strftime('%Y-%m-%dT%H:%M:%S')

        # Try direct Postgres insert if configured
        if self.use_pg:
            try:
                pg = self._pg_connect()
                with pg:
                    with pg.cursor() as cur:
                        cur.execute(
                            "INSERT INTO security_events (timestamp, event_type, details, mode) VALUES (%s, %s, %s, %s)",
                            (ts, event_type, details, mode)
                        )
                try:
                    pg.close()
                except Exception:
                    pass
                logger.debug("Logged security event to Postgres")
                return
            except Exception as e:
                logger.warning(f"Postgres insert failed, falling back to local SQLite: {e}")

        # Fallback to local sqlite
        try:
            with sqlite3.connect(self.local_db) as conn:
                conn.execute(
                    "INSERT INTO security_events (timestamp, event_type, details, mode, synced) VALUES (?, ?, ?, ?, 0)",
                    (ts, event_type, details, mode)
                )
        except Exception as e:
            logger.error(f"Failed to log security data to local DB: {e}")

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
        try:
            # Fetch unsynced measurements from local sqlite
            with sqlite3.connect(self.local_db) as conn:
                cur = conn.cursor()
                cur.execute("SELECT id, timestamp, temperature, humidity FROM measurements WHERE synced=0 ORDER BY id LIMIT 100")
                rows = cur.fetchall()

            if not rows:
                return

            # Connect to Postgres (Neon)
            conn_params = {}
            try:
                pg = psycopg2.connect(self.pg_conn_str, sslmode='require')
            except Exception:
                pg = psycopg2.connect(self.pg_conn_str)

            with pg:
                with pg.cursor() as pc:
                    for r in rows:
                        local_id, ts, temp, hum = r
                        try:
                            pc.execute(
                                "INSERT INTO measurements (timestamp, temperature, humidity) VALUES (%s, %s, %s)",
                                (ts, temp, hum)
                            )
                            # Mark local row as synced
                            with sqlite3.connect(self.local_db) as lconn:
                                lcur = lconn.cursor()
                                lcur.execute("UPDATE measurements SET synced=1 WHERE id=?", (local_id,))
                                lconn.commit()
                            logger.info(f"Synced measurement id={local_id} to Postgres")
                        except Exception as e:
                            logger.error(f"Failed to sync measurement id={local_id}: {e}")
            try:
                pg.close()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"_sync_measurements error: {e}", exc_info=True)

    def _sync_security(self):
        try:
            # Fetch unsynced security events
            with sqlite3.connect(self.local_db) as conn:
                cur = conn.cursor()
                cur.execute("SELECT id, timestamp, event_type, details, mode FROM security_events WHERE synced=0 ORDER BY id LIMIT 100")
                rows = cur.fetchall()

            if not rows:
                return

            # Connect to Postgres (Neon)
            try:
                pg = psycopg2.connect(self.pg_conn_str, sslmode='require')
            except Exception:
                pg = psycopg2.connect(self.pg_conn_str)

            with pg:
                with pg.cursor() as pc:
                    for r in rows:
                        local_id, ts, etype, details, mode = r
                        try:
                            pc.execute(
                                "INSERT INTO security_events (timestamp, event_type, details, mode) VALUES (%s, %s, %s, %s)",
                                (ts, etype, details, mode)
                            )
                            # Mark local row as synced
                            with sqlite3.connect(self.local_db) as lconn:
                                lcur = lconn.cursor()
                                lcur.execute("UPDATE security_events SET synced=1 WHERE id=?", (local_id,))
                                lconn.commit()
                            logger.info(f"Synced security_event id={local_id} to Postgres")
                        except Exception as e:
                            logger.error(f"Failed to sync security_event id={local_id}: {e}")
            try:
                pg.close()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"_sync_security error: {e}", exc_info=True)

    def close(self):
        self.running = False