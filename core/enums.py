"""
enums.py
--------
Central location for every system-wide constant.

UML Reference: Class Diagram – Enumeration classes
    - DifficultyLevel
    - CourseStatus
    - EnrollmentStatus
    - UserRole
    - CompletionStatus

Why enums instead of strings?
    ❌  if user.role == "admin":       ← magic string, typo-prone
    ✅  if user.role == UserRole.ADMIN: ← IDE autocomplete, type-safe

Used across every layer: Core, Auth, Services, Algorithms, GUI, Analytics
"""

from enum import Enum

# Add this to core/enums.py — after CompletionStatus

class AccountStatus(Enum):
    """
    Account activation status for user accounts.

    ACTIVE   : Account is approved and can log in normally.
    PENDING  : Account registered but awaiting admin approval.
    REJECTED : Registration was rejected by admin.
    INACTIVE : Account was deactivated by admin.

    Used by:
        - User model        (user.account_status)
        - AuthService       (login checks)
        - AccountService    (approval workflow)
        - PendingRegistrationsScreen (admin UI)

    Default for new accounts created by admin: ACTIVE
    Default for self-registered learners:      PENDING
    """
    ACTIVE   = "ACTIVE"
    PENDING  = "PENDING"
    REJECTED = "REJECTED"
    INACTIVE = "INACTIVE"
    
class DifficultyLevel(Enum):
    """
    How hard a course is.

    UML Class Diagram:
        <<enumeration>>
        DifficultyLevel
        ───────────────
        BEGINNER
        INTERMEDIATE
        ADVANCED

    Used by:
        - Course.difficulty
        - Learning path engine (filter by level)
        - Analytics (difficulty distribution charts)
    """
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class CourseStatus(Enum):
    """
    Lifecycle state of a course.

    UML Class Diagram:
        <<enumeration>>
        CourseStatus
        ────────────
        DRAFT
        PUBLISHED
        ARCHIVED

    State transitions:
        DRAFT ──publish──> PUBLISHED ──archive──> ARCHIVED

    Used by:
        - Course.status
        - Admin GUI (Publish / Archive buttons)
        - Use Case: "Publish Course", "Archive Course"
    """
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class EnrollmentStatus(Enum):
    """
    Where a learner stands in a specific course.

    UML State Diagram reference:
        ENROLLED ──start──> IN_PROGRESS ──complete──> COMPLETED
                                        ──cancel───> CANCELLED
        ENROLLED ──cancel──> CANCELLED

    Used by:
        - Enrollment.status
        - State Diagram (Section 9)
        - Progress tracking
    """
    ENROLLED = "ENROLLED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class UserRole(Enum):
    """
    What a user is allowed to do in the system.

    UML Use Case Diagram actors map to these roles:
        ADMIN      → Administrator actor
        LEARNER    → Learner actor
        ANALYST    → Analyst actor
        INSTRUCTOR → Instructor actor

    Used by:
        - User.role
        - Authentication (login validation)
        - Authorization (permission guards)
    """
    ADMIN = "ADMIN"
    LEARNER = "LEARNER"
    ANALYST = "ANALYST"
    INSTRUCTOR = "INSTRUCTOR"


class CompletionStatus(Enum):
    """
    Fine-grained progress tracking for individual course modules.

    UML Class Diagram:
        <<enumeration>>
        CompletionStatus
        ────────────────
        NOT_STARTED
        IN_PROGRESS
        COMPLETED
        FAILED

    Used by:
        - COURSE_PROGRESS table (ER Diagram, Section 10)
        - Analytics dashboards
        - Progress service
    """
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CancellationRequestStatus(Enum):
    """
    Status of a learner's course cancellation request.

    Workflow:
        PENDING        → Waiting for instructor review
        APPROVED       → Instructor approved, learner unenrolled
        REJECTED       → Instructor rejected, enrollment continues
        WITHDRAWN      → Learner withdrew the request

    Used by:
        - CancellationRequest.status
        - Instructor dashboard (PLR Approval equivalent)
        - Enrollment workflow validation
    """
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"