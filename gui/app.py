"""
app.py
------
LMPTS Application Entry Point.

Usage:
    python gui/app.py

Or from project root:
    python -m gui.app

Startup sequence:
    1. Initialize database (create tables if not exist)
    2. Create all service instances (global container)
    3. Create default users (admin/learner/analyst)
    4. Open login window
    5. On login success → open main window

Service container structure:
    services = {
        "auth_service"          : AuthService,
        "course_service"        : CourseService,
        "enrollment_service"    : EnrollmentService,
        "progress_service"      : ProgressService,
        "analytics_service"     : AnalyticsService,
        "learning_path_service" : LearningPathService,
        "recommendation_service": RecommendationService,
        "user_repo"             : SQLiteUserRepository,
        "learner_repo"          : SQLiteLearnerRepository,
        "database"              : Database,
    }
"""

import sys
import os
import traceback
import tkinter as tk
from tkinter import messagebox

# ── Ensure project root is on sys.path when running from gui/ folder ──────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ══════════════════════════════════════════════════════════════════════════════
# Pre-flight checks  (run BEFORE Tk is created so errors are visible early)
# ══════════════════════════════════════════════════════════════════════════════

def _check_file_integrity(filepath: str) -> tuple[bool, str]:
    """
    Check a Python source file for null bytes or other corruption.

    Args:
        filepath: Absolute path to the .py file.

    Returns:
        (ok: bool, message: str)
    """
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}"

    try:
        with open(filepath, "rb") as fh:
            raw = fh.read()

        if b"\x00" in raw:
            null_count = raw.count(b"\x00")
            return (
                False,
                f"Corrupted file ({null_count} null bytes): {filepath}\n"
                f"Fix: run  python fix_nullbytes.py  then restart.",
            )

        # Try compiling to catch SyntaxErrors early
        compile(raw.decode("utf-8", errors="replace"), filepath, "exec")
        return True, "OK"

    except SyntaxError as exc:
        return False, f"SyntaxError in {filepath}:\n  {exc}"
    except Exception as exc:
        return False, f"Cannot read {filepath}:\n  {exc}"


def _preflight_checks() -> None:
    """
    Validate critical source files before the GUI is created.

    Raises SystemExit with a clear message if anything is wrong.
    This prevents cryptic errors from appearing inside Tkinter callbacks.
    """
    gui_dir = os.path.dirname(os.path.abspath(__file__))

    critical_files = [
        os.path.join(gui_dir, "main_window.py"),
        os.path.join(gui_dir, "login_window.py"),
    ]

    errors = []
    for path in critical_files:
        ok, msg = _check_file_integrity(path)
        if not ok:
            errors.append(msg)

    if errors:
        # Print to stderr so it is visible in the terminal
        print("\n[LMPTS] STARTUP ERROR — corrupted source files:\n", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}\n", file=sys.stderr)

        # Also show a plain Tk dialog (no main window needed)
        _show_fatal_dialog(
            title="LMPTS — Startup Error",
            message=(
                "One or more application files are corrupted.\n\n"
                + "\n\n".join(errors)
                + "\n\nPlease run  fix_nullbytes.py  and restart."
            ),
        )
        sys.exit(1)


def _show_fatal_dialog(title: str, message: str) -> None:
    """
    Show a standalone error dialog that does NOT depend on the main window.

    Safe to call at any point, even before or after the main Tk loop.
    """
    try:
        root = tk.Tk()
        root.withdraw()          # Hide the blank root window
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        pass  # Terminal-only fallback; message already printed to stderr


# ══════════════════════════════════════════════════════════════════════════════
# Service container
# ══════════════════════════════════════════════════════════════════════════════

