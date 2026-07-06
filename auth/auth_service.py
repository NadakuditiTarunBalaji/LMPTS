"""
auth_service.py
---------------
Business logic layer for all authentication operations.

UML Class Diagram:
    ┌──────────────────────┐
    │     AuthService      │
    ├──────────────────────┤
    │ register()           │
    │ login()              │
    │ logout()             │
    │ verify_user()        │
    │ change_password()    │
    └──────────────────────┘

UML Dependencies (dashed arrows):
    AuthService ───> PasswordManager
    AuthService ───> SessionManager
    AuthService ───> UserRepository

UML Sequence Diagram (Section 5) — Login Flow:
    1. User enters credentials
    2. GUI calls AuthService.login()
    3. AuthService calls UserRepository.find_by_username()
    4. Repository queries SQLite
    5. SQLite returns user row
    6. PasswordManager.verify_password() checks bcrypt hash
    7. SessionManager.login(user) creates session
    8. Dashboard opens

UML Activity Diagram (Section 8) — Authentication:
    Start → Enter Credentials → Find User
    → [not found] → Invalid Login → End
    → [found] → Verify Password
    → [wrong] → Authentication Error → End
    → [correct] → Create Session → Open Dashboard → End

Default Users (created during initialization):
    admin   / admin123   → ADMIN
    learner / learner123 → LEARNER
    analyst / analyst123 → ANALYST
"""

from core.user import User
from core.enums import UserRole
from core.exceptions import (
    ValidationError,
    AuthenticationError,
    LearnerNotFoundError,
)
from auth.password_manager import PasswordManager
from auth.user_repository import UserRepository
from auth.session_manager import SessionManager


class AuthService:
    """
    Orchestrates authentication and user management.

    UML Component Diagram position:
        GUI → AuthService → (PasswordManager, SessionManager, UserRepository)

    Attributes:
        _repo    (UserRepository) : Data access layer (injected)
        _session (SessionManager) : Session tracker (singleton)
        _pm      (PasswordManager): Password operations
    """

    def __init__(self, user_repository: UserRepository):
        """
        Initialize with a concrete UserRepository.

        Dependency Injection: repository is passed in, not created here.
        This follows the UML dependency arrows exactly.

        Args:
            user_repository: Any object implementing UserRepository interface.
        """
        self._repo = user_repository
        self._session = SessionManager()
        self._pm = PasswordManager()

    # ── Registration ───────────────────────────────────────────────────────────

    def register(
        self,
        username: str,
        plain_password: str,
        role: UserRole = UserRole.LEARNER,
    ) -> User:
        """
        Register a new user account.

        UML Activity flow:
            Validate username → Validate password → Hash password
            → Create User → Save to repository → Return User

        Args:
            username       : Desired login name (must be unique).
            plain_password : Plain-text password (min 8 chars).
            role           : User role (defaults to LEARNER).

        Returns:
            User: Newly created User with id assigned.

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
            username=username,
            password_hash=password_hash,
            role=role,
        )
        user.validate()
        saved_user = self._repo.create_user(user)

        return saved_user

    # ── Login ──────────────────────────────────────────────────────────────────

    def login(self, username: str, plain_password: str) -> User:
        """
        Authenticate a user and start a session.

        UML Sequence Diagram (Section 5):
            Steps 2–8 are implemented here.

        UML Activity Diagram (Section 8):
            Find User → Verify Password → Create Session

        Args:
            username       : Login name.
            plain_password : Password to verify.

        Returns:
            User: The authenticated user object.

        Raises:
            AuthenticationError: If username not found or password wrong.
                                 (same message prevents enumeration)
        """
        user = self._repo.find_by_username(username)
        if user is None:
            raise AuthenticationError("Invalid username or password")

        if not self._pm.verify_password(plain_password, user.password_hash):
            raise AuthenticationError("Invalid username or password")

        self._session.login(user)
        return user

    # ── Logout ─────────────────────────────────────────────────────────────────

    def logout(self) -> None:
        """
        End the current session.

        UML Use Case: "Logout" (available to all actors)
        """
        self._session.logout()

    # ── Password Change ────────────────────────────────────────────────────────

    def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> None:
        """
        Change a user's password after verifying the old one.

        Flow:
            Get user → Verify old password → Validate new password
            → Hash new password → Persist

        Args:
            user_id      : ID of the user.
            old_password : Must match current hash.
            new_password : New plain-text password (min 8 chars).

        Raises:
            LearnerNotFoundError: If user_id not found.
            AuthenticationError : If old password wrong.
            ValidationError     : If new password too short.
        """
        user = self._repo.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User with ID {user_id} not found")

        if not self._pm.verify_password(old_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")

        if not new_password or len(new_password) < 8:
            raise ValidationError(
                "New password must be at least 8 characters long"
            )

        new_hash = self._pm.hash_password(new_password)
        self._repo.update_password(user_id, new_hash)

    # ── Verification ───────────────────────────────────────────────────────────

    def verify_user(self) -> bool:
        """
        Check whether a user is currently authenticated.

        Returns:
            True if session active, False otherwise.
        """
        return self._session.is_authenticated()

    def current_user(self) -> User | None:
        """
        Get the currently logged-in user.

        Returns:
            User if logged in, None otherwise.
        """
        return self._session.current_user()

    # ── Default Users ──────────────────────────────────────────────────────────

    def create_default_users(self) -> None:
        """
        Seed the system with required default accounts.

        UML Default Users table:
            admin   / admin123   → ADMIN
            learner / learner123 → LEARNER
            analyst / analyst123 → ANALYST

        Idempotent: safe to call multiple times.
        """
        defaults = [
            ("admin", "admin123", UserRole.ADMIN),
            ("learner", "learner123", UserRole.LEARNER),
            ("analyst", "analyst123", UserRole.ANALYST),
        ]

        for username, password, role in defaults:
            if self._repo.find_by_username(username) is None:
                self.register(username, password, role)