import os
import sqlite3
import json
from contextlib import contextmanager

DB_FILE = os.getenv("STUDYMATE_DB", "studymate.db")


@contextmanager
def get_db():
    """Opens the database, saves changes on success, undoes them on error, always closes."""
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _add_column_if_missing(conn, table, column, definition):
    existing = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                embedding TEXT,
                subject TEXT
            )
        """)
        

        conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                difficulty TEXT,
                questions TEXT,
                user_answers TEXT,
                score INTEGER,
                total INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS login_failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        # add the owner column to tables created before auth existed
        for table in ("messages", "notes", "quiz_results"):
            _add_column_if_missing(conn, table, "user_id", "INTEGER")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_user_subject ON notes(user_id, subject)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quiz_user ON quiz_results(user_id)")


        # add the owner column to tables created before auth existed
        for table in ("messages", "notes", "quiz_results"):
            _add_column_if_missing(conn, table, "user_id", "INTEGER")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_user_subject ON notes(user_id, subject)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quiz_user ON quiz_results(user_id)")


# ---------- users ----------

def create_user(username, password_hash):
    """Returns the new user's id, or None if that username is already taken."""
    try:
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_user_by_username(username):
    """Returns (id, username, password_hash) or None."""
    with get_db() as conn:
        return conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()


def get_user_by_id(user_id):
    """Returns (id, username) or None."""
    with get_db() as conn:
        return conn.execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def claim_unowned_data(user_id):
    """Gives all data saved before auth existed to this user. Returns rows claimed per table."""
    claimed = {}
    with get_db() as conn:
        for table in ("messages", "notes", "quiz_results"):
            cursor = conn.execute(
                f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL", (user_id,)
            )
            claimed[table] = cursor.rowcount
    return claimed


# ---------- messages ----------

def save_message(role, content, user_id=None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (role, content, user_id) VALUES (?, ?, ?)",
            (role, content, user_id),
        )


def get_all_messages(user_id=None):
    sql = "SELECT role, content FROM messages"
    params = []
    if user_id is not None:
        sql += " WHERE user_id = ?"
        params.append(user_id)
    with get_db() as conn:
        return conn.execute(sql, params).fetchall()


# ---------- notes ----------

def save_note(content, embedding, subject="General", user_id=None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO notes (content, embedding, subject, user_id) VALUES (?, ?, ?, ?)",
            (content, json.dumps(embedding), subject, user_id),
        )


def get_all_notes(user_id=None):
    sql = "SELECT id, content, embedding, subject FROM notes"
    params = []
    if user_id is not None:
        sql += " WHERE user_id = ?"
        params.append(user_id)
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [(id, content, json.loads(embedding), subject) for id, content, embedding, subject in rows]


def get_notes_by_subject(subject, user_id=None):
    sql = "SELECT id, content, embedding, subject FROM notes WHERE subject = ? COLLATE NOCASE"
    params = [subject]
    if user_id is not None:
        sql += " AND user_id = ?"
        params.append(user_id)
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [(id, content, json.loads(embedding), subject) for id, content, embedding, subject in rows]


# ---------- quiz results ----------

def save_quiz_result(subject, difficulty, questions, user_answers, score, total, user_id=None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO quiz_results (subject, difficulty, questions, user_answers, score, total, user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (subject, difficulty, json.dumps(questions), json.dumps(user_answers), score, total, user_id),
        )


def get_all_quiz_results(user_id=None):
    sql = "SELECT id, subject, difficulty, questions, user_answers, score, total FROM quiz_results"
    params = []
    if user_id is not None:
        sql += " WHERE user_id = ?"
        params.append(user_id)
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [(id, subject, difficulty, json.loads(q), json.loads(a), score, total)
            for id, subject, difficulty, q, a, score, total in rows]
# ---------- login protection ----------

def record_failed_login(key):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO login_failures (key, created_at) VALUES (?, strftime('%s','now'))",
            (key,)
        )


def count_recent_failures(key, window_seconds):
    with get_db() as conn:
        result = conn.execute(
            """
            SELECT COUNT(*) FROM login_failures
            WHERE key = ?
            AND created_at > strftime('%s','now') - ?
            """,
            (key, window_seconds),
        ).fetchone()

    return result[0]


def clear_failures(key):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM login_failures WHERE key = ?",
            (key,)
        )



