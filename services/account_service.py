"""
account_service.py
------------------
Handles learner account activation workflow.

Responsibilities:
    - Process admin approval of pending registrations
    - Process admin rejection with reason
    - Request additional information
    - Create learner profile on approval
    - Send notifications

Workflow:
    Learner registers (PENDING, is_active=0)
         ↓
    Admin reviews in "Pending Registrations"
         ↓
    Admin APPROVES:
        is_active = 1
        account_status = ACTIVE
        learner profile created automatically
        notification sent to learner
         ↓
    Admin REJECTS:
        account_status = REJECTED
        rejection_reason stored
        notification sent to learner
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from core.user import User
from core.enums import AccountStatus
from core.learner import Learner
from core.notification import Notification, NotificationType
from core.exceptions import LearnerNotFoundError, ValidationError
from repository.user_repo import SQLiteUserRepository
from repository.learner_repo import LearnerRepositoryInterface
from repository.prior_learning_repo import NotificationRepository

logger = logging.getLogger(__name__)


class AccountService:
    """
    Manages learner account registration and activation.

    Dependencies:
        user_repo         : For reading/updating user accounts
        learner_repo      : For creating learner profiles on approval
        notification_repo : For sending notifications
    """

    def __init__(
        self,
        user_repo:         SQLiteUserRepository,
        learner_repo:      LearnerRepositoryInterface,
        notification_repo: NotificationRepository,
    ):
        self._user_repo    = user_repo
        self._learner_repo = learner_repo
        self._notif_repo   = notification_repo

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_pending_registrations(self) -> List[User]:
        """
        Return all users with PENDING account status.

        Used by admin Pending Registrations screen.

        Returns:
            list[User]: All pending users ordered by registration date.
        """
        return self._user_repo.get_pending_users()

    def count_pending(self) -> int:
        """
        Return count of pending registrations.

        Used for badge counter in admin sidebar.

        Returns:
            int: Number of pending accounts.
        """
        return self._user_repo.count_pending()

    def get_all_users_with_status(self) -> List[User]:
        """
        Return all users including status information.

        Returns:
            list[User]: All users.
        """
        return self._user_repo.get_all_users()

    # ── Admin Actions ──────────────────────────────────────────────────────────

    def approve_registration(
        self,
        user_id:  int,
        admin_id: int,
        note:     str = "",
    ) -> User:
        """
        Approve a pending learner registration.

        Steps:
            1. Verify user exists and is PENDING
            2. Activate account (is_active=1, status=ACTIVE)
            3. Create learner profile linked to this user
            4. Send notification to learner
            5. Return updated user

        Args:
            user_id  : ID of the pending user to approve.
            admin_id : ID of the approving admin.
            note     : Optional welcome message from admin.

        Returns:
            User: Updated user with ACTIVE status.

        Raises:
            LearnerNotFoundError: If user not found.
            ValidationError     : If user is not PENDING.
        """
        user = self._user_repo.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        if user.account_status != AccountStatus.PENDING:
            current = (
                user.account_status.value
                if hasattr(user.account_status, "value")
                else str(user.account_status)
            )
            raise ValidationError(
                f"User '{user.username}' is not in PENDING state "
                f"(current: {current})"
            )

        # Step 1: Activate the account
        self._user_repo.update_account_status(
            user_id        = user_id,
            is_active      = True,
            account_status = AccountStatus.ACTIVE,
        )

        # Step 2: Create learner profile if it does not exist
        existing_profile = self._learner_repo.get_learner_by_user_id(
            user_id
        )
        if existing_profile is None:
            learner = Learner(
                name    = user.full_name or user.username,
                email   = user.email or f"{user.username}@lmpts.edu",
                user_id = user_id,
            )
            try:
                self._learner_repo.create_learner(learner)
                logger.info(
                    f"Created learner profile for user {user_id} "
                    f"({user.username})"
                )
            except Exception as e:
                logger.warning(
                    f"Could not create learner profile for {user_id}: {e}"
                )

        # Step 3: Notify learner
        welcome = note or (
            "Welcome to LMPTS! You can now log in and start learning."
        )
        self._send_notification(
            user_id           = user_id,
            message           = (
                f"✅ Your LMPTS registration has been approved! "
                f"{welcome} "
                f"Log in with your username and password to get started."
            ),
            notification_type = NotificationType.SUCCESS,
        )

        logger.info(
            f"Admin {admin_id} approved registration for "
            f"user {user_id} ({user.username})"
        )

        return self._user_repo.get_user(user_id)

    def reject_registration(
        self,
        user_id:          int,
        admin_id:         int,
        rejection_reason: str,
    ) -> User:
        """
        Reject a pending learner registration.

        The account is kept in the database with REJECTED status.
        The rejection reason is stored and shown to the learner
        if they attempt to log in.

        Args:
            user_id          : ID of the pending user to reject.
            admin_id         : ID of the rejecting admin.
            rejection_reason : Explanation shown to the learner.

        Returns:
            User: Updated user with REJECTED status.

        Raises:
            LearnerNotFoundError: If user not found.
            ValidationError     : If user is not PENDING.
            ValidationError     : If rejection reason is empty.
        """
        if not rejection_reason or not rejection_reason.strip():
            raise ValidationError(
                "Rejection reason is required when rejecting a registration"
            )

        user = self._user_repo.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        if user.account_status != AccountStatus.PENDING:
            raise ValidationError(
                f"User '{user.username}' is not in PENDING state "
                f"(current: {user.account_status})"
            )

        # Update status to REJECTED with reason
        self._user_repo.update_account_status(
            user_id          = user_id,
            is_active        = False,
            account_status   = AccountStatus.REJECTED,
            rejection_reason = rejection_reason.strip(),
        )

        # Notify learner (they see this when they try to log in)
        self._send_notification(
            user_id           = user_id,
            message           = (
                f"❌ Your LMPTS registration has been rejected. "
                f"Reason: {rejection_reason}. "
                f"Please contact the administrator if you have questions."
            ),
            notification_type = NotificationType.WARNING,
        )

        logger.info(
            f"Admin {admin_id} rejected registration for "
            f"user {user_id} ({user.username}). "
            f"Reason: {rejection_reason}"
        )

        return self._user_repo.get_user(user_id)

    def request_more_information(
        self,
        user_id:  int,
        admin_id: int,
        message:  str,
    ) -> User:
        """
        Keep account PENDING but send a message asking for more info.

        Account stays PENDING — learner still cannot log in.
        A notification is stored for when admin checks manually.

        Args:
            user_id  : ID of the pending user.
            admin_id : ID of the requesting admin.
            message  : What additional information is needed.

        Returns:
            User: Unchanged user (still PENDING).
        """
        if not message or not message.strip():
            raise ValidationError("Message cannot be empty")

        user = self._user_repo.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        # Store the info request as a notification
        # (learner cannot log in yet, but it is recorded)
        self._send_notification(
            user_id           = user_id,
            message           = (
                f"ℹ️ The administrator needs more information about "
                f"your registration. Message: {message}. "
                f"Please contact the LMPTS administrator directly."
            ),
            notification_type = NotificationType.INFO,
        )

        logger.info(
            f"Admin {admin_id} requested more info from "
            f"user {user_id} ({user.username})"
        )

        return user

    def deactivate_user(
        self,
        user_id:  int,
        admin_id: int,
        reason:   str = "",
    ) -> None:
        """
        Deactivate an existing ACTIVE user account.

        Used to suspend a learner without deleting their data.

        Args:
            user_id  : User to deactivate.
            admin_id : Admin performing the action.
            reason   : Optional reason for deactivation.
        """
        user = self._user_repo.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        self._user_repo.update_account_status(
            user_id          = user_id,
            is_active        = False,
            account_status   = AccountStatus.INACTIVE,   # ← enum
            rejection_reason = reason,
        )

        self._send_notification(
            user_id           = user_id,
            message           = (
                f"Your LMPTS account has been deactivated. "
                + (f"Reason: {reason}. " if reason else "")
                + "Please contact the administrator for assistance."
            ),
            notification_type = NotificationType.WARNING,
        )

        logger.info(
            f"Admin {admin_id} deactivated user {user_id} ({user.username})"
        )

    def reactivate_user(self, user_id: int, admin_id: int) -> None:
        """
        Reactivate a previously deactivated or rejected account.

        Args:
            user_id  : User to reactivate.
            admin_id : Admin performing the action.
        """
        user = self._user_repo.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        self._user_repo.update_account_status(
            user_id          = user_id,
            is_active        = True,
            account_status   = AccountStatus.ACTIVE,
            rejection_reason = "",
        )

        self._send_notification(
            user_id           = user_id,
            message           = (
                "✅ Your LMPTS account has been reactivated. "
                "You can now log in."
            ),
            notification_type = NotificationType.SUCCESS,
        )

        logger.info(
            f"Admin {admin_id} reactivated user {user_id} ({user.username})"
        )

    # ── Internal ───────────────────────────────────────────────────────────────

    def _send_notification(
        self,
        user_id:           int,
        message:           str,
        notification_type: str = NotificationType.INFO,
    ) -> None:
        """Create a notification record for a user."""
        try:
            self._notif_repo.create(Notification(
                user_id           = user_id,
                message           = message,
                notification_type = notification_type,
            ))
        except Exception as e:
            logger.warning(f"Could not create notification: {e}")

    def _notify_admins(self, message: str) -> None:
        """Send notification to all admin users."""
        try:
            from core.enums import UserRole
            admins = self._user_repo.find_by_role(UserRole.ADMIN)
            for admin in admins:
                self._send_notification(
                    admin.id, message, NotificationType.INFO
                )
        except Exception as e:
            logger.warning(f"Could not notify admins: {e}")