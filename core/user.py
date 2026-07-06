"""
user.py
-------
Represents a system user account.

UML Class Diagram:
    ┌──────────────────┐
    │       User       │
    ├──────────────────┤
    │ id: int          │
    │ username: str    │
    │ password_hash: str│
    │ role: UserRole   │
    │ created_at: datetime│
    ├──────────────────┤
    │ validate()       │
    │ to_dict()        │
    │ from_dict()      │
    └──────────────────┘

UML ER Diagram (Section 10):
    USERS table:
        id           PK
        username     UNIQUE NOT NULL
        password_hash NOT NULL
        role         NOT NULL
        created_at   NOT NULL

UML Relationship:
    User ──── Learner   (association, linked by user_id)
    This is NOT inheritance. User is the auth identity.
    Learner is the learning profile attached to a LEARNER-role User.
"""

from datetime import datetime,timezone
from typing import Optional

from core.enums import UserRole
from core.exceptions import ValidationError


class User:
    """
    One account in the LMPTS system.

    UML Actors → UserRole mapping:
        Administrator → UserRole.ADMIN
        Learner       → UserRole.LEARNER
        Instructor    → UserRole.INSTRUCTOR
        Analyst       → UserRole.ANALYST

    Attributes:
        id            (int)      : Database primary key (None before first save)
        username      (str)      : Login name, must be unique and non-empty
        password_hash (str)      : bcrypt hash — plain text is NEVER stored
        role          (UserRole) : Determines permissions
        created_at    (datetime) : Account creation timestamp
    """

    def __init__(
        self,
        username: str,
        password_hash: str,
        role: UserRole,
        id: Optional[int] = None,
        created_at: Optional[datetime] = None,
    ):
        """
        Create a User object.

        Args:
            username      : Login name (must be non-empty after stripping)
            password_hash : Pre-hashed password from PasswordManager.hash_password()
            role          : UserRole enum value
            id            : Database primary key (None for unsaved users)
            created_at    : Timestamp; defaults to now timezone.utcif not provided

        Example:
            user = User(
                username="admin",
                password_hash="$2b$12$...",
                role=UserRole.ADMIN,
            )
        """
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at or datetime.now(timezone.utc)

    # ── Validation ─────────────────────────────────────────────────────────────

    def validate(self) -> None:
        """
        Verify all required fields contain valid data.

        UML validation rules:
            - username must exist (non-empty after strip)
            - password_hash must exist (non-empty after strip)
            - role must be a valid UserRole enum member

        Raises:
            ValidationError: Descriptive message for first failing rule.

        Example:
            user.validate()  # silent if valid
        """
        if not self.username or not self.username.strip():
            raise ValidationError("Username cannot be empty")

        if not self.password_hash or not self.password_hash.strip():
            raise ValidationError("Password hash cannot be empty")

        if not isinstance(self.role, UserRole):
            raise ValidationError(
                f"Invalid role '{self.role}'. "
                f"Must be one of: {[r.value for r in UserRole]}"
            )

    # ── Serialization ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """
        Convert User to a plain dictionary.

        UML Usage: Repository layer, API responses, serialization.

        SECURITY: password_hash is EXCLUDED to prevent accidental leaks.
        Use to_dict_with_hash() when saving to database.

        Returns:
            dict: {id, username, role, created_at}

        Example:
            user.to_dict()
            → {"id": 1, "username": "admin", "role": "ADMIN",
               "created_at": "2024-01-15T10:30:00"}
        """
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
        }

    def to_dict_with_hash(self) -> dict:
        """
        Full dictionary INCLUDING password_hash for database persistence.

        WARNING: Do NOT use for API responses or logging.

        Returns:
            dict: {id, username, password_hash, role, created_at}
        """
        data = self.to_dict()
        data["password_hash"] = self.password_hash
        return data

    @classmethod
    def from_dict(cls, row: dict) -> "User":
        """
        Reconstruct a User from a database row dictionary.

        UML: Factory method used by UserRepository implementations.

        Args:
            row: Dict with keys matching USERS table columns.
                 Required: username, password_hash, role
                 Optional: id, created_at

        Returns:
            User: Fully populated User object.

        Raises:
            ValidationError: If role value is unrecognised.

        Example:
            row = {"id": 1, "username": "admin",
                   "password_hash": "$2b$12$...", "role": "ADMIN",
                   "created_at": "2024-01-15T10:30:00"}
            user = User.from_dict(row)
        """
        try:
            role = UserRole(row["role"])
        except ValueError:
            raise ValidationError(
                f"Unknown role value '{row['role']}' in database row"
            )

        created_at = row.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=row.get("id"),
            username=row["username"],
            password_hash=row["password_hash"],
            role=role,
            created_at=created_at,
        )

    # ── Dunder Methods ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"User(id={self.id}, username='{self.username}', "
            f"role={self.role.value})"
        )

    def __eq__(self, other: object) -> bool:
        """Two users are equal if they share the same database ID."""
        if not isinstance(other, User):
            return NotImplemented
        return self.id == other.id