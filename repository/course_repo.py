"""
course_repo.py
--------------
Abstract interface and SQLite implementation for Course data access.

UML Class Diagram:
    <<interface>>
    CourseRepositoryInterface
        └── SQLiteCourseRepository

ER Diagram tables:
    COURSES
        code PK, name, description, difficulty, duration, status

    PREREQUISITES (junction table - Q2)
        id PK
        course_code      FK → courses.code
        prerequisite_code FK → courses.code

Design decision (Q2):
    Prerequisites are stored ONLY in the PREREQUISITES junction table.
    The courses table has NO prerequisites column.
    When loading a course, prerequisites are fetched via JOIN.
"""

import sqlite3
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Set

from core.course import Course
from core.enums import DifficultyLevel, CourseStatus
from core.exceptions import (
    ValidationError,
    CourseNotFoundError,
    CircularDependencyError,
)
from repository.database import Database

logger = logging.getLogger(__name__)


# ── Abstract Interface ─────────────────────────────────────────────────────────

class CourseRepositoryInterface(ABC):
    """
    Abstract interface defining all Course database operations.

    Follows the same Repository Pattern as Person 1's UserRepository.
    Services depend on this interface, not on SQLite directly.
    """

    @abstractmethod
    def create_course(self, course: Course) -> Course:
        """
        Persist a new course and its prerequisites.

        Args:
            course: Course object with all fields set.

        Returns:
            Course: Same object (code is already the PK, no id assigned).

        Raises:
            ValidationError: If course code already exists.
        """

    @abstractmethod
    def get_course(self, code: str) -> Optional[Course]:
        """
        Retrieve a course by its code, including prerequisites.

        Args:
            code: Course code (primary key).

        Returns:
            Course if found (with prerequisites loaded), None otherwise.
        """

    @abstractmethod
    def get_all_courses(self) -> List[Course]:
        """
        Retrieve all courses with prerequisites loaded.

        Returns:
            list[Course]: All courses.
        """

    @abstractmethod
    def update_course(self, course: Course) -> None:
        """
        Update an existing course's fields and prerequisites.

        Args:
            course: Course with updated fields.

        Raises:
            CourseNotFoundError: If course code does not exist.
        """

    @abstractmethod
    def delete_course(self, code: str) -> None:
        """
        Delete a course and all its prerequisites.

        Args:
            code: Course code to delete.

        Raises:
            CourseNotFoundError: If code does not exist.
        """

    @abstractmethod
    def add_prerequisite(self, course_code: str, prereq_code: str) -> None:
        """
        Add a prerequisite relationship to the junction table.

        Args:
            course_code: The course that has the prerequisite.
            prereq_code: The course that must be completed first.

        Raises:
            CourseNotFoundError: If either code does not exist.
        """

    @abstractmethod
    def remove_prerequisite(self, course_code: str, prereq_code: str) -> None:
        """
        Remove a prerequisite from the junction table.

        Args:
            course_code: The course to modify.
            prereq_code: The prerequisite to remove.
        """

    @abstractmethod
    def get_prerequisites(self, course_code: str) -> Set[str]:
        """
        Get all direct prerequisites for a course.

        Args:
            course_code: The course to look up.

        Returns:
            set[str]: Prerequisite course codes.
        """

    @abstractmethod
    def find_by_status(self, status: CourseStatus) -> List[Course]:
        """
        Retrieve all courses with a specific status.

        Args:
            status: CourseStatus to filter by.

        Returns:
            list[Course]: Matching courses.
        """

    @abstractmethod
    def find_by_difficulty(self, difficulty: DifficultyLevel) -> List[Course]:
        """
        Retrieve all courses at a specific difficulty level.

        Args:
            difficulty: DifficultyLevel to filter by.

        Returns:
            list[Course]: Matching courses.
        """

    @abstractmethod
    def course_exists(self, code: str) -> bool:
        """
        Check whether a course code exists.

        Args:
            code: Course code to check.

        Returns:
            bool: True if exists.
        """

    @abstractmethod
    def count(self) -> int:
        """Total number of courses."""


# ── SQLite Implementation ──────────────────────────────────────────────────────

