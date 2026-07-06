"""
user_repo.py
------------
Abstract interface and SQLite implementation for User data access.

UML Class Diagram:
    <<interface>>
    UserRepositoryInterface
        └── SQLiteUserRepository

Inherits from:
    auth.user_repository.UserRepository  (Person 1 interface)

This file EXTENDS Person 1's UserRepository with additional
methods needed for the full application (get_all_users, etc.)

ER Diagram table: USERS
    id            PK
    username      UNIQUE NOT NULL
    password_hash NOT NULL
    role          NOT NULL
    created_at    NOT NULL
"""

import sqlite3
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, List

from auth.user_repository import UserRepository
from core.user import User
from core.enums import UserRole
from core.exceptions import ValidationError, LearnerNotFoundError
from repository.database import Database

logger = logging.getLogger(__name__)


# ── Abstract Interface ─────────────────────────────────────────────────────────

class UserRepositoryInterface(UserRepository):
    """
    Extended abstract interface for User data access.

    Inherits all methods from Person 1's UserRepository:
        create_user()
        get_user()
        find_by_username()
        update_password()
        delete_user()
        get_all_users()

    Adds Person 2 specific methods:
        find_by_role()
        username_exists()
        count()
    """

    @abstractmethod
    def find_by_role(self, role: UserRole) -> List[User]:
        """
        Retrieve all users with a specific role.

        Args:
            role: UserRole enum value to filter by.

        Returns:
            list[User]: All users with the given role.

        Example:
            admins = repo.find_by_role(UserRole.ADMIN)
        """

    @abstractmethod
    def username_exists(self, username: str) -> bool:
        """
        Check whether a username is already taken.

        Args:
            username: Login name to check.

        Returns:
            bool: True if taken, False if available.

        Example:
            if repo.username_exists("alice"):
                raise ValidationError("Username taken")
        """

    @abstractmethod
    def count(self) -> int:
        """
        Count the total number of users.

        Returns:
            int: Total user count.
        """


# ── SQLite Implementation ──────────────────────────────────────────────────────

class SQLiteUserRepository(UserRepositoryInterface):
    """
    SQLite implementation of UserRepositoryInterface.

    Each method opens its own connection (Q8: connection per operation).
    Write operations use the transaction context manager (Q14).

    Args:
        database: Database instance providing connections.

    Example:
        db = Database()
        db.initialize()
        repo = SQLiteUserRepository(db)

        user = User("alice", hash_password("pass"), UserRole.LEARNER)
        saved = repo.create_user(user)
        print(saved.id)   # → assigned by SQLite
    """

    def __init__(self, database: Database):
        self._db = database

    # ── Private Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        """
        Convert a SQLite row to a User object.

        Args:
            row: sqlite3.Row from the users table.

        Returns:
            User: Populated User object.
        """
        return User.from_dict({
            "id":            row["id"],
            "username":      row["username"],
            "password_hash": row["password_hash"],
            "role":          row["role"],
            "created_at":    row["created_at"],
        })

    # ── Create ─────────────────────────────────────────────────────────────────

    def create_user(self, user: User) -> User:
        """
        Insert a new user into the USERS table.

        Steps:
            1. Check username uniqueness
            2. Validate the user object
            3. Insert into database
            4. Assign the generated id back to the user object

        Args:
            user: User object (id should be None).

        Returns:
            User: Same object with id assigned.

        Raises:
            ValidationError: If username already exists.
        """
        if self.username_exists(user.username):
            raise ValidationError(
                f"Username '{user.username}' already exists"
            )

        user.validate()

        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (username, password_hash, role, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user.username,
                    user.password_hash,
                    user.role.value,
                    user.created_at.isoformat(),
                )
            )
            user.id = cursor.lastrowid

        logger.info(f"Created user: {user.username} (id={user.id})")
        return user

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_user(self, user_id: int) -> Optional[User]:
        """
        Retrieve a user by primary key.

        Args:
            user_id: Integer primary key.

        Returns:
            User if found, None otherwise.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
        finally:
            conn.close()

    def find_by_username(self, username: str) -> Optional[User]:
        """
        Look up a user by their unique username.

        Used by AuthService.login() during authentication.

        Args:
            username: Login name to search for.

        Returns:
            User if found, None otherwise.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
        finally:
            conn.close()

    def get_all_users(self) -> List[User]:
        """
        Retrieve all users ordered by id.

        Returns:
            list[User]: All user records.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM users ORDER BY id"
            )
            return [self._row_to_user(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def find_by_role(self, role: UserRole) -> List[User]:
        """
        Retrieve all users with a specific role.

        Args:
            role: UserRole to filter by.

        Returns:
            list[User]: Users with the given role.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM users WHERE role = ? ORDER BY id",
                (role.value,)
            )
            return [self._row_to_user(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def username_exists(self, username: str) -> bool:
        """
        Check if a username is already in the database.

        Args:
            username: Login name to check.

        Returns:
            bool: True if taken.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (username,)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def count(self) -> int:
        """
        Count total users in the database.

        Returns:
            int: Total user count.
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) as c FROM users")
            return cursor.fetchone()["c"]
        finally:
            conn.close()

    # ── Update ─────────────────────────────────────────────────────────────────

    def update_password(self, user_id: int, new_password_hash: str) -> None:
        """
        Replace the stored password hash for a user.

        Args:
            user_id          : ID of the user to update.
            new_password_hash: New bcrypt hash.

        Raises:
            LearnerNotFoundError: If user_id does not exist.
        """
        if self.get_user(user_id) is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_password_hash, user_id)
            )

        logger.info(f"Password updated for user id={user_id}")

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_user(self, user_id: int) -> None:
        """
        Permanently remove a user from the database.

        Due to ON DELETE CASCADE, the associated learner record
        and all their enrollments are also deleted.

        Args:
            user_id: ID of the user to delete.

        Raises:
            LearnerNotFoundError: If user_id does not exist.
        """
        if self.get_user(user_id) is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        with self._db.transaction() as conn:
            conn.execute(
                "DELETE FROM users WHERE id = ?",
                (user_id,)
            )

        logger.info(f"Deleted user id={user_id}")