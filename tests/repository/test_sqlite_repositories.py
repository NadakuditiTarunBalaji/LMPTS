"""
test_sqlite_repositories.py
----------------------------
Comprehensive tests for all Person 2 repository implementations.

Test Strategy (Q11):
    Unit Tests      → Use SQLite :memory: database (fast, no file cleanup)
    Integration Tests → Use real temporary file database

Test Coverage:
    TestDatabase                 → database.py
    TestSQLiteUserRepository     → user_repo.py
    TestSQLiteCourseRepository   → course_repo.py
    TestSQLiteLearnerRepository  → learner_repo.py
    TestSQLiteEnrollmentRepository → enrollment_repo.py
    TestSQLiteProgressRepository → enrollment_repo.py (progress section)
    TestIntegration              → Full workflow with file database

Run:
    python -m pytest tests/repository/test_sqlite_repositories.py -v

Run integration tests only:
    python -m pytest tests/repository/ -v -k "Integration"

Run unit tests only:
    python -m pytest tests/repository/ -v -k "not Integration"
"""

import os
import pytest
import tempfile
from datetime import datetime, timezone

from core.user import User
from core.course import Course
from core.learner import Learner
from core.enrollment import Enrollment
from core.course_progress import CourseProgress
from core.enums import (
    UserRole, DifficultyLevel, CourseStatus,
    EnrollmentStatus, CompletionStatus,
)
from core.exceptions import (
    ValidationError, LearnerNotFoundError,
    CourseNotFoundError, DuplicateEnrollmentError,
)
from auth.password_manager import PasswordManager

