import os
import sqlite3
import json
import time
from contextlib import contextmanager

try:
    import psycopg
except ImportError:  # only needed when DATABASE_URL is set
    psycopg = None

DB_FILE = os.getenv("STUDYMATE_DB", "studymate.db")

# Set DATABASE_URL on the host (Render) to use Postgres.
# Leave it unset on your laptop and the app uses the SQLite file, exactly as before.
DATABASE_URL = os.getenv("DATABASE_URL")


def _use_postgres():
    return bool(DATABASE_URL)


class _PgConnection:
    """Lets the rest of this file write '?' placeholders for both databases."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(sql.replace("?", "%s"), params)


@contextmanager
def get_db():
    """Opens the database, saves changes on success, undoes them on error, always closes."""
    if _use_postgres():
        if psycopg is None:
            raise RuntimeError("DATABASE_URL is set but psycopg is not installed.")
        # prepare_threshold=None keeps this safe behind Neon's pooled connection
        conn = psycopg.connect(DATABASE_URL, prepare_threshold=None)
        wrapped = _PgConnection(conn)
    else:
        conn = sqlite3.connect(DB_FILE)
        wrapped = conn
    try:
        yield wrapped
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _integrity_errors():
    errors = [sqlite3.IntegrityError]
    if psycopg is not None:
        errors.append(psycopg.IntegrityError)
    return tuple(errors)


def _add_user_id_column(conn, table):
    """Adds the owner column to tables created before accounts existed."""
    if _use_postgres():
        conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS user_id INTEGER")
    else:
        existing = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if "user_id" not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER")


def init_db():
    pg = _use_postgres()
    print(f"StudyMate database: {'Postgres' if pg else DB_FILE}")
    primary_key = "SERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    username_column = "TEXT NOT NULL" if pg else "TEXT NOT NULL UNIQUE COLLATE NOCASE"

    with get_db() as conn:
        if pg:
            # stops two starting processes from creating tables at the same moment
            conn.execute("SELECT pg_advisory_xact_lock(424242)")

        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                id {primary_key},
                username {username_column},
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS messages (
                id {primary_key},
                role TEXT,
                content TEXT
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS notes (
                id {primary_key},
                content TEXT,
                embedding TEXT,
                subject TEXT
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS quiz_results (
                id {primary_key},
                subject TEXT,
                difficulty TEXT,
                questions TEXT,
                user_answers TEXT,
                score INTEGER,
                total INTEGER
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS login_failures (
                id {primary_key},
                key TEXT NOT NULL,
                created_at DOUBLE PRECISION NOT NULL
            )
        """)

        for table in ("messages", "notes", "quiz_results"):
            _add_user_id_column(conn, table)

        # usernames are unique ignoring capital letters, on both databases
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_lower ON users (lower(username))")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_user_subject ON notes(user_id, subject)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quiz_user ON quiz_results(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_login_failures_key ON login_failures(key, created_at)")


# ---------- users ----------

def create_user(username, password_hash):
    """Returns the new user's id, or None if that username is already taken."""
    try:
        with get_db() as conn:
            row = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?) RETURNING id",
                (username, password_hash),
            ).fetchone()
            return row[0]
    except _integrity_errors():
        return None


def get_user_by_username(username):
    """Returns (id, username, password_hash) or None."""
    with get_db() as conn:
        return conn.execute(
            "SELECT id, username, password_hash FROM users WHERE lower(username) = lower(?)",
            (username,),
        ).fetchone()


def get_user_by_id(user_id):
    """Returns (id, username) or None."""
    with get_db() as conn:
        return conn.execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def claim_unowned_data(user_id):
    """Gives all data saved before accounts existed to this user. Returns rows claimed per table."""
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
    sql = "SELECT id, content, embedding, subject FROM notes WHERE lower(subject) = lower(?)"
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


# ---------- login attempt limits ----------

def record_failed_login(key):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO login_failures (key, created_at) VALUES (?, ?)",
            (key, time.time()),
        )


def count_recent_failures(key, window_seconds):
    now = time.time()
    with get_db() as conn:
        # tidy up rows older than a day so the table doesn't grow forever
        conn.execute("DELETE FROM login_failures WHERE created_at < ?", (now - 86400,))
        return conn.execute(
            "SELECT COUNT(*) FROM login_failures WHERE key = ? AND created_at >= ?",
            (key, now - window_seconds),
        ).fetchone()[0]


def clear_failures(key):
    with get_db() as conn:
        conn.execute("DELETE FROM login_failures WHERE key = ?", (key,))