"""
notification.py
---------------
System notification for users.
"""

from datetime import datetime, timezone
from typing import Optional


class NotificationType:
    INFO     = "INFO"
    SUCCESS  = "SUCCESS"
    WARNING  = "WARNING"
    ERROR    = "ERROR"


class Notification:
    """
    A notification message for a user.

    Used to inform learners of PLR decisions,
    instructors of new requests, admins of submissions.
    """

    def __init__(
        self,
        user_id:           int,
        message:           str,
        notification_type: str = NotificationType.INFO,
        is_read:           bool = False,
        id:                Optional[int] = None,
        created_at:        Optional[datetime] = None,
    ):
        self.id                = id
        self.user_id           = user_id
        self.message           = message
        self.notification_type = notification_type
        self.is_read           = is_read
        self.created_at        = created_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id":                self.id,
            "user_id":           self.user_id,
            "message":           self.message,
            "notification_type": self.notification_type,
            "is_read":           1 if self.is_read else 0,
            "created_at":        self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, row: dict) -> "Notification":
        created_at = row.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return cls(
            id                = row.get("id"),
            user_id           = row["user_id"],
            message           = row["message"],
            notification_type = row.get("notification_type", "INFO"),
            is_read           = bool(row.get("is_read", 0)),
            created_at        = created_at,
        )