class SQLiteCourseRepository(CourseRepositoryInterface):
    """
    SQLite implementation of CourseRepositoryInterface.

    Prerequisites are managed in the PREREQUISITES junction table.
    Every course load automatically fetches its prerequisites.

    Args:
        database: Database instance providing connections.
    """

    def __init__(self, database: Database):
        self._db = database

    # ── Private Helpers ────────────────────────────────────────────────────────

    def _row_to_course(
        self,
        row: sqlite3.Row,
        prerequisites: Set[str]
    ) -> Course:
        """
        Convert a COURSES row + prerequisites set into a Course object.

        Args:
            row          : sqlite3.Row from courses table.
            prerequisites: Set of prerequisite codes already fetched.

        Returns:
            Course: Fully populated Course object.
        """
        return Course.from_dict({
            "code":          row["code"],
            "name":          row["name"],
            "description":   row["description"],
            "difficulty":    row["difficulty"],
            "duration":      row["duration"],
            "status":        row["status"],
            "prerequisites": prerequisites,
        })

    def _fetch_prerequisites(
        self,
        conn: sqlite3.Connection,
        course_code: str
    ) -> Set[str]:
        """
        Fetch all prerequisite codes for a course from the junction table.

        Args:
            conn       : Active database connection.
            course_code: Course to look up.

        Returns:
            set[str]: Set of prerequisite course codes.
        """
        cursor = conn.execute(
            "SELECT prerequisite_code FROM prerequisites "
            "WHERE course_code = ?",
            (course_code,)
        )
        return {row["prerequisite_code"] for row in cursor.fetchall()}

    # ── Create ─────────────────────────────────────────────────────────────────

    def create_course(self, course: Course) -> Course:
        """
        Insert a new course and all its prerequisites atomically.

        Both the courses row and all prerequisite rows are inserted
        inside a single transaction — either all succeed or none do.

        Args:
            course: Course object to persist.

        Returns:
            Course: The same object (unchanged, code is already PK).

        Raises:
            ValidationError: If course code already exists.
        """
        if self.course_exists(course.code):
            raise ValidationError(
                f"Course '{course.code}' already exists"
            )

        course.validate()

        with self._db.transaction() as conn:
            # Insert main course record
            conn.execute(
                """
                INSERT INTO courses
                    (code, name, description, difficulty, duration, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    course.code,
                    course.name,
                    course.description,
                    course.difficulty.value,
                    course.duration,
                    course.status.value,
                )
            )

            # Insert all prerequisites into junction table
            for prereq_code in course.prerequisites:
                conn.execute(
                    """
                    INSERT INTO prerequisites (course_code, prerequisite_code)
                    VALUES (?, ?)
                    """,
                    (course.code, prereq_code)
                )

        logger.info(
            f"Created course: {course.code} "
            f"with {len(course.prerequisites)} prerequisites"
        )
        return course

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_course(self, code: str) -> Optional[Course]:
        """
        Retrieve a course with all prerequisites loaded.

        Args:
            code: Course code (PK).

        Returns:
            Course with prerequisites set, or None if not found.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM courses WHERE code = ?",
                (code,)
            )
            row = cursor.fetchone()
            if row is None:
                return None

            prerequisites = self._fetch_prerequisites(conn, code)
            return self._row_to_course(row, prerequisites)
        finally:
            conn.close()

    def get_all_courses(self) -> List[Course]:
        """
        Retrieve all courses with prerequisites.

        Returns:
            list[Course]: All courses, ordered by code.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM courses ORDER BY code"
            )
            rows = cursor.fetchall()
            courses = []
            for row in rows:
                prerequisites = self._fetch_prerequisites(conn, row["code"])
                courses.append(self._row_to_course(row, prerequisites))
            return courses
        finally:
            conn.close()

    def find_by_status(self, status: CourseStatus) -> List[Course]:
        """
        Retrieve all courses with a specific status.

        Args:
            status: CourseStatus to filter by.

        Returns:
            list[Course]: Matching courses with prerequisites.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM courses WHERE status = ? ORDER BY code",
                (status.value,)
            )
            rows = cursor.fetchall()
            courses = []
            for row in rows:
                prerequisites = self._fetch_prerequisites(conn, row["code"])
                courses.append(self._row_to_course(row, prerequisites))
            return courses
        finally:
            conn.close()

    def find_by_difficulty(self, difficulty: DifficultyLevel) -> List[Course]:
        """
        Retrieve all courses at a specific difficulty level.

        Args:
            difficulty: DifficultyLevel to filter by.

        Returns:
            list[Course]: Matching courses with prerequisites.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM courses WHERE difficulty = ? ORDER BY code",
                (difficulty.value,)
            )
            rows = cursor.fetchall()
            courses = []
            for row in rows:
                prerequisites = self._fetch_prerequisites(conn, row["code"])
                courses.append(self._row_to_course(row, prerequisites))
            return courses
        finally:
            conn.close()

    def course_exists(self, code: str) -> bool:
        """Check if a course code exists."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM courses WHERE code = ?",
                (code,)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def count(self) -> int:
        """Total number of courses."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) as c FROM courses")
            return cursor.fetchone()["c"]
        finally:
            conn.close()

    # ── Update ─────────────────────────────────────────────────────────────────

    def update_course(self, course: Course) -> None:
        """
        Update course fields and replace all prerequisites atomically.

        Strategy for prerequisites:
            1. Delete all existing prerequisites for this course
            2. Insert the new set
        This is simpler and safer than diffing old vs new sets.

        Args:
            course: Course with updated fields.

        Raises:
            CourseNotFoundError: If course code does not exist.
        """
        if not self.course_exists(course.code):
            raise CourseNotFoundError(
                f"Course '{course.code}' not found"
            )

        course.validate()

        with self._db.transaction() as conn:
            # Update main course fields
            conn.execute(
                """
                UPDATE courses
                SET name = ?, description = ?, difficulty = ?,
                    duration = ?, status = ?
                WHERE code = ?
                """,
                (
                    course.name,
                    course.description,
                    course.difficulty.value,
                    course.duration,
                    course.status.value,
                    course.code,
                )
            )

            # Replace all prerequisites
            conn.execute(
                "DELETE FROM prerequisites WHERE course_code = ?",
                (course.code,)
            )
            for prereq_code in course.prerequisites:
                conn.execute(
                    """
                    INSERT INTO prerequisites (course_code, prerequisite_code)
                    VALUES (?, ?)
                    """,
                    (course.code, prereq_code)
                )

        logger.info(f"Updated course: {course.code}")

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_course(self, code: str) -> None:
        """
        Delete a course and cascade to prerequisites and enrollments.

        ON DELETE CASCADE handles:
            - prerequisites rows where course_code = code
            - enrollments rows where course_code = code
            - course_progress rows where course_code = code

        Args:
            code: Course code to delete.

        Raises:
            CourseNotFoundError: If code does not exist.
        """
        if not self.course_exists(code):
            raise CourseNotFoundError(f"Course '{code}' not found")

        with self._db.transaction() as conn:
            conn.execute(
                "DELETE FROM courses WHERE code = ?",
                (code,)
            )

        logger.info(f"Deleted course: {code}")

    # ── Prerequisite Management ────────────────────────────────────────────────

    def add_prerequisite(self, course_code: str, prereq_code: str) -> None:
        """
        Add a prerequisite row to the junction table.

        Args:
            course_code: Course that has the prerequisite.
            prereq_code: Course that must be completed first.

        Raises:
            CourseNotFoundError: If either code does not exist.
        """
        if not self.course_exists(course_code):
            raise CourseNotFoundError(
                f"Course '{course_code}' not found"
            )
        if not self.course_exists(prereq_code):
            raise CourseNotFoundError(
                f"Prerequisite course '{prereq_code}' not found"
            )

        with self._db.transaction() as conn:
            # INSERT OR IGNORE: safe if relationship already exists
            conn.execute(
                """
                INSERT OR IGNORE INTO prerequisites
                    (course_code, prerequisite_code)
                VALUES (?, ?)
                """,
                (course_code, prereq_code)
            )

        logger.info(f"Added prerequisite: {prereq_code} → {course_code}")

    def remove_prerequisite(self, course_code: str, prereq_code: str) -> None:
        """
        Remove a prerequisite from the junction table.

        Safe to call even if the relationship doesn't exist.

        Args:
            course_code: Course to modify.
            prereq_code: Prerequisite to remove.
        """
        with self._db.transaction() as conn:
            conn.execute(
                """
                DELETE FROM prerequisites
                WHERE course_code = ? AND prerequisite_code = ?
                """,
                (course_code, prereq_code)
            )

        logger.info(
            f"Removed prerequisite: {prereq_code} → {course_code}"
        )

    def get_prerequisites(self, course_code: str) -> Set[str]:
        """
        Get all direct prerequisite codes for a course.

        Args:
            course_code: Course to look up.

        Returns:
            set[str]: Prerequisite course codes.
        """
        conn = self._db.get_connection()
        try:
            return self._fetch_prerequisites(conn, course_code)
        finally:
            conn.close()