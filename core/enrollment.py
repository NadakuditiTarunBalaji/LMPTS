"""
enrollment.py
-------------
Represents the relationship between a Learner and a Course.

UML Class Diagram:
    ┌──────────────────────────┐
    │      Enrollment          │
    ├──────────────────────────┤
    │ id: int                  │
    │ learner_id: int          │
    │ course_code: str         │
    │ status: EnrollmentStatus │
    │ score: float             │
    │ enrolled_at: datetime    │
    │ completed_at: datetime   │
    ├──────────────────────────┤
    │ complete()               │
    │ cancel()                 │
    │ validate()               │
    └──────────────────────────┘

UML Relationships:
    Learner 1──* Enrollment
    Course  1──* Enrollment

UML State Diagram (Section 9):
    ┌──────────┐
    │ ENROLLED │
    └────┬─────┘
         │ start()
    ┌────▼──────────┐
    │  IN_PROGRESS  │
    └───┬───────┬───┘
        │       │
   complete() cancel()
        │       │
    ┌───▼───┐ ┌─▼────────┐
    │COMPLETED│ │CANCELLED │
    └────────┘ └──────────┘

UML ER Diagram (Section 10):
    ENROLLMENTS table:
        id PK, learner_id FK, course_code FK,
        status, score, enrolled_at
"""

from datetime import datetime, timezone
from typing import Optional

from core.enums import EnrollmentStatus
from core.exceptions import ValidationError, EnrollmentError


class Enrollment:
    """
    Records one learner's participation in one course.

    UML State Diagram lifecycle:
        ENROLLED → IN_PROGRESS → COMPLETED
                                → CANCELLED
        ENROLLED → CANCELLED (direct cancellation also allowed)

    Attributes:
        id           (int)              : Database primary key
        learner_id   (int)              : FK to Learners
        course_code  (str)              : FK to Courses
        status       (EnrollmentStatus) : Current lifecycle state
        score        (float | None)     : Final score 0–100
        enrolled_at  (datetime)         : When enrollment was created
        completed_at (datetime | None)  : When course was finished/cancelled
    """

    def __init__(
        self,
        learner_id: int,
        course_code: str,
        status: EnrollmentStatus = EnrollmentStatus.ENROLLED,
        score: Optional[float] = None,
        id: Optional[int] = None,
        enrolled_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        """
        Create an Enrollment record.

        Args:
            learner_id   : ID of the learner
            course_code  : Code of the course
            status       : Initial status (defaults to ENROLLED)
            score        : Final score (leave None on creation)
            id           : DB primary key (None for new records)
            enrolled_at  : Defaults to now
timezone.utc            completed_at : Set when course finishes

        Example:
            enrollment = Enrollment(learner_id=7, course_code="CS201")
        """
        self.id = id
        self.learner_id = learner_id
        self.course_code = course_code
        self.status = status
        self.score = score
        self.enrolled_at = enrolled_at or datetime.now(timezone.utc)
        self.completed_at = completed_at

    # ── Validation ─────────────────────────────────────────────────────────────

    def validate(self) -> None:
        """
        Verify that the enrollment record is internally consistent.

        UML Validation Rules:
            - learner_id must be set (not None)
            - course_code must be non-empty
            - status must be a valid EnrollmentStatus
            - score (if present) must be 0-100

        Raises:
            ValidationError: With descriptive message.
        """
        if self.learner_id is None:
            raise ValidationError("Enrollment must have a learner_id")

        if not self.course_code or not self.course_code.strip():
            raise ValidationError("Enrollment must have a course_code")

        if not isinstance(self.status, EnrollmentStatus):
            raise ValidationError(
                f"Invalid status '{self.status}'. "
                f"Must be an EnrollmentStatus enum value."
            )

        if self.score is not None and not (0.0 <= self.score <= 100.0):
            raise ValidationError(
                f"Score must be between 0 and 100, got {self.score}"
            )

    # ── State Transitions (UML State Diagram) ─────────────────────────────────

    def start(self) -> None:
        """
        Transition: ENROLLED → IN_PROGRESS

        UML State Diagram:
            ENROLLED ──start()──> IN_PROGRESS

        Called when the learner begins working on course content.

        Raises:
            EnrollmentError: If not in ENROLLED state.
        """
        if self.status != EnrollmentStatus.ENROLLED:
            raise EnrollmentError(
                f"Can only start an ENROLLED enrollment, "
                f"current status: {self.status.value}"
            )
        self.status = EnrollmentStatus.IN_PROGRESS

    def complete(self, score: float) -> None:
        """
        Transition: (ENROLLED | IN_PROGRESS) → COMPLETED

        UML State Diagram:
            IN_PROGRESS ──complete()──> COMPLETED

        Sets status, score, and completed_at timestamp.

        Args:
            score: Final score achieved (must be 0-100).

        Raises:
            ValidationError: If score is out of range.
            EnrollmentError: If already completed or cancelled.

        Example:
            enrollment.complete(95)
        """
        if self.status == EnrollmentStatus.COMPLETED:
            raise EnrollmentError(
                f"Enrollment for '{self.course_code}' is already completed"
            )

        if self.status == EnrollmentStatus.CANCELLED:
            raise EnrollmentError(
                f"Cannot complete a cancelled enrollment "
                f"for '{self.course_code}'"
            )

        if not (0.0 <= score <= 100.0):
            raise ValidationError(
                f"Score must be between 0 and 100, got {score}"
            )

        self.score = score
        self.status = EnrollmentStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """
        Transition: (ENROLLED | IN_PROGRESS) → CANCELLED

        UML State Diagram:
            ENROLLED    ──cancel()──> CANCELLED
            IN_PROGRESS ──cancel()──> CANCELLED

        Raises:
            EnrollmentError: If already completed or cancelled.

        Example:
            enrollment.cancel()
        """
        if self.status == EnrollmentStatus.COMPLETED:
            raise EnrollmentError(
                f"Cannot cancel a completed enrollment "
                f"for '{self.course_code}'"
            )

        if self.status == EnrollmentStatus.CANCELLED:
            raise EnrollmentError(
                f"Enrollment for '{self.course_code}' is already cancelled"
            )

        self.status = EnrollmentStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)

    # ── Serialization ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """
        Convert to a plain dictionary for storage or API responses.

        Returns:
            dict with all enrollment fields.
        """
        return {
            "id": self.id,
            "learner_id": self.learner_id,
            "course_code": self.course_code,
            "status": self.status.value,
            "score": self.score,
            "enrolled_at": self.enrolled_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at else None
            ),
        }

    @classmethod
    def from_dict(cls, row: dict) -> "Enrollment":
        """
        Reconstruct an Enrollment from a database row.

        Args:
            row: Dictionary with enrollment field keys.

        Returns:
            Enrollment: Fully populated object.

        Raises:
            ValidationError: If status value is unrecognised.
        """
        try:
            status = EnrollmentStatus(row["status"])
        except ValueError:
            raise ValidationError(
                f"Unknown enrollment status '{row['status']}'"
            )

        def parse_dt(value) -> Optional[datetime]:
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            return value

        return cls(
            id=row.get("id"),
            learner_id=row["learner_id"],
            course_code=row["course_code"],
            status=status,
            score=row.get("score"),
            enrolled_at=parse_dt(row.get("enrolled_at")),
            completed_at=parse_dt(row.get("completed_at")),
        )

    # ── Dunder Methods ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"Enrollment(id={self.id}, learner_id={self.learner_id}, "
            f"course='{self.course_code}', status={self.status.value})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Enrollment):
            return NotImplemented
        return self.id == other.id