"""
enrollment_repo.py
------------------
Abstract interface and SQLite implementation for Enrollment data access.

UML Class Diagram:
    <<interface>>
    EnrollmentRepositoryInterface
        └── SQLiteEnrollmentRepository

Also contains:
    ProgressRepositoryInterface
        └── SQLiteProgressRepository

ER Diagram tables:
    ENROLLMENTS
        id PK, learner_id FK, course_code FK,
        status, score, enrolled_at, completed_at

    COURSE_PROGRESS
        id PK, learner_id FK, course_code FK,
        percentage, completion_status, updated_at

Design decisions:
    - UNIQUE(learner_id, course_code) prevents duplicate enrollment
    - completed/current courses are derived from this table (Q3)
    - Transactions ensure enrollment + progress updates are atomic (Q14)
"""

import sqlite3
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, List

from core.enrollment import Enrollment
from core.course_progress import CourseProgress
from core.enums import EnrollmentStatus, CompletionStatus
from core.exceptions import (
    ValidationError,
    LearnerNotFoundError,
    EnrollmentError,
    DuplicateEnrollmentError,
)
from repository.database import Database

logger = logging.getLogger(__name__)


# ── Enrollment Abstract Interface ──────────────────────────────────────────────

class EnrollmentRepositoryInterface(ABC):
    """
    Abstract interface for Enrollment data access.
    """

    @abstractmethod
    def create_enrollment(self, enrollment: Enrollment) -> Enrollment:
        """
        Persist a new enrollment record.

        Args:
            enrollment: Enrollment object (id should be None).

        Returns:
            Enrollment: Same object with id assigned.

        Raises:
            DuplicateEnrollmentError: If learner already enrolled.
        """

    @abstractmethod
    def get_enrollment(self, enrollment_id: int) -> Optional[Enrollment]:
        """Retrieve enrollment by primary key."""

    @abstractmethod
    def get_enrollment_by_learner_course(
        self,
        learner_id: int,
        course_code: str
    ) -> Optional[Enrollment]:
        """
        Find a specific enrollment record.

        Args:
            learner_id  : Learner's ID.
            course_code : Course code.

        Returns:
            Enrollment if found, None otherwise.
        """

    @abstractmethod
    def get_enrollments_by_learner(
        self,
        learner_id: int
    ) -> List[Enrollment]:
        """All enrollments for a specific learner."""

    @abstractmethod
    def get_enrollments_by_course(
        self,
        course_code: str
    ) -> List[Enrollment]:
        """All enrollments for a specific course."""

    @abstractmethod
    def update_enrollment(self, enrollment: Enrollment) -> None:
        """
        Update enrollment status, score, and completed_at.

        Raises:
            LearnerNotFoundError: If enrollment id does not exist.
        """

    @abstractmethod
    def delete_enrollment(self, enrollment_id: int) -> None:
        """
        Delete an enrollment record.

        Raises:
            LearnerNotFoundError: If enrollment_id does not exist.
        """

    @abstractmethod
    def get_completed_course_codes(self, learner_id: int) -> List[str]:
        """
        Return course codes where status = COMPLETED for a learner.
        Used to derive Learner.completed_courses (Q3).
        """

    @abstractmethod
    def get_active_course_codes(self, learner_id: int) -> List[str]:
        """
        Return course codes where status IN (ENROLLED, IN_PROGRESS).
        Used to derive Learner.current_courses (Q3).
        """

    @abstractmethod
    def count_by_learner(self, learner_id: int) -> int:
        """Total enrollments for a learner."""

    @abstractmethod
    def count_by_course(self, course_code: str) -> int:
        """Total enrollments for a course."""

    @abstractmethod
    def get_all_enrollments(self) -> List[Enrollment]:
        """
        All enrollments in the system, across every learner and course.

        Used by analytics for system-wide reporting (student performance,
        score distributions, enrollment trend charts) where per-course or
        per-learner queries would require looping every course/learner.
        """


# ── Progress Abstract Interface ────────────────────────────────────────────────

class ProgressRepositoryInterface(ABC):
    """
    Abstract interface for CourseProgress data access.

    Manages the COURSE_PROGRESS table from the ER Diagram.
    """

    @abstractmethod
    def create_progress(self, progress: CourseProgress) -> CourseProgress:
        """Create a new progress record."""

    @abstractmethod
    def get_progress(
        self,
        learner_id: int,
        course_code: str
    ) -> Optional[CourseProgress]:
        """Get progress for a specific learner-course pair."""

    @abstractmethod
    def get_all_progress_by_learner(
        self,
        learner_id: int
    ) -> List[CourseProgress]:
        """All progress records for a learner."""

    @abstractmethod
    def get_all_progress(self) -> List[CourseProgress]:
        """All course_progress rows in the system, across every learner and course."""

    @abstractmethod
    def update_progress(self, progress: CourseProgress) -> None:
        """Update an existing progress record."""

    @abstractmethod
    def delete_progress(
        self,
        learner_id: int,
        course_code: str
    ) -> None:
        """Delete a progress record."""


# ── SQLite Enrollment Implementation ──────────────────────────────────────────

