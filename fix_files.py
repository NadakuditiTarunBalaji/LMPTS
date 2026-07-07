# fix_files.py
# Run: python fix_files.py

import os

# ── Fix gui/app.py ─────────────────────────────────────────────────────────────

APP_CONTENT = '''\
"""
app.py
------
LMPTS Application Entry Point.

Run from project root:
    python gui/app.py
"""

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def create_services(database) -> dict:
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
    from auth.auth_service import AuthService
    from algorithms.graph import CourseGraph
    from services.course_service import CourseService
    from services.enrollment_service import EnrollmentService
    from services.progress_service import ProgressService
    from services.analytics_service import AnalyticsService
    from services.learning_path_service import LearningPathService
    from services.recommendation_service import RecommendationService
    from services.prior_learning_service import PriorLearningService
    from services.account_service import AccountService

    user_repo       = SQLiteUserRepository(database)
    learner_repo    = SQLiteLearnerRepository(database)
    course_repo     = SQLiteCourseRepository(database)
    enrollment_repo = SQLiteEnrollmentRepository(database)
    progress_repo   = SQLiteProgressRepository(database)
    plr_repo        = PriorLearningRepository(database)
    notif_repo      = NotificationRepository(database)

    graph = CourseGraph()

    course_service = CourseService(course_repo, graph)

    enrollment_service = EnrollmentService(
        enrollment_repo=enrollment_repo,
        progress_repo=progress_repo,
        learner_repo=learner_repo,
        course_repo=course_repo,
        graph=graph,
        database=database,
    )

    progress_service = ProgressService(
        progress_repo=progress_repo,
        enrollment_repo=enrollment_repo,
        learner_repo=learner_repo,
        course_repo=course_repo,
        graph=graph,
    )

    analytics_service = AnalyticsService(
        enrollment_repo=enrollment_repo,
        progress_repo=progress_repo,
        learner_repo=learner_repo,
        course_repo=course_repo,
        graph=graph,
    )

    learning_path_service = LearningPathService(
        enrollment_repo=enrollment_repo,
        learner_repo=learner_repo,
        course_repo=course_repo,
        graph=graph,
    )

    recommendation_service = RecommendationService(
        enrollment_repo=enrollment_repo,
        learner_repo=learner_repo,
        course_repo=course_repo,
        graph=graph,
    )

    prior_learning_service = PriorLearningService(
        plr_repo=plr_repo,
        notification_repo=notif_repo,
        learner_repo=learner_repo,
        course_repo=course_repo,
        user_repo=user_repo,
        enrollment_service=enrollment_service,
    )

    account_service = AccountService(
        user_repo=user_repo,
        learner_repo=learner_repo,
        notification_repo=notif_repo,
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
        "account_service"        : account_service,
        "user_repo"              : user_repo,
        "learner_repo"           : learner_repo,
        "course_repo"            : course_repo,
        "plr_repo"               : plr_repo,
        "notification_repo"      : notif_repo,
        "database"               : database,
    }


def ensure_defaults_active(services):
    from core.enums import AccountStatus
    user_repo = services["user_repo"]
    for username in ("admin", "learner", "analyst", "instructor"):
        user = user_repo.find_by_username(username)
        if user and user.account_status != AccountStatus.ACTIVE:
            user_repo.update_account_status(
                user_id=user.id,
                is_active=True,
                account_status=AccountStatus.ACTIVE,
            )


def seed_sample_data(services):
    course_svc = services["course_service"]
    if course_svc.count_courses() > 0:
        return

    from core.course import Course
    from core.enums import DifficultyLevel, CourseStatus, UserRole

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
    auth_service = services["auth_service"]

    learner_user = user_repo.find_by_username("learner")
    if learner_user:
        if not learner_repo.get_learner_by_user_id(learner_user.id):
            try:
                learner_repo.create_learner(Learner(
                    name="Default Learner",
                    email="learner@lmpts.edu",
                    user_id=learner_user.id,
                ))
            except Exception:
                pass

    if user_repo.find_by_username("instructor") is None:
        try:
            auth_service.register("instructor", "instructor123", UserRole.INSTRUCTOR)
            instr = user_repo.find_by_username("instructor")
            if instr:
                from core.enums import AccountStatus
                user_repo.update_account_status(
                    user_id=instr.id,
                    is_active=True,
                    account_status=AccountStatus.ACTIVE,
                )
        except Exception:
            pass

    print("Sample data seeded.")


def on_login_success(user, services):
    from gui.main_window import MainWindow
    window = MainWindow(user, services)
    window.mainloop()


def main():
    print("=" * 50)
    print("  LMPTS - Learning Management System")
    print("=" * 50)

    from repository.database import Database
    db = Database()
    db.initialize()
    print(f"Database : {db.db_path}")
    print(f"Schema   : v{db.get_schema_version()}")

    services = create_services(db)
    print("Services : initialized")

    auth = services["auth_service"]
    auth.create_default_users()
    ensure_defaults_active(services)
    print("Accounts : defaults ready")

    seed_sample_data(services)

    print("=" * 50)
    print()
    print("Default credentials:")
    print("  admin      / admin123")
    print("  learner    / learner123")
    print("  analyst    / analyst123")
    print("  instructor / instructor123")
    print()

    from gui.login_window import LoginWindow
    print("Opening login window...")

    login_window = LoginWindow(
        services=services,
        on_login_success=on_login_success,
    )
    login_window.mainloop()
    print("LMPTS closed.")


if __name__ == "__main__":
    main()
'''

