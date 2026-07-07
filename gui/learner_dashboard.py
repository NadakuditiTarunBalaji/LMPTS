"""
learner_dashboard.py
--------------------
Learner's personal dashboard showing progress overview.
"""

import tkinter as tk
from tkinter import ttk
from core.user import User


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


class LearnerDashboard(tk.Frame):
    """
    Learner dashboard overview.

    Displays:
        - Welcome message
        - Current enrollment count
        - Completion rate (progress bar)
        - Active courses list
        - Available next courses
    """

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user     = user
        self._services = services
        self._learner_id = None
        self._build()
        self._load_data()

    def _build(self):
        """Build the learner dashboard layout."""
        # Welcome header
        header = tk.Frame(self, bg=CONTENT_BG, pady=15)
        header.pack(fill="x", padx=20)

        tk.Label(
            header,
            text=f"Welcome back, {self._user.username}!",
            font=("Segoe UI", 18, "bold"),
            bg=CONTENT_BG,
            fg="#1a3a5c",
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Here is your learning progress overview",
            font=("Segoe UI", 10),
            bg=CONTENT_BG,
            fg="#666666",
        ).pack(anchor="w")

        # Stats row
        stats_frame = tk.Frame(self, bg=CONTENT_BG)
        stats_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._stat_labels = {}
        for title, colour in [
            ("Enrolled",    "#1a3a5c"),
            ("Completed",   "#27ae60"),
            ("In Progress", "#e67e22"),
            ("Available",   "#8e44ad"),
        ]:
            card = tk.Frame(
                stats_frame, bg=CARD_BG,
                padx=20, pady=15, relief="flat"
            )
            card.pack(side="left", padx=8, fill="x", expand=True)

            val_lbl = tk.Label(
                card, text="0",
                font=("Segoe UI", 22, "bold"),
                bg=CARD_BG, fg=colour,
            )
            val_lbl.pack()

            tk.Label(
                card, text=title,
                font=("Segoe UI", 8),
                bg=CARD_BG, fg="#888888",
            ).pack()

            self._stat_labels[title] = val_lbl

        ttk.Separator(self, orient="horizontal").pack(
            fill="x", padx=20, pady=5
        )

        # Bottom: two columns
        bottom = tk.Frame(self, bg=CONTENT_BG)
        bottom.pack(fill="both", expand=True, padx=20, pady=10)

        # Active courses
        left = tk.LabelFrame(
            bottom, text="  My Active Courses",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c", relief="flat",
        )
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._active_tree = ttk.Treeview(
            left,
            columns=("course", "status", "progress"),
            show="headings",
            height=10,
        )
        for col, header, width in [
            ("course",   "Course",   120),
            ("status",   "Status",    90),
            ("progress", "Progress",  80),
        ]:
            self._active_tree.heading(col, text=header)
            self._active_tree.column(col, width=width)
        self._active_tree.pack(fill="both", expand=True)

        # Available courses + completion progress
        right = tk.Frame(bottom, bg=CONTENT_BG)
        right.pack(side="left", fill="both", padx=(10, 0))

        # Completion rate
        rate_frame = tk.LabelFrame(
            right, text="  Overall Completion",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c", relief="flat",
        )
        rate_frame.pack(fill="x", pady=(0, 10))

        self._rate_var = tk.StringVar(value="0%")
        tk.Label(
            rate_frame,
            textvariable=self._rate_var,
            font=("Segoe UI", 20, "bold"),
            bg=CONTENT_BG,
            fg="#27ae60",
        ).pack()

        self._progress_bar = ttk.Progressbar(
            rate_frame,
            length=250,
            mode="determinate",
            maximum=100,
        )
        self._progress_bar.pack(pady=5)

        # Available next courses
        avail_frame = tk.LabelFrame(
            right, text="  Available to Enroll",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c", relief="flat",
        )
        avail_frame.pack(fill="both", expand=True)

        self._avail_listbox = tk.Listbox(
            avail_frame,
            font=("Segoe UI", 9),
            height=8,
            relief="flat",
        )
        self._avail_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        tk.Button(
            avail_frame,
            text="➕ Enroll in Selected",
            font=("Segoe UI", 9),
            bg="#27ae60",
            fg="#ffffff",
            relief="flat",
            cursor="hand2",
            pady=5,
            command=self._enroll_selected,
        ).pack(fill="x", padx=5, pady=(0, 5))

    # ── Data Loading ───────────────────────────────────────────────────────────

    def _load_data(self):
        """Load all learner dashboard data."""
        try:
            self._find_learner_id()
            if self._learner_id is None:
                return

            self._load_stats()
            self._load_active_courses()
            self._load_available_courses()

        except Exception as e:
            print(f"Learner dashboard error: {e}")

    def _find_learner_id(self):
        """Find the learner profile ID for the current user."""
        try:
            learner_repo = self._services.get("learner_repo")
            if learner_repo:
                learner = learner_repo.get_learner_by_user_id(
                    self._user.id
                )
                if learner:
                    self._learner_id = learner.id
        except Exception:
            pass

    def _load_stats(self):
        """Load and display summary statistics."""
        try:
            progress_svc = self._services.get("progress_service")
            if progress_svc is None or self._learner_id is None:
                return

            summary = progress_svc.get_overall_summary(self._learner_id)

            self._stat_labels["Enrolled"].config(
                text=str(summary.get("total_enrolled", 0))
            )
            self._stat_labels["Completed"].config(
                text=str(summary.get("completed", 0))
            )
            self._stat_labels["In Progress"].config(
                text=str(summary.get("in_progress", 0))
            )

            rate = summary.get("completion_rate", 0.0)
            self._rate_var.set(f"{rate}%")
            self._progress_bar["value"] = rate

        except Exception as e:
            print(f"Stats error: {e}")

    def _load_active_courses(self):
        """Load active enrollment list."""
        for item in self._active_tree.get_children():
            self._active_tree.delete(item)

        try:
            enrollment_svc = self._services.get("enrollment_service")
            progress_svc   = self._services.get("progress_service")
            if not enrollment_svc or self._learner_id is None:
                return

            active_codes = enrollment_svc.get_active_courses(
                self._learner_id
            )
            for code in active_codes:
                progress_pct = 0
                if progress_svc:
                    p = progress_svc.get_progress(self._learner_id, code)
                    if p:
                        progress_pct = int(p.percentage)

                self._active_tree.insert(
                    "", "end",
                    values=(code, "In Progress", f"{progress_pct}%")
                )

            self._stat_labels["In Progress"].config(
                text=str(len(active_codes))
            )

        except Exception as e:
            print(f"Active courses error: {e}")

    def _load_available_courses(self):
        """Load courses available to enroll in."""
        self._avail_listbox.delete(0, "end")

        try:
            path_svc = self._services.get("learning_path_service")
            if path_svc is None or self._learner_id is None:
                return

            available = path_svc.get_available_next_courses(
                self._learner_id
            )
            for code in available:
                self._avail_listbox.insert("end", f"  {code}")

            self._stat_labels["Available"].config(text=str(len(available)))

        except Exception as e:
            print(f"Available courses error: {e}")

    def _enroll_selected(self):
        """Enroll in the course selected from the available list."""
        selection = self._avail_listbox.curselection()
        if not selection:
            from gui.dialogs.confirm_dialog import show_info
            show_info(self, "Select Course",
                      "Please select a course to enroll in.")
            return

        course_code = self._avail_listbox.get(selection[0]).strip()

        try:
            enrollment_svc = self._services.get("enrollment_service")
            if enrollment_svc is None or self._learner_id is None:
                return

            result = enrollment_svc.enroll_learner(
                self._learner_id, course_code
            )
            if result.success:
                from gui.dialogs.confirm_dialog import show_info
                show_info(self, "Enrolled", result.message)
                self._load_data()
            else:
                from gui.dialogs.confirm_dialog import show_error
                show_error(self, "Enrollment Failed", result.message)
        except Exception as e:
            from gui.dialogs.confirm_dialog import show_error
            show_error(self, "Error", str(e))