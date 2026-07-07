"""
admin_dashboard.py
------------------
Admin overview dashboard showing key system statistics.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict
from core.user import User


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"
HEADER_BG  = "#1a3a5c"
ACCENT     = "#4a90d9"


class StatCard(tk.Frame):
    """A single statistics card widget."""

    def __init__(
        self,
        parent,
        title: str,
        value: str,
        colour: str = "#1a3a5c",
        **kwargs
    ):
        super().__init__(
            parent,
            bg=CARD_BG,
            relief="flat",
            bd=0,
            padx=20,
            pady=15,
            **kwargs
        )

        tk.Label(
            self,
            text=value,
            font=("Segoe UI", 28, "bold"),
            bg=CARD_BG,
            fg=colour,
        ).pack()

        tk.Label(
            self,
            text=title,
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg="#666666",
        ).pack()


class AdminDashboard(tk.Frame):
    """
    Admin dashboard showing system overview statistics.

    Displays:
        - Total courses / learners / enrollments
        - Overall completion rate
        - Recent activity table
        - Quick action buttons
    """

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user     = user
        self._services = services
        self._build()
        self._load_data()

    def _build(self):
        """Build the dashboard layout."""
        # Page title
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)

        tk.Label(
            title_frame,
            text="Admin Dashboard",
            font=("Segoe UI", 18, "bold"),
            bg=CONTENT_BG,
            fg="#1a3a5c",
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="System overview and quick actions",
            font=("Segoe UI", 10),
            bg=CONTENT_BG,
            fg="#666666",
        ).pack(anchor="w")

        # Stats row
        self._stats_frame = tk.Frame(self, bg=CONTENT_BG)
        self._stats_frame.pack(fill="x", padx=20, pady=(0, 20))

        # Placeholder stat cards (filled by _load_data)
        self._stat_cards = {}

        stats = [
            ("Total Courses",      "0", "#1a3a5c"),
            ("Total Learners",     "0", "#27ae60"),
            ("Total Enrollments",  "0", "#e67e22"),
            ("Completion Rate",    "0%", "#8e44ad"),
        ]
        for title, value, colour in stats:
            card = StatCard(
                self._stats_frame,
                title=title,
                value=value,
                colour=colour,
            )
            card.pack(side="left", padx=8, pady=5, fill="x", expand=True)
            self._stat_cards[title] = card

        # Separator
        ttk.Separator(self, orient="horizontal").pack(
            fill="x", padx=20, pady=5
        )

        # Bottom: two columns
        bottom = tk.Frame(self, bg=CONTENT_BG)
        bottom.pack(fill="both", expand=True, padx=20, pady=10)

        # Left: recent enrollments table
        left = tk.LabelFrame(
            bottom,
            text="  Recent Enrollments",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG,
            fg="#1a3a5c",
            relief="flat",
            bd=1,
        )
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self._build_recent_table(left)

        # Right: quick actions + difficulty distribution
        right = tk.Frame(bottom, bg=CONTENT_BG)
        right.pack(side="left", fill="both", padx=(10, 0))
        self._build_quick_actions(right)
        self._build_difficulty_frame(right)

    def _build_recent_table(self, parent):
        """Build recent enrollments treeview."""
        columns = ("learner", "course", "status", "date")
        self._recent_tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=12,
        )
        for col, header, width in [
            ("learner", "Learner", 120),
            ("course",  "Course",  100),
            ("status",  "Status",   90),
            ("date",    "Date",    110),
        ]:
            self._recent_tree.heading(col, text=header)
            self._recent_tree.column(col, width=width)

        scroll = ttk.Scrollbar(
            parent, orient="vertical",
            command=self._recent_tree.yview
        )
        self._recent_tree.configure(yscrollcommand=scroll.set)
        self._recent_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_quick_actions(self, parent):
        """Build quick action buttons panel."""
        qa_frame = tk.LabelFrame(
            parent,
            text="  Quick Actions",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG,
            fg="#1a3a5c",
            relief="flat",
        )
        qa_frame.pack(fill="x", pady=(0, 10))

        actions = [
            ("➕  Add New Course",    self._action_add_course),
            ("👤  Add New Learner",   self._action_add_learner),
            ("📊  View Analytics",    self._action_analytics),
            ("🔄  Refresh Data",      self._load_data),
        ]

        for text, command in actions:
            btn = tk.Button(
                qa_frame,
                text=text,
                font=("Segoe UI", 9),
                bg="#ffffff",
                fg="#1a3a5c",
                activebackground="#e8f0fe",
                relief="flat",
                bd=1,
                cursor="hand2",
                anchor="w",
                padx=15,
                pady=6,
                command=command,
            )
            btn.pack(fill="x", pady=2, padx=5)

    def _build_difficulty_frame(self, parent):
        """Build difficulty distribution panel."""
        diff_frame = tk.LabelFrame(
            parent,
            text="  Difficulty Distribution",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG,
            fg="#1a3a5c",
            relief="flat",
        )
        diff_frame.pack(fill="x")

        self._diff_labels = {}
        for level, colour in [
            ("BEGINNER",     "#27ae60"),
            ("INTERMEDIATE", "#e67e22"),
            ("ADVANCED",     "#c0392b"),
        ]:
            row = tk.Frame(diff_frame, bg=CONTENT_BG)
            row.pack(fill="x", padx=10, pady=3)

            tk.Label(
                row,
                text=level,
                font=("Segoe UI", 9),
                bg=CONTENT_BG,
                fg=colour,
                width=14,
                anchor="w",
            ).pack(side="left")

            lbl = tk.Label(
                row,
                text="0",
                font=("Segoe UI", 9, "bold"),
                bg=CONTENT_BG,
                fg="#333333",
            )
            lbl.pack(side="right")
            self._diff_labels[level] = lbl

    # ── Data Loading ───────────────────────────────────────────────────────────

    def _load_data(self):
        """Load and display all dashboard data."""
        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                return

            overview = analytics.system_overview()

            # Update stat cards
            self._update_stat("Total Courses",
                str(overview.get("total_courses", 0)))
            self._update_stat("Total Learners",
                str(overview.get("total_learners", 0)))
            self._update_stat("Total Enrollments",
                str(overview.get("total_enrollments", 0)))
            self._update_stat("Completion Rate",
                f"{overview.get('overall_completion_rate', 0)}%")

            # Difficulty distribution
            diff = overview.get("difficulty_distribution", {})
            for level in ("BEGINNER", "INTERMEDIATE", "ADVANCED"):
                if level in self._diff_labels:
                    self._diff_labels[level].config(
                        text=str(diff.get(level, 0))
                    )

            # Recent enrollments
            self._load_recent_enrollments()

        except Exception as e:
            print(f"Dashboard load error: {e}")

    def _update_stat(self, title: str, value: str):
        """Update a stat card's value label."""
        card = self._stat_cards.get(title)
        if card:
            for widget in card.winfo_children():
                if isinstance(widget, tk.Label):
                    current = widget.cget("font")
                    if "28" in str(current):
                        widget.config(text=value)
                        break

    def _load_recent_enrollments(self):
        """Populate recent enrollments table."""
        for item in self._recent_tree.get_children():
            self._recent_tree.delete(item)

        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                return

            report = analytics.learner_activity_report()

            for learner_data in report[:20]:
                for course_data in learner_data.get("courses", [])[:3]:
                    enrolled_at = ""
                    self._recent_tree.insert(
                        "", "end",
                        values=(
                            learner_data.get("learner_name", ""),
                            course_data.get("course_code", ""),
                            course_data.get("status", ""),
                            enrolled_at,
                        )
                    )
        except Exception as e:
            print(f"Recent enrollments error: {e}")

    # ── Quick Actions ──────────────────────────────────────────────────────────

    def _action_add_course(self):
        from gui.dialogs.confirm_dialog import show_info
        show_info(
            self,
            "Add Course",
            "Go to Courses → Add Course to create a new course."
        )

    def _action_add_learner(self):
        from gui.dialogs.confirm_dialog import show_info
        show_info(
            self,
            "Add Learner",
            "Go to Learners → Add Learner to create a new learner."
        )

    def _action_analytics(self):
        from gui.dialogs.confirm_dialog import show_info
        show_info(
            self,
            "Analytics",
            "Go to Analytics in the sidebar to view reports."
        )
        