import sqlite3
import os

DB_PATH = "data/app.db"

def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # Reversals table
    c.execute("""
    CREATE TABLE IF NOT EXISTS reversals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tx_date TEXT,
        branch TEXT,
        reversal_ref TEXT,
        replacement_ref TEXT,
        amount REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()