from repository.database import Database
from repository.user_repo import SQLiteUserRepository
from repository.course_repo import SQLiteCourseRepository
from repository.learner_repo import SQLiteLearnerRepository
from repository.enrollment_repo import (
    SQLiteEnrollmentRepository,
    SQLiteProgressRepository,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def db(tmp_path):
    """
    Fresh temporary file database for each test.

    pytest tmp_path gives a unique directory per test function.
    The entire directory including the database file is automatically
    deleted after each test completes.

    Why not :memory:?
        connection-per-operation + SQLite :memory: = database disappears
        connection-per-operation + file database   = works correctly

    Why not a shared file?
        Each test must start with a clean empty database.
        tmp_path guarantees isolation between every test.
    """
    db_path = str(tmp_path / "test_lmpts.db")
    database = Database(db_path)
    database.initialize()
    return database


@pytest.fixture
def user_repo(db):
    """SQLiteUserRepository backed by in-memory database."""
    return SQLiteUserRepository(db)


@pytest.fixture
def course_repo(db):
    """SQLiteCourseRepository backed by in-memory database."""
    return SQLiteCourseRepository(db)


@pytest.fixture
def learner_repo(db):
    """SQLiteLearnerRepository backed by in-memory database."""
    return SQLiteLearnerRepository(db)


@pytest.fixture
def enrollment_repo(db):
    """SQLiteEnrollmentRepository backed by in-memory database."""
    return SQLiteEnrollmentRepository(db)


@pytest.fixture
def progress_repo(db):
    """SQLiteProgressRepository backed by in-memory database."""
    return SQLiteProgressRepository(db)


@pytest.fixture
def pm():
    """PasswordManager for hashing test passwords."""
    return PasswordManager()


@pytest.fixture
def sample_user(pm):
    """A valid unsaved User object."""
    return User(
        username="testuser",
        password_hash=pm.hash_password("password123"),
        role=UserRole.LEARNER,
    )


@pytest.fixture
def saved_user(user_repo, sample_user):
    """A User already saved to the database."""
    return user_repo.create_user(sample_user)


@pytest.fixture
def sample_course():
    """A valid unsaved Course object."""
    return Course(
        code="CS101",
        name="Intro to Programming",
        difficulty=DifficultyLevel.BEGINNER,
        duration=30,
        status=CourseStatus.PUBLISHED,
    )


@pytest.fixture
def saved_course(course_repo, sample_course):
    """A Course already saved to the database."""
    return course_repo.create_course(sample_course)


@pytest.fixture
def sample_learner(saved_user):
    """A valid unsaved Learner linked to saved_user."""
    return Learner(
        name="Alice Smith",
        email="alice@example.com",
        user_id=saved_user.id,
    )


@pytest.fixture
def saved_learner(learner_repo, sample_learner):
    """A Learner already saved to the database."""
    return learner_repo.create_learner(sample_learner)


@pytest.fixture
def sample_enrollment(saved_learner, saved_course):
    """A valid unsaved Enrollment."""
    return Enrollment(
        learner_id=saved_learner.id,
        course_code=saved_course.code,
    )


@pytest.fixture
def saved_enrollment(enrollment_repo, sample_enrollment):
    """An Enrollment already saved to the database."""
    return enrollment_repo.create_enrollment(sample_enrollment)


# ═══════════════════════════════════════════════════════════════════════════════
# TestDatabase
# ═══════════════════════════════════════════════════════════════════════════════

class TestDatabase:
    """Verify database.py infrastructure."""

    def test_initialize_creates_all_tables(self, db):
        """All 6 ER diagram tables must be created."""
        expected_tables = [
            "users",
            "learners",
            "courses",
            "prerequisites",
            "enrollments",
            "course_progress",
            "schema_version",
        ]
        for table in expected_tables:
            assert db.table_exists(table), (
                f"Table '{table}' was not created"
            )

    def test_schema_version_recorded(self, db):
        """Migration v1 must be recorded in schema_version."""
        version = db.get_schema_version()
        assert version == 1

    def test_initialize_idempotent(self, db):
        """Calling initialize() twice must not raise."""
        db.initialize()
        db.initialize()
        assert db.get_schema_version() == 1

    def test_get_connection_returns_connection(self, db):
        """get_connection() must return a usable SQLite connection."""
        import sqlite3
        conn = db.get_connection()
        try:
            assert isinstance(conn, sqlite3.Connection)
            cursor = conn.execute("SELECT 1 as val")
            row = cursor.fetchone()
            assert row["val"] == 1
        finally:
            conn.close()

    def test_transaction_commits_on_success(self, db):
        """Data written inside transaction() must be persisted."""
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO users "
                "(username, password_hash, role, created_at) "
                "VALUES ('txuser', 'hash', 'LEARNER', '2024-01-01')"
            )

        # Verify data persisted in a new connection
        conn2 = db.get_connection()
        try:
            cursor = conn2.execute(
                "SELECT username FROM users WHERE username = 'txuser'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn2.close()

    def test_transaction_rolls_back_on_error(self, db):
        """Data written inside a failed transaction must be rolled back."""
        try:
            with db.transaction() as conn:
                conn.execute(
                    "INSERT INTO users "
                    "(username, password_hash, role, created_at) "
                    "VALUES ('rollback_user', 'hash', 'LEARNER', '2024-01-01')"
                )
                raise RuntimeError("Simulated failure")
        except RuntimeError:
            pass

        # Verify data was NOT persisted
        conn2 = db.get_connection()
        try:
            cursor = conn2.execute(
                "SELECT username FROM users "
                "WHERE username = 'rollback_user'"
            )
            assert cursor.fetchone() is None
        finally:
            conn2.close()

    def test_foreign_keys_enabled(self, db):
        """FK constraints must be enforced."""
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            with db.transaction() as conn:
                # learner references non-existent user_id
                conn.execute(
                    "INSERT INTO learners (user_id, name, email) "
                    "VALUES (99999, 'Test', 'test@test.com')"
                )

    def test_drop_all_tables(self, db):
        """drop_all_tables() must remove every table."""
        db.drop_all_tables()
        assert not db.table_exists("users")
        assert not db.table_exists("courses")
        assert not db.table_exists("enrollments")

    def test_database_file_created_on_disk(self, tmp_path):
        """Database file must exist on disk after initialize()."""
        db_path = str(tmp_path / "verify.db")
        assert not os.path.exists(db_path)

        db = Database(db_path)
        db.initialize()

        assert os.path.exists(db_path)
        assert os.path.getsize(db_path) > 0
        assert db.get_schema_version() == 1

    def test_default_db_path_in_data_folder(self):
        """Default database path must be inside data/ directory."""
        from repository.database import DEFAULT_DB_PATH
        assert "data" in DEFAULT_DB_PATH
        assert DEFAULT_DB_PATH.endswith("lmpts.db")


# ═══════════════════════════════════════════════════════════════════════════════
# TestSQLiteUserRepository
# ═══════════════════════════════════════════════════════════════════════════════

class TestSQLiteUserRepository:
    """Verify user_repo.py SQLite implementation."""

    def test_create_user(self, user_repo, sample_user):
        """create_user() must assign an integer id."""
        saved = user_repo.create_user(sample_user)
        assert saved.id is not None
        assert isinstance(saved.id, int)
        assert saved.username == "testuser"

    def test_create_user_assigns_incrementing_ids(self, user_repo, pm):
        u1 = user_repo.create_user(
            User("user1", pm.hash_password("pass1111"), UserRole.LEARNER)
        )
        u2 = user_repo.create_user(
            User("user2", pm.hash_password("pass2222"), UserRole.ADMIN)
        )
        assert u2.id > u1.id

    def test_create_duplicate_username_raises(self, user_repo, pm):
        user_repo.create_user(
            User("alice", pm.hash_password("pass1234"), UserRole.LEARNER)
        )
        with pytest.raises(ValidationError, match="already exists"):
            user_repo.create_user(
                User("alice", pm.hash_password("pass5678"), UserRole.ADMIN)
            )

    def test_get_user_found(self, user_repo, saved_user):
        found = user_repo.get_user(saved_user.id)
        assert found is not None
        assert found.username == "testuser"
        assert found.role == UserRole.LEARNER

    def test_get_user_not_found(self, user_repo):
        assert user_repo.get_user(99999) is None

    def test_find_by_username_found(self, user_repo, saved_user):
        found = user_repo.find_by_username("testuser")
        assert found is not None
        assert found.id == saved_user.id

    def test_find_by_username_not_found(self, user_repo):
        assert user_repo.find_by_username("nobody") is None

    def test_get_all_users_empty(self, user_repo):
        assert user_repo.get_all_users() == []

    def test_get_all_users(self, user_repo, pm):
        user_repo.create_user(
            User("a", pm.hash_password("pass1234"), UserRole.ADMIN)
        )
        user_repo.create_user(
            User("b", pm.hash_password("pass5678"), UserRole.LEARNER)
        )
        users = user_repo.get_all_users()
        assert len(users) == 2

    def test_find_by_role(self, user_repo, pm):
        user_repo.create_user(
            User("admin1", pm.hash_password("pass1234"), UserRole.ADMIN)
        )
        user_repo.create_user(
            User("learner1", pm.hash_password("pass5678"), UserRole.LEARNER)
        )
        admins = user_repo.find_by_role(UserRole.ADMIN)
        assert len(admins) == 1
        assert admins[0].username == "admin1"

    def test_username_exists_true(self, user_repo, saved_user):
        assert user_repo.username_exists("testuser") is True

    def test_username_exists_false(self, user_repo):
        assert user_repo.username_exists("nobody") is False

    def test_count(self, user_repo, pm):
        assert user_repo.count() == 0
        user_repo.create_user(
            User("x", pm.hash_password("pass1234"), UserRole.LEARNER)
        )
        assert user_repo.count() == 1

    def test_update_password(self, user_repo, saved_user, pm):
        new_hash = pm.hash_password("newpassword!")
        user_repo.update_password(saved_user.id, new_hash)
        updated = user_repo.get_user(saved_user.id)
        assert updated.password_hash == new_hash

    def test_update_password_not_found(self, user_repo):
        with pytest.raises(LearnerNotFoundError):
            user_repo.update_password(99999, "newhash")

    def test_delete_user(self, user_repo, saved_user):
        user_repo.delete_user(saved_user.id)
        assert user_repo.get_user(saved_user.id) is None

    def test_delete_user_not_found(self, user_repo):
        with pytest.raises(LearnerNotFoundError):
            user_repo.delete_user(99999)

    def test_password_hash_stored_correctly(self, user_repo, saved_user, pm):
        """Password hash in DB must verify against original password."""
        found = user_repo.find_by_username("testuser")
        assert pm.verify_password("password123", found.password_hash)

    def test_role_stored_as_string_retrieved_as_enum(
        self, user_repo, saved_user
    ):
        """Role must come back as UserRole enum, not raw string."""
        found = user_repo.get_user(saved_user.id)
        assert isinstance(found.role, UserRole)
        assert found.role == UserRole.LEARNER


# ═══════════════════════════════════════════════════════════════════════════════
# TestSQLiteCourseRepository
# ═══════════════════════════════════════════════════════════════════════════════

class TestSQLiteCourseRepository:
    """Verify course_repo.py SQLite implementation."""

    def test_create_course(self, course_repo, sample_course):
        saved = course_repo.create_course(sample_course)
        assert saved.code == "CS101"

    def test_create_course_duplicate_raises(self, course_repo, saved_course):
        duplicate = Course(
            "CS101", "Duplicate", DifficultyLevel.BEGINNER, 10
        )
        with pytest.raises(ValidationError, match="already exists"):
            course_repo.create_course(duplicate)

    def test_get_course_found(self, course_repo, saved_course):
        found = course_repo.get_course("CS101")
        assert found is not None
        assert found.code == "CS101"
        assert found.name == "Intro to Programming"

    def test_get_course_not_found(self, course_repo):
        assert course_repo.get_course("UNKNOWN") is None

    def test_get_all_courses_empty(self, course_repo):
        assert course_repo.get_all_courses() == []

    def test_get_all_courses(self, course_repo):
        course_repo.create_course(
            Course("CS101", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.create_course(
            Course("CS201", "B", DifficultyLevel.INTERMEDIATE, 20,
                   status=CourseStatus.PUBLISHED)
        )
        courses = course_repo.get_all_courses()
        assert len(courses) == 2

    def test_difficulty_stored_and_retrieved(self, course_repo, saved_course):
        found = course_repo.get_course("CS101")
        assert isinstance(found.difficulty, DifficultyLevel)
        assert found.difficulty == DifficultyLevel.BEGINNER

    def test_status_stored_and_retrieved(self, course_repo, saved_course):
        found = course_repo.get_course("CS101")
        assert isinstance(found.status, CourseStatus)
        assert found.status == CourseStatus.PUBLISHED

    def test_duration_is_int(self, course_repo, saved_course):
        found = course_repo.get_course("CS101")
        assert isinstance(found.duration, int)
        assert found.duration == 30

    def test_prerequisites_is_set(self, course_repo, saved_course):
        found = course_repo.get_course("CS101")
        assert isinstance(found.prerequisites, set)

    # ── Prerequisites (Junction Table) ────────────────────────────────────────

    def test_create_course_with_prerequisites(self, course_repo):
        """Prerequisites must be stored in junction table on creation."""
        prereq = Course(
            "CS100", "Pre-Course", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        )
        course_repo.create_course(prereq)

        main = Course(
            "CS101", "Main Course", DifficultyLevel.BEGINNER, 20,
            status=CourseStatus.PUBLISHED,
            prerequisites={"CS100"}
        )
        course_repo.create_course(main)

        found = course_repo.get_course("CS101")
        assert "CS100" in found.prerequisites
        assert isinstance(found.prerequisites, set)

    def test_add_prerequisite(self, course_repo):
        """add_prerequisite() must insert into junction table."""
        course_repo.create_course(
            Course("CS100", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.create_course(
            Course("CS101", "B", DifficultyLevel.BEGINNER, 20,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.add_prerequisite("CS101", "CS100")

        found = course_repo.get_course("CS101")
        assert "CS100" in found.prerequisites

    def test_add_prerequisite_course_not_found(self, course_repo):
        with pytest.raises(CourseNotFoundError):
            course_repo.add_prerequisite("UNKNOWN", "CS100")

    def test_add_prerequisite_prereq_not_found(self, course_repo):
        course_repo.create_course(
            Course("CS101", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        with pytest.raises(CourseNotFoundError):
            course_repo.add_prerequisite("CS101", "UNKNOWN")

    def test_add_prerequisite_idempotent(self, course_repo):
        """Adding same prerequisite twice must not raise or duplicate."""
        course_repo.create_course(
            Course("CS100", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.create_course(
            Course("CS101", "B", DifficultyLevel.BEGINNER, 20,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.add_prerequisite("CS101", "CS100")
        course_repo.add_prerequisite("CS101", "CS100")  # second call: safe

        prereqs = course_repo.get_prerequisites("CS101")
        assert len(prereqs) == 1

    def test_remove_prerequisite(self, course_repo):
        course_repo.create_course(
            Course("CS100", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.create_course(
            Course("CS101", "B", DifficultyLevel.BEGINNER, 20,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.add_prerequisite("CS101", "CS100")
        course_repo.remove_prerequisite("CS101", "CS100")

        prereqs = course_repo.get_prerequisites("CS101")
        assert "CS100" not in prereqs

    def test_remove_prerequisite_safe_if_not_exists(self, course_repo):
        """remove_prerequisite on non-existent relationship must not raise."""
        course_repo.create_course(
            Course("CS101", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.remove_prerequisite("CS101", "NONEXISTENT")  # no error

    def test_get_prerequisites_returns_set(self, course_repo):
        course_repo.create_course(
            Course("CS100", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.create_course(
            Course("CS101", "B", DifficultyLevel.BEGINNER, 20,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.add_prerequisite("CS101", "CS100")
        prereqs = course_repo.get_prerequisites("CS101")
        assert isinstance(prereqs, set)
        assert "CS100" in prereqs

    def test_get_prerequisites_empty(self, course_repo, saved_course):
        prereqs = course_repo.get_prerequisites("CS101")
        assert prereqs == set()

    # ── Filters ───────────────────────────────────────────────────────────────

    def test_find_by_status(self, course_repo):
        course_repo.create_course(
            Course("CS101", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.create_course(
            Course("CS102", "B", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.DRAFT)
        )
        published = course_repo.find_by_status(CourseStatus.PUBLISHED)
        assert len(published) == 1
        assert published[0].code == "CS101"

    def test_find_by_difficulty(self, course_repo):
        course_repo.create_course(
            Course("CS101", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.create_course(
            Course("CS201", "B", DifficultyLevel.ADVANCED, 30,
                   status=CourseStatus.PUBLISHED)
        )
        beginners = course_repo.find_by_difficulty(DifficultyLevel.BEGINNER)
        assert len(beginners) == 1
        assert beginners[0].code == "CS101"

    def test_course_exists_true(self, course_repo, saved_course):
        assert course_repo.course_exists("CS101") is True

    def test_course_exists_false(self, course_repo):
        assert course_repo.course_exists("UNKNOWN") is False

    def test_count(self, course_repo):
        assert course_repo.count() == 0
        course_repo.create_course(
            Course("CS101", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        assert course_repo.count() == 1

    # ── Update ────────────────────────────────────────────────────────────────

    def test_update_course(self, course_repo, saved_course):
        saved_course.name = "Updated Name"
        saved_course.duration = 60
        saved_course.status = CourseStatus.ARCHIVED
        course_repo.update_course(saved_course)

        updated = course_repo.get_course("CS101")
        assert updated.name == "Updated Name"
        assert updated.duration == 60
        assert updated.status == CourseStatus.ARCHIVED

    def test_update_course_not_found(self, course_repo):
        fake = Course("UNKNOWN", "A", DifficultyLevel.BEGINNER, 10,
                      status=CourseStatus.DRAFT)
        with pytest.raises(CourseNotFoundError):
            course_repo.update_course(fake)

    def test_update_course_replaces_prerequisites(self, course_repo):
        """Updating prerequisites must replace old ones."""
        course_repo.create_course(
            Course("CS100", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.create_course(
            Course("CS101", "B", DifficultyLevel.BEGINNER, 20,
                   status=CourseStatus.PUBLISHED,
                   prerequisites={"CS100"})
        )
        course_repo.create_course(
            Course("CS102", "C", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )

        # Update to use CS102 instead of CS100
        cs101 = course_repo.get_course("CS101")
        cs101.prerequisites = {"CS102"}
        course_repo.update_course(cs101)

        updated = course_repo.get_course("CS101")
        assert "CS102" in updated.prerequisites
        assert "CS100" not in updated.prerequisites

    # ── Delete ────────────────────────────────────────────────────────────────

    def test_delete_course(self, course_repo, saved_course):
        course_repo.delete_course("CS101")
        assert course_repo.get_course("CS101") is None

    def test_delete_course_not_found(self, course_repo):
        with pytest.raises(CourseNotFoundError):
            course_repo.delete_course("UNKNOWN")

    def test_delete_course_cascades_prerequisites(self, course_repo):
        """Deleting a course must remove its prerequisite rows."""
        course_repo.create_course(
            Course("CS100", "A", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )
        course_repo.create_course(
            Course("CS101", "B", DifficultyLevel.BEGINNER, 20,
                   status=CourseStatus.PUBLISHED,
                   prerequisites={"CS100"})
        )
        course_repo.delete_course("CS101")

        # Prerequisites for CS101 should be gone
        conn = course_repo._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) as c FROM prerequisites "
                "WHERE course_code = 'CS101'"
            )
            assert cursor.fetchone()["c"] == 0
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# TestSQLiteLearnerRepository
# ═══════════════════════════════════════════════════════════════════════════════

class TestSQLiteLearnerRepository:
    """Verify learner_repo.py SQLite implementation."""

    def test_create_learner(self, learner_repo, sample_learner):
        saved = learner_repo.create_learner(sample_learner)
        assert saved.id is not None
        assert saved.name == "Alice Smith"

    def test_create_learner_duplicate_email_raises(
        self, learner_repo, saved_learner, pm, user_repo
    ):
        # Create second user to link to
        user2 = user_repo.create_user(
            User("user2", pm.hash_password("pass1234"), UserRole.LEARNER)
        )
        duplicate = Learner(
            name="Another Alice",
            email="alice@example.com",   # same email
            user_id=user2.id,
        )
        with pytest.raises(ValidationError, match="already registered"):
            learner_repo.create_learner(duplicate)

    def test_get_learner_found(self, learner_repo, saved_learner):
        found = learner_repo.get_learner(saved_learner.id)
        assert found is not None
        assert found.name == "Alice Smith"
        assert found.email == "alice@example.com"

    def test_get_learner_not_found(self, learner_repo):
        assert learner_repo.get_learner(99999) is None

    def test_get_learner_by_user_id(self, learner_repo, saved_learner):
        found = learner_repo.get_learner_by_user_id(saved_learner.user_id)
        assert found is not None
        assert found.id == saved_learner.id

    def test_get_all_learners_empty(self, learner_repo):
        assert learner_repo.get_all_learners() == []

    def test_get_all_learners(
        self, learner_repo, saved_learner
    ):
        learners = learner_repo.get_all_learners()
        assert len(learners) == 1

    def test_find_by_email_found(self, learner_repo, saved_learner):
        found = learner_repo.find_by_email("alice@example.com")
        assert found is not None

    def test_find_by_email_not_found(self, learner_repo):
        assert learner_repo.find_by_email("nobody@x.com") is None

    def test_email_exists_true(self, learner_repo, saved_learner):
        assert learner_repo.email_exists("alice@example.com") is True

    def test_email_exists_false(self, learner_repo):
        assert learner_repo.email_exists("nobody@x.com") is False

    def test_count(self, learner_repo, saved_learner):
        assert learner_repo.count() == 1

    def test_completed_courses_empty_initially(
        self, learner_repo, saved_learner
    ):
        """No enrollments yet → completed_courses must be empty set."""
        found = learner_repo.get_learner(saved_learner.id)
        assert found.completed_courses == set()

    def test_current_courses_empty_initially(
        self, learner_repo, saved_learner
    ):
        """No enrollments yet → current_courses must be empty set."""
        found = learner_repo.get_learner(saved_learner.id)
        assert found.current_courses == set()

    def test_courses_derived_from_enrollments(
        self,
        learner_repo, saved_learner,
        enrollment_repo, saved_course, db
    ):
        """
        completed/current courses must reflect actual enrollment status.
        """
        # Create enrollment and mark as IN_PROGRESS
        enrollment = Enrollment(
            learner_id=saved_learner.id,
            course_code=saved_course.code,
        )
        saved_e = enrollment_repo.create_enrollment(enrollment)
        saved_e.start()
        enrollment_repo.update_enrollment(saved_e)

        learner = learner_repo.get_learner(saved_learner.id)
        assert saved_course.code in learner.current_courses
        assert saved_course.code not in learner.completed_courses

    def test_completed_course_after_completion(
        self,
        learner_repo, saved_learner,
        enrollment_repo, saved_course
    ):
        """After completing enrollment, course moves to completed."""
        enrollment = Enrollment(
            learner_id=saved_learner.id,
            course_code=saved_course.code,
        )
        saved_e = enrollment_repo.create_enrollment(enrollment)
        saved_e.complete(90)
        enrollment_repo.update_enrollment(saved_e)

        learner = learner_repo.get_learner(saved_learner.id)
        assert saved_course.code in learner.completed_courses
        assert saved_course.code not in learner.current_courses

    def test_update_learner(self, learner_repo, saved_learner):
        saved_learner.name = "Alice Updated"
        saved_learner.email = "alice_updated@example.com"
        learner_repo.update_learner(saved_learner)

        updated = learner_repo.get_learner(saved_learner.id)
        assert updated.name == "Alice Updated"
        assert updated.email == "alice_updated@example.com"

    def test_update_learner_not_found(self, learner_repo):
        fake = Learner(name="X", email="x@x.com", id=99999)
        with pytest.raises(LearnerNotFoundError):
            learner_repo.update_learner(fake)

    def test_delete_learner(self, learner_repo, saved_learner):
        learner_repo.delete_learner(saved_learner.id)
        assert learner_repo.get_learner(saved_learner.id) is None

    def test_delete_learner_not_found(self, learner_repo):
        with pytest.raises(LearnerNotFoundError):
            learner_repo.delete_learner(99999)

    def test_returned_courses_are_sets(self, learner_repo, saved_learner):
        """UML requires sets, not lists."""
        found = learner_repo.get_learner(saved_learner.id)
        assert isinstance(found.completed_courses, set)
        assert isinstance(found.current_courses, set)


# ═══════════════════════════════════════════════════════════════════════════════
# TestSQLiteEnrollmentRepository
# ═══════════════════════════════════════════════════════════════════════════════

class TestSQLiteEnrollmentRepository:
    """Verify enrollment_repo.py SQLite implementation."""

    def test_create_enrollment(
        self, enrollment_repo, sample_enrollment
    ):
        saved = enrollment_repo.create_enrollment(sample_enrollment)
        assert saved.id is not None
        assert saved.status == EnrollmentStatus.ENROLLED

    def test_create_duplicate_enrollment_raises(
        self, enrollment_repo, saved_enrollment,
        saved_learner, saved_course
    ):
        duplicate = Enrollment(
            learner_id=saved_learner.id,
            course_code=saved_course.code,
        )
        with pytest.raises(DuplicateEnrollmentError):
            enrollment_repo.create_enrollment(duplicate)

    def test_get_enrollment_found(
        self, enrollment_repo, saved_enrollment
    ):
        found = enrollment_repo.get_enrollment(saved_enrollment.id)
        assert found is not None
        assert found.status == EnrollmentStatus.ENROLLED

    def test_get_enrollment_not_found(self, enrollment_repo):
        assert enrollment_repo.get_enrollment(99999) is None

    def test_get_enrollment_by_learner_course(
        self,
        enrollment_repo, saved_enrollment,
        saved_learner, saved_course
    ):
        found = enrollment_repo.get_enrollment_by_learner_course(
            saved_learner.id,
            saved_course.code,
        )
        assert found is not None
        assert found.id == saved_enrollment.id

    def test_get_enrollment_by_learner_course_not_found(
        self, enrollment_repo
    ):
        assert enrollment_repo.get_enrollment_by_learner_course(
            99999, "UNKNOWN"
        ) is None

    def test_get_enrollments_by_learner(
        self, enrollment_repo, saved_enrollment, saved_learner
    ):
        enrollments = enrollment_repo.get_enrollments_by_learner(
            saved_learner.id
        )
        assert len(enrollments) == 1

    def test_get_enrollments_by_course(
        self, enrollment_repo, saved_enrollment, saved_course
    ):
        enrollments = enrollment_repo.get_enrollments_by_course(
            saved_course.code
        )
        assert len(enrollments) == 1

    # ── State Transitions via Repository ──────────────────────────────────────

    def test_update_enrollment_to_in_progress(
        self, enrollment_repo, saved_enrollment
    ):
        saved_enrollment.start()
        enrollment_repo.update_enrollment(saved_enrollment)

        updated = enrollment_repo.get_enrollment(saved_enrollment.id)
        assert updated.status == EnrollmentStatus.IN_PROGRESS

    def test_update_enrollment_to_completed(
        self, enrollment_repo, saved_enrollment
    ):
        saved_enrollment.complete(88)
        enrollment_repo.update_enrollment(saved_enrollment)

        updated = enrollment_repo.get_enrollment(saved_enrollment.id)
        assert updated.status == EnrollmentStatus.COMPLETED
        assert updated.score == 88
        assert updated.completed_at is not None

    def test_update_enrollment_to_cancelled(
        self, enrollment_repo, saved_enrollment
    ):
        saved_enrollment.cancel()
        enrollment_repo.update_enrollment(saved_enrollment)

        updated = enrollment_repo.get_enrollment(saved_enrollment.id)
        assert updated.status == EnrollmentStatus.CANCELLED

    def test_update_enrollment_not_found(self, enrollment_repo):
        fake = Enrollment(learner_id=1, course_code="CS101", id=99999)
        with pytest.raises(LearnerNotFoundError):
            enrollment_repo.update_enrollment(fake)

    def test_delete_enrollment(
        self, enrollment_repo, saved_enrollment
    ):
        enrollment_repo.delete_enrollment(saved_enrollment.id)
        assert enrollment_repo.get_enrollment(saved_enrollment.id) is None

    def test_delete_enrollment_not_found(self, enrollment_repo):
        with pytest.raises(LearnerNotFoundError):
            enrollment_repo.delete_enrollment(99999)

    # ── Derived Course Lists (Q3) ──────────────────────────────────────────────

    def test_get_completed_course_codes_empty(
        self, enrollment_repo, saved_learner
    ):
        codes = enrollment_repo.get_completed_course_codes(saved_learner.id)
        assert codes == []

    def test_get_completed_course_codes(
        self, enrollment_repo, saved_enrollment, saved_learner
    ):
        saved_enrollment.complete(90)
        enrollment_repo.update_enrollment(saved_enrollment)
        codes = enrollment_repo.get_completed_course_codes(saved_learner.id)
        assert "CS101" in codes

    def test_get_active_course_codes_enrolled(
        self, enrollment_repo, saved_enrollment, saved_learner
    ):
        """ENROLLED status counts as active."""
        codes = enrollment_repo.get_active_course_codes(saved_learner.id)
        assert "CS101" in codes

    def test_get_active_course_codes_in_progress(
        self, enrollment_repo, saved_enrollment, saved_learner
    ):
        """IN_PROGRESS status counts as active."""
        saved_enrollment.start()
        enrollment_repo.update_enrollment(saved_enrollment)
        codes = enrollment_repo.get_active_course_codes(saved_learner.id)
        assert "CS101" in codes

    def test_get_active_course_codes_not_completed(
        self, enrollment_repo, saved_enrollment, saved_learner
    ):
        """COMPLETED does not count as active."""
        saved_enrollment.complete(85)
        enrollment_repo.update_enrollment(saved_enrollment)
        codes = enrollment_repo.get_active_course_codes(saved_learner.id)
        assert "CS101" not in codes

    def test_count_by_learner(
        self, enrollment_repo, saved_enrollment, saved_learner
    ):
        assert enrollment_repo.count_by_learner(saved_learner.id) == 1

    def test_count_by_course(
        self, enrollment_repo, saved_enrollment, saved_course
    ):
        assert enrollment_repo.count_by_course(saved_course.code) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestSQLiteProgressRepository
# ═══════════════════════════════════════════════════════════════════════════════

class TestSQLiteProgressRepository:
    """Verify SQLiteProgressRepository implementation."""

    def test_create_progress(
        self, progress_repo, saved_learner, saved_course
    ):
        progress = CourseProgress(
            learner_id=saved_learner.id,
            course_code=saved_course.code,
        )
        saved = progress_repo.create_progress(progress)
        assert saved.id is not None
        assert saved.percentage == 0.0
        assert saved.completion_status == CompletionStatus.NOT_STARTED

    def test_get_progress_found(
        self, progress_repo, saved_learner, saved_course
    ):
        progress = CourseProgress(
            learner_id=saved_learner.id,
            course_code=saved_course.code,
            percentage=50.0,
            completion_status=CompletionStatus.IN_PROGRESS,
        )
        progress_repo.create_progress(progress)

        found = progress_repo.get_progress(
            saved_learner.id, saved_course.code
        )
        assert found is not None
        assert found.percentage == 50.0
        assert found.completion_status == CompletionStatus.IN_PROGRESS

    def test_get_progress_not_found(
        self, progress_repo
    ):
        assert progress_repo.get_progress(99999, "UNKNOWN") is None

    def test_get_all_progress_by_learner(
        self, progress_repo, saved_learner, saved_course
    ):
        progress = CourseProgress(
            learner_id=saved_learner.id,
            course_code=saved_course.code,
        )
        progress_repo.create_progress(progress)
        all_progress = progress_repo.get_all_progress_by_learner(
            saved_learner.id
        )
        assert len(all_progress) == 1

    def test_update_progress(
        self, progress_repo, saved_learner, saved_course
    ):
        progress = CourseProgress(
            learner_id=saved_learner.id,
            course_code=saved_course.code,
        )
        progress_repo.create_progress(progress)

        progress.update_progress(75.0)
        progress_repo.update_progress(progress)

        updated = progress_repo.get_progress(
            saved_learner.id, saved_course.code
        )
        assert updated.percentage == 75.0
        assert updated.completion_status == CompletionStatus.IN_PROGRESS

    def test_delete_progress(
        self, progress_repo, saved_learner, saved_course
    ):
        progress = CourseProgress(
            learner_id=saved_learner.id,
            course_code=saved_course.code,
        )
        progress_repo.create_progress(progress)
        progress_repo.delete_progress(
            saved_learner.id, saved_course.code
        )
        assert progress_repo.get_progress(
            saved_learner.id, saved_course.code
        ) is None

    def test_completion_status_stored_as_enum(
        self, progress_repo, saved_learner, saved_course
    ):
        """completion_status must come back as CompletionStatus enum."""
        progress = CourseProgress(
            learner_id=saved_learner.id,
            course_code=saved_course.code,
            completion_status=CompletionStatus.IN_PROGRESS,
            percentage=50.0,
        )
        progress_repo.create_progress(progress)
        found = progress_repo.get_progress(
            saved_learner.id, saved_course.code
        )
        assert isinstance(found.completion_status, CompletionStatus)


# ═══════════════════════════════════════════════════════════════════════════════
# TestIntegration — File-based database (Q11)
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """
    Integration tests using a real temporary SQLite file.

    These tests verify that data actually persists to disk
    and can be read back in a new connection.
    """

    @pytest.fixture
    def file_db(self, tmp_path):
        """Real file-based database in a temp directory."""
        db_path = str(tmp_path / "test_lmpts.db")
        database = Database(db_path)
        database.initialize()
        return database

    def test_data_persists_to_disk(self, file_db, pm):
        """Data written must survive closing and reopening."""
        repo = SQLiteUserRepository(file_db)

        user = User("alice", pm.hash_password("pass1234"), UserRole.LEARNER)
        saved = repo.create_user(user)

        # Open a brand new repository pointing to same file
        repo2 = SQLiteUserRepository(file_db)
        found = repo2.find_by_username("alice")

        assert found is not None
        assert found.id == saved.id
        assert found.username == "alice"

    def test_full_workflow(self, file_db, pm):
        """
        Complete end-to-end workflow:
            User → Learner → Course → Enrollment → Progress
        """
        user_repo     = SQLiteUserRepository(file_db)
        course_repo   = SQLiteCourseRepository(file_db)
        learner_repo  = SQLiteLearnerRepository(file_db)
        enroll_repo   = SQLiteEnrollmentRepository(file_db)
        progress_repo = SQLiteProgressRepository(file_db)

        # 1. Create user
        user = user_repo.create_user(
            User("bob", pm.hash_password("pass1234"), UserRole.LEARNER)
        )
        assert user.id is not None

        # 2. Create learner profile
        learner = learner_repo.create_learner(
            Learner(name="Bob Jones", email="bob@test.com", user_id=user.id)
        )
        assert learner.id is not None

        # 3. Create prerequisite course
        course_repo.create_course(
            Course("CS100", "Basics", DifficultyLevel.BEGINNER, 10,
                   status=CourseStatus.PUBLISHED)
        )

        # 4. Create main course with prerequisite
        course_repo.create_course(
            Course("CS101", "Programming",
                   DifficultyLevel.BEGINNER, 30,
                   status=CourseStatus.PUBLISHED,
                   prerequisites={"CS100"})
        )

        # 5. Verify prerequisite stored in junction table
        cs101 = course_repo.get_course("CS101")
        assert "CS100" in cs101.prerequisites
        assert isinstance(cs101.prerequisites, set)

        # 6. Enroll learner in CS100
        enrollment = enroll_repo.create_enrollment(
            Enrollment(learner_id=learner.id, course_code="CS100")
        )
        assert enrollment.id is not None

        # 7. Start and complete CS100
        enrollment.start()
        enroll_repo.update_enrollment(enrollment)
        enrollment.complete(95)
        enroll_repo.update_enrollment(enrollment)

        # 8. Verify completed courses derived from enrollments
        learner_reloaded = learner_repo.get_learner(learner.id)
        assert "CS100" in learner_reloaded.completed_courses
        assert isinstance(learner_reloaded.completed_courses, set)

        # 9. Enroll in CS101
        enrollment2 = enroll_repo.create_enrollment(
            Enrollment(learner_id=learner.id, course_code="CS101")
        )

        # 10. Track progress
        progress = progress_repo.create_progress(
            CourseProgress(
                learner_id=learner.id,
                course_code="CS101",
                percentage=50.0,
                completion_status=CompletionStatus.IN_PROGRESS,
            )
        )

        # 11. Verify progress
        loaded_progress = progress_repo.get_progress(
            learner.id, "CS101"
        )
        assert loaded_progress.percentage == 50.0
        assert loaded_progress.completion_status == CompletionStatus.IN_PROGRESS

        # 12. Verify current courses include CS101
        learner_final = learner_repo.get_learner(learner.id)
        assert "CS101" in learner_final.current_courses
        assert "CS100" in learner_final.completed_courses

        print("\n  Integration test PASSED — full workflow verified")

    def test_cascade_delete_user_removes_learner(self, file_db, pm):
        """Deleting a user must cascade to their learner profile."""
        user_repo    = SQLiteUserRepository(file_db)
        learner_repo = SQLiteLearnerRepository(file_db)

        user = user_repo.create_user(
            User("cascade_user", pm.hash_password("pass1234"), UserRole.LEARNER)
        )
        learner = learner_repo.create_learner(
            Learner(
                name="Cascade",
                email="cascade@test.com",
                user_id=user.id
            )
        )

        # Delete user → learner should cascade
        user_repo.delete_user(user.id)
        assert learner_repo.get_learner(learner.id) is None

    def test_schema_version_in_real_file(self, file_db):
        """Schema version must be recorded in real file database."""
        assert file_db.get_schema_version() == 1

    def test_multiple_connections_concurrent_reads(self, file_db, pm):
        """Multiple connections must be able to read simultaneously."""
        repo1 = SQLiteUserRepository(file_db)
        repo2 = SQLiteUserRepository(file_db)

        user = repo1.create_user(
            User("shared_user", pm.hash_password("pass1234"), UserRole.ADMIN)
        )

        # Both repos read the same user simultaneously
        found1 = repo1.find_by_username("shared_user")
        found2 = repo2.find_by_username("shared_user")

        assert found1 is not None
        assert found2 is not None
        assert found1.id == found2.id