"""
database.py
-----------
Core database infrastructure for the LMPTS system.

Architecture decision (Q8): connection-per-operation
    Every get_connection() opens a new connection to the file.
    Every transaction() opens, uses, and closes a connection.

Why NO :memory: and NO shared-cache URI:
    connection-per-operation + SQLite shared memory = fragile
    connection-per-operation + file database        = reliable

Testing strategy:
    Production : data/lmpts.db
    Tests      : tmp_path/"test.db"  (pytest tmp_path fixture)
    Integration: tmp_path/"integration.db"

WAL mode:
    Only applied to file databases.
    WAL is not supported on in-memory databases.
"""

import sqlite3
import os
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 3

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "lmpts.db"
)

# ── SQL Schema ─────────────────────────────────────────────────────────────────

SQL_CREATE_SCHEMA_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER NOT NULL,
    applied_at  TEXT    NOT NULL
)
"""

SQL_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    username          TEXT    NOT NULL UNIQUE,
    password_hash     TEXT    NOT NULL,
    role              TEXT    NOT NULL,
    created_at        TEXT    NOT NULL,
    is_active         INTEGER NOT NULL DEFAULT 1,
    account_status    TEXT    NOT NULL DEFAULT 'ACTIVE',
    rejection_reason  TEXT    DEFAULT '',
    full_name         TEXT    DEFAULT '',
    email             TEXT    DEFAULT ''
)
"""

SQL_CREATE_LEARNERS = """
CREATE TABLE IF NOT EXISTS learners (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL UNIQUE,
    name     TEXT    NOT NULL,
    email    TEXT    NOT NULL UNIQUE,
    FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
)
"""

SQL_CREATE_COURSES = """
CREATE TABLE IF NOT EXISTS courses (
    code        TEXT    PRIMARY KEY,
    name        TEXT    NOT NULL,
    description TEXT    DEFAULT '',
    difficulty  TEXT    NOT NULL,
    duration    INTEGER NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'DRAFT'
)
"""

SQL_CREATE_PREREQUISITES = """
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
"""

SQL_CREATE_ENROLLMENTS = """
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
"""

SQL_CREATE_COURSE_PROGRESS = """
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
"""
# Add these SQL constants to database.py

SQL_CREATE_PRIOR_LEARNING_REQUESTS = """
CREATE TABLE IF NOT EXISTS prior_learning_requests (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id                  INTEGER NOT NULL,
    course_code                 TEXT    NOT NULL,
    pathway                     TEXT    NOT NULL,
    evidence_description        TEXT    NOT NULL,
    external_platform           TEXT    DEFAULT '',
    external_score              REAL,
    status                      TEXT    NOT NULL DEFAULT 'PENDING',
    instructor_recommendation   TEXT,
    instructor_note             TEXT,
    instructor_id               INTEGER,
    admin_note                  TEXT,
    admin_id                    INTEGER,
    submitted_at                TEXT    NOT NULL,
    reviewed_by_instructor_at   TEXT,
    decided_by_admin_at         TEXT,
    FOREIGN KEY (learner_id)
        REFERENCES learners(id) ON DELETE CASCADE,
    FOREIGN KEY (course_code)
        REFERENCES courses(code) ON DELETE CASCADE
)
"""

SQL_CREATE_COURSE_SUBMISSIONS = """
CREATE TABLE IF NOT EXISTS course_submissions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code      TEXT    NOT NULL,
    instructor_id    INTEGER NOT NULL,
    status           TEXT    NOT NULL DEFAULT 'PENDING',
    instructor_note  TEXT    DEFAULT '',
    admin_note       TEXT    DEFAULT '',
    submitted_at     TEXT    NOT NULL,
    decided_at       TEXT,
    FOREIGN KEY (course_code)
        REFERENCES courses(code) ON DELETE CASCADE
)
"""

SQL_CREATE_NOTIFICATIONS = """
CREATE TABLE IF NOT EXISTS notifications (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL,
    message           TEXT    NOT NULL,
    is_read           INTEGER NOT NULL DEFAULT 0,
    notification_type TEXT    NOT NULL DEFAULT 'INFO',
    created_at        TEXT    NOT NULL,
    FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE
)
"""

