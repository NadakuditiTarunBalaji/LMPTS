"""
cancellation_request.py
-----------------------
Represents a learner's request to cancel a course enrollment.

Workflow:
    Learner submits (PENDING)
         ↓
    Instructor reviews → APPROVED / REJECTED
         ↓ (if APPROVED)
    Learner unenrolled
         ↓
    Learner can re-enroll
"""

from datetime import datetime, timezone
from typing import Optional
from core.enums import CancellationRequestStatus


class CancellationRequest:
    """
    A learner's request to cancel a course enrollment.

    Before a course is started, a learner can request to cancel
    their enrollment. The instructor reviews the request and can
    approve (unenroll learner) or reject (keep enrollment active).

    Attributes:
        id                    : Database primary key
        learner_id            : FK to learners
        course_code           : Course to be cancelled
        status                : Current workflow status (PENDING/APPROVED/REJECTED/WITHDRAWN)
        learner_note          : Learner's reason for cancellation
        instructor_note       : Instructor's decision comment
        instructor_id         : Instructor who reviewed
        submitted_at          : When request was submitted
        reviewed_by_instructor_at : When instructor reviewed
    """

    def __init__(
        self,
        learner_id: int,
        course_code: str,
        status: CancellationRequestStatus = CancellationRequestStatus.PENDING,
        learner_note: str = "",
        instructor_note: Optional[str] = None,
        instructor_id: Optional[int] = None,
        id: Optional[int] = None,
        submitted_at: Optional[datetime] = None,
        reviewed_by_instructor_at: Optional[datetime] = None,
    ):
        """
        Create a CancellationRequest record.

        Args:
            learner_id      : ID of the learner requesting cancellation
            course_code     : Code of the course to cancel
            status          : Current status (defaults to PENDING)
            learner_note    : Reason for cancellation
            instructor_note : Instructor's decision comments
            instructor_id   : ID of instructor who reviewed
            id              : DB primary key (None for new records)
            submitted_at    : Defaults to now
            reviewed_by_instructor_at : Set when instructor reviews
        """
        self.id = id
        self.learner_id = learner_id
        self.course_code = course_code
        self.status = status
        self.learner_note = learner_note
        self.instructor_note = instructor_note
        self.instructor_id = instructor_id
        self.submitted_at = submitted_at or datetime.now(timezone.utc)
        self.reviewed_by_instructor_at = reviewed_by_instructor_at

    def approve(self, instructor_id: int, instructor_note: str = "") -> None:
        """
        Approve the cancellation request.

        Sets status to APPROVED and records instructor details.

        Args:
            instructor_id   : ID of instructor approving
            instructor_note : Optional decision comment
        """
        self.status = CancellationRequestStatus.APPROVED
        self.instructor_id = instructor_id
        self.instructor_note = instructor_note
        self.reviewed_by_instructor_at = datetime.now(timezone.utc)

    def reject(self, instructor_id: int, instructor_note: str = "") -> None:
        """
        Reject the cancellation request.

        Sets status to REJECTED and records instructor details.
        The enrollment will continue as normal.

        Args:
            instructor_id   : ID of instructor rejecting
            instructor_note : Optional decision comment
        """
        self.status = CancellationRequestStatus.REJECTED
        self.instructor_id = instructor_id
        self.instructor_note = instructor_note
        self.reviewed_by_instructor_at = datetime.now(timezone.utc)

    def withdraw(self) -> None:
        """
        Withdraw the cancellation request (learner changes mind).

        Sets status to WITHDRAWN.
        """
        self.status = CancellationRequestStatus.WITHDRAWN

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        def fmt(dt):
            return dt.isoformat() if dt else None

        return {
            "id": self.id,
            "learner_id": self.learner_id,
            "course_code": self.course_code,
            "status": self.status.value,
            "learner_note": self.learner_note,
            "instructor_note": self.instructor_note,
            "instructor_id": self.instructor_id,
            "submitted_at": fmt(self.submitted_at),
            "reviewed_by_instructor_at": fmt(self.reviewed_by_instructor_at),
        }

    @classmethod
    def from_dict(cls, row: dict) -> "CancellationRequest":
        """Create from dictionary (from database row)."""
        def parse_dt(v):
            if isinstance(v, str):
                return datetime.fromisoformat(v)
            return v

        status_value = row.get("status", "PENDING")
        status = (
            CancellationRequestStatus[status_value]
            if isinstance(status_value, str)
            else status_value
        )

        return cls(
            id=row.get("id"),
            learner_id=row["learner_id"],
            course_code=row["course_code"],
            status=status,
            learner_note=row.get("learner_note", ""),
            instructor_note=row.get("instructor_note"),
            instructor_id=row.get("instructor_id"),
            submitted_at=parse_dt(row.get("submitted_at")),
            reviewed_by_instructor_at=parse_dt(
                row.get("reviewed_by_instructor_at")
            ),
        )

    def __repr__(self):
        return (
            f"CancellationRequest(id={self.id}, "
            f"learner={self.learner_id}, "
            f"course={self.course_code}, "
            f"status={self.status.value})"
        )
