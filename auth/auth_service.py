"""
auth_service.py
---------------
Authentication business logic.

Handles:
    - User registration (admin-created + learner self-registration)
    - Login with account status checks (PENDING/REJECTED/INACTIVE)
    - Session management
    - Password changes
    - Default account creation
"""

import logging
from typing import Optional

from core.user import User
from core.enums import UserRole, AccountStatus
from core.exceptions import (
    ValidationError,
    AuthenticationError,
    LearnerNotFoundError,
)
from auth.password_manager import PasswordManager
from auth.user_repository import UserRepository
from auth.session_manager import SessionManager

logger = logging.getLogger(__name__)


class AuthService:
    """
    Business logic for authentication and user account management.
    """

    def __init__(self, user_repository: UserRepository):
        self._repo    = user_repository
        self._session = SessionManager()
        self._pm      = PasswordManager()

    # ── Login ──────────────────────────────────────────────────────────────────

    def login(self, username: str, plain_password: str) -> User:
        """
        Authenticate a user and start a session.

        Rejects login if account is PENDING, REJECTED, or INACTIVE.

        Raises:
            AuthenticationError: Wrong credentials or account inactive.
        """
        user = self._repo.find_by_username(username)

        if user is None:
            raise AuthenticationError("Invalid username or password")

        # Check account status BEFORE password verification
        if user.account_status == AccountStatus.PENDING:
            raise AuthenticationError(
                "PENDING: Your account is pending admin approval. "
                "Please wait for the administrator to review "
                "your registration."
            )

        if user.account_status == AccountStatus.REJECTED:
            reason = user.rejection_reason or "No reason provided"
            raise AuthenticationError(
                f"REJECTED: Your registration was rejected. "
                f"Reason: {reason}"
            )

        if user.account_status == AccountStatus.INACTIVE:
            raise AuthenticationError(
                "INACTIVE: Your account has been deactivated. "
                "Please contact the administrator."
            )

        if not user.is_active:
            raise AuthenticationError(
                "Your account is not active. "
                "Please contact the administrator."
            )

        if not self._pm.verify_password(plain_password, user.password_hash):
            raise AuthenticationError("Invalid username or password")

        self._session.login(user)
        logger.info(f"Login success: {username}")
        return user

    # ── Logout ─────────────────────────────────────────────────────────────────

    def logout(self) -> None:
        """End the current session."""
        self._session.logout()

    # ── Admin Registration (creates ACTIVE users) ─────────────────────────────

    def register(
        self,
        username:       str,
        plain_password: str,
        role:           UserRole = UserRole.LEARNER,
    ) -> User:
        """
        Register a new user (used by admin — creates ACTIVE account).

        Raises:
            ValidationError: If validation fails or username taken.
        """
        if not username or not username.strip():
            raise ValidationError("Username cannot be empty")

        username = username.strip()

        if self._repo.find_by_username(username) is not None:
            raise ValidationError(
                f"Username '{username}' is already taken"
            )

        if not plain_password or len(plain_password) < 8:
            raise ValidationError(
                "Password must be at least 8 characters long"
            )

        password_hash = self._pm.hash_password(plain_password)

        user = User(
            username         = username,
            password_hash    = password_hash,
            role             = role,
            is_active        = True,
            account_status   = AccountStatus.ACTIVE,
        )
        user.validate()
        saved_user = self._repo.create_user(user)
        logger.info(f"Admin created user: {username} ({role.value})")
        return saved_user

    # ── Learner Self-Registration (creates PENDING accounts) ──────────────────

    def register_learner(
        self,
        username:  str,
        password:  str,
        full_name: str,
        email:     str,
    ) -> User:
        """
        Self-registration for learners.

        Creates account with PENDING status.
        Admin must approve before the learner can log in.

        Raises:
            ValidationError: If validation fails.
        """
        if not username or not username.strip():
            raise ValidationError("Username cannot be empty")

        username = username.strip()

        if self._repo.find_by_username(username) is not None:
            raise ValidationError(
                f"Username '{username}' is already taken. "
                f"Please choose a different username."
            )

        if not password or len(password) < 8:
            raise ValidationError(
                "Password must be at least 8 characters long"
            )

        if not full_name or not full_name.strip():
            raise ValidationError("Full name cannot be empty")

        if not email or not email.strip():
            raise ValidationError("Email address cannot be empty")

        if "@" not in email:
            raise ValidationError("Please enter a valid email address")

        password_hash = self._pm.hash_password(password)

        user = User(
            username         = username,
            password_hash    = password_hash,
            role             = UserRole.LEARNER,
            is_active        = False,
            account_status   = AccountStatus.PENDING,
            rejection_reason = "",
            full_name        = full_name.strip(),
            email            = email.strip(),
        )
        user.validate()
        saved_user = self._repo.create_user(user)

        logger.info(
            f"New learner registration: {username} "
            f"(id={saved_user.id}) — PENDING approval"
        )
        return saved_user

    # ── Password Change ────────────────────────────────────────────────────────

    def change_password(
        self,
        user_id:      int,
        old_password: str,
        new_password: str,
    ) -> None:
        """
        Change a user's password after verifying the old one.

        Raises:
            LearnerNotFoundError: If user_id not found.
            AuthenticationError : If old password wrong.
            ValidationError     : If new password too short.
        """
        user = self._repo.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        if not self._pm.verify_password(old_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")

        if not new_password or len(new_password) < 8:
            raise ValidationError(
                "New password must be at least 8 characters long"
            )

        new_hash = self._pm.hash_password(new_password)
        self._repo.update_password(user_id, new_hash)
        logger.info(f"Password changed for user id={user_id}")

    # ── Verification ───────────────────────────────────────────────────────────

    def verify_user(self) -> bool:
        """Return True if a user is currently logged in."""
        return self._session.is_authenticated()

    def current_user(self) -> Optional[User]:
        """Return the currently logged-in user or None."""
        return self._session.current_user()

    # ── Default Users ──────────────────────────────────────────────────────────

    def create_default_users(self) -> None:
        """
        Create the default system accounts if they do not exist.

        All default accounts are created ACTIVE:
            admin      / admin123      → ADMIN
            learner    / learner123    → LEARNER
            analyst    / analyst123    → ANALYST
            instructor / instructor123 → INSTRUCTOR

        Safe to call multiple times (idempotent).
        """
        defaults = [
            ("admin",      "admin123",      UserRole.ADMIN),
            ("learner",    "learner123",    UserRole.LEARNER),
            ("analyst",    "analyst123",    UserRole.ANALYST),
            ("instructor", "instructor123", UserRole.INSTRUCTOR),
        ]

        for username, password, role in defaults:
            if self._repo.find_by_username(username) is not None:
                continue

            try:
                password_hash = self._pm.hash_password(password)
                user = User(
                    username         = username,
                    password_hash    = password_hash,
                    role             = role,
                    is_active        = True,
                    account_status   = AccountStatus.ACTIVE,
                    rejection_reason = "",
                    full_name        = f"Default {role.value.title()}",
                    email            = f"{username}@lmpts.edu",
                )
                user.validate()
                self._repo.create_user(user)
                logger.info(f"Created default user: {username}")
            except Exception as e:
                logger.warning(
                    f"Could not create default user '{username}': {e}"
                )