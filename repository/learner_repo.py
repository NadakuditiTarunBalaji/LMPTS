"""
learner_repo.py
---------------
Abstract interface and SQLite implementation for Learner data access.

UML Class Diagram:
    <<interface>>
    LearnerRepositoryInterface
        └── SQLiteLearnerRepository

ER Diagram table: LEARNERS
    id       PK
    user_id  FK → USERS.id
    name     NOT NULL
    email    UNIQUE NOT NULL

Design decision (Q3 + Q13):
    completed_courses and current_courses are NOT stored in LEARNERS.
    They are derived from the ENROLLMENTS table:
        completed = SELECT course_code FROM enrollments
                    WHERE learner_id=? AND status='COMPLETED'
        current   = SELECT course_code FROM enrollments
                    WHERE learner_id=? AND status IN ('ENROLLED','IN_PROGRESS')
"""

import sqlite3
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Set

from core.learner import Learner
from core.exceptions import ValidationError, LearnerNotFoundError
from repository.database import Database

logger = logging.getLogger(__name__)


# ── Abstract Interface ─────────────────────────────────────────────────────────

class LearnerRepositoryInterface(ABC):
    """
    Abstract interface for Learner data access.

    Follows the Repository Pattern from Person 1.
    Services depend on this interface, not on SQLite.
    """

    @abstractmethod
    def create_learner(self, learner: Learner) -> Learner:
        """
        Persist a new learner profile.

        Args:
            learner: Learner object (id should be None).

        Returns:
            Learner: Same object with id assigned.

        Raises:
            ValidationError: If email already exists.
        """

    @abstractmethod
    def get_learner(self, learner_id: int) -> Optional[Learner]:
        """
        Retrieve a learner by primary key.

        Returns:
            Learner with completed/current courses derived from
            ENROLLMENTS, or None if not found.
        """

    @abstractmethod
    def get_learner_by_user_id(self, user_id: int) -> Optional[Learner]:
        """
        Find a learner by their associated User ID.

        Args:
            user_id: FK to Users table.

        Returns:
            Learner if found, None otherwise.
        """

    @abstractmethod
    def get_all_learners(self) -> List[Learner]:
        """
        Retrieve all learners with their progress derived from enrollments.

        Returns:
            list[Learner]: All learner profiles.
        """

    @abstractmethod
    def update_learner(self, learner: Learner) -> None:
        """
        Update a learner's name and email.

        Args:
            learner: Learner with updated fields.

        Raises:
            LearnerNotFoundError: If learner id does not exist.
        """

    @abstractmethod
    def delete_learner(self, learner_id: int) -> None:
        """
        Delete a learner and cascade to enrollments and progress.

        Raises:
            LearnerNotFoundError: If learner_id does not exist.
        """

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[Learner]:
        """
        Find a learner by email address.

        Returns:
            Learner if found, None otherwise.
        """

    @abstractmethod
    def email_exists(self, email: str) -> bool:
        """Check whether an email is already registered."""

    @abstractmethod
    def count(self) -> int:
        """Total number of learners."""


# ── SQLite Implementation ──────────────────────────────────────────────────────

