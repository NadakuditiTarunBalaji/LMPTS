"""
prior_learning_repo.py
-----------------------
Repository for Prior Learning Requests and Notifications.
"""

import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from core.prior_learning_request import PriorLearningRequest, PLRStatus
from core.notification import Notification
from repository.database import Database


class PriorLearningRepository:
    """
    SQLite repository for prior_learning_requests table.
    """

    def __init__(self, database: Database):
        self._db = database

    @staticmethod
    def _row_to_plr(row: sqlite3.Row) -> PriorLearningRequest:
        return PriorLearningRequest.from_dict(dict(row))

    # ── Create ─────────────────────────────────────────────────────────────────

    def create_request(
        self, request: PriorLearningRequest
    ) -> PriorLearningRequest:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO prior_learning_requests (
                    learner_id, course_code, pathway,
                    evidence_description, external_platform,
                    external_score, status, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.learner_id,
                    request.course_code,
                    request.pathway,
                    request.evidence_description,
                    request.external_platform,
                    request.external_score,
                    request.status,
                    request.submitted_at.isoformat(),
                )
            )
            request.id = cursor.lastrowid
        return request

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_request(self, request_id: int) -> Optional[PriorLearningRequest]:
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM prior_learning_requests WHERE id = ?",
                (request_id,)
            )
            row = cursor.fetchone()
            return self._row_to_plr(row) if row else None
        finally:
            conn.close()

    def get_by_learner(
        self, learner_id: int
    ) -> List[PriorLearningRequest]:
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM prior_learning_requests
                WHERE learner_id = ?
                ORDER BY submitted_at DESC
                """,
                (learner_id,)
            )
            return [self._row_to_plr(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_by_status(
        self, status: str
    ) -> List[PriorLearningRequest]:
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM prior_learning_requests
                WHERE status = ?
                ORDER BY submitted_at ASC
                """,
                (status,)
            )
            return [self._row_to_plr(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all(self) -> List[PriorLearningRequest]:
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM prior_learning_requests
                ORDER BY submitted_at DESC
                """
            )
            return [self._row_to_plr(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_pending_for_instructor(self) -> List[PriorLearningRequest]:
        """Requests waiting for instructor review."""
        return self.get_by_status(PLRStatus.PENDING)

    def get_pending_for_admin(self) -> List[PriorLearningRequest]:
        """Requests reviewed by instructor, waiting for admin."""
        return self.get_by_status(PLRStatus.INSTRUCTOR_REVIEWED)

    # ── Update ─────────────────────────────────────────────────────────────────

    def update_instructor_review(
        self,
        request_id:       int,
        recommendation:   str,
        instructor_note:  str,
        instructor_id:    int,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._db.transaction() as conn:
            conn.execute(
                """
                UPDATE prior_learning_requests
                SET status = ?,
                    instructor_recommendation = ?,
                    instructor_note = ?,
                    instructor_id = ?,
                    reviewed_by_instructor_at = ?
                WHERE id = ?
                """,
                (
                    PLRStatus.INSTRUCTOR_REVIEWED,
                    recommendation,
                    instructor_note,
                    instructor_id,
                    now,
                    request_id,
                )
            )

    def update_admin_decision(
        self,
        request_id: int,
        status:     str,
        admin_note: str,
        admin_id:   int,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._db.transaction() as conn:
            conn.execute(
                """
                UPDATE prior_learning_requests
                SET status = ?,
                    admin_note = ?,
                    admin_id = ?,
                    decided_by_admin_at = ?
                WHERE id = ?
                """,
                (status, admin_note, admin_id, now, request_id)
            )

    def count_pending(self) -> int:
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT COUNT(*) as c FROM prior_learning_requests
                WHERE status IN (?, ?)
                """,
                (PLRStatus.PENDING, PLRStatus.INSTRUCTOR_REVIEWED)
            )
            return cursor.fetchone()["c"]
        finally:
            conn.close()


class NotificationRepository:
    """
    SQLite repository for notifications table.
    """

    def __init__(self, database: Database):
        self._db = database

    def create(self, notification: Notification) -> Notification:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notifications
                    (user_id, message, notification_type,
                     is_read, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    notification.user_id,
                    notification.message,
                    notification.notification_type,
                    1 if notification.is_read else 0,
                    notification.created_at.isoformat(),
                )
            )
            notification.id = cursor.lastrowid
        return notification

    def get_for_user(
        self, user_id: int, unread_only: bool = False
    ) -> List[Notification]:
        conn = self._db.get_connection()
        try:
            if unread_only:
                cursor = conn.execute(
                    """
                    SELECT * FROM notifications
                    WHERE user_id = ? AND is_read = 0
                    ORDER BY created_at DESC
                    """,
                    (user_id,)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM notifications
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    """,
                    (user_id,)
                )
            return [
                Notification.from_dict(dict(row))
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def mark_all_read(self, user_id: int) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
                (user_id,)
            )

    def count_unread(self, user_id: int) -> int:
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT COUNT(*) as c FROM notifications
                WHERE user_id = ? AND is_read = 0
                """,
                (user_id,)
            )
            return cursor.fetchone()["c"]
        finally:
            conn.close()