"""
course.py
---------
Represents a learning course in the LMPTS catalogue.

UML Class Diagram:
    ┌────────────────────────────┐
    │          Course            │
    ├────────────────────────────┤
    │ code: str                  │
    │ name: str                  │
    │ description: str           │
    │ difficulty: DifficultyLevel│
    │ duration: int              │  ← UML specifies int, not float
    │ status: CourseStatus       │
    │ prerequisites: set         │  ← UML specifies set, not list
    ├────────────────────────────┤
    │ validate()                 │
    │ add_prerequisite()         │
    │ remove_prerequisite()      │
    │ has_prerequisite()         │
    │ get_prerequisites()        │
    └────────────────────────────┘

UML Relationships:
    Course ──── Course  (self-referencing prerequisite association)
    Course 1──* Enrollment

UML ER Diagram (Section 10):
    COURSES table:
        code PK, name, description, difficulty, duration, status

    PREREQUISITES junction table:
        id PK, prerequisite FK → COURSES.code, dependent FK → COURSES.code

UML Prerequisite Graph (Section 11):
    Valid:   CS101 → CS201 → CS301 → CS401
    Invalid: CS101 → CS201 → CS301 → CS101  (cycle detected by DFS)
"""

import json
from typing import Set, Optional

from core.enums import DifficultyLevel, CourseStatus
from core.exceptions import ValidationError