# ── Fix gui/login_window.py ────────────────────────────────────────────────────

LOGIN_CONTENT = '''\
"""
login_window.py
---------------
LMPTS Login Screen with self-registration link.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable

BG_OUTER  = "#1a3a5c"
BG_CARD   = "#ffffff"
FG_LABEL  = "#333333"
FG_ERROR  = "#c0392b"
BTN_BG    = "#1a3a5c"
BTN_FG    = "#ffffff"
BTN_HOVER = "#2d5986"


class LoginWindow(tk.Tk):
    """
    LMPTS Login Window.

    Shows login form with username/password fields.
    Includes Register link for new learner self-registration.
    Shows specific messages for PENDING and REJECTED accounts.
    """

    def __init__(self, services: dict, on_login_success: Callable):
        super().__init__()
        self._services         = services
        self._on_login_success = on_login_success
        self._remember_var     = tk.BooleanVar(value=False)

        self.title("LMPTS - Login")
        self.geometry("480x600")
        self.resizable(False, False)
        self.configure(bg=BG_OUTER)

        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 480) // 2
        y = (self.winfo_screenheight() - 600) // 2
        self.geometry(f"480x600+{x}+{y}")

        self._build()

    def _build(self):
        """Construct all UI widgets."""
        outer = tk.Frame(self, bg=BG_OUTER)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        tk.Label(
            outer,
            text="LMPTS",
            font=("Segoe UI", 28, "bold"),
            bg=BG_OUTER, fg="#ffffff",
        ).pack(pady=(0, 4))

        tk.Label(
            outer,
            text="Learning Management and\\nPrerequisite Tracking System",
            font=("Segoe UI", 10),
            bg=BG_OUTER, fg="#a8c8e8",
            justify="center",
        ).pack(pady=(0, 20))

        # Card
        card = tk.Frame(outer, bg=BG_CARD, padx=40, pady=35)
        card.pack()

        # Username
        tk.Label(
            card,
            text="Username",
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD, fg=FG_LABEL, anchor="w",
        ).pack(fill="x", pady=(0, 3))

        self._username_var = tk.StringVar()
        self._username_entry = ttk.Entry(
            card,
            textvariable=self._username_var,
            font=("Segoe UI", 11),
            width=28,
        )
        self._username_entry.pack(fill="x", ipady=4)

        tk.Frame(card, height=12, bg=BG_CARD).pack()

        # Password
        tk.Label(
            card,
            text="Password",
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD, fg=FG_LABEL, anchor="w",
        ).pack(fill="x", pady=(0, 3))

        self._password_var = tk.StringVar()
        self._password_entry = ttk.Entry(
            card,
            textvariable=self._password_var,
            show="*",
            font=("Segoe UI", 11),
            width=28,
        )
        self._password_entry.pack(fill="x", ipady=4)

        tk.Frame(card, height=8, bg=BG_CARD).pack()

        # Remember me
        ttk.Checkbutton(
            card,
            text="Remember me",
            variable=self._remember_var,
        ).pack(anchor="w")

        tk.Frame(card, height=20, bg=BG_CARD).pack()

        # Login button
        self._login_btn = tk.Button(
            card,
            text="LOGIN",
            font=("Segoe UI", 11, "bold"),
            bg=BTN_BG, fg=BTN_FG,
            activebackground=BTN_HOVER,
            activeforeground=BTN_FG,
            relief="flat", cursor="hand2",
            width=24, pady=8,
            command=self._attempt_login,
        )
        self._login_btn.pack(fill="x")

        self._login_btn.bind(
            "<Enter>", lambda e: self._login_btn.config(bg=BTN_HOVER)
        )
        self._login_btn.bind(
            "<Leave>", lambda e: self._login_btn.config(bg=BTN_BG)
        )

        tk.Frame(card, height=12, bg=BG_CARD).pack()

        # Status / error label
        self._error_var = tk.StringVar()
        self._error_label = tk.Label(
            card,
            textvariable=self._error_var,
            font=("Segoe UI", 9),
            bg=BG_CARD, fg=FG_ERROR,
            wraplength=300,
            justify="center",
        )
        self._error_label.pack()

        # Divider
        tk.Frame(card, height=1, bg="#eeeeee").pack(
            fill="x", pady=(12, 0)
        )

        # Register link
        reg_frame = tk.Frame(card, bg=BG_CARD)
        reg_frame.pack(fill="x", pady=(10, 0))

        tk.Label(
            reg_frame,
            text="New to LMPTS?",
            font=("Segoe UI", 9),
            bg=BG_CARD, fg="#666666",
        ).pack(side="left")

        reg_link = tk.Label(
            reg_frame,
            text="  Create Account",
            font=("Segoe UI", 9, "bold", "underline"),
            bg=BG_CARD, fg="#1a3a5c",
            cursor="hand2",
        )
        reg_link.pack(side="left")
        reg_link.bind("<Button-1>", lambda e: self._open_register())

        # Bind Enter key
        self.bind("<Return>", lambda e: self._attempt_login())

        # Focus username
        self._username_entry.focus()

    def _attempt_login(self):
        """Validate credentials and attempt login."""
        self._error_var.set("")
        self._error_label.config(fg=FG_ERROR)

        username = self._username_var.get().strip()
        password = self._password_var.get()

        if not username:
            self._error_var.set("Please enter your username.")
            self._username_entry.focus()
            return

        if not password:
            self._error_var.set("Please enter your password.")
            self._password_entry.focus()
            return

        try:
            auth_service = self._services.get("auth_service")
            if auth_service is None:
                self._error_var.set("Authentication service unavailable.")
                return

            user = auth_service.login(username, password)
            self.destroy()
            self._on_login_success(user, self._services)

        except Exception as e:
            error_msg = str(e)

            if error_msg.startswith("PENDING:"):
                clean = error_msg.replace("PENDING:", "").strip()
                self._error_var.set(clean)
                self._error_label.config(fg="#e67e22")
            elif error_msg.startswith("REJECTED:"):
                clean = error_msg.replace("REJECTED:", "").strip()
                self._error_var.set(clean)
                self._error_label.config(fg=FG_ERROR)
            else:
                self._error_var.set("Invalid username or password.")

            self._password_var.set("")
            try:
                self._password_entry.focus()
            except Exception:
                pass

    def _open_register(self):
        """Open the self-registration window."""
        try:
            from gui.register_window import RegisterWindow

            def on_back():
                try:
                    self.deiconify()
                    self.focus_force()
                    self._username_entry.focus()
                except Exception:
                    pass

            self.iconify()
            RegisterWindow(
                parent=self,
                services=self._services,
                on_back_to_login=on_back,
            )
        except Exception as ex:
            self._error_var.set(f"Could not open registration: {ex}")
'''

# ── Write both files ───────────────────────────────────────────────────────────

files = {
    r"C:\LMPTS\gui\app.py":          APP_CONTENT,
    r"C:\LMPTS\gui\login_window.py": LOGIN_CONTENT,
}

for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    with open(path, "rb") as f:
        raw = f.read()

    null_bytes = raw.count(b"\x00")
    size       = len(raw)
    status     = "CLEAN" if null_bytes == 0 else f"BAD ({null_bytes} nulls)"

    print(f"{status}  {path}  ({size} bytes)")

print()
print("Done. Run: python gui/app.py")