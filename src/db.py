import os
import sqlite3

import bcrypt

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "app.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS forms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                form_id TEXT,
                edit_url TEXT,
                respond_url TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", ("admin",)
        ).fetchone()
        if not existing:
            pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("admin", pw_hash),
            )


def get_user(username: str):
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def save_form(user_id: int, file_name: str, form_id: str, edit_url: str, respond_url: str, created_at: str):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO forms (user_id, file_name, form_id, edit_url, respond_url, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, file_name, form_id, edit_url, respond_url, created_at),
        )


def get_forms(user_id: int):
    with _conn() as conn:
        rows = conn.execute(
            "SELECT file_name, form_id, edit_url, respond_url, created_at "
            "FROM forms WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
