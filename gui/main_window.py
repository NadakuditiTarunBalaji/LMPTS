"""
main_window.py
--------------
Main application window after successful login.
"""

import tkinter as tk
from tkinter import ttk
from core.user import User
from core.enums import UserRole
from gui.widgets.sidebar import Sidebar


HEADER_BG  = "#1a3a5c"
HEADER_FG  = "#ffffff"
CONTENT_BG = "#f0f4f8"


class MainWindow(tk.Tk):
    """
    Main application shell.
    Builds header + sidebar + content area.
    Routes to the correct dashboard based on user role.
    """

    def __init__(self, user: User, services: dict):
        super().__init__()
        self._user     = user
        self._services = services

        self.title(f"LMPTS — {user.role.value.title()} Panel")
        self.geometry("1200x750")
        self.minsize(900, 600)
        self.configure(bg=CONTENT_BG)

        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 1200) // 2
        y = (self.winfo_screenheight() - 750)  // 2
        self.geometry(f"1200x750+{x}+{y}")

        self._content_frame = None
        self._build_header()
        self._build_body()
        self._load_default_screen()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Header ─────────────────────────────────────────────────────────────────

    def _build_header(self):
        header = tk.Frame(self, bg=HEADER_BG, height=55)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(
            header, text="LMPTS",
            font=("Segoe UI", 16, "bold"),
            bg=HEADER_BG, fg=HEADER_FG,
        ).pack(side="left", padx=20, pady=10)

        tk.Label(
            header,
            text="Learning Management & Prerequisite Tracking System",
            font=("Segoe UI", 9),
            bg=HEADER_BG, fg="#a8c8e8",
        ).pack(side="left", pady=10)

        user_frame = tk.Frame(header, bg=HEADER_BG)
        user_frame.pack(side="right", padx=20, pady=5)

        tk.Label(
            user_frame,
            text=f"👤  {self._user.username}",
            font=("Segoe UI", 10, "bold"),
            bg=HEADER_BG, fg=HEADER_FG,
        ).pack(anchor="e")

        tk.Label(
            user_frame,
            text=self._user.role.value,
            font=("Segoe UI", 8),
            bg=HEADER_BG, fg="#a8c8e8",
        ).pack(anchor="e")

    # ── Body ───────────────────────────────────────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self, bg=CONTENT_BG)
        body.pack(fill="both", expand=True)

        nav_items = self._get_nav_items()

        self._sidebar = Sidebar(
            body,
            title="LMPTS",
            subtitle=f"{self._user.role.value.title()} Panel",
            nav_items=nav_items,
            logout_command=self._logout,
        )
        self._sidebar.pack(side="left", fill="y")

        tk.Frame(body, bg="#cccccc", width=1).pack(side="left", fill="y")

        self._content_frame = tk.Frame(body, bg=CONTENT_BG)
        self._content_frame.pack(side="left", fill="both", expand=True)

    def _get_nav_items(self) -> list:
        role = self._user.role
        # In _get_nav_items() for ADMIN role — update to include pending:
        if role == UserRole.ADMIN:
            return [
                ("Dashboard",              self._show_admin_dashboard),
                ("⏳ Pending Registrations", self._show_pending_registrations),  # NEW
                ("Courses",                self._show_course_management),
                ("Course Approvals",       self._show_course_approvals),
                ("Prerequisites",          self._show_prerequisite_management),
                ("Learners",               self._show_learner_management),
                ("Users",                  self._show_user_management),
                ("Prior Learning",         self._show_plr_approval),
                ("Analytics",              self._show_analytics),
            ]
            # LEARNER — add Prior Learning

        elif role == UserRole.LEARNER:
            return [
                ("Dashboard",          self._show_learner_dashboard),
                ("My Courses",         self._show_enrollments),
                ("Learning Path",      self._show_learning_path),
                ("Progress",           self._show_progress),
                ("Prior Learning",     self._show_prior_learning),      # NEW
                ("Recommendations",    self._show_recommendations),
            ]
        elif role == UserRole.ANALYST:
            return [
                ("Dashboard",        self._show_analyst_dashboard),
                ("Reports",          self._show_analytics_reports),
                ("Completion Stats", self._show_completion_stats),
                ("Bottlenecks",      self._show_bottlenecks),
            ]
        elif role == UserRole.INSTRUCTOR:
            return [
                ("Dashboard",          self._show_instructor_dashboard),
                ("My Courses",         self._show_instructor_courses),
                ("Monitor Learners",   self._show_learner_monitor),
                ("Review Prior Learning", self._show_plr_review),
                ("Course Reports",     self._show_course_reports),
            ]
        return []
    # Add this method to MainWindow:
    def _show_pending_registrations(self):
        self._clear_content()
        from gui.admin.pending_registrations import PendingRegistrationsScreen
        PendingRegistrationsScreen(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    # ── Screen routing ─────────────────────────────────────────────────────────

    def _clear_content(self):
        if self._content_frame:
            for widget in self._content_frame.winfo_children():
                widget.destroy()

    def _load_default_screen(self):
        role = self._user.role
        if role == UserRole.ADMIN:
            self._show_admin_dashboard()
        elif role == UserRole.LEARNER:
            self._show_learner_dashboard()
        elif role == UserRole.ANALYST:
            self._show_analyst_dashboard()
        elif role == UserRole.INSTRUCTOR:
            self._show_instructor_dashboard()

    # ── Admin screens ──────────────────────────────────────────────────────────
    # Admin new methods
    def _show_course_approvals(self):
        self._clear_content()
        from gui.admin.course_approvals import CourseApprovalScreen
        CourseApprovalScreen(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    def _show_plr_approval(self):
        self._clear_content()
        from gui.admin.plr_approval import PLRApprovalScreen
        PLRApprovalScreen(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    # Learner new method
    def _show_prior_learning(self):
        self._clear_content()
        from gui.learner.prior_learning import PriorLearningScreen
        PriorLearningScreen(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    def _show_admin_dashboard(self):
        self._clear_content()
        from gui.admin_dashboard import AdminDashboard
        AdminDashboard(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    def _show_course_management(self):
        self._clear_content()
        from gui.admin.course_management import CourseManagementScreen
        CourseManagementScreen(
            self._content_frame, self._services
        ).pack(fill="both", expand=True)

    def _show_prerequisite_management(self):
        self._clear_content()
        from gui.admin.prerequisite_management import PrerequisiteManagementScreen
        PrerequisiteManagementScreen(
            self._content_frame, self._services
        ).pack(fill="both", expand=True)

    def _show_learner_management(self):
        self._clear_content()
        from gui.admin.learner_management import LearnerManagementScreen
        LearnerManagementScreen(
            self._content_frame, self._services
        ).pack(fill="both", expand=True)

    def _show_user_management(self):
        self._clear_content()
        from gui.admin.user_management import UserManagementScreen
        UserManagementScreen(
            self._content_frame, self._services
        ).pack(fill="both", expand=True)

    def _show_analytics(self):
        self._clear_content()
        from gui.analytics_dashboard import AnalyticsDashboard
        AnalyticsDashboard(
            self._content_frame, self._services
        ).pack(fill="both", expand=True)

    # ── Learner screens ────────────────────────────────────────────────────────

    def _show_learner_dashboard(self):
        self._clear_content()
        from gui.learner_dashboard import LearnerDashboard
        LearnerDashboard(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    def _show_enrollments(self):
        self._clear_content()
        from gui.learner.enrollments import EnrollmentsScreen
        EnrollmentsScreen(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    def _show_learning_path(self):
        self._clear_content()
        from gui.learner.progress import LearningPathScreen
        LearningPathScreen(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    def _show_progress(self):
        self._clear_content()
        from gui.learner.progress import ProgressScreen
        ProgressScreen(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    def _show_recommendations(self):
        self._clear_content()
        from gui.learner.recommendations import RecommendationsScreen
        RecommendationsScreen(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    # ── Analyst screens ────────────────────────────────────────────────────────

    def _show_analyst_dashboard(self):
        self._clear_content()
        from gui.analytics_dashboard import AnalyticsDashboard
        AnalyticsDashboard(
            self._content_frame, self._services
        ).pack(fill="both", expand=True)

    def _show_analytics_reports(self):
        self._clear_content()
        from gui.analyst.analytics import AnalyticsScreen
        AnalyticsScreen(
            self._content_frame, self._services
        ).pack(fill="both", expand=True)

    def _show_completion_stats(self):
        self._clear_content()
        from gui.analyst.analytics import CompletionStatsScreen
        CompletionStatsScreen(
            self._content_frame, self._services
        ).pack(fill="both", expand=True)

    def _show_bottlenecks(self):
        self._clear_content()
        from gui.analyst.analytics import BottleneckScreen
        BottleneckScreen(
            self._content_frame, self._services
        ).pack(fill="both", expand=True)

    # ── Instructor screens ─────────────────────────────────────────────────────

    # Update existing _show_instructor_dashboard
    def _show_instructor_dashboard(self):
        self._clear_content()
        from gui.instructor.dashboard import InstructorDashboard
        InstructorDashboard(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    # Update existing _show_learner_monitor
    def _show_learner_monitor(self):
        self._clear_content()
        from gui.instructor.learner_monitor import LearnerMonitorScreen
        LearnerMonitorScreen(
            self._content_frame, self._services, self._user
        ).pack(fill="both", expand=True)

    # ── Session ────────────────────────────────────────────────────────────────

    def _logout(self):
        from gui.dialogs.confirm_dialog import confirm
        if confirm(self, "Logout", "Are you sure you want to logout?"):
            try:
                auth = self._services.get("auth_service")
                if auth:
                    auth.logout()
            except Exception:
                pass
            self.destroy()
            self._reopen_login()

    def _reopen_login(self):
        import subprocess
        import sys
        subprocess.Popen([sys.executable, "gui/app.py"])

    def _on_close(self):
        try:
            auth = self._services.get("auth_service")
            if auth:
                auth.logout()
        except Exception:
            pass
        self.destroy()
    def _show_instructor_courses(self):
        self._clear_content()
        from gui.instructor.course_manager import InstructorCourseManager
        InstructorCourseManager(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    def _show_plr_review(self):
        self._clear_content()
        from gui.instructor.plr_review import PLRReviewScreen
        PLRReviewScreen(
            self._content_frame, self._user, self._services
        ).pack(fill="both", expand=True)

    def _show_course_reports(self):
        self._clear_content()
        from gui.instructor.learner_monitor import LearnerMonitorScreen
        LearnerMonitorScreen(
            self._content_frame, self._services, self._user
        ).pack(fill="both", expand=True)

