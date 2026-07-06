"""
test_enrollment_service.py
--------------------------
Tests for EnrollmentService.
"""

import pytest
from core.user import User
from core.course import Course
from core.learner import Learner
from core.enums import (
    UserRole, DifficultyLevel, CourseStatus, EnrollmentStatus
)
from core.exceptions import LearnerNotFoundError, CourseNotFoundError
from algorithms.graph import CourseGraph
from repository.database import Database
from repository.user_repo import SQLiteUserRepository
from repository.course_repo import SQLiteCourseRepository
from repository.learner_repo import SQLiteLearnerRepository
from repository.enrollment_repo import (
    SQLiteEnrollmentRepository,
    SQLiteProgressRepository,
)
from services.course_service import CourseService
from services.enrollment_service import EnrollmentService
from auth.password_manager import PasswordManager


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.initialize()
    return database


@pytest.fixture
def pm():
    return PasswordManager()


@pytest.fixture
def graph():
    return CourseGraph()


@pytest.fixture
def repos(db):
    return {
        "user":       SQLiteUserRepository(db),
        "course":     SQLiteCourseRepository(db),
        "learner":    SQLiteLearnerRepository(db),
        "enrollment": SQLiteEnrollmentRepository(db),
        "progress":   SQLiteProgressRepository(db),
    }


@pytest.fixture
def course_service(repos, graph):
    return CourseService(repos["course"], graph)


@pytest.fixture
def enrollment_service(repos, graph, db):
    return EnrollmentService(
        enrollment_repo = repos["enrollment"],
        progress_repo   = repos["progress"],
        learner_repo    = repos["learner"],
        course_repo     = repos["course"],
        graph           = graph,
        database        = db,
    )


@pytest.fixture
def saved_learner(repos, pm):
    user = repos["user"].create_user(
        User("alice", pm.hash_password("pass1234"), UserRole.LEARNER)
    )
    learner = repos["learner"].create_learner(
        Learner(name="Alice", email="alice@test.com", user_id=user.id)
    )
    return learner


@pytest.fixture
def saved_course(course_service):
    course = Course(
        "CS101", "Intro", DifficultyLevel.BEGINNER, 30,
        status=CourseStatus.PUBLISHED
    )
    return course_service.create_course(course)


class TestEnrollLearner:

    def test_enroll_success(
        self, enrollment_service, saved_learner, saved_course
    ):
        result = enrollment_service.enroll_learner(
            saved_learner.id, "CS101"
        )
        assert result.success is True
        assert result.enrollment is not None
        assert result.enrollment.status == EnrollmentStatus.ENROLLED

    def test_enroll_creates_progress_record(
        self, enrollment_service, repos, saved_learner, saved_course
    ):
        enrollment_service.enroll_learner(saved_learner.id, "CS101")
        progress = repos["progress"].get_progress(
            saved_learner.id, "CS101"
        )
        assert progress is not None
        assert progress.percentage == 0.0

    def test_enroll_learner_not_found(
        self, enrollment_service, saved_course
    ):
        with pytest.raises(LearnerNotFoundError):
            enrollment_service.enroll_learner(99999, "CS101")

    def test_enroll_course_not_found(
        self, enrollment_service, saved_learner
    ):
        with pytest.raises(CourseNotFoundError):
            enrollment_service.enroll_learner(saved_learner.id, "UNKNOWN")

    def test_enroll_duplicate_returns_failure(
        self, enrollment_service, saved_learner, saved_course
    ):
        enrollment_service.enroll_learner(saved_learner.id, "CS101")
        result = enrollment_service.enroll_learner(
            saved_learner.id, "CS101"
        )
        assert result.success is False
        assert "already enrolled" in result.message.lower()

    def test_enroll_missing_prerequisite(
        self, enrollment_service, course_service, saved_learner
    ):
        prereq = Course(
            "CS100", "Pre", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        )
        main = Course(
            "CS200", "Main", DifficultyLevel.INTERMEDIATE, 20,
            status=CourseStatus.PUBLISHED
        )
        course_service.create_course(prereq)
        course_service.create_course(main)
        course_service.add_prerequisite("CS200", "CS100")

        result = enrollment_service.enroll_learner(
            saved_learner.id, "CS200"
        )
        assert result.success is False
        assert "CS100" in result.missing_prerequisites

    def test_enroll_after_prerequisite_completed(
        self, enrollment_service, course_service, saved_learner
    ):
        prereq = Course(
            "CS100", "Pre", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        )
        main = Course(
            "CS200", "Main", DifficultyLevel.INTERMEDIATE, 20,
            status=CourseStatus.PUBLISHED
        )
        course_service.create_course(prereq)
        course_service.create_course(main)
        course_service.add_prerequisite("CS200", "CS100")

        # Complete prerequisite first
        enrollment_service.enroll_learner(saved_learner.id, "CS100")
        enrollment_service.complete_enrollment(saved_learner.id, "CS100", 85)

        # Now should be allowed
        result = enrollment_service.enroll_learner(
            saved_learner.id, "CS200"
        )
        assert result.success is True

    def test_enroll_bypass_prereqs(
        self, enrollment_service, course_service, saved_learner
    ):
        prereq = Course(
            "CS100", "Pre", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        )
        main = Course(
            "CS200", "Main", DifficultyLevel.INTERMEDIATE, 20,
            status=CourseStatus.PUBLISHED
        )
        course_service.create_course(prereq)
        course_service.create_course(main)
        course_service.add_prerequisite("CS200", "CS100")

        result = enrollment_service.enroll_learner(
            saved_learner.id, "CS200",
            bypass_prereqs=True
        )
        assert result.success is True

    def test_enroll_draft_course_fails(
        self, enrollment_service, course_service, saved_learner
    ):
        draft = Course(
            "CS999", "Draft", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.DRAFT
        )
        course_service.create_course(draft)
        result = enrollment_service.enroll_learner(
            saved_learner.id, "CS999"
        )
        assert result.success is False


