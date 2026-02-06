"""
Database connection and initialization for GoalFeed.
"""
import sqlite3
import os
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """SQLite database connection manager."""
    
    def __init__(self, db_path: str = "data/goalfeed.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_directory()
        self._connection: Optional[sqlite3.Connection] = None
    
    def _ensure_directory(self):
        """Ensure the database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
    
    def connect(self) -> sqlite3.Connection:
        """
        Get or create a database connection.
        
        Returns:
            SQLite connection
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Return rows as dictionaries
            self._connection.row_factory = sqlite3.Row
            logger.info(f"Connected to database: {self.db_path}")
        
        return self._connection
    
    @contextmanager
    def get_cursor(self):
        """
        Context manager for database cursor.
        
        Yields:
            SQLite cursor
        """
        conn = self.connect()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a query and return the cursor.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Cursor with results
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor
    
    def executemany(self, query: str, params_list: list) -> sqlite3.Cursor:
        """
        Execute a query with multiple parameter sets.
        
        Args:
            query: SQL query
            params_list: List of parameter tuples
            
        Returns:
            Cursor with results
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        return cursor
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """
        Fetch a single row.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Row or None
        """
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetchall(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """
        Fetch all rows.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List of rows
        """
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def init_schema(self, schema_path: Optional[str] = None):
        """
        Initialize database schema from SQL file.
        
        Args:
            schema_path: Path to schema.sql file
        """
        if schema_path is None:
            # Default schema path relative to this file
            schema_path = os.path.join(
                os.path.dirname(__file__),
                'schema.sql'
            )
        
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        conn = self.connect()
        conn.executescript(schema_sql)
        conn.commit()
        
        logger.info("Database schema initialized")
    
    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")


# Global database instance
_db_instance: Optional[Database] = None


def get_database(db_path: Optional[str] = None) -> Database:
    """
    Get or create the global database instance.
    
    Args:
        db_path: Path to database file (only used on first call)
        
    Returns:
        Database instance
    """
    global _db_instance
    
    if _db_instance is None:
        from config import get_config
        config = get_config()
        path = db_path or config.db_path
        _db_instance = Database(path)
    
    return _db_instance


def init_db(db_path: Optional[str] = None) -> Database:
    """
    Initialize the database with schema.
    
    Args:
        db_path: Path to database file
        
    Returns:
        Initialized Database instance
    """
    db = get_database(db_path)
    db.init_schema()
    return db
