"""
user_repository.py
------------------
Abstract interface defining all database operations for Users.

UML Class Diagram:
    ┌──────────────────────────┐
    │  <<interface>>           │
    │    UserRepository        │
    ├──────────────────────────┤
    │ create_user()            │
    │ get_user()               │
    │ find_by_username()       │
    │ update_password()        │
    │ delete_user()            │
    └──────────────────────────┘

UML Component Diagram:
    AuthService ──depends on──> UserRepository
    UserRepository ──depends on──> SQLite Database

UML Sequence Diagram (Section 5):
    Step 3: AuthService calls UserRepository.find_by_username()
    Step 4: Repository queries SQLite
    Step 5: SQLite returns user row

Pattern: Repository Pattern (decouples business logic from storage)
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from core.user import User


class UserRepository(ABC):
    """
    Abstract base class (interface) for user data access.

    UML: Marked as <<interface>> in the class diagram.

    All concrete implementations (SQLite, PostgreSQL, in-memory)
    must implement every method defined here.

    AuthService depends on this interface, NOT on any specific
    database — following the Dependency Inversion Principle.
    """

    @abstractmethod
    def create_user(self, user: User) -> User:
        """
        Persist a new User to the database.

        Implementation must:
            1. Insert the user record
            2. Set user.id to the auto-generated primary key
            3. Return the updated User object

        Args:
            user: User object with all fields except id.

        Returns:
            User: Same object with id populated.

        Raises:
            ValidationError: If username already exists.
        """

    @abstractmethod
    def get_user(self, user_id: int) -> Optional[User]:
        """
        Retrieve a user by their primary key.

        Args:
            user_id: The integer ID to look up.

        Returns:
            User if found, None otherwise.
        """

    @abstractmethod
    def find_by_username(self, username: str) -> Optional[User]:
        """
        Look up a user by their unique username.

        UML Sequence Diagram (Section 5):
            Step 3 — called by AuthService.login()

        Args:
            username: Login name to search for.

        Returns:
            User if found, None otherwise.
        """

    @abstractmethod
    def update_password(self, user_id: int, new_password_hash: str) -> None:
        """
        Replace the stored password hash for a user.

        Args:
            user_id          : ID of the user to update.
            new_password_hash: New bcrypt hash.

        Raises:
            LearnerNotFoundError: If user_id does not exist.
        """

    @abstractmethod
    def delete_user(self, user_id: int) -> None:
        """
        Permanently remove a user.

        Args:
            user_id: ID of the user to delete.

        Raises:
            LearnerNotFoundError: If user_id does not exist.
        """

    @abstractmethod
    def get_all_users(self) -> List[User]:
        """
        Retrieve all users in the system.

        Returns:
            list[User]: All user records (may be empty).
        """


# ── In-Memory Implementation ─────────────────────────────────────────────────

class InMemoryUserRepository(UserRepository):
    """
    Concrete implementation storing users in a Python dictionary.

    Use for:
        - Unit tests (no database dependency)
        - Development / prototyping
        - Other team members testing their modules

    UML: Implements <<interface>> UserRepository
    """

    def __init__(self):
        self._users: dict[int, User] = {}
        self._next_id: int = 1

    def create_user(self, user: User) -> User:
        if self.find_by_username(user.username) is not None:
            from core.exceptions import ValidationError
            raise ValidationError(
                f"Username '{user.username}' already exists"
            )
        user.id = self._next_id
        self._next_id += 1
        self._users[user.id] = user
        return user

    def get_user(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    def find_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def update_password(self, user_id: int, new_password_hash: str) -> None:
        user = self.get_user(user_id)
        if user is None:
            from core.exceptions import LearnerNotFoundError
            raise LearnerNotFoundError(f"User {user_id} not found")
        user.password_hash = new_password_hash

    def delete_user(self, user_id: int) -> None:
        if user_id not in self._users:
            from core.exceptions import LearnerNotFoundError
            raise LearnerNotFoundError(f"User {user_id} not found")
        del self._users[user_id]

    def get_all_users(self) -> List[User]:
        return list(self._users.values())