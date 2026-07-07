"""
learner_monitor.py
------------------
Complete instructor learner monitoring screen.

Features:
    - View all learners with enrollment stats
    - Select a learner to view their course progress
    - Mark course as complete with score entry
    - View per-course enrollment details
    - Generate course report
"""

import tkinter as tk
from tkinter import ttk, simpledialog
from typing import Optional

from core.user import User
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"
HEADER_COL = "#1a3a5c"


class LearnerMonitorScreen(tk.Frame):
    """
    Complete learner monitoring interface for instructors.
    """

    def __init__(self, parent, services: dict,
                 user: Optional[User] = None):
        super().__init__(parent, bg=CONTENT_BG)
        self._services            = services
        self._user                = user
        self._selected_learner_id: Optional[int] = None
        self._selected_course:     Optional[str] = None
        self._build()
        self._load_learners()

    def _build(self):
        # Title
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame, text="Monitor Learners",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL,
        ).pack(side="left")
        tk.Button(
            title_frame, text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat",
            cursor="hand2", command=self._load_learners,
        ).pack(side="right")

        # Three-pane layout
        panes = tk.Frame(self, bg=CONTENT_BG)
        panes.pack(fill="both", expand=True, padx=20, pady=(0, 5))

        # ── Pane 1: Learner list ────────────────────────────────────────────
        left = tk.LabelFrame(
            panes, text="  Learners",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL, relief="flat",
        )
        left.pack(side="left", fill="both",
                  expand=True, padx=(0, 8))

        learner_cols = ("name", "enrolled", "completed", "rate")
        self._learner_tree = ttk.Treeview(
            left, columns=learner_cols,
            show="headings", selectmode="browse",
        )
        for col, hdr, w in [
            ("name",      "Learner",     140),
            ("enrolled",  "Enrolled",     70),
            ("completed", "Completed",    80),
            ("rate",      "Rate %",       65),
        ]:
            self._learner_tree.heading(col, text=hdr)
            self._learner_tree.column(col, width=w)

        ls = ttk.Scrollbar(
            left, orient="vertical",
            command=self._learner_tree.yview
        )
        self._learner_tree.configure(yscrollcommand=ls.set)
        self._learner_tree.pack(
            side="left", fill="both", expand=True
        )
        ls.pack(side="right", fill="y")
        self._learner_tree.bind(
            "<<TreeviewSelect>>", self._on_learner_selected
        )

        # ── Pane 2: Course enrollments ──────────────────────────────────────
        mid = tk.LabelFrame(
            panes, text="  Course Enrollments",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL, relief="flat",
        )
        mid.pack(side="left", fill="both",
                 expand=True, padx=(0, 8))

        course_cols = ("course", "status", "score", "progress")
        self._course_tree = ttk.Treeview(
            mid, columns=course_cols,
            show="headings", selectmode="browse",
        )
        for col, hdr, w in [
            ("course",   "Course",   100),
            ("status",   "Status",    90),
            ("score",    "Score",      60),
            ("progress", "Progress%",  80),
        ]:
            self._course_tree.heading(col, text=hdr)
            self._course_tree.column(col, width=w)

        self._course_tree.tag_configure(
            "COMPLETED",   background="#e8f5e9"
        )
        self._course_tree.tag_configure(
            "IN_PROGRESS", background="#fff8e1"
        )
        self._course_tree.tag_configure(
            "CANCELLED",   background="#fce4ec"
        )

        cs = ttk.Scrollbar(
            mid, orient="vertical",
            command=self._course_tree.yview
        )
        self._course_tree.configure(yscrollcommand=cs.set)
        self._course_tree.pack(
            side="left", fill="both", expand=True
        )
        cs.pack(side="right", fill="y")
        self._course_tree.bind(
            "<<TreeviewSelect>>", self._on_course_selected
        )

        # ── Pane 3: Actions ─────────────────────────────────────────────────
        right = tk.Frame(
            panes, bg=CARD_BG, width=220,
            relief="flat", bd=1,
        )
        right.pack(side="left", fill="y")
        right.pack_propagate(False)

        tk.Label(
            right, text="Actions",
            font=("Segoe UI", 11, "bold"),
            bg=CARD_BG, fg=HEADER_COL, pady=12,
        ).pack(fill="x", padx=10)

        ttk.Separator(right, orient="horizontal").pack(
            fill="x", padx=10
        )

        # Selected info
        self._selected_info = tk.Label(
            right,
            text="Select a learner\nthen a course",
            font=("Segoe UI", 9),
            bg=CARD_BG, fg="#666666",
            justify="center", pady=10,
        )
        self._selected_info.pack(fill="x", padx=10)

        ttk.Separator(right, orient="horizontal").pack(
            fill="x", padx=10
        )

        # Action buttons
        actions = [
            ("✅ Mark Complete + Score", "#27ae60",
             self._mark_complete),
            ("▶ Mark In Progress",      "#3498db",
             self._mark_in_progress),
            ("📊 Course Report",         "#8e44ad",
             self._generate_report),
        ]

        for text, colour, cmd in actions:
            tk.Button(
                right, text=text,
                font=("Segoe UI", 9),
                bg=colour, fg="#ffffff",
                activebackground=colour,
                relief="flat", cursor="hand2",
                pady=7, anchor="w", padx=10,
                command=cmd,
            ).pack(fill="x", padx=10, pady=3)

        # Per-course stats
        ttk.Separator(right, orient="horizontal").pack(
            fill="x", padx=10, pady=5
        )
        tk.Label(
            right, text="Course Stats",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg="#666666",
        ).pack(anchor="w", padx=10)

        self._course_stats = tk.Text(
            right,
            font=("Courier New", 8),
            bg=CARD_BG, fg="#333333",
            height=8, relief="flat",
            state="disabled",
        )
        self._course_stats.pack(
            fill="x", padx=10, pady=5
        )

    # ── Data Loading ───────────────────────────────────────────────────────────

    def _load_learners(self):
        """Load all learners into the learner pane."""
        for item in self._learner_tree.get_children():
            self._learner_tree.delete(item)

        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                return

            report = analytics.learner_activity_report()
            for d in report:
                self._learner_tree.insert(
                    "", "end",
                    iid=str(d["learner_id"]),
                    values=(
                        d["learner_name"],
                        d["total_enrolled"],
                        d["completed"],
                        f"{d['completion_rate']}%",
                    )
                )
        except Exception as e:
            show_error(self, "Error", str(e))

    def _on_learner_selected(self, event=None):
        """Load courses for selected learner."""
        sel = self._learner_tree.selection()
        if not sel:
            return

        self._selected_learner_id = int(sel[0])
        self._selected_course     = None
        self._selected_info.config(
            text=f"Learner: {sel[0]}\nSelect a course"
        )
        self._load_learner_courses()

    def _load_learner_courses(self):
        """Load enrollments for the selected learner."""
        for item in self._course_tree.get_children():
            self._course_tree.delete(item)

        if self._selected_learner_id is None:
            return

        try:
            enrollment_svc = self._services.get("enrollment_service")
            progress_svc   = self._services.get("progress_service")
            if not enrollment_svc:
                return

            enrollments = enrollment_svc.get_learner_enrollments(
                self._selected_learner_id
            )

            for e in enrollments:
                pct = 0
                if progress_svc:
                    p = progress_svc.get_progress(
                        self._selected_learner_id, e.course_code
                    )
                    if p:
                        pct = int(p.percentage)

                score_str = (
                    f"{e.score:.0f}" if e.score is not None else "—"
                )
                self._course_tree.insert(
                    "", "end",
                    iid=e.course_code,
                    values=(
                        e.course_code,
                        e.status.value,
                        score_str,
                        f"{pct}%",
                    ),
                    tags=(e.status.value,),
                )

        except Exception as e:
            show_error(self, "Error", str(e))

    def _on_course_selected(self, event=None):
        """Update action panel when course selected."""
        sel = self._course_tree.selection()
        if not sel:
            return

        self._selected_course = sel[0]
        self._selected_info.config(
            text=(
                f"Learner ID: {self._selected_learner_id}\n"
                f"Course: {self._selected_course}"
            )
        )
        self._load_course_stats()

    def _load_course_stats(self):
        """Load stats for the selected course."""
        if not self._selected_course:
            return

        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                return

            stats = analytics.course_completion_rate(
                self._selected_course
            )

            text = (
                f"Enrolled : {stats['total_enrolled']}\n"
                f"Completed: {stats['completed']}\n"
                f"Active   : {stats['in_progress']}\n"
                f"Cancelled: {stats['cancelled']}\n"
                f"Rate     : {stats['completion_rate']}%\n"
                f"Dropout  : {stats['dropout_rate']}%"
            )

            self._course_stats.config(state="normal")
            self._course_stats.delete("1.0", "end")
            self._course_stats.insert("1.0", text)
            self._course_stats.config(state="disabled")

        except Exception as e:
            print(f"Course stats error: {e}")

    # ── Actions ────────────────────────────────────────────────────────────────

    def _mark_complete(self):
        """Mark selected learner's course as complete with a score."""
        if not self._selected_learner_id:
            show_info(self, "Select", "Please select a learner.")
            return
        if not self._selected_course:
            show_info(self, "Select", "Please select a course.")
            return

        score_str = simpledialog.askstring(
            "Mark Complete",
            f"Enter score for learner {self._selected_learner_id} "
            f"in '{self._selected_course}' (0-100):",
            parent=self,
        )
        if score_str is None:
            return

        try:
            score = float(score_str)
            if not 0 <= score <= 100:
                show_error(self, "Invalid Score",
                           "Score must be between 0 and 100.")
                return

            enrollment_svc = self._services["enrollment_service"]
            enrollment_svc.complete_enrollment(
                self._selected_learner_id,
                self._selected_course,
                score,
            )
            show_info(
                self, "Completed",
                f"Marked '{self._selected_course}' as complete "
                f"with score {score} for learner "
                f"{self._selected_learner_id}."
            )
            self._load_learner_courses()
            self._load_learners()

        except Exception as e:
            show_error(self, "Error", str(e))

    def _mark_in_progress(self):
        """Mark enrollment as IN_PROGRESS."""
        if not self._selected_learner_id or not self._selected_course:
            show_info(self, "Select",
                      "Please select a learner and course.")
            return

        try:
            enrollment_svc = self._services["enrollment_service"]
            enrollment_svc.start_enrollment(
                self._selected_learner_id, self._selected_course
            )
            show_info(self, "Updated",
                      f"'{self._selected_course}' marked as In Progress.")
            self._load_learner_courses()

        except Exception as e:
            show_error(self, "Error", str(e))

    def _generate_report(self):
        """Generate a text report for the selected course."""
        if not self._selected_course:
            show_info(self, "Select", "Please select a course.")
            return

        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                return

            stats = analytics.course_completion_rate(
                self._selected_course
            )
            avg_scores = analytics.average_score_by_course()
            avg = next(
                (s["average_score"] for s in avg_scores
                 if s["course_code"] == self._selected_course),
                None
            )

            lines = [
                f"Course Report: {self._selected_course}",
                "=" * 40,
                f"Total Enrolled  : {stats['total_enrolled']}",
                f"Completed       : {stats['completed']}",
                f"In Progress     : {stats['in_progress']}",
                f"Cancelled       : {stats['cancelled']}",
                f"Completion Rate : {stats['completion_rate']}%",
                f"Dropout Rate    : {stats['dropout_rate']}%",
                f"Average Score   : "
                f"{f'{avg:.1f}' if avg else 'N/A'}",
            ]
            show_info(
                self,
                f"Report: {self._selected_course}",
                "\n".join(lines)
            )

        except Exception as e:
            show_error(self, "Error", str(e))