class TestCompleteEnrollment:

    def test_complete_enrollment(
        self, enrollment_service, saved_learner, saved_course
    ):
        enrollment_service.enroll_learner(saved_learner.id, "CS101")
        enrollment = enrollment_service.complete_enrollment(
            saved_learner.id, "CS101", 90
        )
        assert enrollment.status == EnrollmentStatus.COMPLETED
        assert enrollment.score == 90

    def test_complete_updates_progress(
        self, enrollment_service, repos, saved_learner, saved_course
    ):
        enrollment_service.enroll_learner(saved_learner.id, "CS101")
        enrollment_service.complete_enrollment(
            saved_learner.id, "CS101", 85
        )
        progress = repos["progress"].get_progress(
            saved_learner.id, "CS101"
        )
        assert progress.percentage == 100.0

    def test_complete_not_enrolled_raises(
        self, enrollment_service, saved_learner, saved_course
    ):
        with pytest.raises(LearnerNotFoundError):
            enrollment_service.complete_enrollment(
                saved_learner.id, "CS101", 80
            )


class TestCancelEnrollment:

    def test_cancel_enrollment(
        self, enrollment_service, repos, saved_learner, saved_course
    ):
        enrollment_service.enroll_learner(saved_learner.id, "CS101")
        enrollment_service.cancel_enrollment(saved_learner.id, "CS101")

        enrollments = repos["enrollment"].get_enrollments_by_learner(
            saved_learner.id
        )
        assert enrollments[0].status == EnrollmentStatus.CANCELLED

    def test_cancel_not_enrolled_raises(
        self, enrollment_service, saved_learner, saved_course
    ):
        with pytest.raises(LearnerNotFoundError):
            enrollment_service.cancel_enrollment(
                saved_learner.id, "CS101"
            )


class TestTransferAndExemption:

    def test_transfer_credit(
        self, enrollment_service, saved_learner, saved_course
    ):
        result = enrollment_service.transfer_credit(
            saved_learner.id, "CS101"
        )
        assert result.success is True

        completed = enrollment_service.get_completed_courses(
            saved_learner.id
        )
        assert "CS101" in completed

    def test_transfer_credit_learner_not_found(
        self, enrollment_service, saved_course
    ):
        with pytest.raises(LearnerNotFoundError):
            enrollment_service.transfer_credit(99999, "CS101")

    def test_approve_exemption(
        self, enrollment_service, saved_learner, saved_course
    ):
        result = enrollment_service.approve_exemption(
            saved_learner.id, "CS101"
        )
        assert result.success is True
        completed = enrollment_service.get_completed_courses(
            saved_learner.id
        )
        assert "CS101" in completed

    def test_transfer_unlocks_dependent(
        self, enrollment_service, course_service, saved_learner
    ):
        prereq = Course(
            "CS100", "Pre", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        )
        main = Course(
            "CS200", "Main", DifficultyLevel.INTERMEDIATE, 20,
            status=CourseStatus.PUBLISHED
        )
        course_service.create_course(prereq)
        course_service.create_course(main)
        course_service.add_prerequisite("CS200", "CS100")

        # Transfer credit for prerequisite
        enrollment_service.transfer_credit(saved_learner.id, "CS100")

        # Should now be able to enroll in dependent
        result = enrollment_service.enroll_learner(
            saved_learner.id, "CS200"
        )
        assert result.success is True


class TestEnrollmentQueries:

    def test_get_learner_enrollments(
        self, enrollment_service, saved_learner, saved_course
    ):
        enrollment_service.enroll_learner(saved_learner.id, "CS101")
        enrollments = enrollment_service.get_learner_enrollments(
            saved_learner.id
        )
        assert len(enrollments) == 1

    def test_get_completed_courses(
        self, enrollment_service, saved_learner, saved_course
    ):
        enrollment_service.enroll_learner(saved_learner.id, "CS101")
        enrollment_service.complete_enrollment(
            saved_learner.id, "CS101", 90
        )
        completed = enrollment_service.get_completed_courses(
            saved_learner.id
        )
        assert "CS101" in completed

    def test_get_active_courses(
        self, enrollment_service, saved_learner, saved_course
    ):
        enrollment_service.enroll_learner(saved_learner.id, "CS101")
        active = enrollment_service.get_active_courses(saved_learner.id)
        assert "CS101" in active