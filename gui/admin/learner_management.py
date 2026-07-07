"""
learner_management.py
---------------------
View and manage learner profiles, enrollments, and transfer credits.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from core.learner import Learner
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


class LearnerManagementScreen(tk.Frame):
    """
    Learner management interface.

    Features:
        - View all learners in a table
        - View learner's enrollments
        - Grant transfer credit
        - Approve exemption
    """

    def __init__(self, parent, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._services        = services
        self._selected_learner: Optional[dict] = None
        self._build()
        self._load_learners()

    def _build(self):
        """Build the learner management UI."""
        # Title
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)

        tk.Label(
            title_frame,
            text="Learner Management",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG,
            fg="#1a3a5c",
        ).pack(side="left")

        tk.Button(
            title_frame,
            text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG,
            relief="flat",
            cursor="hand2",
            command=self._load_learners,
        ).pack(side="right")

        # Main split
        content = tk.Frame(self, bg=CONTENT_BG)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # ── Left: Learner list ──────────────────────────────────────────────
        left = tk.Frame(content, bg=CONTENT_BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(
            left,
            text="All Learners",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG,
            fg="#1a3a5c",
        ).pack(anchor="w", pady=(0, 5))

        # Learner treeview
        cols = ("id", "name", "email", "completed", "current")
        self._learner_tree = ttk.Treeview(
            left,
            columns=cols,
            show="headings",
            selectmode="browse",
        )
        for col, header, width in [
            ("id",        "ID",        40),
            ("name",      "Name",     140),
            ("email",     "Email",    180),
            ("completed", "Done",      50),
            ("current",   "Active",    50),
        ]:
            self._learner_tree.heading(col, text=header)
            self._learner_tree.column(col, width=width)

        scroll = ttk.Scrollbar(
            left, orient="vertical",
            command=self._learner_tree.yview
        )
        self._learner_tree.configure(yscrollcommand=scroll.set)
        self._learner_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._learner_tree.bind(
            "<<TreeviewSelect>>", self._on_learner_selected
        )

        # ── Right: Details panel ────────────────────────────────────────────
        right = tk.Frame(content, bg=CARD_BG, width=320, relief="flat", bd=1)
        right.pack(side="left", fill="y")
        right.pack_propagate(False)

        tk.Label(
            right,
            text="Learner Details",
            font=("Segoe UI", 11, "bold"),
            bg=CARD_BG,
            fg="#1a3a5c",
            pady=12,
        ).pack(fill="x", padx=15)

        ttk.Separator(right, orient="horizontal").pack(fill="x", padx=15)

        # Info labels
        self._info_frame = tk.Frame(right, bg=CARD_BG, padx=15, pady=10)
        self._info_frame.pack(fill="x")

        self._info_vars = {}
        for label in ("Name", "Email", "Completed", "In Progress"):
            row = tk.Frame(self._info_frame, bg=CARD_BG)
            row.pack(fill="x", pady=3)
            tk.Label(
                row, text=f"{label}:",
                font=("Segoe UI", 9, "bold"),
                bg=CARD_BG, fg="#666666",
                width=12, anchor="w",
            ).pack(side="left")
            var = tk.StringVar(value="—")
            tk.Label(
                row, textvariable=var,
                font=("Segoe UI", 9),
                bg=CARD_BG, fg="#333333",
                anchor="w",
            ).pack(side="left")
            self._info_vars[label] = var

        ttk.Separator(right, orient="horizontal").pack(fill="x", padx=15, pady=5)

        # Actions
        tk.Label(
            right,
            text="Actions",
            font=("Segoe UI", 10, "bold"),
            bg=CARD_BG,
            fg="#1a3a5c",
        ).pack(anchor="w", padx=15)

        actions = [
            ("📜 View Enrollments",  "#1a3a5c", self._view_enrollments),
            ("📥 Grant Transfer Credit", "#8e44ad", self._grant_transfer),
            ("✅ Approve Exemption", "#27ae60", self._approve_exemption),
        ]

        for text, colour, cmd in actions:
            tk.Button(
                right,
                text=text,
                font=("Segoe UI", 9),
                bg=colour,
                fg="#ffffff",
                relief="flat",
                cursor="hand2",
                pady=6,
                command=cmd,
            ).pack(fill="x", padx=15, pady=3)

        # Enrollments sub-list
        tk.Label(
            right,
            text="Enrollments",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG,
            fg="#666666",
            pady=5,
        ).pack(anchor="w", padx=15)

        self._enroll_listbox = tk.Listbox(
            right,
            font=("Courier New", 8),
            height=8,
            relief="flat",
            bd=1,
        )
        self._enroll_listbox.pack(fill="x", padx=15)

    # ── Data ───────────────────────────────────────────────────────────────────

    def _load_learners(self):
        """Load all learners into the table."""
        for item in self._learner_tree.get_children():
            self._learner_tree.delete(item)

        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                return

            report = analytics.learner_activity_report()

            for learner_data in report:
                self._learner_tree.insert(
                    "", "end",
                    iid=str(learner_data["learner_id"]),
                    values=(
                        learner_data["learner_id"],
                        learner_data["learner_name"],
                        "—",
                        learner_data["completed"],
                        learner_data["in_progress"],
                    )
                )
        except Exception as e:
            show_error(self, "Error", f"Failed to load learners: {e}")

    def _on_learner_selected(self, event=None):
        """Load details for the selected learner."""
        selection = self._learner_tree.selection()
        if not selection:
            return

        learner_id = int(selection[0])
        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                return

            summary = analytics.learner_progress_summary(learner_id)
            self._selected_learner = summary

            self._info_vars["Name"].set(summary.get("learner_name", "—"))
            self._info_vars["Email"].set("—")
            self._info_vars["Completed"].set(
                str(summary.get("completed", 0))
            )
            self._info_vars["In Progress"].set(
                str(summary.get("in_progress", 0))
            )

            # Update enrollment list
            self._enroll_listbox.delete(0, "end")
            for c in summary.get("courses", []):
                self._enroll_listbox.insert(
                    "end",
                    f"{c['course_code']:8s}  {c['status']}"
                )

        except Exception as e:
            show_error(self, "Error", str(e))

    # ── Actions ────────────────────────────────────────────────────────────────

    def _view_enrollments(self):
        """Show full enrollment list for selected learner."""
        if not self._selected_learner:
            show_info(self, "Select Learner", "Please select a learner.")
            return
        show_info(
            self, "Enrollments",
            f"Learner: {self._selected_learner.get('learner_name')}\n"
            f"Courses: {len(self._selected_learner.get('courses', []))}\n"
            f"See enrollment list on the right panel."
        )

    def _grant_transfer(self):
        """Grant transfer credit to the selected learner."""
        if not self._selected_learner:
            show_info(self, "Select Learner", "Please select a learner.")
            return

        learner_id  = self._selected_learner["learner_id"]
        course_code = self._prompt_course_code("Transfer Credit")
        if not course_code:
            return

        try:
            enrollment_svc = self._services["enrollment_service"]
            result = enrollment_svc.transfer_credit(learner_id, course_code)
            if result.success:
                show_info(self, "Success", result.message)
                self._load_learners()
            else:
                show_error(self, "Failed", result.message)
        except Exception as e:
            show_error(self, "Error", str(e))

    def _approve_exemption(self):
        """Approve an exemption for the selected learner."""
        if not self._selected_learner:
            show_info(self, "Select Learner", "Please select a learner.")
            return

        learner_id  = self._selected_learner["learner_id"]
        course_code = self._prompt_course_code("Approve Exemption")
        if not course_code:
            return

        try:
            enrollment_svc = self._services["enrollment_service"]
            result = enrollment_svc.approve_exemption(learner_id, course_code)
            if result.success:
                show_info(self, "Success", result.message)
                self._load_learners()
            else:
                show_error(self, "Failed", result.message)
        except Exception as e:
            show_error(self, "Error", str(e))

    def _prompt_course_code(self, action: str) -> Optional[str]:
        """Prompt for a course code via simple dialog."""
        from tkinter import simpledialog
        code = simpledialog.askstring(
            action,
            "Enter course code:",
            parent=self,
        )
        return code.strip().upper() if code else None