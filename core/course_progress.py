"""
course_progress.py
------------------
Represents detailed progress tracking for a learner in a course.

UML ER Diagram (Section 10) — NEW table not in original Person 1 code:
    COURSE_PROGRESS table:
        id PK
        learner_id FK → LEARNERS.id
        course_code FK → COURSES.code
        percentage REAL
        completion_status TEXT

This model bridges the gap between the Enrollment (lifecycle state)
and fine-grained progress percentages needed by the analytics module.

UML CompletionStatus enum:
    NOT_STARTED → IN_PROGRESS → COMPLETED
                              → FAILED
"""

from datetime import datetime, timezone

from typing import Optional

from core.enums import CompletionStatus
from core.exceptions import ValidationError


class CourseProgress:
    """
    Tracks a learner's detailed progress in a specific course.

    UML ER Diagram:
        COURSE_PROGRESS
        ─────────────────
        id                PK
        learner_id        FK → LEARNERS.id
        course_code       FK → COURSES.code
        percentage        REAL  (0.0 – 100.0)
        completion_status TEXT  (CompletionStatus enum value)
        updated_at        TEXT  (ISO 8601)

    Attributes:
        id                (int)             : Database primary key
        learner_id        (int)             : FK to Learners
        course_code       (str)             : FK to Courses
        percentage        (float)           : 0.0 – 100.0
        completion_status (CompletionStatus): Current progress state
        updated_at        (datetime)        : Last update timestamp
    """

    def __init__(
        self,
        learner_id: int,
        course_code: str,
        percentage: float = 0.0,
        completion_status: CompletionStatus = CompletionStatus.NOT_STARTED,
        id: Optional[int] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.learner_id = learner_id
        self.course_code = course_code
        self.percentage = percentage
        self.completion_status = completion_status
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def validate(self) -> None:
        """
        Validate all fields.

        Rules:
            - learner_id must be set
            - course_code must be non-empty
            - percentage must be 0–100
            - completion_status must be a valid CompletionStatus

        Raises:
            ValidationError: With descriptive message.
        """
        if self.learner_id is None:
            raise ValidationError(
                "CourseProgress must have a learner_id"
            )

        if not self.course_code or not self.course_code.strip():
            raise ValidationError(
                "CourseProgress must have a course_code"
            )

        if not (0.0 <= self.percentage <= 100.0):
            raise ValidationError(
                f"Percentage must be between 0 and 100, "
                f"got {self.percentage}"
            )

        if not isinstance(self.completion_status, CompletionStatus):
            raise ValidationError(
                f"Invalid completion status '{self.completion_status}'"
            )

    def update_progress(self, new_percentage: float) -> None:
        """
        Update the progress percentage and auto-adjust status.

        Logic:
            0%        → NOT_STARTED
            1% – 99%  → IN_PROGRESS
            100%      → COMPLETED

        Args:
            new_percentage: New progress value (0–100).

        Raises:
            ValidationError: If percentage is out of range.
        """
        if not (0.0 <= new_percentage <= 100.0):
            raise ValidationError(
                f"Percentage must be between 0 and 100, "
                f"got {new_percentage}"
            )

        self.percentage = new_percentage
        self.updated_at = datetime.now(timezone.utc)

        if new_percentage == 0.0:
            self.completion_status = CompletionStatus.NOT_STARTED
        elif new_percentage >= 100.0:
            self.completion_status = CompletionStatus.COMPLETED
        else:
            self.completion_status = CompletionStatus.IN_PROGRESS

    def mark_failed(self) -> None:
        """
        Mark this progress as FAILED.

        Used when a learner does not meet passing criteria.
        """
        self.completion_status = CompletionStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "learner_id": self.learner_id,
            "course_code": self.course_code,
            "percentage": self.percentage,
            "completion_status": self.completion_status.value,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, row: dict) -> "CourseProgress":
        try:
            status = CompletionStatus(row["completion_status"])
        except ValueError:
            raise ValidationError(
                f"Unknown completion status '{row['completion_status']}'"
            )

        updated_at = row.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        return cls(
            id=row.get("id"),
            learner_id=row["learner_id"],
            course_code=row["course_code"],
            percentage=float(row["percentage"]),
            completion_status=status,
            updated_at=updated_at,
        )

    def __repr__(self) -> str:
        return (
            f"CourseProgress(learner={self.learner_id}, "
            f"course='{self.course_code}', "
            f"{self.percentage}%, "
            f"status={self.completion_status.value})"
        )   