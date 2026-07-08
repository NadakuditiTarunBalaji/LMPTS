"""
app.py
------
LMPTS Application Entry Point.

Updated to include:
    - PriorLearningService
    - NotificationService
    - Learner account activation
    - New database tables (migration v2)
"""

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def create_services(database) -> dict:
    """Build and return the global service container."""
    from repository.user_repo import SQLiteUserRepository
    from repository.learner_repo import SQLiteLearnerRepository
    from repository.course_repo import SQLiteCourseRepository
    from repository.enrollment_repo import (
        SQLiteEnrollmentRepository,
        SQLiteProgressRepository,
    )
    from repository.prior_learning_repo import (
        PriorLearningRepository,
        NotificationRepository,
    )
    from repository.cancellation_request_repo import SQLiteCancellationRequestRepository
    from auth.auth_service import AuthService
    from algorithms.graph import CourseGraph
    from services.course_service import CourseService
    from services.enrollment_service import EnrollmentService
    from services.progress_service import ProgressService
    from services.analytics_service import AnalyticsService
    from services.learning_path_service import LearningPathService
    from services.recommendation_service import RecommendationService
    from services.prior_learning_service import PriorLearningService

    # ── Repositories ──────────────────────────────────────────────────────────
    user_repo       = SQLiteUserRepository(database)
    learner_repo    = SQLiteLearnerRepository(database)
    course_repo     = SQLiteCourseRepository(database)
    enrollment_repo = SQLiteEnrollmentRepository(database)
    progress_repo   = SQLiteProgressRepository(database)
    plr_repo        = PriorLearningRepository(database)
    notif_repo      = NotificationRepository(database)
    cancellation_request_repo = SQLiteCancellationRequestRepository(database)

    # ── Shared graph ──────────────────────────────────────────────────────────
    graph = CourseGraph()

    # ── Services ──────────────────────────────────────────────────────────────
    course_service = CourseService(course_repo, graph)

    enrollment_service = EnrollmentService(
        enrollment_repo = enrollment_repo,
        progress_repo   = progress_repo,
        learner_repo    = learner_repo,
        course_repo     = course_repo,
        cancellation_request_repo = cancellation_request_repo,
        graph           = graph,
        database        = database,
    )

    progress_service = ProgressService(
        progress_repo   = progress_repo,
        enrollment_repo = enrollment_repo,
        learner_repo    = learner_repo,
        course_repo     = course_repo,
        graph           = graph,
    )

    analytics_service = AnalyticsService(
        enrollment_repo = enrollment_repo,
        progress_repo   = progress_repo,
        learner_repo    = learner_repo,
        course_repo     = course_repo,
        graph           = graph,
    )

    learning_path_service = LearningPathService(
        enrollment_repo = enrollment_repo,
        learner_repo    = learner_repo,
        course_repo     = course_repo,
        graph           = graph,
    )

    recommendation_service = RecommendationService(
        enrollment_repo = enrollment_repo,
        learner_repo    = learner_repo,
        course_repo     = course_repo,
        graph           = graph,
    )

    prior_learning_service = PriorLearningService(
        plr_repo          = plr_repo,
        notification_repo = notif_repo,
        learner_repo      = learner_repo,
        course_repo       = course_repo,
        user_repo         = user_repo,
        enrollment_service = enrollment_service,
    )

    auth_service = AuthService(user_repo)

    return {
        "auth_service"           : auth_service,
        "course_service"         : course_service,
        "enrollment_service"     : enrollment_service,
        "progress_service"       : progress_service,
        "analytics_service"      : analytics_service,
        "learning_path_service"  : learning_path_service,
        "recommendation_service" : recommendation_service,
        "prior_learning_service" : prior_learning_service,
        "user_repo"              : user_repo,
        "learner_repo"           : learner_repo,
        "course_repo"            : course_repo,
        "plr_repo"               : plr_repo,
        "notification_repo"      : notif_repo,
        "database"               : database,
    }


def seed_sample_data(services: dict) -> None:
    """Seed sample courses and learner profiles."""
    course_svc = services["course_service"]
    if course_svc.count_courses() > 0:
        return

    from core.course import Course
    from core.enums import DifficultyLevel, CourseStatus

    courses = [
        Course("CS101", "Intro to Programming",
               DifficultyLevel.BEGINNER, 20,
               description="Fundamentals of programming",
               status=CourseStatus.PUBLISHED),
        Course("CS102", "Mathematics for CS",
               DifficultyLevel.BEGINNER, 25,
               description="Discrete mathematics",
               status=CourseStatus.PUBLISHED),
        Course("CS201", "Data Structures",
               DifficultyLevel.INTERMEDIATE, 40,
               description="Arrays, trees, graphs",
               status=CourseStatus.PUBLISHED),
        Course("CS301", "Algorithms",
               DifficultyLevel.ADVANCED, 60,
               description="Sorting, searching, complexity",
               status=CourseStatus.PUBLISHED),
        Course("ML101", "Machine Learning Basics",
               DifficultyLevel.INTERMEDIATE, 50,
               description="Supervised and unsupervised learning",
               status=CourseStatus.PUBLISHED),
        Course("PY101", "Python Programming",
               DifficultyLevel.BEGINNER, 15,
               description="Python fundamentals",
               status=CourseStatus.PUBLISHED),
    ]

    for course in courses:
        try:
            course_svc.create_course(course)
        except Exception:
            pass

    for course_code, prereq_code in [
        ("CS201", "CS101"),
        ("CS201", "CS102"),
        ("CS301", "CS201"),
        ("ML101", "CS201"),
    ]:
        try:
            course_svc.add_prerequisite(course_code, prereq_code)
        except Exception:
            pass

    from core.learner import Learner
    user_repo    = services["user_repo"]
    learner_repo = services["learner_repo"]

    learner_user = user_repo.find_by_username("learner")
    if learner_user and not learner_repo.get_learner_by_user_id(
        learner_user.id
    ):
        try:
            learner_repo.create_learner(Learner(
                name    = "Default Learner",
                email   = "learner@lmpts.edu",
                user_id = learner_user.id,
            ))
        except Exception:
            pass

    # Create instructor account if not exists
    auth_service = services["auth_service"]
    from core.enums import UserRole
    if user_repo.find_by_username("instructor") is None:
        try:
            auth_service.register(
                "instructor", "instructor123", UserRole.INSTRUCTOR
            )
        except Exception:
            pass

    print("Sample data seeded.")


def on_login_success(user, services: dict) -> None:
    """Open the main window after successful login."""
    from gui.main_window import MainWindow
    window = MainWindow(user, services)
    window.mainloop()


def main():
    """Application entry point."""
    print("Starting LMPTS...")

    from repository.database import Database
    db = Database()
    db.initialize()
    print(f"Database: {db.db_path}  Schema v{db.get_schema_version()}")

    services = create_services(db)
    print("Services initialized.")

    auth = services["auth_service"]
    auth.create_default_users()

    seed_sample_data(services)

    from gui.login_window import LoginWindow
    login_window = LoginWindow(
        services         = services,
        on_login_success = on_login_success,
    )
    login_window.mainloop()
    print("LMPTS closed.")


if __name__ == "__main__":
    main()