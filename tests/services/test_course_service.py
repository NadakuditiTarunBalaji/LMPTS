"""
test_course_service.py
----------------------
Tests for CourseService.
"""

import pytest
from core.course import Course
from core.enums import DifficultyLevel, CourseStatus
from core.exceptions import (
    CourseNotFoundError,
    ValidationError,
    CircularDependencyError,
)
from algorithms.graph import CourseGraph
from repository.course_repo import SQLiteCourseRepository
from services.course_service import CourseService
from repository.database import Database


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.initialize()
    return database


@pytest.fixture
def service(db):
    repo  = SQLiteCourseRepository(db)
    graph = CourseGraph()
    return CourseService(repo, graph)


@pytest.fixture
def sample_course():
    return Course(
        code       = "CS101",
        name       = "Intro to Programming",
        difficulty = DifficultyLevel.BEGINNER,
        duration   = 30,
        status     = CourseStatus.PUBLISHED,
    )


@pytest.fixture
def saved_course(service, sample_course):
    return service.create_course(sample_course)


class TestCourseCreation:

    def test_create_course(self, service, sample_course):
        saved = service.create_course(sample_course)
        assert saved.code == "CS101"

    def test_create_course_added_to_graph(self, service, sample_course):
        service.create_course(sample_course)
        assert service.get_graph().has_course("CS101")

    def test_create_duplicate_raises(self, service, saved_course):
        duplicate = Course(
            "CS101", "Duplicate", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        )
        with pytest.raises(ValidationError):
            service.create_course(duplicate)


class TestCourseRead:

    def test_get_course_found(self, service, saved_course):
        found = service.get_course("CS101")
        assert found is not None
        assert found.code == "CS101"

    def test_get_course_not_found_returns_none(self, service):
        assert service.get_course("UNKNOWN") is None

    def test_get_all_courses(self, service, saved_course):
        courses = service.get_all_courses()
        assert len(courses) == 1

    def test_get_available_courses(self, service):
        # PUBLISHED
        published = Course(
            "CS101", "A", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        )
        # DRAFT
        draft = Course(
            "CS102", "B", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.DRAFT
        )
        service.create_course(published)
        service.create_course(draft)
        available = service.get_available_courses()
        codes = [c.code for c in available]
        assert "CS101" in codes
        assert "CS102" not in codes

    def test_course_exists_true(self, service, saved_course):
        assert service.course_exists("CS101") is True

    def test_course_exists_false(self, service):
        assert service.course_exists("UNKNOWN") is False


class TestCourseUpdate:

    def test_update_course(self, service, saved_course):
        saved_course.name = "Updated Name"
        service.update_course(saved_course)
        updated = service.get_course("CS101")
        assert updated.name == "Updated Name"

    def test_update_course_not_found_raises(self, service):
        fake = Course("UNKNOWN", "A", DifficultyLevel.BEGINNER, 10,
                      status=CourseStatus.DRAFT)
        with pytest.raises(CourseNotFoundError):
            service.update_course(fake)


class TestCourseDelete:

    def test_delete_course(self, service, saved_course):
        service.delete_course("CS101")
        assert service.get_course("CS101") is None

    def test_delete_removes_from_graph(self, service, saved_course):
        service.delete_course("CS101")
        assert not service.get_graph().has_course("CS101")

    def test_delete_not_found_raises(self, service):
        with pytest.raises(CourseNotFoundError):
            service.delete_course("UNKNOWN")


class TestStatusTransitions:

    def test_publish_course(self, service):
        draft = Course(
            "CS101", "A", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.DRAFT
        )
        service.create_course(draft)
        updated = service.publish_course("CS101")
        assert updated.status == CourseStatus.PUBLISHED

    def test_publish_already_published_raises(self, service, saved_course):
        with pytest.raises(ValidationError):
            service.publish_course("CS101")

    def test_archive_course(self, service, saved_course):
        updated = service.archive_course("CS101")
        assert updated.status == CourseStatus.ARCHIVED

    def test_archive_draft_raises(self, service):
        draft = Course(
            "CS102", "B", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.DRAFT
        )
        service.create_course(draft)
        with pytest.raises(ValidationError):
            service.archive_course("CS102")

    def test_publish_not_found_raises(self, service):
        with pytest.raises(CourseNotFoundError):
            service.publish_course("UNKNOWN")

    def test_archive_not_found_raises(self, service):
        with pytest.raises(CourseNotFoundError):
            service.archive_course("UNKNOWN")


class TestPrerequisiteManagement:

    def test_add_prerequisite(self, service):
        service.create_course(Course(
            "CS101", "A", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        ))
        service.create_course(Course(
            "CS201", "B", DifficultyLevel.INTERMEDIATE, 20,
            status=CourseStatus.PUBLISHED
        ))
        service.add_prerequisite("CS201", "CS101")
        prereqs = service.get_prerequisites("CS201")
        assert "CS101" in prereqs

    def test_add_prerequisite_updates_graph(self, service):
        service.create_course(Course(
            "CS101", "A", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        ))
        service.create_course(Course(
            "CS201", "B", DifficultyLevel.INTERMEDIATE, 20,
            status=CourseStatus.PUBLISHED
        ))
        service.add_prerequisite("CS201", "CS101")
        assert service.get_graph().has_edge("CS101", "CS201")

    def test_add_prerequisite_cycle_raises(self, service):
        service.create_course(Course(
            "CS101", "A", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        ))
        service.create_course(Course(
            "CS201", "B", DifficultyLevel.INTERMEDIATE, 20,
            status=CourseStatus.PUBLISHED
        ))
        service.add_prerequisite("CS201", "CS101")
        with pytest.raises(CircularDependencyError):
            service.add_prerequisite("CS101", "CS201")

    def test_add_prerequisite_course_not_found(self, service):
        with pytest.raises(CourseNotFoundError):
            service.add_prerequisite("UNKNOWN", "CS101")

    def test_remove_prerequisite(self, service):
        service.create_course(Course(
            "CS101", "A", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        ))
        service.create_course(Course(
            "CS201", "B", DifficultyLevel.INTERMEDIATE, 20,
            status=CourseStatus.PUBLISHED
        ))
        service.add_prerequisite("CS201", "CS101")
        service.remove_prerequisite("CS201", "CS101")
        prereqs = service.get_prerequisites("CS201")
        assert "CS101" not in prereqs


class TestStudyOrder:

    def test_get_study_order(self, service):
        service.create_course(Course(
            "CS101", "A", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        ))
        service.create_course(Course(
            "CS201", "B", DifficultyLevel.INTERMEDIATE, 20,
            status=CourseStatus.PUBLISHED
        ))
        service.add_prerequisite("CS201", "CS101")
        order = service.get_study_order()
        assert order.index("CS101") < order.index("CS201")

    def test_get_course_levels(self, service):
        service.create_course(Course(
            "CS101", "A", DifficultyLevel.BEGINNER, 10,
            status=CourseStatus.PUBLISHED
        ))
        service.create_course(Course(
            "CS201", "B", DifficultyLevel.INTERMEDIATE, 20,
            status=CourseStatus.PUBLISHED
        ))
        service.add_prerequisite("CS201", "CS101")
        levels = service.get_course_levels()
        assert len(levels) == 2
        assert "CS101" in levels[0]
        assert "CS201" in levels[1]