def create_services(database) -> dict:
    """
    Build and return the global service container.

    All services share the same Database instance and CourseGraph.
    The CourseGraph is built once from the database and reused.

    Args:
        database: Initialized Database instance.

    Returns:
        dict: All services and key repositories.
    """
    from repository.user_repo import SQLiteUserRepository
    from repository.learner_repo import SQLiteLearnerRepository
    from repository.course_repo import SQLiteCourseRepository
    from repository.enrollment_repo import (
        SQLiteEnrollmentRepository,
        SQLiteProgressRepository,
    )
    from auth.auth_service import AuthService
    from algorithms.graph import CourseGraph
    from services.course_service import CourseService
    from services.enrollment_service import EnrollmentService
    from services.progress_service import ProgressService
    from services.analytics_service import AnalyticsService
    from services.learning_path_service import LearningPathService
    from services.recommendation_service import RecommendationService

    # ── Repositories ──────────────────────────────────────────────────────────
    user_repo       = SQLiteUserRepository(database)
    learner_repo    = SQLiteLearnerRepository(database)
    course_repo     = SQLiteCourseRepository(database)
    enrollment_repo = SQLiteEnrollmentRepository(database)
    progress_repo   = SQLiteProgressRepository(database)

    # ── Shared CourseGraph (built from DB, reused across all services) ────────
    graph = CourseGraph()

    # ── Services ──────────────────────────────────────────────────────────────
    course_service = CourseService(course_repo, graph)

    enrollment_service = EnrollmentService(
        enrollment_repo = enrollment_repo,
        progress_repo   = progress_repo,
        learner_repo    = learner_repo,
        course_repo     = course_repo,
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

    auth_service = AuthService(user_repo)

    return {
        # Core services
        "auth_service"           : auth_service,
        "course_service"         : course_service,
        "enrollment_service"     : enrollment_service,
        "progress_service"       : progress_service,
        "analytics_service"      : analytics_service,
        "learning_path_service"  : learning_path_service,
        "recommendation_service" : recommendation_service,
        # Key repositories (needed by some GUI screens)
        "user_repo"    : user_repo,
        "learner_repo" : learner_repo,
        "database"     : database,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Sample data seeder
# ══════════════════════════════════════════════════════════════════════════════

def seed_sample_data(services: dict) -> None:
    """
    Seed sample courses and learners for demonstration.

    Creates:
        - 6 sample courses with prerequisites
        - 2 sample learners (linked to default user accounts)

    Only runs if no courses exist (idempotent).
    """
    course_svc = services["course_service"]

    # Skip if data already exists
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
            pass  # Already exists

    # ── Prerequisites ─────────────────────────────────────────────────────────
    prereqs = [
        ("CS201", "CS101"),
        ("CS201", "CS102"),
        ("CS301", "CS201"),
        ("ML101", "CS201"),
    ]
    for course_code, prereq_code in prereqs:
        try:
            course_svc.add_prerequisite(course_code, prereq_code)
        except Exception:
            pass

    # ── Learner profiles for default users ────────────────────────────────────
    from core.learner import Learner

    user_repo    = services["user_repo"]
    learner_repo = services["learner_repo"]

    learner_user = user_repo.find_by_username("learner")
    if learner_user and not learner_repo.get_learner_by_user_id(learner_user.id):
        try:
            learner_repo.create_learner(Learner(
                name    = "Default Learner",
                email   = "learner@lmpts.edu",
                user_id = learner_user.id,
            ))
        except Exception:
            pass

    print("Sample data seeded successfully.")


# ══════════════════════════════════════════════════════════════════════════════
# Login-success callback
# ══════════════════════════════════════════════════════════════════════════════

def on_login_success(user, services: dict) -> None:
    """
    Callback invoked by LoginWindow after successful authentication.

    Imports and opens MainWindow.  Any import or runtime error is caught
    here so it never leaks back into the LoginWindow's event handler.

    Args:
        user     : Authenticated User object.
        services : Global service container dict.
    """
    try:
        # Import here so startup is not slowed down unnecessarily,
        # but we do the import BEFORE destroying the login window.
        from gui.main_window import MainWindow

    except SyntaxError as exc:
        # Corrupted file — should have been caught by _preflight_checks,
        # but handle gracefully just in case the file was changed at runtime.
        _show_fatal_dialog(
            title="LMPTS — Import Error",
            message=(
                f"Cannot open Main Window.\n\n"
                f"main_window.py contains a syntax error:\n"
                f"  {exc}\n\n"
                f"Run  fix_nullbytes.py  and restart the application."
            ),
        )
        sys.exit(1)

    except ImportError as exc:
        _show_fatal_dialog(
            title="LMPTS — Import Error",
            message=f"Cannot open Main Window.\n\nMissing module:\n  {exc}",
        )
        sys.exit(1)

    except Exception as exc:
        _show_fatal_dialog(
            title="LMPTS — Unexpected Error",
            message=(
                f"Cannot open Main Window.\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                f"{traceback.format_exc()}"
            ),
        )
        sys.exit(1)

    # ── All imports succeeded — launch the main window ────────────────────────
    try:
        window = MainWindow(user, services)
        window.mainloop()

    except Exception as exc:
        _show_fatal_dialog(
            title="LMPTS — Runtime Error",
            message=(
                f"Main Window crashed unexpectedly.\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                f"{traceback.format_exc()}"
            ),
        )
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Application entry point.

    Order:
        1. Pre-flight integrity checks on critical .py files.
        2. Database initialization.
        3. Service container creation.
        4. Default users + sample data seeding.
        5. Login window.
        6. On success → main window (via on_login_success callback).
    """
    # ── 1. Integrity checks (before any Tk window is created) ─────────────────
    _preflight_checks()

    print("Starting LMPTS...")

    # ── 2. Database ───────────────────────────────────────────────────────────
    try:
        from repository.database import Database
        db = Database()
        db.initialize()
        print(f"Database ready   : {db.db_path}")
        print(f"Schema version   : {db.get_schema_version()}")
    except Exception as exc:
        print(f"[FATAL] Database initialization failed: {exc}", file=sys.stderr)
        _show_fatal_dialog(
            "LMPTS — Database Error",
            f"Could not initialize database:\n\n{exc}",
        )
        sys.exit(1)

    # ── 3. Services ───────────────────────────────────────────────────────────
    try:
        services = create_services(db)
        print("Services initialized.")
    except Exception as exc:
        print(f"[FATAL] Service creation failed: {exc}", file=sys.stderr)
        _show_fatal_dialog(
            "LMPTS — Service Error",
            f"Could not create services:\n\n{exc}",
        )
        sys.exit(1)

    # ── 4. Default users + sample data ────────────────────────────────────────
    try:
        auth = services["auth_service"]
        auth.create_default_users()
        print("Default users ready.")
        seed_sample_data(services)
    except Exception as exc:
        # Non-fatal — log and continue
        print(f"[WARNING] Seeding failed: {exc}", file=sys.stderr)

    # ── 5. Login window ───────────────────────────────────────────────────────
    try:
        from gui.login_window import LoginWindow
        print("Opening LMPTS login window...")

        login_window = LoginWindow(
            services         = services,
            on_login_success = on_login_success,
        )
        login_window.mainloop()

    except Exception as exc:
        print(f"[FATAL] Login window error: {exc}", file=sys.stderr)
        traceback.print_exc()
        _show_fatal_dialog(
            "LMPTS — Fatal Error",
            f"Application failed to start:\n\n{type(exc).__name__}: {exc}",
        )
        sys.exit(1)

    print("LMPTS closed.")


if __name__ == "__main__":
    main()