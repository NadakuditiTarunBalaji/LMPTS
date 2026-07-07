"""
learner_monitor.py
------------------
Instructor view of learner progress across all courses.
"""

import tkinter as tk
from tkinter import ttk
from gui.dialogs.confirm_dialog import show_error


CONTENT_BG = "#f0f4f8"


class LearnerMonitorScreen(tk.Frame):
    """Monitor learner progress (read-only for instructors)."""

    def __init__(self, parent, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._services = services
        self._build()
        self._load_data()

    def _build(self):
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame, text="Monitor Learners",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(side="left")
        tk.Button(
            title_frame, text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat", cursor="hand2",
            command=self._load_data,
        ).pack(side="right")

        cols = ("name", "enrolled", "completed", "in_progress", "rate")
        self._tree = ttk.Treeview(
            self, columns=cols, show="headings"
        )
        for col, header, width in [
            ("name",        "Learner",      150),
            ("enrolled",    "Enrolled",      80),
            ("completed",   "Completed",     90),
            ("in_progress", "In Progress",   90),
            ("rate",        "Completion %",  100),
        ]:
            self._tree.heading(col, text=header)
            self._tree.column(col, width=width)

        scroll = ttk.Scrollbar(
            self, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both",
                        expand=True, padx=(20, 0))
        scroll.pack(side="left", fill="y")

    def _load_data(self):
        """Load all learner activity."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                return
            report = analytics.learner_activity_report()
            for d in report:
                self._tree.insert(
                    "", "end",
                    values=(
                        d["learner_name"],
                        d["total_enrolled"],
                        d["completed"],
                        d["in_progress"],
                        f"{d['completion_rate']}%",
                    )
                )
        except Exception as e:
            show_error(self, "Error", str(e))