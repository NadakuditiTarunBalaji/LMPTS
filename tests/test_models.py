"""
test_models.py
--------------
Comprehensive unit tests for all Person 1 components.

Verifies that the code matches every UML diagram exactly:
    - Class Diagram   : attributes, methods, types (set vs list, int vs float)
    - State Diagram   : enrollment state transitions
    - ER Diagram      : CourseProgress model exists
    - Sequence Diagram: login/register flows
    - Singleton       : SessionManager pattern

Run:
    python -m pytest tests/test_models.py -v

Coverage:
    python -m pytest tests/test_models.py --cov=. --cov-report=term-missing
"""

import json
import pytest
from datetime import datetime

# Core models
from core.enums import (
    DifficultyLevel, CourseStatus, EnrollmentStatus,
    UserRole, CompletionStatus,
)
from core.exceptions import (
    LMPTSException, ValidationError, AuthenticationError,
    CourseNotFoundError, LearnerNotFoundError,
    EnrollmentError, DuplicateEnrollmentError,
    PrerequisiteNotMetError, CircularDependencyError,
)
from core.user import User
from core.course import Course
from core.learner import Learner
from core.enrollment import Enrollment
from core.course_progress import CourseProgress

# Auth
from auth.password_manager import PasswordManager
from auth.user_repository import InMemoryUserRepository
from auth.session_manager import SessionManager
from auth.auth_service import AuthService


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_session():
    """Reset the SessionManager singleton before every test."""
    SessionManager.reset()
    yield
    SessionManager.reset()


@pytest.fixture
def pm():
    """PasswordManager instance."""
    return PasswordManager()


@pytest.fixture
def repo():
    """Fresh InMemoryUserRepository for each test."""
    return InMemoryUserRepository()


@pytest.fixture
def auth(repo):
    """AuthService wired to an in-memory repository."""
    return AuthService(repo)


@pytest.fixture
def sample_user(pm):
    """A valid unsaved User object."""
    return User(
        username="testuser",
        password_hash=pm.hash_password("password123"),
        role=UserRole.LEARNER,
    )


@pytest.fixture
def sample_course():
    """A valid Course object — duration is int, prerequisites is set."""
    return Course(
        code="CS101",
        name="Intro to Programming",
        difficulty=DifficultyLevel.BEGINNER,
        duration=30,                            # int per UML
        status=CourseStatus.PUBLISHED,
    )


@pytest.fixture
def sample_learner():
    """A valid Learner object — courses stored as sets."""
    return Learner(
        name="Alice Smith",
        email="alice@example.com",
        user_id=1,
    )


@pytest.fixture
def sample_enrollment():
    """A valid Enrollment object."""
    return Enrollment(
        learner_id=1,
        course_code="CS101",
    )


