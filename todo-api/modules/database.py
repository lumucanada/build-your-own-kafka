"""数据库连接、初始化、种子数据"""

import sqlite3
from contextlib import contextmanager
from werkzeug.security import generate_password_hash
from config import DATABASE, DEFAULT_USERNAME, DEFAULT_PASSWORD


@contextmanager
def get_db():
    """上下文管理器，自动关闭连接，查询返回 Row 对象"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """创建所有表"""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task        TEXT    NOT NULL,
                completed   INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT    UNIQUE NOT NULL,
                password_hash   TEXT    NOT NULL,
                role            TEXT    DEFAULT 'admin',
                created_at      TEXT    DEFAULT (datetime('now','localtime'))
            );
        """)
        conn.commit()


def seed_admin():
    """没有管理员时自动创建默认账号"""
    with get_db() as conn:
        exists = conn.execute("SELECT id FROM users WHERE role='admin'").fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (DEFAULT_USERNAME, generate_password_hash(DEFAULT_PASSWORD))
            )
            conn.commit()
            print(f"[OK] 默认管理员: {DEFAULT_USERNAME} / {DEFAULT_PASSWORD}")
