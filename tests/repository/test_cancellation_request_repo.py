"""
test_cancellation_request_repo.py
---------------------------------
Tests for CancellationRequestRepository.
"""

import pytest
from datetime import datetime, timezone

from core.user import User
from core.course import Course
from core.learner import Learner
from core.enums import CancellationRequestStatus, UserRole, DifficultyLevel, CourseStatus
from core.cancellation_request import CancellationRequest
from core.exceptions import ValidationError
from repository.database import Database
from repository.user_repo import SQLiteUserRepository
from repository.course_repo import SQLiteCourseRepository
from repository.learner_repo import SQLiteLearnerRepository
from repository.cancellation_request_repo import (
    SQLiteCancellationRequestRepository,
)
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
def repo(db):
    return SQLiteCancellationRequestRepository(db)


def _make_learner(db, pm, username, email):
    user = SQLiteUserRepository(db).create_user(
        User(username, pm.hash_password("pass1234"), UserRole.LEARNER)
    )
    return SQLiteLearnerRepository(db).create_learner(
        Learner(name=username, email=email, user_id=user.id)
    )


@pytest.fixture
def learner1(db, pm):
    return _make_learner(db, pm, "alice", "alice@test.com")


@pytest.fixture
def learner2(db, pm):
    return _make_learner(db, pm, "bob", "bob@test.com")


@pytest.fixture
def course1(db):
    return SQLiteCourseRepository(db).create_course(
        Course("CS101", "Intro", DifficultyLevel.BEGINNER, 30,
               status=CourseStatus.PUBLISHED)
    )


@pytest.fixture
def course2(db):
    return SQLiteCourseRepository(db).create_course(
        Course("CS102", "Data Structures", DifficultyLevel.BEGINNER, 30,
               status=CourseStatus.PUBLISHED)
    )


class TestCreateRequest:

    def test_create_success(self, repo, learner1, course1):
        """Create a new cancellation request."""
        request = CancellationRequest(
            learner_id=learner1.id,
            course_code=course1.code,
            learner_note="Need more time",
        )

        created = repo.create_request(request)

        assert created.id is not None
        assert created.learner_id == learner1.id
        assert created.course_code == course1.code
        assert created.status == CancellationRequestStatus.PENDING

    def test_create_duplicate_pending_raises(self, repo, learner1, course1):
        """Cannot create duplicate PENDING requests."""
        request1 = CancellationRequest(
            learner_id=learner1.id,
            course_code=course1.code,
        )
        repo.create_request(request1)

        request2 = CancellationRequest(
            learner_id=learner1.id,
            course_code=course1.code,
        )

        with pytest.raises(ValidationError, match="duplicate"):
            repo.create_request(request2)

    def test_create_after_approved_allowed(self, repo, learner1, course1):
        """Can create new PENDING request after previous was approved."""
        request1 = CancellationRequest(
            learner_id=learner1.id,
            course_code=course1.code,
        )
        created1 = repo.create_request(request1)

        # Approve it
        created1.approve(instructor_id=2)
        repo.update_request(created1)

        # Create a new one for the same course
        request2 = CancellationRequest(
            learner_id=learner1.id,
            course_code=course1.code,
        )
        created2 = repo.create_request(request2)

        assert created2.id != created1.id
        assert created2.status == CancellationRequestStatus.PENDING


