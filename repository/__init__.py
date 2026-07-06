"""
repository/__init__.py
----------------------
Exports all repository classes and interfaces for easy importing.

Usage by other modules:
    from repository import Database
    from repository import SQLiteUserRepository
    from repository import SQLiteCourseRepository
    from repository import SQLiteLearnerRepository
    from repository import SQLiteEnrollmentRepository
"""

from repository.database import Database
from repository.user_repo import (
    UserRepositoryInterface,
    SQLiteUserRepository,
)
from repository.course_repo import (
    CourseRepositoryInterface,
    SQLiteCourseRepository,
)
from repository.learner_repo import (
    LearnerRepositoryInterface,
    SQLiteLearnerRepository,
)
from repository.enrollment_repo import (
    EnrollmentRepositoryInterface,
    SQLiteEnrollmentRepository,
)

__all__ = [
    "Database",
    "UserRepositoryInterface",
    "SQLiteUserRepository",
    "CourseRepositoryInterface",
    "SQLiteCourseRepository",
    "LearnerRepositoryInterface",
    "SQLiteLearnerRepository",
    "EnrollmentRepositoryInterface",
    "SQLiteEnrollmentRepository",
]