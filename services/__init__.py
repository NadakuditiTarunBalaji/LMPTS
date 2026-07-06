"""
services/__init__.py
--------------------
Public API for the LMPTS Service Layer.

The service layer sits between the GUI and the data/algorithm layers:

    Tkinter GUI
         ↓
    Service Layer       ← THIS PACKAGE
         ↓          ↓
    Repositories   Algorithms
         ↓
    SQLite Database

Responsibilities:
    - Orchestrate repository + algorithm calls
    - Enforce business rules
    - Manage cross-repository transactions
    - Return results/raise exceptions the GUI can display

Factory functions (production use):
    create_course_service(db)
    create_enrollment_service(db)
    create_progress_service(db)
    create_analytics_service(db)
    create_learning_path_service(db)
    create_recommendation_service(db)

Direct injection (test use):
    CourseService(course_repo, graph)
    EnrollmentService(enrollment_repo, learner_repo, ...)
"""

from services.course_service import CourseService, create_course_service
from services.enrollment_service import (
    EnrollmentService,
    EnrollmentResult,
    create_enrollment_service,
)
from services.progress_service import (
    ProgressService,
    create_progress_service,
)
from services.analytics_service import (
    AnalyticsService,
    create_analytics_service,
)
from services.learning_path_service import (
    LearningPathService,
    create_learning_path_service,
)
from services.recommendation_service import (
    RecommendationService,
    create_recommendation_service,
)

__all__ = [
    # Services
    "CourseService",
    "EnrollmentService",
    "ProgressService",
    "AnalyticsService",
    "LearningPathService",
    "RecommendationService",
    # Result objects
    "EnrollmentResult",
    # Factories
    "create_course_service",
    "create_enrollment_service",
    "create_progress_service",
    "create_analytics_service",
    "create_learning_path_service",
    "create_recommendation_service",
]