class TestGetRequest:

    def test_get_by_id(self, repo, learner1, course1):
        """Retrieve request by ID."""
        request = CancellationRequest(
            learner_id=learner1.id,
            course_code=course1.code,
        )
        created = repo.create_request(request)

        retrieved = repo.get_request(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.learner_id == learner1.id

    def test_get_nonexistent_returns_none(self, repo):
        """Nonexistent request returns None."""
        result = repo.get_request(9999)
        assert result is None


class TestGetPendingRequest:

    def test_get_pending_request(self, repo, learner1, course1):
        """Get pending request for learner+course."""
        request = CancellationRequest(
            learner_id=learner1.id,
            course_code=course1.code,
        )
        repo.create_request(request)

        pending = repo.get_pending_request(learner1.id, course1.code)

        assert pending is not None
        assert pending.learner_id == learner1.id
        assert pending.course_code == course1.code
        assert pending.status == CancellationRequestStatus.PENDING

    def test_get_pending_nonexistent_returns_none(self, repo, learner1, course1):
        """Nonexistent pending request returns None."""
        result = repo.get_pending_request(learner1.id, course1.code)
        assert result is None

    def test_get_pending_ignores_approved(self, repo, learner1, course1):
        """Get pending ignores approved requests."""
        request = CancellationRequest(
            learner_id=learner1.id,
            course_code=course1.code,
        )
        created = repo.create_request(request)

        # Approve it
        created.approve(instructor_id=2)
        repo.update_request(created)

        # Should return None for pending
        pending = repo.get_pending_request(learner1.id, course1.code)
        assert pending is None


class TestGetRequestsByLearner:

    def test_get_all_requests(self, repo, learner1, course1, course2):
        """Get all requests for a learner."""
        repo.create_request(
            CancellationRequest(learner_id=learner1.id, course_code=course1.code)
        )
        repo.create_request(
            CancellationRequest(
                learner_id=learner1.id,
                course_code=course2.code,
                status=CancellationRequestStatus.APPROVED,
            )
        )

        requests = repo.get_requests_by_learner(learner1.id)

        assert len(requests) == 2

    def test_get_requests_by_status(self, repo, learner1, course1, course2):
        """Filter requests by status."""
        repo.create_request(
            CancellationRequest(learner_id=learner1.id, course_code=course1.code)
        )
        r2 = repo.create_request(
            CancellationRequest(
                learner_id=learner1.id,
                course_code=course2.code,
                status=CancellationRequestStatus.APPROVED,
            )
        )

        # Create the request but update it to APPROVED
        r2.approve(instructor_id=2)
        repo.update_request(r2)

        pending_only = repo.get_requests_by_learner(
            learner1.id, CancellationRequestStatus.PENDING
        )

        assert len(pending_only) == 1
        assert pending_only[0].status == CancellationRequestStatus.PENDING


class TestGetPendingRequestsForInstructor:

    def test_get_all_pending(self, repo, learner1, learner2, course1, course2):
        """Get all PENDING requests across all learners."""
        repo.create_request(
            CancellationRequest(learner_id=learner1.id, course_code=course1.code)
        )
        repo.create_request(
            CancellationRequest(learner_id=learner2.id, course_code=course2.code)
        )

        pending = repo.get_pending_requests_for_instructor(None)

        assert len(pending) == 2
        assert all(r.status == CancellationRequestStatus.PENDING for r in pending)

    def test_ignores_approved_and_rejected(self, repo, learner1, learner2, course1, course2):
        """Only returns PENDING requests."""
        r1 = repo.create_request(
            CancellationRequest(learner_id=learner1.id, course_code=course1.code)
        )
        r2 = repo.create_request(
            CancellationRequest(learner_id=learner2.id, course_code=course2.code)
        )

        # Approve first one
        r1.approve(instructor_id=1)
        repo.update_request(r1)

        # Reject second one
        r2.reject(instructor_id=1)
        repo.update_request(r2)

        pending = repo.get_pending_requests_for_instructor(None)

        assert len(pending) == 0


class TestUpdateRequest:

    def test_update_status(self, repo, learner1, course1):
        """Update request status."""
        request = CancellationRequest(
            learner_id=learner1.id,
            course_code=course1.code,
        )
        created = repo.create_request(request)

        created.approve(instructor_id=2, instructor_note="Approved")
        repo.update_request(created)

        retrieved = repo.get_request(created.id)

        assert retrieved.status == CancellationRequestStatus.APPROVED
        assert retrieved.instructor_id == 2
        assert retrieved.instructor_note == "Approved"


class TestDeleteRequest:

    def test_delete_request(self, repo, learner1, course1):
        """Delete a cancellation request."""
        request = CancellationRequest(
            learner_id=learner1.id,
            course_code=course1.code,
        )
        created = repo.create_request(request)

        repo.delete_request(created.id)

        retrieved = repo.get_request(created.id)
        assert retrieved is None