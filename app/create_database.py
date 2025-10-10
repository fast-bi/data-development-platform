import sqlite3
import contextlib
import os
from app.utils import DB_PATH  # Import the DB_PATH

def create_connection(db_file: str) -> None:
    """ Create a database connection to a SQLite database """
    try:
        conn = sqlite3.connect(db_file)
    finally:
        conn.close()

def create_table(db_file: str) -> None:
    """ Create a table for users """
    query = '''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            email TEXT,
            status TEXT DEFAULT 'logoff' CHECK(status IN ('active', 'passive', 'logoff')),
            last_activity TEXT
        );
    '''

    with contextlib.closing(sqlite3.connect(db_file)) as conn:
        with conn:
            conn.execute(query)

def setup_database() -> None:
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Create the database and table
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    email TEXT,
                    status TEXT DEFAULT 'logoff' CHECK(status IN ('active', 'passive', 'logoff')),
                    last_activity TEXT
                )
            ''')
        print(f"User Database setup complete at {DB_PATH}")
    except Exception as e:
        print(f"Error setting up user database: {e}")
        raise
