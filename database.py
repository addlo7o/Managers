import sqlite3
import threading
from datetime import datetime, timedelta

DB_NAME = "yasha_bot.db"
_local = threading.local()


def get_db():
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        _local.cursor = _local.conn.cursor()
    return _local.conn, _local.cursor


def init_db():
    conn, cursor = get_db()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS group_settings (
            chat_id INTEGER PRIMARY KEY,
            welcome_text TEXT,
            goodbye_text TEXT,
            welcome_enabled INTEGER DEFAULT 1,
            goodbye_enabled INTEGER DEFAULT 1,
            delete_links INTEGER DEFAULT 1,
            delete_spam INTEGER DEFAULT 1,
            delete_arabic INTEGER DEFAULT 0,
            delete_mentions INTEGER DEFAULT 0,
            delete_stickers INTEGER DEFAULT 0,
            force_sub INTEGER DEFAULT 1,
            captcha_enabled INTEGER DEFAULT 0,
            log_enabled INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER,
            chat_id INTEGER,
            reason TEXT,
            admin_id INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        );

        CREATE TABLE IF NOT EXISTS muted_users (
            user_id INTEGER,
            chat_id INTEGER,
            until TIMESTAMP,
            reason TEXT,
            PRIMARY KEY (user_id, chat_id)
        );

        CREATE TABLE IF NOT EXISTS group_admins (
            user_id INTEGER,
            chat_id INTEGER,
            level TEXT DEFAULT 'admin',
            added_by INTEGER,
            PRIMARY KEY (user_id, chat_id)
        );
    """)
    conn.commit()


# ===== group_settings =====

def get_group_settings(chat_id: int) -> dict:
    conn, cursor = get_db()
    cursor.execute("SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
        cursor.execute("SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def update_group_setting(chat_id: int, key: str, value):
    conn, cursor = get_db()
    cursor.execute(
        f"INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)", (chat_id,)
    )
    cursor.execute(
        f"UPDATE group_settings SET {key} = ? WHERE chat_id = ?", (value, chat_id)
    )
    conn.commit()


def get_setting(chat_id: int, key: str, default=None):
    settings = get_group_settings(chat_id)
    return settings.get(key, default)


def set_setting(chat_id: int, key: str, value):
    update_group_setting(chat_id, key, value)


# ===== banned_users =====

def ban_user(user_id: int, chat_id: int, reason: str = "", admin_id: int = 0):
    conn, cursor = get_db()
    cursor.execute(
        "INSERT OR REPLACE INTO banned_users (user_id, chat_id, reason, admin_id) VALUES (?, ?, ?, ?)",
        (user_id, chat_id, reason, admin_id),
    )
    conn.commit()


def unban_user(user_id: int, chat_id: int):
    conn, cursor = get_db()
    cursor.execute(
        "DELETE FROM banned_users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id)
    )
    conn.commit()


def is_banned(user_id: int, chat_id: int) -> bool:
    _, cursor = get_db()
    cursor.execute(
        "SELECT 1 FROM banned_users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id)
    )
    return cursor.fetchone() is not None


# ===== muted_users =====

def mute_user(user_id: int, chat_id: int, until: datetime, reason: str = ""):
    conn, cursor = get_db()
    cursor.execute(
        "INSERT OR REPLACE INTO muted_users (user_id, chat_id, until, reason) VALUES (?, ?, ?, ?)",
        (user_id, chat_id, until.isoformat(), reason),
    )
    conn.commit()


def unmute_user(user_id: int, chat_id: int):
    conn, cursor = get_db()
    cursor.execute(
        "DELETE FROM muted_users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id)
    )
    conn.commit()


def is_muted(user_id: int, chat_id: int) -> bool:
    _, cursor = get_db()
    cursor.execute(
        "SELECT until FROM muted_users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id)
    )
    row = cursor.fetchone()
    if not row:
        return False
    until = datetime.fromisoformat(row[0])
    if datetime.now() > until:
        unmute_user(user_id, chat_id)
        return False
    return True
