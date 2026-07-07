"""
user_repo.py
------------
SQLite implementation of the user repository.

All row-to-object conversion goes through User.from_dict() to
guarantee proper enum handling (role, account_status).

All enum-to-string conversion for SQL binding happens in this file
because SQLite cannot serialize Python enum objects.
"""

import sqlite3
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from core.user import User
from core.enums import UserRole, AccountStatus
from core.exceptions import ValidationError, LearnerNotFoundError
from auth.user_repository import UserRepository

logger = logging.getLogger(__name__)


# ── Extended Interface ────────────────────────────────────────────────────────

class UserRepositoryInterface(UserRepository):
    """Extended interface with pending/status query methods."""

    @abstractmethod
    def find_by_role(self, role: UserRole) -> List[User]:
        pass

    @abstractmethod
    def username_exists(self, username: str) -> bool:
        pass

    @abstractmethod
    def count(self) -> int:
        pass

    @abstractmethod
    def update_account_status(
        self,
        user_id:          int,
        is_active:        bool,
        account_status,
        rejection_reason: str = "",
    ) -> None:
        pass

    @abstractmethod
    def get_pending_users(self) -> List[User]:
        pass

    @abstractmethod
    def count_pending(self) -> int:
        pass


# ── SQLite Implementation ─────────────────────────────────────────────────────

class SQLiteUserRepository(UserRepositoryInterface):
    """
    SQLite implementation of the user repository.

    Every read goes through _row_to_user() which uses User.from_dict()
    to convert database strings into proper enum objects.
    """

    def __init__(self, database):
        self._db = database

    # ── Row → User conversion (single source of truth) ────────────────────────

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        """
        Convert a SQLite row to a User object.

        Explicitly extracts every column so that missing optional
        columns get proper defaults. Delegates enum conversion to
        User.from_dict().
        """
        keys = row.keys()

        row_dict = {
            "id":            row["id"],
            "username":      row["username"],
            "password_hash": row["password_hash"],
            "role":          row["role"],
            "created_at":    row["created_at"],
        }

        # Optional columns from migration v3
        row_dict["is_active"] = (
            row["is_active"] if "is_active" in keys else 1
        )
        row_dict["account_status"] = (
            row["account_status"] if "account_status" in keys else "ACTIVE"
        )
        row_dict["rejection_reason"] = (
            row["rejection_reason"] if "rejection_reason" in keys else ""
        )
        row_dict["full_name"] = (
            row["full_name"] if "full_name" in keys else ""
        )
        row_dict["email"] = (
            row["email"] if "email" in keys else ""
        )

        return User.from_dict(row_dict)

    # ── Create ─────────────────────────────────────────────────────────────────

    def create_user(self, user: User) -> User:
        """Insert a new user, converting all enums to strings for SQLite."""
        if self.username_exists(user.username):
            raise ValidationError(
                f"Username '{user.username}' already exists"
            )
        user.validate()

        # Convert enums to string values for SQLite binding
        role_value = (
            user.role.value
            if isinstance(user.role, UserRole)
            else str(user.role)
        )
        status_value = (
            user.account_status.value
            if isinstance(user.account_status, AccountStatus)
            else str(user.account_status)
        )

        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (
                    username, password_hash, role, created_at,
                    is_active, account_status, rejection_reason,
                    full_name, email
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user.username,
                    user.password_hash,
                    role_value,
                    user.created_at.isoformat(),
                    1 if user.is_active else 0,
                    status_value,
                    user.rejection_reason or "",
                    user.full_name or "",
                    user.email or "",
                )
            )
            user.id = cursor.lastrowid

        logger.info(
            f"Created user: {user.username} "
            f"(id={user.id}, status={status_value})"
        )
        return user

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_user(self, user_id: int) -> Optional[User]:
        """Retrieve user by ID — ALWAYS uses _row_to_user."""
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
        """Look up user by username — ALWAYS uses _row_to_user."""
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
        """Retrieve all users."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM users ORDER BY id")
            return [self._row_to_user(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def find_by_role(self, role: UserRole) -> List[User]:
        """Retrieve all users with a specific role."""
        role_value = (
            role.value if isinstance(role, UserRole) else str(role)
        )
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM users WHERE role = ? ORDER BY id",
                (role_value,)
            )
            return [self._row_to_user(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def username_exists(self, username: str) -> bool:
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
        conn = self._db.get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) as c FROM users")
            return cursor.fetchone()["c"]
        finally:
            conn.close()

    def get_pending_users(self) -> List[User]:
        """Return all users with account_status = PENDING."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM users WHERE account_status = ? "
                "ORDER BY created_at ASC",
                (AccountStatus.PENDING.value,)
            )
            return [self._row_to_user(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def count_pending(self) -> int:
        """Count of users in PENDING state."""
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) as c FROM users WHERE account_status = ?",
                (AccountStatus.PENDING.value,)
            )
            return cursor.fetchone()["c"]
        finally:
            conn.close()

    # ── Update ─────────────────────────────────────────────────────────────────

    def update_password(self, user_id: int, new_password_hash: str) -> None:
        if self.get_user(user_id) is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_password_hash, user_id)
            )
        logger.info(f"Password updated for user id={user_id}")

    def update_account_status(
        self,
        user_id:          int,
        is_active:        bool,
        account_status,
        rejection_reason: str = "",
    ) -> None:
        """
        Update account activation status.

        Accepts AccountStatus enum OR string.
        Converts to string for SQLite binding.
        """
        if self.get_user(user_id) is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        if isinstance(account_status, AccountStatus):
            status_value = account_status.value
        else:
            status_value = str(account_status)

        with self._db.transaction() as conn:
            conn.execute(
                """
                UPDATE users
                SET is_active = ?,
                    account_status = ?,
                    rejection_reason = ?
                WHERE id = ?
                """,
                (
                    1 if is_active else 0,
                    status_value,
                    rejection_reason or "",
                    user_id,
                )
            )
        logger.info(
            f"Updated user {user_id}: "
            f"status={status_value}, active={is_active}"
        )

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_user(self, user_id: int) -> None:
        if self.get_user(user_id) is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        with self._db.transaction() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        logger.info(f"Deleted user id={user_id}")