class SQLiteEnrollmentRepository(EnrollmentRepositoryInterface):
    """
    SQLite implementation of EnrollmentRepositoryInterface.

    This table is the source of truth for:
        - Enrollment state (ENROLLED / IN_PROGRESS / COMPLETED / CANCELLED)
        - Learner's completed_courses (derived: status=COMPLETED)
        - Learner's current_courses   (derived: status=ENROLLED or IN_PROGRESS)

    Args:
        database: Database instance.
    """

    def __init__(self, database: Database):
        self._db = database

    # ── Private Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_enrollment(row: sqlite3.Row) -> Enrollment:
        """Convert a ENROLLMENTS row to an Enrollment object."""
        return Enrollment.from_dict({
            "id":           row["id"],
            "learner_id":   row["learner_id"],
            "course_code":  row["course_code"],
            "status":       row["status"],
            "score":        row["score"],
            "enrolled_at":  row["enrolled_at"],
            "completed_at": row["completed_at"],
        })

    # ── Create ─────────────────────────────────────────────────────────────────

    def create_enrollment(self, enrollment: Enrollment) -> Enrollment:
        """
        Insert a new enrollment record.

        The UNIQUE(learner_id, course_code) constraint in the database
        prevents duplicate enrollments at the database level.

        Args:
            enrollment: Enrollment object.

        Returns:
            Enrollment: Same object with id assigned.

        Raises:
            DuplicateEnrollmentError: If already enrolled.
        """
        # Check for existing enrollment before hitting DB constraint
        existing = self.get_enrollment_by_learner_course(
            enrollment.learner_id,
            enrollment.course_code,
        )
        if existing is not None:
            raise DuplicateEnrollmentError(
                f"Learner {enrollment.learner_id} is already enrolled "
                f"in '{enrollment.course_code}' "
                f"(status: {existing.status.value})"
            )

        enrollment.validate()

        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO enrollments
                    (learner_id, course_code, status,
                     score, enrolled_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    enrollment.learner_id,
                    enrollment.course_code,
                    enrollment.status.value,
                    enrollment.score,
                    enrollment.enrolled_at.isoformat(),
                    (enrollment.completed_at.isoformat()
                     if enrollment.completed_at else None),
                )
            )
            enrollment.id = cursor.lastrowid

        logger.info(
            f"Enrolled learner {enrollment.learner_id} "
            f"in {enrollment.course_code}"
        )
        return enrollment

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_enrollment(self, enrollment_id: int) -> Optional[Enrollment]:
        """Retrieve enrollment by primary key."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM enrollments WHERE id = ?",
                (enrollment_id,)
            )
            row = cursor.fetchone()
            return self._row_to_enrollment(row) if row else None
        finally:
            conn.close()

    def get_enrollment_by_learner_course(
        self,
        learner_id: int,
        course_code: str
    ) -> Optional[Enrollment]:
        """Find enrollment for a specific learner-course pair."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM enrollments
                WHERE learner_id = ? AND course_code = ?
                """,
                (learner_id, course_code)
            )
            row = cursor.fetchone()
            return self._row_to_enrollment(row) if row else None
        finally:
            conn.close()

    def get_enrollments_by_learner(
        self,
        learner_id: int
    ) -> List[Enrollment]:
        """All enrollments for a specific learner."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM enrollments
                WHERE learner_id = ?
                ORDER BY enrolled_at DESC
                """,
                (learner_id,)
            )
            return [
                self._row_to_enrollment(row)
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_enrollments_by_course(
        self,
        course_code: str
    ) -> List[Enrollment]:
        """All enrollments for a specific course."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM enrollments
                WHERE course_code = ?
                ORDER BY enrolled_at DESC
                """,
                (course_code,)
            )
            return [
                self._row_to_enrollment(row)
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_completed_course_codes(self, learner_id: int) -> List[str]:
        """
        Return completed course codes for a learner.
        Used to derive Learner.completed_courses (Q3).
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT course_code FROM enrollments
                WHERE learner_id = ? AND status = 'COMPLETED'
                """,
                (learner_id,)
            )
            return [row["course_code"] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_active_course_codes(self, learner_id: int) -> List[str]:
        """
        Return active course codes for a learner.
        Used to derive Learner.current_courses (Q3).
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT course_code FROM enrollments
                WHERE learner_id = ?
                AND status IN ('ENROLLED', 'IN_PROGRESS')
                """,
                (learner_id,)
            )
            return [row["course_code"] for row in cursor.fetchall()]
        finally:
            conn.close()

    def count_by_learner(self, learner_id: int) -> int:
        """Total enrollments for a learner."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) as c FROM enrollments WHERE learner_id = ?",
                (learner_id,)
            )
            return cursor.fetchone()["c"]
        finally:
            conn.close()

    def count_by_course(self, course_code: str) -> int:
        """Total enrollments for a course."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT COUNT(*) as c FROM enrollments
                WHERE course_code = ?
                """,
                (course_code,)
            )
            return cursor.fetchone()["c"]
        finally:
            conn.close()

    def get_all_enrollments(self) -> List[Enrollment]:
        """All enrollments in the system, ordered by enrolled_at (oldest first)."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM enrollments ORDER BY enrolled_at ASC"
            )
            return [
                self._row_to_enrollment(row)
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    # ── Update ─────────────────────────────────────────────────────────────────

    def update_enrollment(self, enrollment: Enrollment) -> None:
        """
        Update enrollment status, score, and completed_at.

        Called when:
            - Learner starts a course (ENROLLED → IN_PROGRESS)
            - Learner completes a course (→ COMPLETED, score set)
            - Learner cancels enrollment (→ CANCELLED)

        Args:
            enrollment: Enrollment with updated fields.

        Raises:
            LearnerNotFoundError: If enrollment id does not exist.
        """
        if self.get_enrollment(enrollment.id) is None:
            raise LearnerNotFoundError(
                f"Enrollment {enrollment.id} not found"
            )

        with self._db.transaction() as conn:
            conn.execute(
                """
                UPDATE enrollments
                SET status = ?, score = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    enrollment.status.value,
                    enrollment.score,
                    (enrollment.completed_at.isoformat()
                     if enrollment.completed_at else None),
                    enrollment.id,
                )
            )

        logger.info(
            f"Updated enrollment id={enrollment.id} "
            f"status={enrollment.status.value}"
        )

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_enrollment(self, enrollment_id: int) -> None:
        """
        Delete an enrollment record.

        Raises:
            LearnerNotFoundError: If enrollment_id does not exist.
        """
        if self.get_enrollment(enrollment_id) is None:
            raise LearnerNotFoundError(
                f"Enrollment {enrollment_id} not found"
            )

        with self._db.transaction() as conn:
            conn.execute(
                "DELETE FROM enrollments WHERE id = ?",
                (enrollment_id,)
            )

        logger.info(f"Deleted enrollment id={enrollment_id}")