@pytest.fixture
def sample_progress():
    """A valid CourseProgress object."""
    return CourseProgress(
        learner_id=1,
        course_code="CS101",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Enum Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnums:
    """Verify all enums match the UML Class Diagram enumeration boxes."""

    def test_difficulty_levels_exist(self):
        assert DifficultyLevel.BEGINNER
        assert DifficultyLevel.INTERMEDIATE
        assert DifficultyLevel.ADVANCED

    def test_course_statuses_exist(self):
        assert CourseStatus.DRAFT
        assert CourseStatus.PUBLISHED
        assert CourseStatus.ARCHIVED

    def test_enrollment_statuses_exist(self):
        assert EnrollmentStatus.ENROLLED
        assert EnrollmentStatus.IN_PROGRESS
        assert EnrollmentStatus.COMPLETED
        assert EnrollmentStatus.CANCELLED

    def test_user_roles_exist(self):
        """UML Use Case actors → UserRole mapping."""
        assert UserRole.ADMIN
        assert UserRole.LEARNER
        assert UserRole.ANALYST
        assert UserRole.INSTRUCTOR

    def test_completion_statuses_exist(self):
        """Used by CourseProgress (UML ER Diagram Section 10)."""
        assert CompletionStatus.NOT_STARTED
        assert CompletionStatus.IN_PROGRESS
        assert CompletionStatus.COMPLETED
        assert CompletionStatus.FAILED

    def test_enum_values_are_strings(self):
        assert UserRole.ADMIN.value == "ADMIN"
        assert DifficultyLevel.BEGINNER.value == "BEGINNER"
        assert CourseStatus.DRAFT.value == "DRAFT"
        assert EnrollmentStatus.ENROLLED.value == "ENROLLED"
        assert CompletionStatus.NOT_STARTED.value == "NOT_STARTED"

    def test_enum_comparison(self):
        """Demonstrates anti-magic-string benefit."""
        assert UserRole.ADMIN == UserRole.ADMIN
        assert UserRole.ADMIN != UserRole.LEARNER


# ═══════════════════════════════════════════════════════════════════════════════
# Exception Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    """Verify the UML exception hierarchy is implemented correctly."""

    def test_all_exceptions_inherit_from_lmpts_exception(self):
        """Every custom exception must be catchable as LMPTSException."""
        exceptions = [
            ValidationError("test"),
            AuthenticationError("test"),
            CourseNotFoundError("test"),
            LearnerNotFoundError("test"),
            EnrollmentError("test"),
            DuplicateEnrollmentError("test"),
            PrerequisiteNotMetError("test"),
            CircularDependencyError("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, LMPTSException), (
                f"{type(exc).__name__} must inherit LMPTSException"
            )

    def test_exception_message_stored(self):
        err = ValidationError("Username cannot be empty")
        assert err.message == "Username cannot be empty"

    def test_exception_str(self):
        err = ValidationError("some error")
        assert str(err) == "some error"

    def test_duplicate_enrollment_is_enrollment_error(self):
        """UML: DuplicateEnrollmentError extends EnrollmentError."""
        err = DuplicateEnrollmentError("already enrolled")
        assert isinstance(err, EnrollmentError)

    def test_prerequisite_not_met_is_enrollment_error(self):
        """UML: PrerequisiteNotMetError extends EnrollmentError."""
        err = PrerequisiteNotMetError("missing CS101")
        assert isinstance(err, EnrollmentError)

    def test_raise_and_catch(self):
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Username cannot be empty")
        assert "Username cannot be empty" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# User Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestUser:
    """Verify User matches UML Class Diagram."""

    def test_user_creation(self):
        user = User(
            username="admin",
            password_hash="$2b$12$fakehash",
            role=UserRole.ADMIN,
        )
        assert user.username == "admin"
        assert user.role == UserRole.ADMIN
        assert user.id is None

    def test_user_created_at_defaults_to_now(self):
        """created_at should be timezone-aware UTC."""
        from datetime import timezone
        before = datetime.now(timezone.utc)
        user = User("u", "hash", UserRole.LEARNER)
        after = datetime.now(timezone.utc)
        assert before <= user.created_at <= after

    def test_user_validate_passes(self, sample_user):
        sample_user.validate()

    def test_user_validate_empty_username(self):
        user = User(username="", password_hash="hash", role=UserRole.LEARNER)
        with pytest.raises(ValidationError, match="Username cannot be empty"):
            user.validate()

    def test_user_validate_whitespace_username(self):
        user = User(username="   ", password_hash="hash", role=UserRole.LEARNER)
        with pytest.raises(ValidationError):
            user.validate()

    def test_user_validate_empty_password_hash(self):
        user = User(username="alice", password_hash="", role=UserRole.LEARNER)
        with pytest.raises(ValidationError, match="Password hash"):
            user.validate()

    def test_user_validate_invalid_role(self):
        user = User(username="alice", password_hash="hash", role="ADMIN")
        with pytest.raises(ValidationError, match="Invalid role"):
            user.validate()

    def test_user_to_dict_excludes_password(self, sample_user):
        d = sample_user.to_dict()
        assert "username" in d
        assert "role" in d
        assert "created_at" in d
        assert "password_hash" not in d

    def test_user_to_dict_with_hash(self, sample_user):
        d = sample_user.to_dict_with_hash()
        assert "password_hash" in d

    def test_user_to_dict_role_is_string(self, sample_user):
        d = sample_user.to_dict()
        assert isinstance(d["role"], str)
        assert d["role"] == "LEARNER"

    def test_user_from_dict(self):
        row = {
            "id": 1,
            "username": "admin",
            "password_hash": "$2b$12$fakehash",
            "role": "ADMIN",
            "created_at": "2024-01-15T10:30:00",
        }
        user = User.from_dict(row)
        assert user.id == 1
        assert user.username == "admin"
        assert user.role == UserRole.ADMIN

    def test_user_from_dict_invalid_role(self):
        row = {"username": "x", "password_hash": "h", "role": "SUPERUSER"}
        with pytest.raises(ValidationError, match="Unknown role"):
            User.from_dict(row)

    def test_user_equality_by_id(self):
        u1 = User("alice", "hash", UserRole.LEARNER, id=5)
        u2 = User("alice", "hash", UserRole.LEARNER, id=5)
        assert u1 == u2

    def test_user_inequality(self):
        u1 = User("alice", "hash", UserRole.LEARNER, id=1)
        u2 = User("alice", "hash", UserRole.LEARNER, id=2)
        assert u1 != u2

    def test_user_repr(self, sample_user):
        result = repr(sample_user)
        assert "testuser" in result
        assert "LEARNER" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Password Manager Tests (NOW A CLASS per UML)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPasswordManager:
    """Verify PasswordManager class matches UML Class Diagram."""

    def test_is_a_class(self):
        """UML shows PasswordManager as a class, not module functions."""
        pm = PasswordManager()
        assert hasattr(pm, "hash_password")
        assert hasattr(pm, "verify_password")
        assert hasattr(pm, "generate_salt")

    def test_hash_password_returns_string(self, pm):
        hashed = pm.hash_password("admin123")
        assert isinstance(hashed, str)

    def test_hash_password_not_plain_text(self, pm):
        plain = "admin123"
        hashed = pm.hash_password(plain)
        assert hashed != plain

    def test_hash_password_starts_with_bcrypt_prefix(self, pm):
        hashed = pm.hash_password("testPassword1")
        assert hashed.startswith("$2b$")

    def test_hash_password_different_each_call(self, pm):
        """Different salts produce different hashes."""
        h1 = pm.hash_password("admin123")
        h2 = pm.hash_password("admin123")
        assert h1 != h2

    def test_verify_password_correct(self, pm):
        hashed = pm.hash_password("admin123")
        assert pm.verify_password("admin123", hashed) is True

    def test_verify_password_wrong(self, pm):
        hashed = pm.hash_password("admin123")
        assert pm.verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty_inputs(self, pm):
        assert pm.verify_password("", "somehash") is False
        assert pm.verify_password("password", "") is False

    def test_hash_password_empty_raises(self, pm):
        with pytest.raises(ValueError):
            pm.hash_password("")

    def test_generate_salt_returns_bytes(self, pm):
        salt = pm.generate_salt()
        assert isinstance(salt, bytes)

    def test_generate_salt_different_each_call(self, pm):
        s1 = pm.generate_salt()
        s2 = pm.generate_salt()
        assert s1 != s2

    def test_static_method_callable_without_instance(self):
        """Static methods should work on the class directly."""
        hashed = PasswordManager.hash_password("test1234")
        assert PasswordManager.verify_password("test1234", hashed)


# ═══════════════════════════════════════════════════════════════════════════════
# Course Tests (SETS and INT duration per UML)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCourse:
    """Verify Course matches UML: duration=int, prerequisites=set."""

    def test_course_creation(self, sample_course):
        assert sample_course.code == "CS101"
        assert sample_course.name == "Intro to Programming"
        assert sample_course.difficulty == DifficultyLevel.BEGINNER
        assert sample_course.duration == 30
        assert sample_course.status == CourseStatus.PUBLISHED

    def test_duration_is_int(self, sample_course):
        """UML specifies duration: int (not float)."""
        assert isinstance(sample_course.duration, int)

    def test_prerequisites_is_set(self, sample_course):
        """UML specifies prerequisites: set (not list)."""
        assert isinstance(sample_course.prerequisites, set)

    def test_course_default_status_is_draft(self):
        course = Course("CS000", "Test", DifficultyLevel.BEGINNER, 10)
        assert course.status == CourseStatus.DRAFT

    def test_course_default_prerequisites_empty_set(self):
        course = Course("CS000", "Test", DifficultyLevel.BEGINNER, 10)
        assert course.get_prerequisites() == set()

    def test_course_validate_passes(self, sample_course):
        sample_course.validate()

    def test_invalid_course_empty_code(self):
        course = Course("", "Algorithms", DifficultyLevel.ADVANCED, 20)
        with pytest.raises(ValidationError, match="code cannot be empty"):
            course.validate()

    def test_invalid_course_empty_name(self):
        course = Course("CS999", "", DifficultyLevel.BEGINNER, 10)
        with pytest.raises(ValidationError, match="name cannot be empty"):
            course.validate()

    def test_invalid_course_zero_duration(self):
        course = Course("CS999", "Test", DifficultyLevel.BEGINNER, 0)
        with pytest.raises(ValidationError, match="Duration must be"):
            course.validate()

    def test_invalid_course_negative_duration(self):
        course = Course("CS999", "Test", DifficultyLevel.BEGINNER, -5)
        with pytest.raises(ValidationError):
            course.validate()

    def test_add_prerequisite(self, sample_course):
        sample_course.add_prerequisite("CS100")
        assert sample_course.has_prerequisite("CS100")

    def test_add_prerequisite_idempotent_via_set(self, sample_course):
        """Set inherently prevents duplicates — no special logic needed."""
        sample_course.add_prerequisite("CS100")
        sample_course.add_prerequisite("CS100")
        assert len(sample_course.prerequisites) == 1

    def test_add_self_as_prerequisite_raises(self, sample_course):
        with pytest.raises(ValidationError):
            sample_course.add_prerequisite("CS101")

    def test_add_empty_prerequisite_raises(self, sample_course):
        with pytest.raises(ValidationError):
            sample_course.add_prerequisite("")

    def test_remove_prerequisite(self, sample_course):
        sample_course.add_prerequisite("CS100")
        sample_course.remove_prerequisite("CS100")
        assert not sample_course.has_prerequisite("CS100")

    def test_remove_nonexistent_prerequisite_safe(self, sample_course):
        """set.discard() is safe — no error on missing element."""
        sample_course.remove_prerequisite("CS999")

    def test_has_prerequisite(self, sample_course):
        sample_course.add_prerequisite("CS100")
        assert sample_course.has_prerequisite("CS100") is True
        assert sample_course.has_prerequisite("CS999") is False

    def test_get_prerequisites_returns_copy(self, sample_course):
        """Mutating returned set must not affect internal state."""
        sample_course.add_prerequisite("CS100")
        prereqs = sample_course.get_prerequisites()
        prereqs.add("HACKED")
        assert "HACKED" not in sample_course.get_prerequisites()

    def test_get_prerequisites_returns_set(self, sample_course):
        """UML specifies set return type."""
        sample_course.add_prerequisite("CS100")
        prereqs = sample_course.get_prerequisites()
        assert isinstance(prereqs, set)

    def test_multiple_prerequisites(self, sample_course):
        sample_course.add_prerequisite("CS100")
        sample_course.add_prerequisite("MATH101")
        prereqs = sample_course.get_prerequisites()
        assert prereqs == {"CS100", "MATH101"}

    def test_course_to_dict(self, sample_course):
        d = sample_course.to_dict()
        assert d["code"] == "CS101"
        assert d["difficulty"] == "BEGINNER"
        assert d["status"] == "PUBLISHED"
        assert isinstance(d["prerequisites"], list)  # JSON-safe sorted list
        assert isinstance(d["duration"], int)

    def test_course_from_dict(self):
        row = {
            "code": "CS201",
            "name": "Data Structures",
            "description": "Learn DS",
            "difficulty": "INTERMEDIATE",
            "duration": 40,
            "status": "PUBLISHED",
            "prerequisites": ["CS101"],
        }
        course = Course.from_dict(row)
        assert course.code == "CS201"
        assert course.difficulty == DifficultyLevel.INTERMEDIATE
        assert course.has_prerequisite("CS101")
        assert isinstance(course.prerequisites, set)
        assert isinstance(course.duration, int)

    def test_course_from_dict_json_prerequisites(self):
        row = {
            "code": "CS301",
            "name": "Algorithms",
            "difficulty": "ADVANCED",
            "duration": 50,
            "status": "DRAFT",
            "prerequisites": json.dumps(["CS201"]),
        }
        course = Course.from_dict(row)
        assert course.has_prerequisite("CS201")
        assert isinstance(course.prerequisites, set)

    def test_course_equality(self):
        c1 = Course("CS101", "A", DifficultyLevel.BEGINNER, 10)
        c2 = Course("CS101", "B", DifficultyLevel.ADVANCED, 20)
        assert c1 == c2

    def test_course_inequality(self):
        c1 = Course("CS101", "A", DifficultyLevel.BEGINNER, 10)
        c2 = Course("CS201", "A", DifficultyLevel.BEGINNER, 10)
        assert c1 != c2

    def test_course_hashable(self):
        """Courses should be usable in sets and as dict keys."""
        c = Course("CS101", "A", DifficultyLevel.BEGINNER, 10)
        course_set = {c}
        assert c in course_set


# ═══════════════════════════════════════════════════════════════════════════════
# Learner Tests (SETS per UML)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLearner:
    """Verify Learner matches UML: completed_courses=set, current_courses=set."""

    def test_learner_creation(self, sample_learner):
        assert sample_learner.name == "Alice Smith"
        assert sample_learner.email == "alice@example.com"
        assert sample_learner.completed_courses == set()
        assert sample_learner.current_courses == set()

    def test_courses_are_sets(self, sample_learner):
        """UML specifies set type for both course collections."""
        assert isinstance(sample_learner.completed_courses, set)
        assert isinstance(sample_learner.current_courses, set)

    def test_learner_validate_passes(self, sample_learner):
        sample_learner.validate()

    def test_learner_validate_empty_name(self):
        learner = Learner(name="", email="x@x.com")
        with pytest.raises(ValidationError, match="name cannot be empty"):
            learner.validate()

    def test_learner_validate_empty_email(self):
        learner = Learner(name="Bob", email="")
        with pytest.raises(ValidationError, match="email cannot be empty"):
            learner.validate()

    def test_enroll_course(self, sample_learner):
        sample_learner.enroll("CS101")
        assert "CS101" in sample_learner.current_courses

    def test_enroll_same_course_twice_raises(self, sample_learner):
        sample_learner.enroll("CS101")
        with pytest.raises(EnrollmentError, match="Already enrolled"):
            sample_learner.enroll("CS101")

    def test_enroll_completed_course_raises(self, sample_learner):
        sample_learner.enroll("CS101")
        sample_learner.complete("CS101")
        with pytest.raises(EnrollmentError, match="already completed"):
            sample_learner.enroll("CS101")

    def test_enroll_empty_code_raises(self, sample_learner):
        with pytest.raises(ValidationError):
            sample_learner.enroll("")

    def test_complete_course(self, sample_learner):
        sample_learner.enroll("CS101")
        sample_learner.complete("CS101")
        assert "CS101" not in sample_learner.current_courses
        assert "CS101" in sample_learner.completed_courses

    def test_complete_not_enrolled_raises(self, sample_learner):
        with pytest.raises(EnrollmentError, match="not in current"):
            sample_learner.complete("CS999")

    def test_progress_no_courses(self, sample_learner):
        assert sample_learner.progress() == 0.0

    def test_progress_calculation(self, sample_learner):
        sample_learner.enroll("CS101")
        sample_learner.complete("CS101")
        sample_learner.enroll("CS201")
        assert sample_learner.progress() == 50.0

    def test_progress_all_completed(self, sample_learner):
        sample_learner.enroll("CS101")
        sample_learner.complete("CS101")
        assert sample_learner.progress() == 100.0

    def test_completion_rate_matches_progress(self, sample_learner):
        sample_learner.enroll("CS101")
        sample_learner.complete("CS101")
        sample_learner.enroll("CS201")
        assert sample_learner.completion_rate() == sample_learner.progress()

    def test_learner_to_dict(self, sample_learner):
        d = sample_learner.to_dict()
        assert d["name"] == "Alice Smith"
        assert isinstance(d["completed_courses"], list)  # JSON-safe
        assert isinstance(d["current_courses"], list)     # JSON-safe

    def test_learner_from_dict(self):
        row = {
            "id": 2,
            "user_id": 1,
            "name": "Bob",
            "email": "bob@x.com",
            "completed_courses": json.dumps(["CS101"]),
            "current_courses": json.dumps(["CS201"]),
        }
        learner = Learner.from_dict(row)
        assert learner.name == "Bob"
        assert isinstance(learner.completed_courses, set)
        assert isinstance(learner.current_courses, set)
        assert "CS101" in learner.completed_courses
        assert "CS201" in learner.current_courses


# ═══════════════════════════════════════════════════════════════════════════════
# Enrollment Tests (UML State Diagram)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnrollment:
    """Verify Enrollment state transitions match UML State Diagram."""

    def test_enrollment_creation(self, sample_enrollment):
        assert sample_enrollment.learner_id == 1
        assert sample_enrollment.course_code == "CS101"
        assert sample_enrollment.status == EnrollmentStatus.ENROLLED
        assert sample_enrollment.score is None

    def test_enrollment_default_status(self, sample_enrollment):
        """UML State Diagram: initial state is ENROLLED."""
        assert sample_enrollment.status == EnrollmentStatus.ENROLLED

    def test_enrollment_enrolled_at_defaults(self):
        """enrolled_at should be timezone-aware UTC."""
        from datetime import timezone
        before = datetime.now(timezone.utc)
        e = Enrollment(learner_id=1, course_code="CS101")
        after = datetime.now(timezone.utc)
        assert before <= e.enrolled_at <= after

    def test_enrollment_validate_passes(self, sample_enrollment):
        sample_enrollment.validate()

    def test_enrollment_validate_no_learner(self):
        e = Enrollment(learner_id=None, course_code="CS101")
        with pytest.raises(ValidationError, match="learner_id"):
            e.validate()

    def test_enrollment_validate_empty_course(self):
        e = Enrollment(learner_id=1, course_code="")
        with pytest.raises(ValidationError, match="course_code"):
            e.validate()

    def test_enrollment_validate_invalid_score(self):
        e = Enrollment(learner_id=1, course_code="CS101", score=150)
        with pytest.raises(ValidationError, match="Score must be"):
            e.validate()

    # ── UML State Transitions ─────────────────────────────────────────────────

    def test_start_transition(self, sample_enrollment):
        """ENROLLED → IN_PROGRESS"""
        sample_enrollment.start()
        assert sample_enrollment.status == EnrollmentStatus.IN_PROGRESS

    def test_start_from_wrong_state_raises(self, sample_enrollment):
        sample_enrollment.start()
        with pytest.raises(EnrollmentError):
            sample_enrollment.start()  # already IN_PROGRESS

    def test_complete_transition(self, sample_enrollment):
        """ENROLLED/IN_PROGRESS → COMPLETED"""
        sample_enrollment.complete(95)
        assert sample_enrollment.status == EnrollmentStatus.COMPLETED
        assert sample_enrollment.score == 95
        assert sample_enrollment.completed_at is not None

    def test_complete_sets_timestamp(self, sample_enrollment):
        """completed_at should be timezone-aware UTC."""
        from datetime import timezone
        before = datetime.now(timezone.utc)
        sample_enrollment.complete(80)
        after = datetime.now(timezone.utc)
        assert before <= sample_enrollment.completed_at <= after


    def test_complete_already_completed_raises(self, sample_enrollment):
        """COMPLETED is terminal — cannot complete again."""
        sample_enrollment.complete(90)
        with pytest.raises(EnrollmentError, match="already completed"):
            sample_enrollment.complete(80)

    def test_complete_cancelled_raises(self, sample_enrollment):
        """CANCELLED is terminal — cannot complete."""
        sample_enrollment.cancel()
        with pytest.raises(EnrollmentError, match="cancelled"):
            sample_enrollment.complete(80)

    def test_complete_invalid_score_raises(self, sample_enrollment):
        with pytest.raises(ValidationError, match="Score must be"):
            sample_enrollment.complete(110)

    def test_complete_zero_score(self, sample_enrollment):
        sample_enrollment.complete(0)
        assert sample_enrollment.score == 0

    def test_complete_perfect_score(self, sample_enrollment):
        sample_enrollment.complete(100)
        assert sample_enrollment.score == 100

    def test_cancel_from_enrolled(self, sample_enrollment):
        """ENROLLED → CANCELLED"""
        sample_enrollment.cancel()
        assert sample_enrollment.status == EnrollmentStatus.CANCELLED

    def test_cancel_from_in_progress(self, sample_enrollment):
        """IN_PROGRESS → CANCELLED"""
        sample_enrollment.start()
        sample_enrollment.cancel()
        assert sample_enrollment.status == EnrollmentStatus.CANCELLED

    def test_cancel_already_cancelled_raises(self, sample_enrollment):
        sample_enrollment.cancel()
        with pytest.raises(EnrollmentError, match="already cancelled"):
            sample_enrollment.cancel()

    def test_cancel_completed_raises(self, sample_enrollment):
        """COMPLETED is terminal — cannot cancel."""
        sample_enrollment.complete(75)
        with pytest.raises(EnrollmentError, match="completed enrollment"):
            sample_enrollment.cancel()

    # ── Full State Machine Path ────────────────────────────────────────────────

    def test_full_lifecycle_happy_path(self, sample_enrollment):
        """ENROLLED → IN_PROGRESS → COMPLETED"""
        assert sample_enrollment.status == EnrollmentStatus.ENROLLED
        sample_enrollment.start()
        assert sample_enrollment.status == EnrollmentStatus.IN_PROGRESS
        sample_enrollment.complete(88)
        assert sample_enrollment.status == EnrollmentStatus.COMPLETED
        assert sample_enrollment.score == 88

    def test_full_lifecycle_cancel_path(self, sample_enrollment):
        """ENROLLED → IN_PROGRESS → CANCELLED"""
        sample_enrollment.start()
        sample_enrollment.cancel()
        assert sample_enrollment.status == EnrollmentStatus.CANCELLED

    # ── Serialization ──────────────────────────────────────────────────────────

    def test_enrollment_to_dict(self, sample_enrollment):
        d = sample_enrollment.to_dict()
        assert d["learner_id"] == 1
        assert d["course_code"] == "CS101"
        assert d["status"] == "ENROLLED"
        assert d["completed_at"] is None

    def test_enrollment_from_dict(self):
        row = {
            "id": 10,
            "learner_id": 2,
            "course_code": "CS201",
            "status": "COMPLETED",
            "score": 88.5,
            "enrolled_at": "2024-01-01T09:00:00",
            "completed_at": "2024-03-01T17:00:00",
        }
        e = Enrollment.from_dict(row)
        assert e.id == 10
        assert e.status == EnrollmentStatus.COMPLETED
        assert e.score == 88.5


# ═══════════════════════════════════════════════════════════════════════════════
# CourseProgress Tests (UML ER Diagram Section 10)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCourseProgress:
    """Verify CourseProgress model matches ER Diagram COURSE_PROGRESS table."""

    def test_creation(self, sample_progress):
        assert sample_progress.learner_id == 1
        assert sample_progress.course_code == "CS101"
        assert sample_progress.percentage == 0.0
        assert sample_progress.completion_status == CompletionStatus.NOT_STARTED

    def test_validate_passes(self, sample_progress):
        sample_progress.validate()

    def test_validate_no_learner_raises(self):
        cp = CourseProgress(learner_id=None, course_code="CS101")
        with pytest.raises(ValidationError, match="learner_id"):
            cp.validate()

    def test_validate_no_course_raises(self):
        cp = CourseProgress(learner_id=1, course_code="")
        with pytest.raises(ValidationError, match="course_code"):
            cp.validate()

    def test_validate_invalid_percentage_raises(self):
        cp = CourseProgress(learner_id=1, course_code="CS101", percentage=150)
        with pytest.raises(ValidationError, match="Percentage"):
            cp.validate()

    def test_update_progress_to_50(self, sample_progress):
        sample_progress.update_progress(50.0)
        assert sample_progress.percentage == 50.0
        assert sample_progress.completion_status == CompletionStatus.IN_PROGRESS

    def test_update_progress_to_100(self, sample_progress):
        sample_progress.update_progress(100.0)
        assert sample_progress.percentage == 100.0
        assert sample_progress.completion_status == CompletionStatus.COMPLETED

    def test_update_progress_to_0(self, sample_progress):
        sample_progress.update_progress(50.0)
        sample_progress.update_progress(0.0)
        assert sample_progress.completion_status == CompletionStatus.NOT_STARTED

    def test_update_progress_invalid_raises(self, sample_progress):
        with pytest.raises(ValidationError, match="Percentage"):
            sample_progress.update_progress(101.0)

    def test_mark_failed(self, sample_progress):
        sample_progress.mark_failed()
        assert sample_progress.completion_status == CompletionStatus.FAILED

    def test_to_dict(self, sample_progress):
        d = sample_progress.to_dict()
        assert d["learner_id"] == 1
        assert d["course_code"] == "CS101"
        assert d["percentage"] == 0.0
        assert d["completion_status"] == "NOT_STARTED"

    def test_from_dict(self):
        row = {
            "id": 5,
            "learner_id": 2,
            "course_code": "CS201",
            "percentage": 75.0,
            "completion_status": "IN_PROGRESS",
            "updated_at": "2024-06-01T12:00:00",
        }
        cp = CourseProgress.from_dict(row)
        assert cp.id == 5
        assert cp.percentage == 75.0
        assert cp.completion_status == CompletionStatus.IN_PROGRESS


# ═══════════════════════════════════════════════════════════════════════════════
# SessionManager Tests (UML Singleton)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionManager:
    """Verify <<Singleton>> stereotype from UML Class Diagram."""

    def test_singleton_same_instance(self):
        s1 = SessionManager()
        s2 = SessionManager()
        assert s1 is s2

    def test_singleton_three_instances(self):
        s1 = SessionManager()
        s2 = SessionManager()
        s3 = SessionManager()
        assert s1 is s2 is s3

    def test_not_authenticated_initially(self):
        session = SessionManager()
        assert session.is_authenticated() is False

    def test_current_user_none_initially(self):
        session = SessionManager()
        assert session.current_user() is None

    def test_login(self):
        user = User("alice", "hash", UserRole.LEARNER, id=1)
        session = SessionManager()
        session.login(user)
        assert session.is_authenticated() is True
        assert session.current_user() is user

    def test_logout(self):
        user = User("alice", "hash", UserRole.LEARNER, id=1)
        session = SessionManager()
        session.login(user)
        session.logout()
        assert session.is_authenticated() is False
        assert session.current_user() is None

    def test_login_with_none_raises(self):
        session = SessionManager()
        with pytest.raises(ValueError):
            session.login(None)

    def test_session_shared_across_references(self):
        """Singleton: changes visible across all references."""
        user = User("bob", "hash", UserRole.ADMIN, id=2)
        s1 = SessionManager()
        s2 = SessionManager()
        s1.login(user)
        assert s2.is_authenticated() is True
        assert s2.current_user() is user

    def test_reset_clears_instance(self):
        s1 = SessionManager()
        s1.login(User("alice", "hash", UserRole.LEARNER, id=1))
        SessionManager.reset()
        s2 = SessionManager()
        assert s2.is_authenticated() is False


# ═══════════════════════════════════════════════════════════════════════════════
# InMemoryUserRepository Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestInMemoryUserRepository:
    """Verify the test-double implements UserRepository interface."""

    def test_create_user(self, repo, sample_user):
        saved = repo.create_user(sample_user)
        assert saved.id is not None
        assert saved.id == 1

    def test_create_incrementing_ids(self, repo):
        u1 = repo.create_user(User("a", "h", UserRole.LEARNER))
        u2 = repo.create_user(User("b", "h", UserRole.LEARNER))
        assert u2.id == u1.id + 1

    def test_create_duplicate_raises(self, repo):
        repo.create_user(User("alice", "hash", UserRole.LEARNER))
        with pytest.raises(ValidationError, match="already exists"):
            repo.create_user(User("alice", "hash2", UserRole.ADMIN))

    def test_get_user_found(self, repo, sample_user):
        saved = repo.create_user(sample_user)
        found = repo.get_user(saved.id)
        assert found.username == "testuser"

    def test_get_user_not_found(self, repo):
        assert repo.get_user(999) is None

    def test_find_by_username_found(self, repo, sample_user):
        repo.create_user(sample_user)
        found = repo.find_by_username("testuser")
        assert found is not None

    def test_find_by_username_not_found(self, repo):
        assert repo.find_by_username("nonexistent") is None

    def test_update_password(self, repo, sample_user, pm):
        saved = repo.create_user(sample_user)
        new_hash = pm.hash_password("newpassword!")
        repo.update_password(saved.id, new_hash)
        updated = repo.get_user(saved.id)
        assert updated.password_hash == new_hash

    def test_update_password_not_found(self, repo):
        with pytest.raises(LearnerNotFoundError):
            repo.update_password(999, "newhash")

    def test_delete_user(self, repo, sample_user):
        saved = repo.create_user(sample_user)
        repo.delete_user(saved.id)
        assert repo.get_user(saved.id) is None

    def test_delete_not_found(self, repo):
        with pytest.raises(LearnerNotFoundError):
            repo.delete_user(999)

    def test_get_all_users_empty(self, repo):
        assert repo.get_all_users() == []

    def test_get_all_users(self, repo):
        repo.create_user(User("a", "h", UserRole.ADMIN))
        repo.create_user(User("b", "h", UserRole.LEARNER))
        assert len(repo.get_all_users()) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# AuthService Tests (UML Sequence + Activity Diagrams)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthService:
    """
    Verify AuthService flows match:
        - UML Sequence Diagram (Section 5): Login
        - UML Activity Diagram (Section 8): Authentication
        - UML Class Diagram: AuthService dependencies
    """

    def test_register_creates_user(self, auth):
        user = auth.register("alice", "password123", UserRole.LEARNER)
        assert user.id is not None
        assert user.username == "alice"
        assert user.role == UserRole.LEARNER

    def test_register_hashes_password(self, auth):
        user = auth.register("alice", "password123")
        assert user.password_hash != "password123"
        assert user.password_hash.startswith("$2b$")

    def test_register_empty_username_raises(self, auth):
        with pytest.raises(ValidationError, match="Username cannot be empty"):
            auth.register("", "password123")

    def test_register_short_password_raises(self, auth):
        with pytest.raises(ValidationError, match="at least 8 characters"):
            auth.register("alice", "short")

    def test_register_duplicate_raises(self, auth):
        auth.register("alice", "password123")
        with pytest.raises(ValidationError, match="already taken"):
            auth.register("alice", "anotherpass")

    # ── UML Sequence Diagram: Login Flow ───────────────────────────────────────

    def test_login_success(self, auth):
        """Steps 2-8 of UML Sequence Diagram."""
        auth.register("alice", "password123", UserRole.LEARNER)
        user = auth.login("alice", "password123")
        assert user.username == "alice"

    def test_login_creates_session(self, auth):
        """Step 7: SessionManager.login(user)"""
        auth.register("alice", "password123")
        auth.login("alice", "password123")
        assert auth.verify_user() is True

    def test_login_wrong_password_raises(self, auth):
        """UML Activity: Verify Password → [wrong] → Auth Error"""
        auth.register("alice", "password123")
        with pytest.raises(AuthenticationError):
            auth.login("alice", "wrongpassword")

    def test_login_unknown_user_raises(self, auth):
        """UML Activity: Find User → [not found] → Invalid Login"""
        with pytest.raises(AuthenticationError):
            auth.login("nobody", "password123")

    def test_login_error_message_same(self, auth):
            """Same message for wrong user and wrong password (anti-enumeration)."""
            auth.register("alice", "password123")

            # Assign outside except so scope is guaranteed after the block
            e1 = None
            e2 = None

            try:
                auth.login("nobody", "password123")
            except AuthenticationError as e:
                e1 = e

            try:
                auth.login("alice", "wrongpass00")
            except AuthenticationError as e:
                e2 = e

            assert e1 is not None, "Expected AuthenticationError for unknown user"
            assert e2 is not None, "Expected AuthenticationError for wrong password"
            assert e1.message == e2.message

    def test_logout_clears_session(self, auth):
        auth.register("alice", "password123")
        auth.login("alice", "password123")
        auth.logout()
        assert auth.verify_user() is False

    def test_change_password_success(self, auth):
        user = auth.register("alice", "password123")
        auth.change_password(user.id, "password123", "newpassword!")
        auth.logout()
        with pytest.raises(AuthenticationError):
            auth.login("alice", "password123")
        logged_in = auth.login("alice", "newpassword!")
        assert logged_in.username == "alice"

    def test_change_password_wrong_old_raises(self, auth):
        user = auth.register("alice", "password123")
        with pytest.raises(AuthenticationError, match="Current password"):
            auth.change_password(user.id, "wrongold", "newpassword!")

    def test_change_password_short_new_raises(self, auth):
        user = auth.register("alice", "password123")
        with pytest.raises(ValidationError, match="at least 8"):
            auth.change_password(user.id, "password123", "short")

    def test_change_password_user_not_found(self, auth):
        with pytest.raises(LearnerNotFoundError):
            auth.change_password(999, "old", "newpassword!")

    def test_verify_user_not_logged_in(self, auth):
        assert auth.verify_user() is False

    def test_verify_user_logged_in(self, auth):
        auth.register("alice", "password123")
        auth.login("alice", "password123")
        assert auth.verify_user() is True

    def test_current_user(self, auth):
        auth.register("alice", "password123", UserRole.LEARNER)
        auth.login("alice", "password123")
        user = auth.current_user()
        assert user is not None
        assert user.username == "alice"

    def test_current_user_none(self, auth):
        assert auth.current_user() is None

    # ── Default Users ──────────────────────────────────────────────────────────

    def test_create_default_users(self, auth):
        """UML Default Users table: admin, learner, analyst."""
        auth.create_default_users()

        admin = auth.login("admin", "admin123")
        assert admin.role == UserRole.ADMIN
        auth.logout()

        learner = auth.login("learner", "learner123")
        assert learner.role == UserRole.LEARNER
        auth.logout()

        analyst = auth.login("analyst", "analyst123")
        assert analyst.role == UserRole.ANALYST
        auth.logout()

    def test_create_default_users_idempotent(self, auth):
        auth.create_default_users()
        auth.create_default_users()  # no error on second call

    def test_default_passwords_are_hashed(self, auth, repo):
        auth.create_default_users()
        admin = repo.find_by_username("admin")
        assert admin.password_hash != "admin123"
        assert admin.password_hash.startswith("$2b$")

    # ── UML Dependencies Verification ─────────────────────────────────────────

    def test_auth_service_uses_password_manager_class(self, auth):
        """UML: AuthService ───> PasswordManager (dependency)."""
        assert isinstance(auth._pm, PasswordManager)

    def test_auth_service_uses_session_manager(self, auth):
        """UML: AuthService ───> SessionManager (dependency)."""
        assert isinstance(auth._session, SessionManager)