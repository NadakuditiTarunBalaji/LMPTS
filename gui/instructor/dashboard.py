"""
instructor/dashboard.py
-----------------------
Complete Instructor Dashboard.

Features:
    - Overview statistics
    - Course creation and submission for admin review
    - Learner monitoring per course
    - Mark learner completion with score
    - Prior Learning Request review
    - Course-specific reports
    - Notifications panel
"""

import tkinter as tk
from tkinter import ttk, simpledialog
from typing import Optional

from core.user import User
from core.course import Course
from core.enums import DifficultyLevel, CourseStatus
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"
HEADER_COL = "#1a3a5c"


class InstructorDashboard(tk.Frame):
    """
    Full instructor dashboard with statistics and quick actions.
    """

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user     = user
        self._services = services
        self._build()
        self._load_data()

    def _build(self):
        # Page title
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)

        tk.Label(
            title_frame,
            text=f"Instructor Dashboard",
            font=("Segoe UI", 18, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL,
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text=f"Welcome, {self._user.username}",
            font=("Segoe UI", 10),
            bg=CONTENT_BG, fg="#666666",
        ).pack(anchor="w")

        # Stats row
        stats_frame = tk.Frame(self, bg=CONTENT_BG)
        stats_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._stat_labels = {}
        for title, colour in [
            ("Total Courses",      HEADER_COL),
            ("Active Learners",    "#27ae60"),
            ("Completions",        "#e67e22"),
            ("Pending PLR Reviews","#e74c3c"),
            ("Avg Score",          "#8e44ad"),
        ]:
            card = tk.Frame(
                stats_frame, bg=CARD_BG, padx=15, pady=12
            )
            card.pack(side="left", padx=6, fill="x", expand=True)
            lbl = tk.Label(
                card, text="0",
                font=("Segoe UI", 20, "bold"),
                bg=CARD_BG, fg=colour,
            )
            lbl.pack()
            tk.Label(
                card, text=title,
                font=("Segoe UI", 8),
                bg=CARD_BG, fg="#888888",
            ).pack()
            self._stat_labels[title] = lbl

        ttk.Separator(self, orient="horizontal").pack(
            fill="x", padx=20, pady=5
        )

        # Notifications panel
        bottom = tk.Frame(self, bg=CONTENT_BG)
        bottom.pack(fill="both", expand=True, padx=20, pady=10)

        # Left: notifications
        left = tk.LabelFrame(
            bottom, text="  Notifications",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL, relief="flat",
        )
        left.pack(side="left", fill="both",
                  expand=True, padx=(0, 10))

        self._notif_listbox = tk.Listbox(
            left,
            font=("Segoe UI", 9),
            height=12,
            relief="flat",
            selectmode="single",
        )
        self._notif_listbox.pack(
            fill="both", expand=True, padx=5, pady=5
        )

        tk.Button(
            left,
            text="✓ Mark All Read",
            font=("Segoe UI", 8),
            bg=CONTENT_BG, relief="flat",
            cursor="hand2",
            command=self._mark_notifications_read,
        ).pack(anchor="e", padx=5, pady=(0, 5))

        # Right: quick actions
        right = tk.LabelFrame(
            bottom, text="  Quick Actions",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL, relief="flat",
        )
        right.pack(side="left", fill="y")

        actions = [
            ("📚 Create New Course",         "#27ae60", self._go_create_course),
            ("👁️ Monitor Learners",          HEADER_COL, self._go_monitor),
            ("🔍 Review Prior Learning",     "#e67e22", self._go_plr_review),
            ("📊 Course Reports",            "#8e44ad", self._go_reports),
            ("🔄 Refresh Dashboard",         "#7f8c8d", self._load_data),
        ]

        for text, colour, cmd in actions:
            tk.Button(
                right,
                text=text,
                font=("Segoe UI", 9),
                bg=colour, fg="#ffffff",
                activebackground=colour,
                relief="flat", cursor="hand2",
                pady=8, anchor="w", padx=12,
                command=cmd,
            ).pack(fill="x", padx=10, pady=3)

    def _load_data(self):
        """Load dashboard statistics and notifications."""
        try:
            analytics = self._services.get("analytics_service")
            if analytics:
                overview = analytics.system_overview()
                self._stat_labels["Total Courses"].config(
                    text=str(overview.get("total_courses", 0))
                )
                self._stat_labels["Active Learners"].config(
                    text=str(overview.get("total_learners", 0))
                )
                self._stat_labels["Completions"].config(
                    text=str(overview.get("total_completions", 0))
                )

            # PLR pending count
            plr_repo = self._services.get("plr_repo")
            if plr_repo:
                pending = plr_repo.count_pending()
                self._stat_labels["Pending PLR Reviews"].config(
                    text=str(pending)
                )

            # Avg score
            analytics_svc = self._services.get("analytics_service")
            if analytics_svc:
                scores = analytics_svc.average_score_by_course()
                valid  = [
                    s["average_score"] for s in scores
                    if s["average_score"] is not None
                ]
                avg = (
                    round(sum(valid) / len(valid), 1)
                    if valid else 0
                )
                self._stat_labels["Avg Score"].config(
                    text=f"{avg}"
                )

            # Load notifications
            self._load_notifications()

        except Exception as e:
            print(f"Instructor dashboard load error: {e}")

    def _load_notifications(self):
        """Load unread notifications for this instructor."""
        self._notif_listbox.delete(0, "end")
        try:
            notif_repo = self._services.get("notification_repo")
            if notif_repo is None:
                return

            notifications = notif_repo.get_for_user(
                self._user.id, unread_only=False
            )

            if not notifications:
                self._notif_listbox.insert(
                    "end", "  No notifications"
                )
                return

            for n in notifications[:20]:
                prefix = "🔵 " if not n.is_read else "   "
                created = str(n.created_at)[:16]
                self._notif_listbox.insert(
                    "end",
                    f"{prefix}[{created}] {n.message}"
                )

        except Exception as e:
            print(f"Notifications error: {e}")

    def _mark_notifications_read(self):
        """Mark all notifications as read."""
        try:
            notif_repo = self._services.get("notification_repo")
            if notif_repo:
                notif_repo.mark_all_read(self._user.id)
                self._load_notifications()
        except Exception as e:
            show_error(self, "Error", str(e))

    def _go_create_course(self):
        show_info(self, "Create Course",
                  "Go to 'My Courses' in the sidebar to create a course.")

    def _go_monitor(self):
        show_info(self, "Monitor",
                  "Go to 'Monitor Learners' in the sidebar.")

    def _go_plr_review(self):
        show_info(self, "PLR Review",
                  "Go to 'Prior Learning Review' in the sidebar.")

    def _go_reports(self):
        show_info(self, "Reports",
                  "Go to 'Course Reports' in the sidebar.")