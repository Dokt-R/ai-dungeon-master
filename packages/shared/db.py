# db.py
import os
import sqlite3
from contextlib import contextmanager
from packages.backend.db.init_db import initialize_schema

DEFAULT_DB_PATH = os.environ.get("DB_PATH", "server_settings.db")


def get_db_path():
    return DEFAULT_DB_PATH


def get_connection(db_path=None):
    return sqlite3.connect(db_path or get_db_path())


@contextmanager
def db_connection(db_path=None, persistent_conn=None):
    """
    Context manager that uses a provided persistent connection if available,
    or creates and manages a temporary one otherwise.
    """
    if persistent_conn:
        yield persistent_conn
    else:
        conn = get_connection(db_path)
        try:
            yield conn
        finally:
            conn.close()


#! May need fixing or testing, affects many tests
def setup_db_for_manager(db_path=None):
    """
    Handles:
    - persistent memory connection
    - transient file connection
    - schema initialization

    If the managers expect . _conn to always exist, we are fine. Otherwise, remember:
        self._conn is:
        sqlite3.Connection if :memory:
        None if file-based

    So when you use connections later, always check if self._conn exists:
        ```python
        if self._conn:
            conn = self._conn
        else:
            conn = get_connection(self.db_path)
        ```
    """
    db_path = db_path or get_db_path()
    if db_path == ":memory:":
        conn = get_connection(db_path)
        initialize_schema(conn)
        return conn
    else:
        with get_connection(db_path) as conn:
            initialize_schema(conn)
        return None
