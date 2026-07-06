"""
learner.py
----------
Represents a student in the LMPTS system.

UML Class Diagram:
    ┌──────────────────────────┐
    │        Learner           │
    ├──────────────────────────┤
    │ id: int                  │
    │ user_id: int             │
    │ name: str                │
    │ email: str               │
    │ completed_courses: set   │  ← UML specifies set
    │ current_courses: set     │  ← UML specifies set
    ├──────────────────────────┤
    │ enroll()                 │
    │ complete()               │
    │ progress()               │
    │ completion_rate()        │
    └──────────────────────────┘

UML Relationships:
    User ──── Learner  (association via user_id, NOT inheritance)
    Learner 1──* Enrollment

UML ER Diagram (Section 10):
    LEARNERS table:
        id PK, user_id FK → USERS.id, name, email
"""

import json
from typing import Set, Optional

from core.exceptions import ValidationError, EnrollmentError


class Learner:
    """
    A student's learning profile.

    UML design decisions:
        - completed_courses and current_courses are SETS (not lists)
          → prevents duplicate enrollment at the data structure level
        - Associated with User via user_id (composition, not inheritance)
        - One Learner has many Enrollments

    Attributes:
        id                (int)      : Database primary key
        user_id           (int)      : FK to Users table
        name              (str)      : Full display name
        email             (str)      : Contact email (unique)
        completed_courses (set[str]) : Course codes finished
        current_courses   (set[str]) : Course codes in progress
    """

    def __init__(
        self,
        name: str,
        email: str,
        user_id: Optional[int] = None,
        id: Optional[int] = None,
        completed_courses: Optional[Set[str]] = None,
        current_courses: Optional[Set[str]] = None,
    ):
        """
        Create a Learner profile.

        Args:
            name              : Full name (non-empty)
            email             : Email address (non-empty)
            user_id           : FK to the associated User record
            id                : Database PK (None for new profiles)
            completed_courses : Pre-loaded set of completed course codes
            current_courses   : Pre-loaded set of active course codes

        Example:
            learner = Learner(
                name="Alice Smith",
                email="alice@example.com",
                user_id=3,
            )
        """
        self.id = id
        self.user_id = user_id
        self.name = name
        self.email = email

        # UML specifies set — enforced here
        self.completed_courses: Set[str] = (
            set(completed_courses) if completed_courses is not None else set()
        )
        self.current_courses: Set[str] = (
            set(current_courses) if current_courses is not None else set()
        )

    # ── Validation ─────────────────────────────────────────────────────────────

    def validate(self) -> None:
        """
        Verify required fields.

        UML Validation Rules:
            - name must be non-empty
            - email must be non-empty

        Raises:
            ValidationError: With descriptive message.
        """
        if not self.name or not self.name.strip():
            raise ValidationError("Learner name cannot be empty")

        if not self.email or not self.email.strip():
            raise ValidationError("Learner email cannot be empty")

    # ── Course Management ──────────────────────────────────────────────────────

    def enroll(self, course_code: str) -> None:
        """
        Add a course to the learner's current (active) courses.

        UML Activity Diagram (Section 7):
            This is called AFTER prerequisite and duplicate checks pass.

        Prerequisite checking is NOT done here — that responsibility
        belongs to the EnrollmentService which has access to the
        course graph and can run DFS.

        Args:
            course_code: Code of the course to add.

        Raises:
            ValidationError: If course_code is empty.
            EnrollmentError: If already enrolled or already completed.

        Example:
            learner.enroll("CS201")
            # learner.current_courses → {"CS201"}
        """
        if not course_code or not course_code.strip():
            raise ValidationError("Course code cannot be empty")

        course_code = course_code.strip()

        if course_code in self.completed_courses:
            raise EnrollmentError(
                f"Cannot enroll: '{course_code}' is already completed"
            )

        if course_code in self.current_courses:
            raise EnrollmentError(
                f"Already enrolled in '{course_code}'"
            )

        self.current_courses.add(course_code)

    def complete(self, course_code: str) -> None:
        """
        Mark a current course as completed.

        Moves the code from current_courses → completed_courses.

        UML State Diagram (Section 9):
            IN_PROGRESS ──complete──> COMPLETED

        Args:
            course_code: Code of the course to complete.

        Raises:
            EnrollmentError: If the course is not in current_courses.

        Example:
            learner.complete("CS201")
            # current_courses   → set()
            # completed_courses → {"CS101", "CS201"}
        """
        course_code = course_code.strip() if course_code else ""

        if course_code not in self.current_courses:
            raise EnrollmentError(
                f"Cannot complete '{course_code}': not in current courses. "
                f"Current: {self.current_courses}"
            )

        self.current_courses.discard(course_code)
        self.completed_courses.add(course_code)

    # ── Progress Calculations ──────────────────────────────────────────────────

    def progress(self) -> float:
        """
        Calculate overall progress as a percentage.

        Formula:
            completed / (completed + current) * 100

        Returns:
            float: 0.0 – 100.0 (returns 0.0 if no courses enrolled)

        Example:
            completed = {"CS101"}
            current   = {"CS201", "CS301"}
            progress  = 1/3 * 100 = 33.33%
        """
        total = len(self.completed_courses) + len(self.current_courses)
        if total == 0:
            return 0.0
        return round(len(self.completed_courses) / total * 100, 2)

    def completion_rate(self) -> float:
        """
        Ratio of completed courses to total courses ever enrolled in.

        UML Class Diagram method. Alias for progress() that provides
        a semantically clear name for analytics contexts.

        Returns:
            float: 0.0 – 100.0

        Example:
            8 completed, 2 current → 80.0
        """
        return self.progress()

    # ── Serialization ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """
        Serialize to a plain dictionary.

        Sets are converted to sorted lists for deterministic
        JSON serialization.

        Returns:
            dict with all learner fields.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "completed_courses": sorted(self.completed_courses),
            "current_courses": sorted(self.current_courses),
        }

    @classmethod
    def from_dict(cls, row: dict) -> "Learner":
        """
        Reconstruct a Learner from a database row dictionary.

        Handles course sets stored as JSON strings in SQLite.

        Args:
            row: Dictionary with learner field keys.

        Returns:
            Learner: Fully populated Learner object.
        """

        def parse_set(value) -> set:
            """Convert JSON string, list, or set to Python set."""
            if isinstance(value, str):
                return set(json.loads(value)) if value else set()
            if isinstance(value, (list, tuple)):
                return set(value)
            if isinstance(value, set):
                return value
            return set()

        return cls(
            id=row.get("id"),
            user_id=row.get("user_id"),
            name=row["name"],
            email=row["email"],
            completed_courses=parse_set(row.get("completed_courses")),
            current_courses=parse_set(row.get("current_courses")),
        )

    # ── Dunder Methods ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"Learner(id={self.id}, name='{self.name}', "
            f"email='{self.email}', "
            f"completed={len(self.completed_courses)}, "
            f"current={len(self.current_courses)})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Learner):
            return NotImplemented
        return self.id == other.id