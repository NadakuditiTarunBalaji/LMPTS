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

from core.enums import UserRole, AccountStatus, DifficultyLevel
from core.exceptions import ValidationError


class User:
    """
    One account in the LMPTS system.

    Attributes:
        id               (int)         : Database primary key
        username         (str)         : Login name
        password_hash    (str)         : bcrypt hash
        role             (UserRole)    : Permissions level
        created_at       (datetime)    : Account creation timestamp
        is_active        (bool)        : Whether account can log in
        account_status   (str)         : ACTIVE / PENDING / REJECTED
        rejection_reason (str)         : Reason if rejected
        full_name        (str)         : Learner's full name
        email            (str)         : Learner's email address
    """

    def __init__(
        self,
        username:             str,
        password_hash:        str,
        role:                 UserRole,
        id:                   Optional[int]           = None,
        created_at:           Optional[datetime]      = None,
        is_active:            bool                    = True,
        account_status:       AccountStatus           = AccountStatus.ACTIVE,
        rejection_reason:     str                     = "",
        full_name:            str                     = "",
        email:                str                     = "",
        bio:                  str                     = "",
        preferred_difficulty: DifficultyLevel         = DifficultyLevel.BEGINNER,
        profile_updated_at:   Optional[datetime]      = None,
    ):
        self.id                   = id
        self.username             = username
        self.password_hash        = password_hash
        self.role                 = role
        self.created_at           = created_at or datetime.now(timezone.utc)
        self.is_active            = is_active
        self.account_status       = account_status
        self.rejection_reason     = rejection_reason
        self.full_name            = full_name
        self.email                = email
        self.bio                  = bio
        self.preferred_difficulty = preferred_difficulty
        self.profile_updated_at   = profile_updated_at
    # ── Validation ─────────────────────────────────────────────────────────────

    def validate(self) -> None:
        """Verify all required fields."""
        if not self.username or not self.username.strip():
            raise ValidationError("Username cannot be empty")

        if not self.password_hash or not self.password_hash.strip():
            raise ValidationError("Password hash cannot be empty")

        if not isinstance(self.role, UserRole):
            raise ValidationError(
                f"Invalid role '{self.role}'. "
                f"Must be one of: {[r.value for r in UserRole]}"
            )

        if not isinstance(self.account_status, AccountStatus):
            raise ValidationError(
                f"Invalid account_status '{self.account_status}'"
            )

        if not isinstance(self.preferred_difficulty, DifficultyLevel):
            raise ValidationError(
                f"Invalid preferred_difficulty "
                f"'{self.preferred_difficulty}'"
            )
            
    # ── Serialization ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id":                   self.id,
            "username":             self.username,
            "role":                 self.role.value,
            "created_at":           self.created_at.isoformat(),
            "is_active":            1 if self.is_active else 0,
            "account_status":       self.account_status.value,
            "rejection_reason":     self.rejection_reason,
            "full_name":            self.full_name,
            "email":                self.email,
            "bio":                  self.bio,
            "preferred_difficulty": self.preferred_difficulty.value,
            "profile_updated_at":   (
                self.profile_updated_at.isoformat()
                if self.profile_updated_at else ""
            ),
        }

    def to_dict_with_hash(self) -> dict:
        data = self.to_dict()
        data["password_hash"] = self.password_hash
        return data

    @classmethod
    def from_dict(cls, row: dict) -> "User":
        try:
            role = UserRole(row["role"])
        except ValueError:
            raise ValidationError(f"Unknown role: {row.get('role')}")

        status_raw = row.get("account_status") or "ACTIVE"
        try:
            account_status = AccountStatus(status_raw)
        except ValueError:
            account_status = AccountStatus.ACTIVE

        diff_raw = row.get("preferred_difficulty") or "BEGINNER"
        try:
            preferred_difficulty = DifficultyLevel(diff_raw)
        except ValueError:
            preferred_difficulty = DifficultyLevel.BEGINNER

        created_at = row.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        profile_updated_at = row.get("profile_updated_at")
        if profile_updated_at and isinstance(profile_updated_at, str):
            try:
                profile_updated_at = datetime.fromisoformat(
                    profile_updated_at
                )
            except ValueError:
                profile_updated_at = None
        else:
            profile_updated_at = None

        is_active_raw = row.get("is_active", 1)
        is_active = bool(is_active_raw) if is_active_raw is not None else True

        return cls(
            id                   = row.get("id"),
            username             = row["username"],
            password_hash        = row["password_hash"],
            role                 = role,
            created_at           = created_at,
            is_active            = is_active,
            account_status       = account_status,
            rejection_reason     = row.get("rejection_reason") or "",
            full_name            = row.get("full_name")        or "",
            email                = row.get("email")            or "",
            bio                  = row.get("bio")              or "",
            preferred_difficulty = preferred_difficulty,
            profile_updated_at   = profile_updated_at,
        )
    # ── Dunder Methods ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"User(id={self.id}, username='{self.username}', "
            f"role={self.role.value}, "
            f"status={self.account_status.value})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self.id == other.id