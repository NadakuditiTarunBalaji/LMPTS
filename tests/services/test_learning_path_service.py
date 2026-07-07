"""
test_learning_path_service.py
------------------------------
Tests for LearningPathService.
"""

import pytest
from core.user import User
from core.course import Course
from core.learner import Learner
from core.enums import UserRole, DifficultyLevel, CourseStatus
from core.exceptions import CourseNotFoundError, LearnerNotFoundError
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
from services.learning_path_service import LearningPathService
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
def path_service(repos, graph):
    return LearningPathService(
        enrollment_repo = repos["enrollment"],
        learner_repo    = repos["learner"],
        course_repo     = repos["course"],
        graph           = graph,
    )


@pytest.fixture
def saved_learner(repos, pm):
    user = repos["user"].create_user(
        User("alice", pm.hash_password("pass1234"), UserRole.LEARNER)
    )
    return repos["learner"].create_learner(
        Learner(name="Alice", email="alice@test.com", user_id=user.id)
    )


@pytest.fixture
def curriculum(course_service):
    """CS101 → CS201 → CS301"""
    courses = [
        Course("CS101", "A", DifficultyLevel.BEGINNER, 20,
               status=CourseStatus.PUBLISHED),
        Course("CS201", "B", DifficultyLevel.INTERMEDIATE, 30,
               status=CourseStatus.PUBLISHED),
        Course("CS301", "C", DifficultyLevel.ADVANCED, 40,
               status=CourseStatus.PUBLISHED),
    ]
    for c in courses:
        course_service.create_course(c)
    course_service.add_prerequisite("CS201", "CS101")
    course_service.add_prerequisite("CS301", "CS201")
    return courses


class TestGetPathToCourse:

    def test_finds_path(self, path_service, curriculum):
        path = path_service.get_path_to_course("CS101", "CS301")
        assert path is not None
        assert path[0]  == "CS101"
        assert path[-1] == "CS301"

    def test_no_reverse_path(self, path_service, curriculum):
        path = path_service.get_path_to_course("CS301", "CS101")
        assert path is None

    def test_course_not_found_raises(self, path_service, curriculum):
        with pytest.raises(CourseNotFoundError):
            path_service.get_path_to_course("UNKNOWN", "CS301")


class TestGetLearnerRoadmap:

    def test_roadmap_no_completion(
        self, path_service, saved_learner, curriculum
    ):
        roadmap = path_service.get_learner_roadmap(
            saved_learner.id, "CS301"
        )
        assert roadmap["goal"]       == "CS301"
        assert roadmap["total"]      == 3
        assert roadmap["done"]       == 0
        assert roadmap["percentage"] == 0.0
        assert "CS101" in roadmap["remaining"]

    def test_roadmap_partial_completion(
        self, path_service, enrollment_service,
        saved_learner, curriculum
    ):
        enrollment_service.enroll_learner(saved_learner.id, "CS101")
        enrollment_service.complete_enrollment(
            saved_learner.id, "CS101", 90
        )
        roadmap = path_service.get_learner_roadmap(
            saved_learner.id, "CS301"
        )
        assert roadmap["done"]       == 1
        assert "CS101" in roadmap["completed"]
        assert "CS101" not in roadmap["remaining"]
        assert "CS201" in roadmap["remaining"]

    def test_roadmap_fully_done(
        self, path_service, enrollment_service,
        saved_learner, curriculum
    ):
        for code, score in [("CS101", 90), ("CS201", 85), ("CS301", 92)]:
            enrollment_service.enroll_learner(saved_learner.id, code)
            enrollment_service.complete_enrollment(
                saved_learner.id, code, score
            )

        roadmap = path_service.get_learner_roadmap(
            saved_learner.id, "CS301"
        )
        assert roadmap["percentage"] == 100.0
        assert roadmap["remaining"]  == []

    def test_roadmap_learner_not_found(self, path_service, curriculum):
        with pytest.raises(LearnerNotFoundError):
            path_service.get_learner_roadmap(99999, "CS301")

    def test_roadmap_course_not_found(
        self, path_service, saved_learner
    ):
        with pytest.raises(CourseNotFoundError):
            path_service.get_learner_roadmap(
                saved_learner.id, "UNKNOWN"
            )


class TestGetAvailableNextCourses:

    def test_no_credits_entry_only(
        self, path_service, saved_learner, curriculum
    ):
        available = path_service.get_available_next_courses(
            saved_learner.id
        )
        assert "CS101" in available
        assert "CS201" not in available

    def test_after_completing_prerequisite(
        self, path_service, enrollment_service,
        saved_learner, curriculum
    ):
        enrollment_service.enroll_learner(saved_learner.id, "CS101")
        enrollment_service.complete_enrollment(
            saved_learner.id, "CS101", 90
        )
        available = path_service.get_available_next_courses(
            saved_learner.id
        )
        assert "CS201" in available
        assert "CS101" not in available

    def test_learner_not_found_raises(self, path_service, curriculum):
        with pytest.raises(LearnerNotFoundError):
            path_service.get_available_next_courses(99999)


class TestCurriculumOrder:

    def test_full_curriculum_order(self, path_service, curriculum):
        order = path_service.get_full_curriculum_order()
        assert order.index("CS101") < order.index("CS201")
        assert order.index("CS201") < order.index("CS301")

    def test_curriculum_levels(self, path_service, curriculum):
        levels = path_service.get_curriculum_levels()
        assert "CS101" in levels[0]
        assert "CS201" in levels[1]
        assert "CS301" in levels[2]

    def test_prerequisites_for_course(self, path_service, curriculum):
        prereqs = path_service.get_prerequisites_for("CS301")
        assert "CS101" in prereqs
        assert "CS201" in prereqs
        assert prereqs.index("CS101") < prereqs.index("CS201")

    def test_prerequisites_for_unknown_raises(
        self, path_service, curriculum
    ):
        with pytest.raises(CourseNotFoundError):
            path_service.get_prerequisites_for("UNKNOWN")