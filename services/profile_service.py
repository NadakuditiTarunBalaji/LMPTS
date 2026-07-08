"""
profile_service.py
------------------
Business logic for user profile management.

Handles:
    - Personal information updates (name, email, bio)
    - Password changes with strong validation
    - Preferred difficulty setting
    - Profile change notifications

Workflow:
    User edits profile
        ↓
    ProfileService validates input
        ↓
    Repository saves changes
        ↓
    Notification created (for email/password changes)

Password change is treated as a security action:
    - Requires old password verification
    - New password must meet strict complexity rules
    - After success, user is forced to log in again
"""

import re
import logging
from datetime import datetime, timezone
from typing import Optional

from core.user import User
from core.enums import DifficultyLevel, UserRole
from core.notification import Notification, NotificationType
from core.exceptions import (
    ValidationError,
    AuthenticationError,
    LearnerNotFoundError,
)
from auth.password_manager import PasswordManager
from repository.user_repo import SQLiteUserRepository
from repository.learner_repo import LearnerRepositoryInterface
from repository.prior_learning_repo import NotificationRepository

logger = logging.getLogger(__name__)


# ── Password Validation Constants ─────────────────────────────────────────────

MIN_PASSWORD_LENGTH = 8


class ProfileService:
    """
    Manages user profile updates and password changes.

    Dependencies:
        user_repo         : Read/update user records
        learner_repo      : Sync learner profile when user is a learner
        notification_repo : Send notifications for security events
        password_manager  : Hash and verify passwords
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
        self._pm           = PasswordManager()

    # ── Read Profile ───────────────────────────────────────────────────────────

    def get_profile(self, user_id: int) -> User:
        """
        Return the full user profile.

        Raises:
            LearnerNotFoundError: If user does not exist.
        """
        user = self._user_repo.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")
        return user

    # ── Update Personal Info ───────────────────────────────────────────────────

    def update_personal_info(
        self,
        user_id:              int,
        full_name:            str,
        email:                str,
        bio:                  str = "",
        preferred_difficulty: Optional[DifficultyLevel] = None,
    ) -> User:
        """
        Update the user's personal profile information.

        Notifies the user via notification if their email changed.

        Args:
            user_id              : User to update.
            full_name            : Display name (required).
            email                : Contact email (required).
            bio                  : About-me description (optional).
            preferred_difficulty : DifficultyLevel preference
                                   (learners only; ignored for others).

        Returns:
            User: Updated user object.

        Raises:
            LearnerNotFoundError: If user not found.
            ValidationError     : If validation fails.
        """
        # ── Validation ─────────────────────────────────────────────────────────
        if not full_name or not full_name.strip():
            raise ValidationError("Full name cannot be empty")

        if not email or not email.strip():
            raise ValidationError("Email cannot be empty")

        if not self._is_valid_email(email):
            raise ValidationError(
                "Please enter a valid email address "
                "(e.g. user@example.com)"
            )

        if len(bio) > 500:
            raise ValidationError(
                "Bio must be 500 characters or less"
            )

        # ── Fetch current user ─────────────────────────────────────────────────
        user = self._user_repo.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        old_email = user.email
        email_changed = old_email.strip().lower() != email.strip().lower()

        # ── Default preferred_difficulty if not provided ──────────────────────
        if preferred_difficulty is None:
            preferred_difficulty = user.preferred_difficulty

        # ── Save to database ───────────────────────────────────────────────────
        self._user_repo.update_profile(
            user_id              = user_id,
            full_name            = full_name.strip(),
            email                = email.strip(),
            bio                  = bio.strip(),
            preferred_difficulty = preferred_difficulty,
        )

        # ── Sync learner profile if user is a learner ─────────────────────────
        if user.role == UserRole.LEARNER:
            self._sync_learner_profile(
                user_id, full_name.strip(), email.strip()
            )

        # ── Send notification if email changed ────────────────────────────────
        if email_changed:
            self._send_notification(
                user_id           = user_id,
                message           = (
                    f"📧 Your email address has been updated to "
                    f"'{email}'. If you did not make this change, "
                    f"please contact the administrator immediately."
                ),
                notification_type = NotificationType.INFO,
            )
            logger.info(
                f"User {user_id} changed email: "
                f"{old_email} -> {email}"
            )

        logger.info(f"Profile updated for user {user_id}")
        return self._user_repo.get_user(user_id)

    # ── Change Password ────────────────────────────────────────────────────────

    def change_password(
        self,
        user_id:      int,
        old_password: str,
        new_password: str,
    ) -> None:
        """
        Change the user's password with strong validation.

        Requirements for new password:
            - At least 8 characters
            - Contains at least one uppercase letter
            - Contains at least one digit
            - Must differ from the old password

        After success:
            - Notification is created
            - Caller (GUI) should force logout for security

        Args:
            user_id      : User changing their password.
            old_password : Current password for verification.
            new_password : New password to set.

        Raises:
            LearnerNotFoundError : If user not found.
            AuthenticationError  : If old password is wrong.
            ValidationError      : If new password fails rules.
        """
        # ── Fetch user ─────────────────────────────────────────────────────────
        user = self._user_repo.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        # ── Verify old password ────────────────────────────────────────────────
        if not self._pm.verify_password(old_password, user.password_hash):
            raise AuthenticationError(
                "Current password is incorrect"
            )

        # ── Validate new password ──────────────────────────────────────────────
        self._validate_new_password(new_password, old_password)

        # ── Hash and save ──────────────────────────────────────────────────────
        new_hash = self._pm.hash_password(new_password)
        self._user_repo.update_password(user_id, new_hash)

        # ── Send security notification ─────────────────────────────────────────
        self._send_notification(
            user_id           = user_id,
            message           = (
                f"🔒 Your password has been changed successfully. "
                f"If you did not make this change, please contact "
                f"the administrator immediately."
            ),
            notification_type = NotificationType.SUCCESS,
        )

        logger.info(f"Password changed for user {user_id}")

    # ── Password Validation ────────────────────────────────────────────────────

    def _validate_new_password(
        self, new_password: str, old_password: str
    ) -> None:
        """
        Validate new password against complexity rules.

        Rules:
            1. Length >= 8
            2. Contains at least one uppercase letter
            3. Contains at least one digit
            4. Must differ from old password

        Raises:
            ValidationError: With specific rule that failed.
        """
        if not new_password:
            raise ValidationError("New password cannot be empty")

        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f"Password must be at least "
                f"{MIN_PASSWORD_LENGTH} characters long"
            )

        if not any(c.isupper() for c in new_password):
            raise ValidationError(
                "Password must contain at least one uppercase letter"
            )

        if not any(c.isdigit() for c in new_password):
            raise ValidationError(
                "Password must contain at least one digit"
            )

        if new_password == old_password:
            raise ValidationError(
                "New password must be different from your current password"
            )

    @staticmethod
    def calculate_password_strength(password: str) -> dict:
        """
        Calculate password strength score.

        Used by GUI for the live strength meter.

        Returns:
            dict: {
                "score"    : int (0-100)
                "label"    : "Weak" / "Fair" / "Good" / "Strong"
                "colour"   : hex colour code
                "issues"   : list of unmet requirements
                "is_valid" : bool (meets all mandatory rules)
            }
        """
        if not password:
            return {
                "score":    0,
                "label":    "",
                "colour":   "#888888",
                "issues":   [],
                "is_valid": False,
            }

        score  = 0
        issues = []

        # Length
        if len(password) >= 8:  score += 25
        else: issues.append("At least 8 characters required")
        if len(password) >= 12: score += 15
        if len(password) >= 16: score += 10

        # Uppercase
        has_upper = any(c.isupper() for c in password)
        if has_upper: score += 15
        else: issues.append("Add an uppercase letter")

        # Lowercase
        has_lower = any(c.islower() for c in password)
        if has_lower: score += 10

        # Digit
        has_digit = any(c.isdigit() for c in password)
        if has_digit: score += 15
        else: issues.append("Add a digit")

        # Special character
        has_special = any(not c.isalnum() for c in password)
        if has_special: score += 10

        score = min(score, 100)

        # Label + colour
        if score < 30:
            label, colour = "Weak",   "#e74c3c"
        elif score < 60:
            label, colour = "Fair",   "#e67e22"
        elif score < 80:
            label, colour = "Good",   "#3498db"
        else:
            label, colour = "Strong", "#27ae60"

        # Meets mandatory rules?
        is_valid = (
            len(password) >= MIN_PASSWORD_LENGTH
            and has_upper
            and has_digit
        )

        return {
            "score":    score,
            "label":    label,
            "colour":   colour,
            "issues":   issues,
            "is_valid": is_valid,
        }

    # ── Internal Helpers ───────────────────────────────────────────────────────

    def _sync_learner_profile(
        self, user_id: int, name: str, email: str
    ) -> None:
        """
        When a learner changes their name/email in the user profile,
        also update their linked learner profile.
        """
        try:
            learner = self._learner_repo.get_learner_by_user_id(user_id)
            if learner:
                learner.name  = name
                learner.email = email
                self._learner_repo.update_learner(learner)
        except Exception as e:
            logger.warning(
                f"Could not sync learner profile for user {user_id}: {e}"
            )

    def _send_notification(
        self,
        user_id:           int,
        message:           str,
        notification_type: str = NotificationType.INFO,
    ) -> None:
        try:
            self._notif_repo.create(Notification(
                user_id           = user_id,
                message           = message,
                notification_type = notification_type,
            ))
        except Exception as e:
            logger.warning(f"Notification error: {e}")

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Basic email format validation."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email.strip()))