class Course:
    """
    One course in the LMPTS catalogue.

    Key UML design decisions:
        - prerequisites is a SET (not list) — no duplicates by design
        - duration is an INT (hours) — no fractional hours
        - Self-referencing association models the prerequisite graph

    Attributes:
        code          (str)            : Unique identifier like "CS101"
        name          (str)            : Human-readable title
        description   (str)            : Optional long description
        difficulty    (DifficultyLevel): BEGINNER / INTERMEDIATE / ADVANCED
        duration      (int)            : Length in hours (must be > 0)
        status        (CourseStatus)   : DRAFT / PUBLISHED / ARCHIVED
        prerequisites (set[str])       : Codes of courses that must be
                                         completed before enrolling
    """

    def __init__(
        self,
        code: str,
        name: str,
        difficulty: DifficultyLevel,
        duration: int,
        description: str = "",
        status: CourseStatus = CourseStatus.DRAFT,
        prerequisites: Optional[Set[str]] = None,
    ):
        """
        Create a Course object.

        Args:
            code          : Short unique code like "CS101"
            name          : Full course title
            difficulty    : DifficultyLevel enum value
            duration      : Hours to complete (int, must be > 0)
            description   : Optional detailed description
            status        : CourseStatus (defaults to DRAFT)
            prerequisites : Set of course codes required before this one

        Example:
            course = Course(
                code="CS201",
                name="Data Structures",
                difficulty=DifficultyLevel.INTERMEDIATE,
                duration=40,
                prerequisites={"CS101"},
            )
        """
        self.code = code
        self.name = name
        self.description = description
        self.difficulty = difficulty
        self.duration = int(duration)
        self.status = status
        # UML specifies set — prevents duplicates by data structure design
        self.prerequisites: Set[str] = (
            set(prerequisites) if prerequisites is not None else set()
        )

    # ── Validation ─────────────────────────────────────────────────────────────

    def validate(self) -> None:
        """
        Check that all required fields contain valid data.

        UML Validation Rules:
            - code must be non-empty
            - name must be non-empty
            - duration must be > 0  (int)
            - difficulty must be a valid DifficultyLevel
            - status must be a valid CourseStatus

        Raises:
            ValidationError: Descriptive message for first failing rule.

        Example:
            course.validate()  # silent on success
        """
        if not self.code or not self.code.strip():
            raise ValidationError("Course code cannot be empty")

        if not self.name or not self.name.strip():
            raise ValidationError("Course name cannot be empty")

        if not isinstance(self.duration, int) or self.duration <= 0:
            raise ValidationError(
                f"Duration must be a positive integer, got '{self.duration}'"
            )

        if not isinstance(self.difficulty, DifficultyLevel):
            raise ValidationError(
                f"Invalid difficulty '{self.difficulty}'. "
                f"Must be a DifficultyLevel enum value."
            )

        if not isinstance(self.status, CourseStatus):
            raise ValidationError(
                f"Invalid status '{self.status}'. "
                f"Must be a CourseStatus enum value."
            )

    # ── Prerequisite Management ────────────────────────────────────────────────

    def add_prerequisite(self, course_code: str) -> None:
        """
        Add a prerequisite course code.

        UML Class Diagram: Course ──── Course (self-association)

        This method does NOT perform cycle detection — the service
        layer (algorithms module) checks the full graph with DFS
        before calling this.

        Since prerequisites is a set, adding the same code twice
        is a safe no-op (idempotent).

        Args:
            course_code: Code of the prerequisite course.

        Raises:
            ValidationError: If code is empty or is self-referencing.

        Example:
            cs201.add_prerequisite("CS101")
        """
        if not course_code or not course_code.strip():
            raise ValidationError("Prerequisite course code cannot be empty")

        course_code = course_code.strip()

        if course_code == self.code:
            raise ValidationError(
                f"A course cannot be its own prerequisite: '{course_code}'"
            )

        # Set.add is inherently idempotent — no duplicate check needed
        self.prerequisites.add(course_code)

    def remove_prerequisite(self, course_code: str) -> None:
        """
        Remove a prerequisite from this course.

        Safe to call even if course_code is not in the set (discard).

        Args:
            course_code: Code to remove.

        Example:
            cs201.remove_prerequisite("CS101")
        """
        self.prerequisites.discard(course_code)

    def has_prerequisite(self, course_code: str) -> bool:
        """
        Check whether a specific course is a direct prerequisite.

        Args:
            course_code: The code to check.

        Returns:
            True  if in the prerequisites set
            False otherwise

        Example:
            cs201.has_prerequisite("CS101")  → True
        """
        return course_code in self.prerequisites

    def get_prerequisites(self) -> set:
        """
        Return a COPY of the prerequisites set.

        Why a copy? External code cannot mutate internal state,
        which would bypass the add/remove validation logic.

        Returns:
            set[str]: Codes of all direct prerequisite courses.

        Example:
            cs301.get_prerequisites()  → {"CS201"}
        """
        return set(self.prerequisites)

    # ── Serialization ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """
        Convert to a plain dictionary for storage or API responses.

        Prerequisites set is converted to a sorted list for
        deterministic JSON serialization.

        Returns:
            dict with all course fields.

        Example:
            course.to_dict()
            → {"code": "CS201", "name": "Data Structures",
               "description": "", "difficulty": "INTERMEDIATE",
               "duration": 40, "status": "DRAFT",
               "prerequisites": ["CS101"]}
        """
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "difficulty": self.difficulty.value,
            "duration": self.duration,
            "status": self.status.value,
            "prerequisites": sorted(self.prerequisites),
        }

    @classmethod
    def from_dict(cls, row: dict) -> "Course":
        """
        Reconstruct a Course from a database row dictionary.

        Handles prerequisites stored as:
            - JSON string (from SQLite TEXT column)
            - Python list (already parsed)
            - Python set  (already correct type)

        Args:
            row: Dictionary with course field keys.

        Returns:
            Course: Fully populated Course object.

        Raises:
            ValidationError: If difficulty or status values are unrecognised.
        """
        try:
            difficulty = DifficultyLevel(row["difficulty"])
        except ValueError:
            raise ValidationError(
                f"Unknown difficulty value '{row['difficulty']}'"
            )

        try:
            status = CourseStatus(row["status"])
        except ValueError:
            raise ValidationError(
                f"Unknown status value '{row['status']}'"
            )

        # Parse prerequisites from various storage formats
        prerequisites_raw = row.get("prerequisites", set())
        if isinstance(prerequisites_raw, str):
            prerequisites_raw = (
                json.loads(prerequisites_raw) if prerequisites_raw else []
            )
        # Convert to set regardless of input type
        prerequisites = set(prerequisites_raw)

        return cls(
            code=row["code"],
            name=row["name"],
            description=row.get("description", ""),
            difficulty=difficulty,
            duration=int(row["duration"]),
            status=status,
            prerequisites=prerequisites,
        )

    # ── Dunder Methods ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"Course(code='{self.code}', name='{self.name}', "
            f"status={self.status.value})"
        )

    def __eq__(self, other: object) -> bool:
        """Courses are equal if their codes match."""
        if not isinstance(other, Course):
            return NotImplemented
        return self.code == other.code

    def __hash__(self) -> int:
        """Allow Course objects in sets and as dict keys."""
        return hash(self.code)