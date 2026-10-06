import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from typing import Generator
import logging
from backend.config import settings

logger = logging.getLogger(__name__)

# Connection pool
_connection_pool = None

def get_pool():
    global _connection_pool
    if _connection_pool is None or _connection_pool.closed:
        try:
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=20,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                dbname=settings.DB_NAME,
                client_encoding="utf-8"
            )
            logger.info("PostgreSQL connection pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            raise e
    return _connection_pool

@contextmanager
def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    p = get_pool()
    conn = p.getconn()
    try:
        yield conn
    finally:
        p.putconn(conn)

@contextmanager
def get_db_cursor(commit: bool = False):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
