"""
user_repo.py
------------
SQLite implementation of the user repository.

All row-to-object conversion goes through _row_to_user() which
delegates to User.from_dict() for proper enum handling.

All enum-to-string conversion for SQL binding happens in this file
because SQLite cannot serialize Python enum objects.
"""

import sqlite3
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional

from core.user import User
from core.enums import UserRole, AccountStatus, DifficultyLevel
from core.exceptions import ValidationError, LearnerNotFoundError
from auth.user_repository import UserRepository

logger = logging.getLogger(__name__)


# ── Extended Interface ────────────────────────────────────────────────────────

class UserRepositoryInterface(UserRepository):
    """Extends the Person 1 UserRepository interface."""

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
        user_id: int,
        is_active: bool,
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

    @abstractmethod
    def update_profile(
        self,
        user_id: int,
        full_name: str,
        email: str,
        bio: str,
        preferred_difficulty,
    ) -> None:
        pass


# ── SQLite Implementation ─────────────────────────────────────────────────────

class SQLiteUserRepository(UserRepositoryInterface):
    """
    SQLite implementation of the user repository.
    Handles all profile columns from migration v4.
    """

    def __init__(self, database):
        self._db = database

    # ── Row → User conversion ─────────────────────────────────────────────────

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        """Convert SQLite row to User with all v4 columns."""
        keys = row.keys()
        row_dict = {
            "id":            row["id"],
            "username":      row["username"],
            "password_hash": row["password_hash"],
            "role":          row["role"],
            "created_at":    row["created_at"],
        }
        for col, default in [
            ("is_active",             1),
            ("account_status",        "ACTIVE"),
            ("rejection_reason",      ""),
            ("full_name",             ""),
            ("email",                 ""),
            ("bio",                   ""),
            ("preferred_difficulty",  "BEGINNER"),
            ("profile_updated_at",    ""),
        ]:
            row_dict[col] = row[col] if col in keys else default
        return User.from_dict(row_dict)

    # ── CREATE ─────────────────────────────────────────────────────────────────

    def create_user(self, user: User) -> User:
        """Insert new user, converting all enums to strings."""
        if self.username_exists(user.username):
            raise ValidationError(
                f"Username '{user.username}' already exists"
            )
        user.validate()

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
        diff_value = (
            user.preferred_difficulty.value
            if isinstance(user.preferred_difficulty, DifficultyLevel)
            else str(user.preferred_difficulty)
        )
        profile_updated = (
            user.profile_updated_at.isoformat()
            if user.profile_updated_at else ""
        )

        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (
                    username, password_hash, role, created_at,
                    is_active, account_status, rejection_reason,
                    full_name, email, bio, preferred_difficulty,
                    profile_updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    user.bio or "",
                    diff_value,
                    profile_updated,
                )
            )
            user.id = cursor.lastrowid

        logger.info(f"Created user: {user.username} (id={user.id})")
        return user

    # ── READ ───────────────────────────────────────────────────────────────────

    def get_user(self, user_id: int) -> Optional[User]:
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
        conn = self._db.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM users ORDER BY id")
            return [self._row_to_user(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def find_by_role(self, role: UserRole) -> List[User]:
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
        conn = self._db.get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) as c FROM users WHERE account_status = ?",
                (AccountStatus.PENDING.value,)
            )
            return cursor.fetchone()["c"]
        finally:
            conn.close()

    # ── UPDATE ─────────────────────────────────────────────────────────────────

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
        if self.get_user(user_id) is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        status_value = (
            account_status.value
            if isinstance(account_status, AccountStatus)
            else str(account_status)
        )

        with self._db.transaction() as conn:
            conn.execute(
                """
                UPDATE users
                SET is_active = ?, account_status = ?, rejection_reason = ?
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
            f"Updated user {user_id}: status={status_value}"
        )

    def update_profile(
        self,
        user_id:              int,
        full_name:            str,
        email:                str,
        bio:                  str,
        preferred_difficulty,
    ) -> None:
        """Update user's personal profile information."""
        if self.get_user(user_id) is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        diff_value = (
            preferred_difficulty.value
            if isinstance(preferred_difficulty, DifficultyLevel)
            else str(preferred_difficulty)
        )

        now = datetime.now(timezone.utc).isoformat()

        with self._db.transaction() as conn:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, email = ?, bio = ?,
                    preferred_difficulty = ?, profile_updated_at = ?
                WHERE id = ?
                """,
                (
                    full_name or "",
                    email or "",
                    bio or "",
                    diff_value,
                    now,
                    user_id,
                )
            )
        logger.info(f"Profile updated for user id={user_id}")

    # ── DELETE ─────────────────────────────────────────────────────────────────

    def delete_user(self, user_id: int) -> None:
        if self.get_user(user_id) is None:
            raise LearnerNotFoundError(f"User {user_id} not found")

        with self._db.transaction() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        logger.info(f"Deleted user id={user_id}")


# ── In-memory Test Repository ─────────────────────────────────────────────────

class InMemoryUserRepository(UserRepositoryInterface):
    """In-memory user repository for testing."""

    def __init__(self):
        self._users: dict = {}
        self._next_id = 1

    def create_user(self, user: User) -> User:
        if self.username_exists(user.username):
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
        for u in self._users.values():
            if u.username == username:
                return u
        return None

    def get_all_users(self) -> List[User]:
        return list(self._users.values())

    def find_by_role(self, role: UserRole) -> List[User]:
        return [u for u in self._users.values() if u.role == role]

    def username_exists(self, username: str) -> bool:
        return self.find_by_username(username) is not None

    def count(self) -> int:
        return len(self._users)

    def update_password(self, user_id: int, new_password_hash: str) -> None:
        user = self.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")
        user.password_hash = new_password_hash

    def update_account_status(
        self,
        user_id: int,
        is_active: bool,
        account_status,
        rejection_reason: str = "",
    ) -> None:
        user = self.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")
        user.is_active = is_active
        user.account_status = (
            account_status
            if isinstance(account_status, AccountStatus)
            else AccountStatus(account_status)
        )
        user.rejection_reason = rejection_reason

    def update_profile(
        self,
        user_id: int,
        full_name: str,
        email: str,
        bio: str,
        preferred_difficulty,
    ) -> None:
        user = self.get_user(user_id)
        if user is None:
            raise LearnerNotFoundError(f"User {user_id} not found")
        user.full_name = full_name
        user.email     = email
        user.bio       = bio
        user.preferred_difficulty = (
            preferred_difficulty
            if isinstance(preferred_difficulty, DifficultyLevel)
            else DifficultyLevel(preferred_difficulty)
        )
        user.profile_updated_at = datetime.now(timezone.utc)

    def get_pending_users(self) -> List[User]:
        return [
            u for u in self._users.values()
            if u.account_status == AccountStatus.PENDING
        ]

    def count_pending(self) -> int:
        return len(self.get_pending_users())

    def delete_user(self, user_id: int) -> None:
        if user_id not in self._users:
            raise LearnerNotFoundError(f"User {user_id} not found")
        del self._users[user_id]



# """
# user_repo.py
# ------------
# SQLite implementation of the user repository.

# All row-to-object conversion goes through _row_to_user() which
# delegates to User.from_dict() for proper enum handling.

# All enum-to-string conversion for SQL binding happens in this file
# because SQLite cannot serialize Python enum objects.
# """

# import sqlite3
# import logging
# from abc import ABC, abstractmethod
# from datetime import datetime, timezone
# from typing import List, Optional

# from core.user import User
# from core.enums import UserRole, AccountStatus, DifficultyLevel
# from core.exceptions import ValidationError, LearnerNotFoundError
# from auth.user_repository import UserRepository

# logger = logging.getLogger(__name__)


# # ── Extended Interface ────────────────────────────────────────────────────────

# class UserRepositoryInterface(UserRepository):
#     """Extends the Person 1 UserRepository interface."""

#     @abstractmethod
#     def find_by_role(self, role: UserRole) -> List[User]:
#         pass

#     @abstractmethod
#     def username_exists(self, username: str) -> bool:
#         pass

#     @abstractmethod
#     def count(self) -> int:
#         pass

#     @abstractmethod
#     def update_account_status(
#         self,
#         user_id: int,
#         is_active: bool,
#         account_status,
#         rejection_reason: str = "",
#     ) -> None:
#         pass

#     @abstractmethod
#     def get_pending_users(self) -> List[User]:
#         pass

#     @abstractmethod
#     def count_pending(self) -> int:
#         pass

#     @abstractmethod
#     def update_profile(
#         self,
#         user_id: int,
#         full_name: str,
#         email: str,
#         bio: str,
#         preferred_difficulty,
#     ) -> None:
#         pass


# # ── SQLite Implementation ─────────────────────────────────────────────────────

# class SQLiteUserRepository(UserRepositoryInterface):
#     """
#     SQLite implementation of the user repository.
#     Handles all profile columns from migration v4.
#     """

#     def __init__(self, database):
#         self._db = database

#     # ── Row → User conversion ─────────────────────────────────────────────────

#     @staticmethod
#     def _row_to_user(row: sqlite3.Row) -> User:
#         """Convert SQLite row to User with all v4 columns."""
#         keys = row.keys()
#         row_dict = {
#             "id":            row["id"],
#             "username":      row["username"],
#             "password_hash": row["password_hash"],
#             "role":          row["role"],
#             "created_at":    row["created_at"],
#         }
#         for col, default in [
#             ("is_active",             1),
#             ("account_status",        "ACTIVE"),
#             ("rejection_reason",      ""),
#             ("full_name",             ""),
#             ("email",                 ""),
#             ("bio",                   ""),
#             ("preferred_difficulty",  "BEGINNER"),
#             ("profile_updated_at",    ""),
#         ]:
#             row_dict[col] = row[col] if col in keys else default
#         return User.from_dict(row_dict)

#     # ── CREATE ─────────────────────────────────────────────────────────────────

#     def create_user(self, user: User) -> User:
#         """Insert new user, converting all enums to strings."""
#         if self.username_exists(user.username):
#             raise ValidationError(
#                 f"Username '{user.username}' already exists"
#             )
#         user.validate()

#         role_value = (
#             user.role.value
#             if isinstance(user.role, UserRole)
#             else str(user.role)
#         )
#         status_value = (
#             user.account_status.value
#             if isinstance(user.account_status, AccountStatus)
#             else str(user.account_status)
#         )
#         diff_value = (
#             user.preferred_difficulty.value
#             if isinstance(user.preferred_difficulty, DifficultyLevel)
#             else str(user.preferred_difficulty)
#         )
#         profile_updated = (
#             user.profile_updated_at.isoformat()
#             if user.profile_updated_at else ""
#         )

#         with self._db.transaction() as conn:
#             cursor = conn.execute(
#                 """
#                 INSERT INTO users (
#                     username, password_hash, role, created_at,
#                     is_active, account_status, rejection_reason,
#                     full_name, email, bio, preferred_difficulty,
#                     profile_updated_at
#                 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                 """,
#                 (
#                     user.username,
#                     user.password_hash,
#                     role_value,
#                     user.created_at.isoformat(),
#                     1 if user.is_active else 0,
#                     status_value,
#                     user.rejection_reason or "",
#                     user.full_name or "",
#                     user.email or "",
#                     user.bio or "",
#                     diff_value,
#                     profile_updated,
#                 )
#             )
#             user.id = cursor.lastrowid

#         logger.info(f"Created user: {user.username} (id={user.id})")
#         return user

#     # ── READ ───────────────────────────────────────────────────────────────────

#     def get_user(self, user_id: int) -> Optional[User]:
#         conn = self._db.get_connection()
#         try:
#             cursor = conn.execute(
#                 "SELECT * FROM users WHERE id = ?",
#                 (user_id,)
#             )
#             row = cursor.fetchone()
#             return self._row_to_user(row) if row else None
#         finally:
#             conn.close()

#     def find_by_username(self, username: str) -> Optional[User]:
#         conn = self._db.get_connection()
#         try:
#             cursor = conn.execute(
#                 "SELECT * FROM users WHERE username = ?",
#                 (username,)
#             )
#             row = cursor.fetchone()
#             return self._row_to_user(row) if row else None
#         finally:
#             conn.close()

#     def get_all_users(self) -> List[User]:
#         conn = self._db.get_connection()
#         try:
#             cursor = conn.execute("SELECT * FROM users ORDER BY id")
#             return [self._row_to_user(r) for r in cursor.fetchall()]
#         finally:
#             conn.close()

#     def find_by_role(self, role: UserRole) -> List[User]:
#         role_value = (
#             role.value if isinstance(role, UserRole) else str(role)
#         )
#         conn = self._db.get_connection()
#         try:
#             cursor = conn.execute(
#                 "SELECT * FROM users WHERE role = ? ORDER BY id",
#                 (role_value,)
#             )
#             return [self._row_to_user(r) for r in cursor.fetchall()]
#         finally:
#             conn.close()

#     def username_exists(self, username: str) -> bool:
#         conn = self._db.get_connection()
#         try:
#             cursor = conn.execute(
#                 "SELECT 1 FROM users WHERE username = ?",
#                 (username,)
#             )
#             return cursor.fetchone() is not None
#         finally:
#             conn.close()

#     def count(self) -> int:
#         conn = self._db.get_connection()
#         try:
#             cursor = conn.execute("SELECT COUNT(*) as c FROM users")
#             return cursor.fetchone()["c"]
#         finally:
#             conn.close()

#     def get_pending_users(self) -> List[User]:
#         conn = self._db.get_connection()
#         try:
#             cursor = conn.execute(
#                 "SELECT * FROM users WHERE account_status = ? "
#                 "ORDER BY created_at ASC",
#                 (AccountStatus.PENDING.value,)
#             )
#             return [self._row_to_user(r) for r in cursor.fetchall()]
#         finally:
#             conn.close()

#     def count_pending(self) -> int:
#         conn = self._db.get_connection()
#         try:
#             cursor = conn.execute(
#                 "SELECT COUNT(*) as c FROM users WHERE account_status = ?",
#                 (AccountStatus.PENDING.value,)
#             )
#             return cursor.fetchone()["c"]
#         finally:
#             conn.close()

#     # ── UPDATE ─────────────────────────────────────────────────────────────────

#     def update_password(self, user_id: int, new_password_hash: str) -> None:
#         if self.get_user(user_id) is None:
#             raise LearnerNotFoundError(f"User {user_id} not found")

#         with self._db.transaction() as conn:
#             conn.execute(
#                 "UPDATE users SET password_hash = ? WHERE id = ?",
#                 (new_password_hash, user_id)
#             )
#         logger.info(f"Password updated for user id={user_id}")

#     def update_account_status(
#         self,
#         user_id:          int,
#         is_active:        bool,
#         account_status,
#         rejection_reason: str = "",
#     ) -> None:
#         if self.get_user(user_id) is None:
#             raise LearnerNotFoundError(f"User {user_id} not found")

#         status_value = (
#             account_status.value
#             if isinstance(account_status, AccountStatus)
#             else str(account_status)
#         )

#         with self._db.transaction() as conn:
#             conn.execute(
#                 """
#                 UPDATE users
#                 SET is_active = ?, account_status = ?, rejection_reason = ?
#                 WHERE id = ?
#                 """,
#                 (
#                     1 if is_active else 0,
#                     status_value,
#                     rejection_reason or "",
#                     user_id,
#                 )
#             )
#         logger.info(
#             f"Updated user {user_id}: status={status_value}"
#         )

#     def update_profile(
#         self,
#         user_id:              int,
#         full_name:            str,
#         email:                str,
#         bio:                  str,
#         preferred_difficulty,
#     ) -> None:
#         """Update user's personal profile information."""
#         if self.get_user(user_id) is None:
#             raise LearnerNotFoundError(f"User {user_id} not found")

#         diff_value = (
#             preferred_difficulty.value
#             if isinstance(preferred_difficulty, DifficultyLevel)
#             else str(preferred_difficulty)
#         )

#         now = datetime.now(timezone.utc).isoformat()

#         with self._db.transaction() as conn:
#             conn.execute(
#                 """
#                 UPDATE users
#                 SET full_name = ?, email = ?, bio = ?,
#                     preferred_difficulty = ?, profile_updated_at = ?
#                 WHERE id = ?
#                 """,
#                 (
#                     full_name or "",
#                     email or "",
#                     bio or "",
#                     diff_value,
#                     now,
#                     user_id,
#                 )
#             )
#         logger.info(f"Profile updated for user id={user_id}")

#     # ── DELETE ─────────────────────────────────────────────────────────────────

#     def delete_user(self, user_id: int) -> None:
#         if self.get_user(user_id) is None:
#             raise LearnerNotFoundError(f"User {user_id} not found")

#         with self._db.transaction() as conn:
#             conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
#         logger.info(f"Deleted user id={user_id}")


# # ── In-memory Test Repository ─────────────────────────────────────────────────

# class InMemoryUserRepository(UserRepositoryInterface):
#     """In-memory user repository for testing."""

#     def __init__(self):
#         self._users: dict = {}
#         self._next_id = 1

#     def create_user(self, user: User) -> User:
#         if self.username_exists(user.username):
#             raise ValidationError(
#                 f"Username '{user.username}' already exists"
#             )
#         user.id = self._next_id
#         self._next_id += 1
#         self._users[user.id] = user
#         return user

#     def get_user(self, user_id: int) -> Optional[User]:
#         return self._users.get(user_id)

#     def find_by_username(self, username: str) -> Optional[User]:
#         for u in self._users.values():
#             if u.username == username:
#                 return u
#         return None

#     def get_all_users(self) -> List[User]:
#         return list(self._users.values())

#     def find_by_role(self, role: UserRole) -> List[User]:
#         return [u for u in self._users.values() if u.role == role]

#     def username_exists(self, username: str) -> bool:
#         return self.find_by_username(username) is not None

#     def count(self) -> int:
#         return len(self._users)

#     def update_password(self, user_id: int, new_password_hash: str) -> None:
#         user = self.get_user(user_id)
#         if user is None:
#             raise LearnerNotFoundError(f"User {user_id} not found")
#         user.password_hash = new_password_hash

#     def update_account_status(
#         self,
#         user_id: int,
#         is_active: bool,
#         account_status,
#         rejection_reason: str = "",
#     ) -> None:
#         user = self.get_user(user_id)
#         if user is None:
#             raise LearnerNotFoundError(f"User {user_id} not found")
#         user.is_active = is_active
#         user.account_status = (
#             account_status
#             if isinstance(account_status, AccountStatus)
#             else AccountStatus(account_status)
#         )
#         user.rejection_reason = rejection_reason

#     def update_profile(
#         self,
#         user_id: int,
#         full_name: str,
#         email: str,
#         bio: str,
#         preferred_difficulty,
#     ) -> None:
#         user = self.get_user(user_id)
#         if user is None:
#             raise LearnerNotFoundError(f"User {user_id} not found")
#         user.full_name = full_name
#         user.email     = email
#         user.bio       = bio
#         user.preferred_difficulty = (
#             preferred_difficulty
#             if isinstance(preferred_difficulty, DifficultyLevel)
#             else DifficultyLevel(preferred_difficulty)
#         )
#         user.profile_updated_at = datetime.now(timezone.utc)

#     def get_pending_users(self) -> List[User]:
#         return [
#             u for u in self._users.values()
#             if u.account_status == AccountStatus.PENDING
#         ]

#     def count_pending(self) -> int:
#         return len(self.get_pending_users())

#     def delete_user(self, user_id: int) -> None:
#         if user_id not in self._users:
#             raise LearnerNotFoundError(f"User {user_id} not found")
#         del self._users[user_id]