ALL_TABLE_SQLS = [
    SQL_CREATE_SCHEMA_VERSION,
    SQL_CREATE_USERS,
    SQL_CREATE_LEARNERS,
    SQL_CREATE_COURSES,
    SQL_CREATE_PREREQUISITES,
    SQL_CREATE_ENROLLMENTS,
    SQL_CREATE_COURSE_PROGRESS,
    SQL_CREATE_PRIOR_LEARNING_REQUESTS,   # NEW
    SQL_CREATE_COURSE_SUBMISSIONS,         # NEW
    SQL_CREATE_NOTIFICATIONS,              # NEW
]

ALL_TABLE_NAMES = [
    "schema_version",
    "users",
    "learners",
    "courses",
    "prerequisites",
    "enrollments",
    "course_progress",
]


class Database:
    """
    Core database infrastructure for LMPTS.

    All operations use connection-per-operation (Q8).
    No persistent connections are kept open.
    Only file-based SQLite databases are used.

    Usage:
        # Production
        db = Database()
        db = Database("data/lmpts.db")

        # Tests — use pytest tmp_path
        db = Database(str(tmp_path / "test.db"))

        db.initialize()
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_data_directory()

    def _ensure_data_directory(self) -> None:
        """
        Create the parent directory of db_path if it does not exist.
        """
        directory = os.path.dirname(os.path.abspath(self.db_path))
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")

    def get_connection(self) -> sqlite3.Connection:
        """
        Open and return a new SQLite connection.

        Settings:
            row_factory  = sqlite3.Row   → dict-like column access
            foreign_keys = ON            → enforce FK constraints
            journal_mode = WAL           → concurrent reads (file DB only)

        Caller must close the connection.
        Prefer using transaction() context manager for write operations.

        Returns:
            sqlite3.Connection: Ready-to-use connection.
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=30,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        # WAL only for file databases — not supported on :memory:
        # Since we only use file DBs, this always applies
        conn.execute("PRAGMA journal_mode = WAL")

        return conn

    @contextmanager
    def transaction(self):
        """
        Context manager for atomic database operations.

        Opens a connection, begins a transaction, yields the connection.
        Commits on success.
        Rolls back and re-raises on any exception.
        Always closes the connection.

        Usage:
            with db.transaction() as conn:
                conn.execute("INSERT INTO users ...")
            # auto-committed

            with db.transaction() as conn:
                conn.execute("INSERT ...")
                raise ValueError("oops")
            # auto-rolled back, exception re-raised
        """
        conn = self.get_connection()
        try:
            conn.execute("BEGIN")
            yield conn
            conn.execute("COMMIT")
            logger.debug("Transaction committed")
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            logger.error(f"Transaction rolled back: {e}")
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """
        Create all 7 tables and apply pending migrations.

        How it works with file databases:
            Connection A: CREATE TABLE schema_version ... COMMIT
            Connection A closes.
            Connection B: SELECT MAX(version) FROM schema_version → 0
            Migration v1 applied.
            Connection B closes.
            All subsequent connections see the complete schema.

        Safe to call multiple times — CREATE TABLE IF NOT EXISTS.
        """
        logger.info(f"Initializing database: {self.db_path}")

        # Step 1: Create all tables in one committed transaction
        with self.transaction() as conn:
            for sql in ALL_TABLE_SQLS:
                conn.execute(sql)

        # Step 2: Apply migrations
        # File is committed — new connections see schema_version table
        self._run_migrations()

        logger.info("Database initialization complete")

    def _get_current_version(self) -> int:
        """
        Read the current schema version from the database.

        Returns:
            int: Current version number, 0 if no records exist.
        """
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "SELECT MAX(version) as v FROM schema_version"
            )
            row = cursor.fetchone()
            return row["v"] if row["v"] is not None else 0
        finally:
            conn.close()

    def _run_migrations(self) -> None:
        """
        Apply pending migrations in version order.

        Each migration:
            - Runs in its own transaction
            - Records its version in schema_version on success
            - Is skipped if already applied

        To add a new migration:
            1. Add method: def _migrate_v2(self, conn)
            2. Add entry:  2: self._migrate_v2
        """
        # 4. Update MIGRATIONS dict in _run_migrations method
