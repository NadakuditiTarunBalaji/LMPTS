"""
cancellation_request_repo.py
----------------------------
Abstract interface and SQLite implementation for CancellationRequest data access.

Design decisions:
    - UNIQUE(learner_id, course_code, status) prevents duplicate pending requests
    - Only one active PENDING request allowed per learner+course
    - Approved/Rejected requests are kept for audit trail
"""

import sqlite3
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, List

from core.cancellation_request import CancellationRequest
from core.enums import CancellationRequestStatus
from core.exceptions import ValidationError
from repository.database import Database

logger = logging.getLogger(__name__)


# ── Cancellation Request Abstract Interface ────────────────────────────────────

class CancellationRequestRepositoryInterface(ABC):
    """
    Abstract interface for CancellationRequest data access.
    """

    @abstractmethod
    def create_request(
        self, request: CancellationRequest
    ) -> CancellationRequest:
        """
        Persist a new cancellation request.

        Args:
            request: CancellationRequest object (id should be None).

        Returns:
            CancellationRequest: Same object with id assigned.

        Raises:
            ValidationError: If duplicate pending request exists.
        """

    @abstractmethod
    def get_request(self, request_id: int) -> Optional[CancellationRequest]:
        """Retrieve request by primary key."""

    @abstractmethod
    def get_pending_request(
        self,
        learner_id: int,
        course_code: str,
    ) -> Optional[CancellationRequest]:
        """
        Find a pending cancellation request for a learner+course.

        Args:
            learner_id  : Learner's ID.
            course_code : Course code.

        Returns:
            CancellationRequest if found, None otherwise.
        """

    @abstractmethod
    def get_requests_by_learner(
        self,
        learner_id: int,
        status: Optional[CancellationRequestStatus] = None,
    ) -> List[CancellationRequest]:
        """
        Get all cancellation requests for a learner.

        Args:
            learner_id : Learner's ID.
            status     : If provided, filter by status.

        Returns:
            List of CancellationRequest objects.
        """

    @abstractmethod
    def get_pending_requests_for_instructor(
        self,
        instructor_id: int,
    ) -> List[CancellationRequest]:
        """
        Get all pending cancellation requests (for instructor review).

        Args:
            instructor_id : Instructor's ID (unused, for API consistency).

        Returns:
            List of all PENDING CancellationRequest objects.
        """

    @abstractmethod
    def update_request(self, request: CancellationRequest) -> None:
        """Update an existing cancellation request."""

    @abstractmethod
    def delete_request(self, request_id: int) -> None:
        """Delete a cancellation request."""


# ── SQLite Implementation ──────────────────────────────────────────────────────

class SQLiteCancellationRequestRepository(CancellationRequestRepositoryInterface):
    """
    SQLite implementation of CancellationRequestRepository.
    """

    def __init__(self, database: Database):
        """Initialize with database connection."""
        self._db = database

    def create_request(
        self, request: CancellationRequest
    ) -> CancellationRequest:
        """
        Persist a new cancellation request.

        Raises:
            ValidationError: If duplicate PENDING request exists.
        """
        conn = self._db.get_connection()
        try:
            # Check for existing PENDING request
            existing = self.get_pending_request(
                request.learner_id, request.course_code
            )
            if existing is not None:
                raise ValidationError(
                    f"A pending cancellation request already exists for "
                    f"learner {request.learner_id} in '{request.course_code}'. "
                    f"Cannot create duplicate."
                )

            cursor = conn.execute(
                """
                INSERT INTO cancellation_requests
                    (learner_id, course_code, status, learner_note,
                     instructor_note, instructor_id,
                     submitted_at, reviewed_by_instructor_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.learner_id,
                    request.course_code,
                    request.status.value,
                    request.learner_note,
                    request.instructor_note,
                    request.instructor_id,
                    request.submitted_at.isoformat(),
                    (
                        request.reviewed_by_instructor_at.isoformat()
                        if request.reviewed_by_instructor_at
                        else None
                    ),
                ),
            )
            request.id = cursor.lastrowid
            conn.commit()
            return request
        finally:
            conn.close()

    def get_request(self, request_id: int) -> Optional[CancellationRequest]:
        """Retrieve by primary key."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, learner_id, course_code, status, learner_note,
                       instructor_note, instructor_id,
                       submitted_at, reviewed_by_instructor_at
                FROM cancellation_requests
                WHERE id = ?
                """,
                (request_id,),
            )
            row = cursor.fetchone()
            if row:
                return CancellationRequest.from_dict(dict(row))
            return None
        finally:
            conn.close()

    def get_pending_request(
        self,
        learner_id: int,
        course_code: str,
    ) -> Optional[CancellationRequest]:
        """Find a pending cancellation request for a learner+course."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, learner_id, course_code, status, learner_note,
                       instructor_note, instructor_id,
                       submitted_at, reviewed_by_instructor_at
                FROM cancellation_requests
                WHERE learner_id = ? AND course_code = ?
                      AND status = 'PENDING'
                """,
                (learner_id, course_code),
            )
            row = cursor.fetchone()
            if row:
                return CancellationRequest.from_dict(dict(row))
            return None
        finally:
            conn.close()

    def get_requests_by_learner(
        self,
        learner_id: int,
        status: Optional[CancellationRequestStatus] = None,
    ) -> List[CancellationRequest]:
        """Get all cancellation requests for a learner."""
        conn = self._db.get_connection()
        try:
            if status:
                cursor = conn.execute(
                    """
                    SELECT id, learner_id, course_code, status, learner_note,
                           instructor_note, instructor_id,
                           submitted_at, reviewed_by_instructor_at
                    FROM cancellation_requests
                    WHERE learner_id = ? AND status = ?
                    ORDER BY submitted_at DESC
                    """,
                    (learner_id, status.value),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT id, learner_id, course_code, status, learner_note,
                           instructor_note, instructor_id,
                           submitted_at, reviewed_by_instructor_at
                    FROM cancellation_requests
                    WHERE learner_id = ?
                    ORDER BY submitted_at DESC
                    """,
                    (learner_id,),
                )
            return [
                CancellationRequest.from_dict(dict(row))
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_pending_requests_for_instructor(
        self,
        instructor_id: int,
    ) -> List[CancellationRequest]:
        """Get all pending cancellation requests."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, learner_id, course_code, status, learner_note,
                       instructor_note, instructor_id,
                       submitted_at, reviewed_by_instructor_at
                FROM cancellation_requests
                WHERE status = 'PENDING'
                ORDER BY submitted_at ASC
                """,
            )
            return [
                CancellationRequest.from_dict(dict(row))
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def update_request(self, request: CancellationRequest) -> None:
        """Update an existing cancellation request."""
        conn = self._db.get_connection()
        try:
            conn.execute(
                """
                UPDATE cancellation_requests
                SET status = ?, learner_note = ?,
                    instructor_note = ?, instructor_id = ?,
                    reviewed_by_instructor_at = ?
                WHERE id = ?
                """,
                (
                    request.status.value,
                    request.learner_note,
                    request.instructor_note,
                    request.instructor_id,
                    (
                        request.reviewed_by_instructor_at.isoformat()
                        if request.reviewed_by_instructor_at
                        else None
                    ),
                    request.id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_request(self, request_id: int) -> None:
        """Delete a cancellation request."""
        conn = self._db.get_connection()
        try:
            conn.execute(
                """
                DELETE FROM cancellation_requests
                WHERE id = ?
                """,
                (request_id,),
            )
            conn.commit()
        finally:
            conn.close()
