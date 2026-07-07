"""
prior_learning_service.py
--------------------------
Orchestrates the Prior Learning / Transfer Credit workflow.

Workflow:
    Learner submits → Instructor reviews → Admin decides → Credits applied
"""

from datetime import datetime, timezone
from typing import List, Optional

from core.prior_learning_request import (
    PriorLearningRequest, PLRStatus, PLRPathway
)
from core.notification import Notification, NotificationType
from core.exceptions import LearnerNotFoundError, CourseNotFoundError
from repository.prior_learning_repo import (
    PriorLearningRepository, NotificationRepository
)
from repository.learner_repo import LearnerRepositoryInterface
from repository.course_repo import CourseRepositoryInterface
from repository.user_repo import UserRepositoryInterface


class PriorLearningService:
    """
    Manages the full Prior Learning / Transfer Credit workflow.

    Responsibilities:
        - Accept learner submissions
        - Route to instructor for review
        - Route to admin for final decision
        - Apply transfer credits on approval
        - Send notifications at each stage
    """

    def __init__(
        self,
        plr_repo:          PriorLearningRepository,
        notification_repo: NotificationRepository,
        learner_repo:      LearnerRepositoryInterface,
        course_repo:       CourseRepositoryInterface,
        user_repo:         UserRepositoryInterface,
        enrollment_service,
    ):
        self._plr_repo          = plr_repo
        self._notification_repo = notification_repo
        self._learner_repo      = learner_repo
        self._course_repo       = course_repo
        self._user_repo         = user_repo
        self._enrollment_svc    = enrollment_service

    # ── Learner: Submit Request ────────────────────────────────────────────────

    def submit_request(
        self,
        learner_id:           int,
        course_code:          str,
        pathway:              str,
        evidence_description: str,
        external_platform:    str  = "",
        external_score:       Optional[float] = None,
    ) -> PriorLearningRequest:
        """
        Learner submits a prior learning request.

        Validates:
            - Learner exists
            - Course exists
            - No duplicate pending request

        Args:
            learner_id           : Learner's ID
            course_code          : Course to be credited
            pathway              : TRANSFER / ASSESSMENT / EXEMPTION
            evidence_description : Description of evidence
            external_platform    : Where course was completed
            external_score       : Score achieved externally

        Returns:
            PriorLearningRequest: The created request.

        Raises:
            LearnerNotFoundError: If learner not found.
            CourseNotFoundError : If course not found.
            ValueError          : If duplicate request exists.
        """
        if self._learner_repo.get_learner(learner_id) is None:
            raise LearnerNotFoundError(f"Learner {learner_id} not found")

        if not self._course_repo.course_exists(course_code):
            raise CourseNotFoundError(
                f"Course '{course_code}' not found"
            )

        # Check for existing pending request
        existing = self._plr_repo.get_by_learner(learner_id)
        for req in existing:
            if (req.course_code == course_code and
                    req.status in (
                        PLRStatus.PENDING,
                        PLRStatus.INSTRUCTOR_REVIEWED
                    )):
                raise ValueError(
                    f"A pending request already exists for "
                    f"'{course_code}'. Please wait for review."
                )

        request = PriorLearningRequest(
            learner_id           = learner_id,
            course_code          = course_code,
            pathway              = pathway,
            evidence_description = evidence_description,
            external_platform    = external_platform,
            external_score       = external_score,
        )

        saved = self._plr_repo.create_request(request)

        # Notify all instructors of new request
        self._notify_instructors(
            f"New prior learning request submitted for course "
            f"'{course_code}'. Please review.",
            NotificationType.INFO,
        )

        return saved

    # ── Instructor: Review Request ─────────────────────────────────────────────

    def instructor_review(
        self,
        request_id:     int,
        recommendation: str,
        note:           str,
        instructor_id:  int,
    ) -> PriorLearningRequest:
        """
        Instructor reviews a prior learning request.

        Recommendation options:
            APPROVE          → recommends approval to admin
            REJECT           → recommends rejection to admin
            INFO_REQUESTED   → asks learner for more information

        Args:
            request_id     : ID of the request to review.
            recommendation : APPROVE / REJECT / INFO_REQUESTED
            note           : Instructor's comments.
            instructor_id  : ID of the reviewing instructor.

        Returns:
            PriorLearningRequest: Updated request.
        """
        valid = ("APPROVE", "REJECT", "INFO_REQUESTED")
        if recommendation not in valid:
            raise ValueError(
                f"Recommendation must be one of {valid}"
            )

        request = self._plr_repo.get_request(request_id)
        if request is None:
            raise ValueError(f"Request {request_id} not found")

        if request.status not in (
            PLRStatus.PENDING, PLRStatus.INFO_REQUESTED
        ):
            raise ValueError(
                f"Request {request_id} is not in a reviewable state "
                f"(current: {request.status})"
            )

        self._plr_repo.update_instructor_review(
            request_id, recommendation, note, instructor_id
        )

        # Notify admin of instructor review
        self._notify_admins(
            f"Instructor has reviewed prior learning request #{request_id} "
            f"for course '{request.course_code}'. "
            f"Recommendation: {recommendation}. Please make final decision.",
            NotificationType.INFO,
        )

        # Notify learner if more info requested
        if recommendation == "INFO_REQUESTED":
            learner = self._learner_repo.get_learner(request.learner_id)
            if learner:
                user = self._user_repo.get_user(learner.user_id)
                if user:
                    self._send_notification(
                        user.id,
                        f"Your prior learning request for "
                        f"'{request.course_code}' requires additional "
                        f"information. Instructor note: {note}",
                        NotificationType.WARNING,
                    )

        return self._plr_repo.get_request(request_id)

    # ── Admin: Final Decision ──────────────────────────────────────────────────

    def admin_decision(
        self,
        request_id: int,
        decision:   str,
        note:       str,
        admin_id:   int,
    ) -> PriorLearningRequest:
        """
        Admin makes the final decision on a prior learning request.

        If APPROVED:
            - transfer_credit() is called automatically
            - Learner is notified of approval
            - Learner's prerequisites are updated

        If REJECTED:
            - Learner is notified of rejection
            - Learner must complete the course normally

        Args:
            request_id : ID of the request.
            decision   : APPROVED or REJECTED.
            note       : Admin's decision comments.
            admin_id   : ID of the deciding admin.

        Returns:
            PriorLearningRequest: Final state of request.
        """
        if decision not in (PLRStatus.APPROVED, PLRStatus.REJECTED):
            raise ValueError(
                "Decision must be APPROVED or REJECTED"
            )

        request = self._plr_repo.get_request(request_id)
        if request is None:
            raise ValueError(f"Request {request_id} not found")

        if request.status != PLRStatus.INSTRUCTOR_REVIEWED:
            raise ValueError(
                f"Request must be INSTRUCTOR_REVIEWED before admin decision "
                f"(current: {request.status})"
            )

        self._plr_repo.update_admin_decision(
            request_id, decision, note, admin_id
        )

        # Get learner's user for notification
        learner = self._learner_repo.get_learner(request.learner_id)
        learner_user_id = None
        if learner:
            user = self._user_repo.get_user(learner.user_id)
            if user:
                learner_user_id = user.id

        if decision == PLRStatus.APPROVED:
            # Automatically apply transfer credit
            try:
                self._enrollment_svc.transfer_credit(
                    request.learner_id,
                    request.course_code,
                    admin_note=note,
                )
            except Exception as e:
                print(f"Transfer credit auto-apply error: {e}")

            # Notify learner
            if learner_user_id:
                self._send_notification(
                    learner_user_id,
                    f"✅ Your prior learning request for "
                    f"'{request.course_code}' has been APPROVED. "
                    f"Transfer credit has been granted automatically. "
                    f"Admin note: {note}",
                    NotificationType.SUCCESS,
                )
        else:
            # Notify learner of rejection
            if learner_user_id:
                self._send_notification(
                    learner_user_id,
                    f"❌ Your prior learning request for "
                    f"'{request.course_code}' has been REJECTED. "
                    f"You will need to complete this course within LMPTS. "
                    f"Admin note: {note}",
                    NotificationType.WARNING,
                )

        return self._plr_repo.get_request(request_id)

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_learner_requests(
        self, learner_id: int
    ) -> List[PriorLearningRequest]:
        """All requests submitted by a learner."""
        return self._plr_repo.get_by_learner(learner_id)

    def get_pending_instructor_review(self) -> List[PriorLearningRequest]:
        """Requests waiting for instructor review."""
        return self._plr_repo.get_pending_for_instructor()

    def get_pending_admin_decision(self) -> List[PriorLearningRequest]:
        """Requests reviewed by instructor, waiting for admin."""
        return self._plr_repo.get_pending_for_admin()

    def get_all_requests(self) -> List[PriorLearningRequest]:
        """All requests (for admin overview)."""
        return self._plr_repo.get_all()

    # ── Notifications ──────────────────────────────────────────────────────────

    def _send_notification(
        self,
        user_id:           int,
        message:           str,
        notification_type: str = NotificationType.INFO,
    ) -> None:
        self._notification_repo.create(Notification(
            user_id           = user_id,
            message           = message,
            notification_type = notification_type,
        ))

    def _notify_instructors(
        self, message: str, notification_type: str
    ) -> None:
        """Send notification to all instructors."""
        from core.enums import UserRole
        instructors = self._user_repo.find_by_role(UserRole.INSTRUCTOR)
        for instructor in instructors:
            self._send_notification(
                instructor.id, message, notification_type
            )

    def _notify_admins(
        self, message: str, notification_type: str
    ) -> None:
        """Send notification to all admins."""
        from core.enums import UserRole
        admins = self._user_repo.find_by_role(UserRole.ADMIN)
        for admin in admins:
            self._send_notification(
                admin.id, message, notification_type
            )