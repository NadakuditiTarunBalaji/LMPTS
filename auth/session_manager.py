"""
session_manager.py
------------------
Manages the currently logged-in user session.

UML Class Diagram:
    ┌──────────────────────────┐
    │  <<Singleton>>           │
    │    SessionManager        │
    ├──────────────────────────┤
    │ login()                  │
    │ logout()                 │
    │ current_user()           │
    │ is_authenticated()       │
    └──────────────────────────┘

UML Stereotype: <<Singleton>>
    Ensures exactly ONE SessionManager exists application-wide.

UML Sequence Diagram (Section 5):
    Step 7: AuthService calls SessionManager.login(user)
    → Session is created
    → Dashboard opens

Why Singleton?
    The "who is logged in?" question must have exactly one answer.
    Two SessionManagers could produce contradictory states.

Implementation:
    Python __new__ override returns the same instance on every call.
"""

from typing import Optional

from core.user import User


class SessionManager:
    """
    Singleton that tracks the active user session.

    UML: <<Singleton>> stereotype applied.

    Verification:
        s1 = SessionManager()
        s2 = SessionManager()
        assert s1 is s2  → True (same object in memory)

    Attributes (instance):
        _current_user (User | None): The logged-in user, or None.
    """

    _instance: Optional["SessionManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "SessionManager":
        """
        Singleton pattern: return existing instance if already created.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initialize state only once, even though __init__ is called
        every time SessionManager() is written.
        """
        if not SessionManager._initialized:
            self._current_user: Optional[User] = None
            SessionManager._initialized = True

    # ── Session Operations ─────────────────────────────────────────────────────

    def login(self, user: User) -> None:
        """
        Record a user as the active session.

        UML Sequence Diagram (Section 5):
            Step 7: SessionManager.login(user) called by AuthService

        Args:
            user: The authenticated User object.

        Raises:
            ValueError: If user is None.
        """
        if user is None:
            raise ValueError("Cannot log in with a None user object")
        self._current_user = user

    def logout(self) -> None:
        """
        Clear the active session.

        After this call:
            is_authenticated() → False
            current_user()     → None
        """
        self._current_user = None

    def current_user(self) -> Optional[User]:
        """
        Return the currently logged-in user.

        Returns:
            User if someone is logged in, None otherwise.
        """
        return self._current_user

    def is_authenticated(self) -> bool:
        """
        Check whether a user is currently logged in.

        Returns:
            True  if session is active.
            False if no user is logged in.
        """
        return self._current_user is not None

    # ── Testing Helper ─────────────────────────────────────────────────────────

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton for unit testing.

        WARNING: NEVER call in production code.
        """
        cls._instance = None
        cls._initialized = False

    def __repr__(self) -> str:
        user_info = (
            self._current_user.username
            if self._current_user else "No active session"
        )
        return f"SessionManager(current_user='{user_info}')"