# ── SQLite Progress Implementation ─────────────────────────────────────────────

class SQLiteProgressRepository(ProgressRepositoryInterface):
    """
    SQLite implementation for COURSE_PROGRESS table.

    Args:
        database: Database instance.
    """

    def __init__(self, database: Database):
        self._db = database

    @staticmethod
    def _row_to_progress(row: sqlite3.Row) -> CourseProgress:
        """Convert a COURSE_PROGRESS row to a CourseProgress object."""
        return CourseProgress.from_dict({
            "id":                row["id"],
            "learner_id":        row["learner_id"],
            "course_code":       row["course_code"],
            "percentage":        row["percentage"],
            "completion_status": row["completion_status"],
            "updated_at":        row["updated_at"],
        })

    def create_progress(self, progress: CourseProgress) -> CourseProgress:
        """
        Insert a new progress record.

        Args:
            progress: CourseProgress object.

        Returns:
            CourseProgress: Same object with id assigned.
        """
        progress.validate()

        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO course_progress
                    (learner_id, course_code, percentage,
                     completion_status, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    progress.learner_id,
                    progress.course_code,
                    progress.percentage,
                    progress.completion_status.value,
                    progress.updated_at.isoformat(),
                )
            )
            progress.id = cursor.lastrowid

        logger.info(
            f"Created progress: learner={progress.learner_id}, "
            f"course={progress.course_code}"
        )
        return progress

    def get_progress(
        self,
        learner_id: int,
        course_code: str
    ) -> Optional[CourseProgress]:
        """Get progress for a specific learner-course pair."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM course_progress
                WHERE learner_id = ? AND course_code = ?
                """,
                (learner_id, course_code)
            )
            row = cursor.fetchone()
            return self._row_to_progress(row) if row else None
        finally:
            conn.close()

    def get_all_progress_by_learner(
        self,
        learner_id: int
    ) -> List[CourseProgress]:
        """All progress records for a learner."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM course_progress
                WHERE learner_id = ?
                ORDER BY course_code
                """,
                (learner_id,)
            )
            return [
                self._row_to_progress(row)
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_all_progress(self) -> List[CourseProgress]:
        """All course_progress records in the system."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM course_progress")
            return [
                self._row_to_progress(row)
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def update_progress(self, progress: CourseProgress) -> None:
        """Update an existing progress record."""
        progress.validate()

        with self._db.transaction() as conn:
            conn.execute(
                """
                UPDATE course_progress
                SET percentage = ?, completion_status = ?, updated_at = ?
                WHERE learner_id = ? AND course_code = ?
                """,
                (
                    progress.percentage,
                    progress.completion_status.value,
                    progress.updated_at.isoformat(),
                    progress.learner_id,
                    progress.course_code,
                )
            )

        logger.info(
            f"Updated progress: learner={progress.learner_id}, "
            f"course={progress.course_code}, "
            f"{progress.percentage}%"
        )

    def delete_progress(
        self,
        learner_id: int,
        course_code: str
    ) -> None:
        """Delete a progress record."""
        with self._db.transaction() as conn:
            conn.execute(
                """
                DELETE FROM course_progress
                WHERE learner_id = ? AND course_code = ?
                """,
                (learner_id, course_code)
            )