class SQLiteLearnerRepository(LearnerRepositoryInterface):
    """
    SQLite implementation of LearnerRepositoryInterface.

    Key design:
        - LEARNERS table stores only: id, user_id, name, email
        - completed_courses is derived from ENROLLMENTS (status=COMPLETED)
        - current_courses is derived from ENROLLMENTS (status=ENROLLED/IN_PROGRESS)
        - Both are returned as Python sets (matching Person 1 UML)

    Args:
        database: Database instance.
    """

    def __init__(self, database: Database):
        self._db = database

    # ── Private Helpers ────────────────────────────────────────────────────────

    def _get_completed_courses(
        self,
        conn: sqlite3.Connection,
        learner_id: int
    ) -> Set[str]:
        """
        Derive completed_courses from ENROLLMENTS table.

        Query:
            SELECT course_code FROM enrollments
            WHERE learner_id = ? AND status = 'COMPLETED'
        """
        cursor = conn.execute(
            """
            SELECT course_code FROM enrollments
            WHERE learner_id = ? AND status = 'COMPLETED'
            """,
            (learner_id,)
        )
        return {row["course_code"] for row in cursor.fetchall()}

    def _get_current_courses(
        self,
        conn: sqlite3.Connection,
        learner_id: int
    ) -> Set[str]:
        """
        Derive current_courses from ENROLLMENTS table.

        Query:
            SELECT course_code FROM enrollments
            WHERE learner_id = ?
            AND status IN ('ENROLLED', 'IN_PROGRESS')
        """
        cursor = conn.execute(
            """
            SELECT course_code FROM enrollments
            WHERE learner_id = ?
            AND status IN ('ENROLLED', 'IN_PROGRESS')
            """,
            (learner_id,)
        )
        return {row["course_code"] for row in cursor.fetchall()}

    def _row_to_learner(
        self,
        row: sqlite3.Row,
        conn: sqlite3.Connection
    ) -> Learner:
        """
        Convert a LEARNERS row to a Learner object.
        Derives completed/current courses from ENROLLMENTS.

        Args:
            row : sqlite3.Row from learners table.
            conn: Active connection (reused for enrollment queries).

        Returns:
            Learner: Fully populated object with sets derived from DB.
        """
        learner_id = row["id"]
        return Learner(
            id=learner_id,
            user_id=row["user_id"],
            name=row["name"],
            email=row["email"],
            completed_courses=self._get_completed_courses(conn, learner_id),
            current_courses=self._get_current_courses(conn, learner_id),
        )

    # ── Create ─────────────────────────────────────────────────────────────────

    def create_learner(self, learner: Learner) -> Learner:
        """
        Insert a new learner into the LEARNERS table.

        Note: completed_courses and current_courses are NOT stored here.
        They are created implicitly when Enrollment records are created.

        Args:
            learner: Learner object (id should be None).

        Returns:
            Learner: Same object with id assigned.

        Raises:
            ValidationError: If email already exists.
        """
        if self.email_exists(learner.email):
            raise ValidationError(
                f"Email '{learner.email}' is already registered"
            )

        learner.validate()

        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO learners (user_id, name, email)
                VALUES (?, ?, ?)
                """,
                (learner.user_id, learner.name, learner.email)
            )
            learner.id = cursor.lastrowid

        logger.info(
            f"Created learner: {learner.name} (id={learner.id})"
        )
        return learner

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_learner(self, learner_id: int) -> Optional[Learner]:
        """
        Retrieve a learner with courses derived from enrollments.

        Args:
            learner_id: Integer primary key.

        Returns:
            Learner if found, None otherwise.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM learners WHERE id = ?",
                (learner_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_learner(row, conn)
        finally:
            conn.close()

    def get_learner_by_user_id(self, user_id: int) -> Optional[Learner]:
        """
        Find the learner profile linked to a specific User.

        Args:
            user_id: FK to Users table.

        Returns:
            Learner if found, None otherwise.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM learners WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_learner(row, conn)
        finally:
            conn.close()

    def get_all_learners(self) -> List[Learner]:
        """
        Retrieve all learners with derived course sets.

        Returns:
            list[Learner]: All profiles ordered by id.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM learners ORDER BY id"
            )
            return [
                self._row_to_learner(row, conn)
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def find_by_email(self, email: str) -> Optional[Learner]:
        """
        Find a learner by their email address.

        Args:
            email: Email to search for.

        Returns:
            Learner if found, None otherwise.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM learners WHERE email = ?",
                (email,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_learner(row, conn)
        finally:
            conn.close()

    def email_exists(self, email: str) -> bool:
        """Check if an email is already in the database."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM learners WHERE email = ?",
                (email,)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def count(self) -> int:
        """Total number of learners."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) as c FROM learners"
            )
            return cursor.fetchone()["c"]
        finally:
            conn.close()

    # ── Update ─────────────────────────────────────────────────────────────────

    def update_learner(self, learner: Learner) -> None:
        """
        Update a learner's name and email.

        Note: completed/current courses are NOT updated here.
        They are managed through the EnrollmentRepository.

        Args:
            learner: Learner with updated name/email.

        Raises:
            LearnerNotFoundError: If learner id does not exist.
        """
        if self.get_learner(learner.id) is None:
            raise LearnerNotFoundError(
                f"Learner {learner.id} not found"
            )

        learner.validate()

        with self._db.transaction() as conn:
            conn.execute(
                """
                UPDATE learners
                SET name = ?, email = ?
                WHERE id = ?
                """,
                (learner.name, learner.email, learner.id)
            )

        logger.info(f"Updated learner id={learner.id}")

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_learner(self, learner_id: int) -> None:
        """
        Delete a learner and cascade to enrollments and progress records.

        ON DELETE CASCADE handles:
            - enrollments where learner_id = learner_id
            - course_progress where learner_id = learner_id

        Args:
            learner_id: ID to delete.

        Raises:
            LearnerNotFoundError: If learner_id does not exist.
        """
        if self.get_learner(learner_id) is None:
            raise LearnerNotFoundError(
                f"Learner {learner_id} not found"
            )

        with self._db.transaction() as conn:
            conn.execute(
                "DELETE FROM learners WHERE id = ?",
                (learner_id,)
            )

        logger.info(f"Deleted learner id={learner_id}")