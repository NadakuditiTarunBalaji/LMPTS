# create_db_standalone.py
# Run from C:\LMPTS with: python create_db_standalone.py

import os
import sqlite3
from datetime import datetime, timezone

print("Creating LMPTS database...")

# ── Paths ──────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH  = os.path.join(DATA_DIR, "lmpts.db")

print(f"Base dir : {BASE_DIR}")
print(f"Data dir : {DATA_DIR}")
print(f"DB path  : {DB_PATH}")
print()

# ── Create data folder ─────────────────────────────────────────
os.makedirs(DATA_DIR, exist_ok=True)
print(f"data/ folder: OK")

# ── Connect ────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")
conn.execute("PRAGMA journal_mode = WAL")
print(f"Connection:   OK")

# ── Create all tables ──────────────────────────────────────────
tables = {
    "schema_version": """
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER NOT NULL,
            applied_at  TEXT    NOT NULL
        )
    """,
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL,
            created_at    TEXT    NOT NULL
        )
    """,
    "learners": """
        CREATE TABLE IF NOT EXISTS learners (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER NOT NULL UNIQUE,
            name     TEXT    NOT NULL,
            email    TEXT    NOT NULL UNIQUE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """,
    "courses": """
        CREATE TABLE IF NOT EXISTS courses (
            code        TEXT    PRIMARY KEY,
            name        TEXT    NOT NULL,
            description TEXT    DEFAULT '',
            difficulty  TEXT    NOT NULL,
            duration    INTEGER NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'DRAFT'
        )
    """,
    "prerequisites": """
        CREATE TABLE IF NOT EXISTS prerequisites (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code       TEXT    NOT NULL,
            prerequisite_code TEXT    NOT NULL,
            UNIQUE (course_code, prerequisite_code),
            FOREIGN KEY (course_code)
                REFERENCES courses(code) ON DELETE CASCADE,
            FOREIGN KEY (prerequisite_code)
                REFERENCES courses(code) ON DELETE CASCADE
        )
    """,
    "enrollments": """
        CREATE TABLE IF NOT EXISTS enrollments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id   INTEGER NOT NULL,
            course_code  TEXT    NOT NULL,
            status       TEXT    NOT NULL DEFAULT 'ENROLLED',
            score        REAL,
            enrolled_at  TEXT    NOT NULL,
            completed_at TEXT,
            UNIQUE (learner_id, course_code),
            FOREIGN KEY (learner_id)
                REFERENCES learners(id) ON DELETE CASCADE,
            FOREIGN KEY (course_code)
                REFERENCES courses(code) ON DELETE CASCADE
        )
    """,
    "course_progress": """
        CREATE TABLE IF NOT EXISTS course_progress (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id        INTEGER NOT NULL,
            course_code       TEXT    NOT NULL,
            percentage        REAL    NOT NULL DEFAULT 0.0,
            completion_status TEXT    NOT NULL DEFAULT 'NOT_STARTED',
            updated_at        TEXT    NOT NULL,
            UNIQUE (learner_id, course_code),
            FOREIGN KEY (learner_id)
                REFERENCES learners(id) ON DELETE CASCADE,
            FOREIGN KEY (course_code)
                REFERENCES courses(code) ON DELETE CASCADE
        )
    """,
}

conn.execute("BEGIN")
for name, sql in tables.items():
    conn.execute(sql)
    print(f"  Table created: {name}")
conn.execute("COMMIT")

# ── Create indexes ─────────────────────────────────────────────
conn.execute("BEGIN")
indexes = [
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
    "CREATE INDEX IF NOT EXISTS idx_enrollments_learner ON enrollments(learner_id)",
    "CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_code)",
    "CREATE INDEX IF NOT EXISTS idx_prerequisites_course ON prerequisites(course_code)",
    "CREATE INDEX IF NOT EXISTS idx_progress_learner ON course_progress(learner_id)",
]
for sql in indexes:
    conn.execute(sql)
print("  Indexes created")

# ── Record schema version ──────────────────────────────────────
conn.execute(
    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
    (1, datetime.now(timezone.utc).isoformat())
)
conn.execute("COMMIT")
print("  Schema version: 1")

conn.close()

# ── Verify ─────────────────────────────────────────────────────
print()
print("Verifying...")
conn2 = sqlite3.connect(DB_PATH)
conn2.row_factory = sqlite3.Row
cursor = conn2.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
)
created_tables = [row["name"] for row in cursor.fetchall()]

cursor2 = conn2.execute("SELECT MAX(version) as v FROM schema_version")
version = cursor2.fetchone()["v"]
conn2.close()

print(f"  File size     : {os.path.getsize(DB_PATH):,} bytes")
print(f"  Schema version: {version}")
print(f"  Tables ({len(created_tables)}):")
for t in created_tables:
    print(f"    ✓ {t}")

print()
print("=" * 60)
print(f"Database ready at: {DB_PATH}")
print("=" * 60)