# Find the MIGRATIONS dict and add entry 3:
        MIGRATIONS = {
            1: self._migrate_v1,
            2: self._migrate_v2,   # ADD THIS
            3: self._migrate_v3,  

        }

        current_version = self._get_current_version()
        logger.info(f"Current schema version: {current_version}")

        for version, migration_fn in sorted(MIGRATIONS.items()):
            if version > current_version:
                logger.info(f"Applying migration v{version}...")
                with self.transaction() as conn:
                    migration_fn(conn)
                    conn.execute(
                        "INSERT INTO schema_version "
                        "(version, applied_at) VALUES (?, ?)",
                        (
                            version,
                            datetime.now(timezone.utc).isoformat(),
                        )
                    )
                logger.info(f"Migration v{version} complete")

    def _migrate_v1(self, conn: sqlite3.Connection) -> None:
        """
        Migration v1: Create performance indexes.

        These indexes speed up the most common queries:
            - Login: find user by username
            - Progress: enrollments by learner
            - Validation: enrollments by course
        """
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_username "
            "ON users(username)",

            "CREATE INDEX IF NOT EXISTS idx_enrollments_learner "
            "ON enrollments(learner_id)",

            "CREATE INDEX IF NOT EXISTS idx_enrollments_course "
            "ON enrollments(course_code)",

            "CREATE INDEX IF NOT EXISTS idx_prerequisites_course "
            "ON prerequisites(course_code)",

            "CREATE INDEX IF NOT EXISTS idx_progress_learner "
            "ON course_progress(learner_id)",
        ]
        for sql in indexes:
            conn.execute(sql)
        logger.debug("Migration v1: indexes created")
    def _migrate_v2(self, conn: sqlite3.Connection) -> None:
        """
        Migration v2: Add user activation, new tables, indexes.
        """
        # Add is_active column to users if not exists
        try:
            conn.execute(
                "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1"
            )
        except Exception:
            pass  # Column already exists

        # Indexes for new tables
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_plr_learner "
            "ON prior_learning_requests(learner_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_plr_status "
            "ON prior_learning_requests(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_status "
            "ON course_submissions(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_user "
            "ON notifications(user_id)"
        )
        logger.debug("Migration v2: user activation + new tables")
    # 3. Add _migrate_v3 method inside Database class
    def _migrate_v3(self, conn: sqlite3.Connection) -> None:
        """
        Migration v3: Add account activation columns to users table.

        Columns added:
            is_active        → 1 = active, 0 = inactive
            account_status   → ACTIVE / PENDING / REJECTED
            rejection_reason → admin's rejection reason
            full_name        → learner's full name from registration
            email            → learner's email from registration
        """
        alterations = [
            "ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE users ADD COLUMN account_status TEXT NOT NULL DEFAULT 'ACTIVE'",
            "ALTER TABLE users ADD COLUMN rejection_reason TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN full_name TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''",
        ]
        for sql in alterations:
            try:
                conn.execute(sql)
            except Exception:
                pass  # Column already exists — safe to skip

        # All existing users are ACTIVE by default
        conn.execute(
            "UPDATE users SET is_active = 1, account_status = 'ACTIVE' "
            "WHERE account_status IS NULL OR account_status = ''"
        )

        # Index for fast pending lookups
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_status "
            "ON users(account_status)"
        )
        logger.debug("Migration v3: account activation columns added")

        
    def get_schema_version(self) -> int:
        """
        Return the current schema version number.

        Returns:
            int: Version number (0 if no migrations applied).
        """
        return self._get_current_version()

    def table_exists(self, table_name: str) -> bool:
        """
        Check whether a table exists in the database.

        Args:
            table_name: Name of the table to check.

        Returns:
            bool: True if the table exists.
        """
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name=?",
                (table_name,)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def drop_all_tables(self) -> None:
        """
        Drop all tables in reverse dependency order.

        WARNING: Destroys all data permanently.
        Use only in tests or development resets.
        """
        drop_order = [
            "course_progress",
            "enrollments",
            "prerequisites",
            "courses",
            "learners",
            "users",
            "schema_version",
        ]
        with self.transaction() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            for table in drop_order:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            conn.execute("PRAGMA foreign_keys = ON")
        logger.info("All tables dropped")