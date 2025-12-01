"""
Neon.tech PostgreSQL Database Service
Stores event logs, system status, and historical data
"""
import logging
import psycopg2
from psycopg2 import pool
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class NeonDatabaseService:
    """PostgreSQL database service for Neon.tech"""
    
    def __init__(self, connection_string: str):
        """
        Initialize Neon database connection
        
        Args:
            connection_string: PostgreSQL connection string from Neon.tech
        """
        self.connection_string = connection_string
        self.enabled = bool(connection_string)
        self.connection_pool = None
        
        if self.enabled:
            try:
                # Create connection pool
                self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                    1, 10,  # min and max connections
                    connection_string
                )
                logger.info("Neon database connection pool created")
                
                # Initialize database schema
                self._init_schema()
                
            except Exception as e:
                logger.error(f"Failed to connect to Neon database: {e}")
                self.enabled = False
        else:
            logger.warning("Neon database not configured (missing connection string)")
    
    def _init_schema(self):
        """Create database tables if they don't exist"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            # Event logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    event_type VARCHAR(100) NOT NULL,
                    details TEXT,
                    mode VARCHAR(50),
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System status table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_status (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    mode VARCHAR(50) NOT NULL,
                    stealth_mode BOOLEAN,
                    temperature FLOAT,
                    humidity FLOAT,
                    servo_position INTEGER,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Photo metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS photos (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    reason VARCHAR(255),
                    mode VARCHAR(50),
                    file_size INTEGER,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_logs_timestamp 
                ON event_logs(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_system_status_timestamp 
                ON system_status(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_photos_timestamp 
                ON photos(timestamp DESC)
            """)
            
            conn.commit()
            logger.info("Database schema initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def log_event(self, event_type: str, details: str = "", mode: str = "unknown"):
        """
        Log an event to the database
        
        Args:
            event_type: Type of event (ARM, DISARM, MOTION_DETECTED, etc.)
            details: Additional details about the event
            mode: Current system mode
        """
        if not self.enabled:
            return
        
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO event_logs (timestamp, event_type, details, mode)
                VALUES (%s, %s, %s, %s)
            """, (datetime.now(timezone.utc), event_type, details, mode))
            
            conn.commit()
            logger.debug(f"Event logged to database: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to log event to database: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def log_system_status(self, mode: str, stealth_mode: bool, 
                         temperature: Optional[float] = None, 
                         humidity: Optional[float] = None,
                         servo_position: Optional[int] = None):
        """
        Log current system status
        
        Args:
            mode: Current system mode
            stealth_mode: Stealth mode enabled/disabled
            temperature: Current temperature
            humidity: Current humidity
            servo_position: Current servo angle
        """
        if not self.enabled:
            return
        
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO system_status 
                (timestamp, mode, stealth_mode, temperature, humidity, servo_position)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (datetime.now(timezone.utc), mode, stealth_mode, 
                  temperature, humidity, servo_position))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to log system status: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def log_photo(self, filename: str, reason: str, mode: str, file_size: int):
        """
        Log photo capture metadata
        
        Args:
            filename: Name of the captured photo file
            reason: Reason for capture (Motion Trigger, Manual, etc.)
            mode: System mode when photo was taken
            file_size: Size of the photo file in bytes
        """
        if not self.enabled:
            return
        
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO photos (filename, timestamp, reason, mode, file_size)
                VALUES (%s, %s, %s, %s, %s)
            """, (filename, datetime.now(timezone.utc), reason, mode, file_size))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to log photo metadata: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent events from database
        
        Args:
            limit: Maximum number of events to return
        
        Returns:
            List of event dictionaries
        """
        if not self.enabled:
            return []
        
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, event_type, details, mode
                FROM event_logs
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    'timestamp': row[0].isoformat(),
                    'type': row[1],
                    'details': row[2],
                    'mode': row[3]
                })
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to fetch events from database: {e}")
            return []
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def get_system_status_history(self, hours: int = 24, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get system status history
        
        Args:
            hours: Number of hours of history to fetch
            limit: Maximum number of records
        
        Returns:
            List of status dictionaries
        """
        if not self.enabled:
            return []
        
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, mode, stealth_mode, temperature, humidity, servo_position
                FROM system_status
                WHERE timestamp > NOW() - INTERVAL '%s hours'
                ORDER BY timestamp DESC
                LIMIT %s
            """, (hours, limit))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'timestamp': row[0].isoformat(),
                    'mode': row[1],
                    'stealth_mode': row[2],
                    'temperature': row[3],
                    'humidity': row[4],
                    'servo_position': row[5]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to fetch status history: {e}")
            return []
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def cleanup(self):
        """Close all database connections"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connections closed")
