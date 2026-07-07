"""
analytics.py
------------
Detailed analytics screens for the Analyst role.
"""

import tkinter as tk
from tkinter import ttk
from gui.dialogs.confirm_dialog import show_error


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


class AnalyticsScreen(tk.Frame):
    """Full analytics report screen."""

    def __init__(self, parent, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._services = services
        self._build()
        self._load_data()

    def _build(self):
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame, text="Analytics Reports",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(side="left")
        tk.Button(
            title_frame, text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat", cursor="hand2",
            command=self._load_data,
        ).pack(side="right")

        # Course completion rates
        tk.Label(
            self, text="Course Completion Rates",
            font=("Segoe UI", 11, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(anchor="w", padx=20, pady=(0, 5))

        cols = ("code", "name", "enrolled", "completed",
                "in_progress", "cancelled", "rate", "dropout")
        self._tree = ttk.Treeview(
            self, columns=cols, show="headings", height=15
        )
        for col, header, width in [
            ("code",        "Code",         80),
            ("name",        "Name",        160),
            ("enrolled",    "Enrolled",      70),
            ("completed",   "Completed",     80),
            ("in_progress", "Active",        60),
            ("cancelled",   "Cancelled",     70),
            ("rate",        "Completion%",   90),
            ("dropout",     "Dropout%",      80),
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

        self._tree.tag_configure("high_completion",  background="#e8f5e9")
        self._tree.tag_configure("low_completion",   background="#fce4ec")

    def _load_data(self):
        """Load completion rate data."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                return

            courses = analytics.most_enrolled_courses(limit=50)
            for course in courses:
                stats = analytics.course_completion_rate(
                    course["course_code"]
                )
                tag = (
                    "high_completion"
                    if stats["completion_rate"] >= 70
                    else "low_completion"
                    if stats["completion_rate"] < 30 and stats["total_enrolled"] > 0
                    else ""
                )
                self._tree.insert(
                    "", "end",
                    values=(
                        course["course_code"],
                        course["course_name"],
                        stats["total_enrolled"],
                        stats["completed"],
                        stats["in_progress"],
                        stats["cancelled"],
                        f"{stats['completion_rate']}%",
                        f"{stats['dropout_rate']}%",
                    ),
                    tags=(tag,),
                )
        except Exception as e:
            show_error(self, "Error", str(e))


class CompletionStatsScreen(tk.Frame):
    """Completion statistics by difficulty and prerequisite chain."""

    def __init__(self, parent, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._services = services
        self._build()
        self._load_data()

    def _build(self):
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame, text="Completion Statistics",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(side="left")

        # Prerequisite chain lengths
        tk.Label(
            self, text="Courses by Prerequisite Chain Length",
            font=("Segoe UI", 11, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(anchor="w", padx=20, pady=(0, 5))

        cols = ("code", "level", "chain", "prerequisites")
        self._chain_tree = ttk.Treeview(
            self, columns=cols, show="headings", height=15
        )
        for col, header, width in [
            ("code",          "Course",        100),
            ("level",         "Study Level",    90),
            ("chain",         "Chain Length",   90),
            ("prerequisites", "Prerequisites", 300),
        ]:
            self._chain_tree.heading(col, text=header)
            self._chain_tree.column(col, width=width)

        scroll = ttk.Scrollbar(
            self, orient="vertical",
            command=self._chain_tree.yview
        )
        self._chain_tree.configure(yscrollcommand=scroll.set)
        self._chain_tree.pack(side="left", fill="both",
                              expand=True, padx=(20, 0))
        scroll.pack(side="left", fill="y")

    def _load_data(self):
        """Load prerequisite chain statistics."""
        for item in self._chain_tree.get_children():
            self._chain_tree.delete(item)

        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                return

            chains = analytics.prerequisite_chain_length()
            for item in chains:
                self._chain_tree.insert(
                    "", "end",
                    values=(
                        item["course_code"],
                        item["study_level"],
                        item["chain_length"],
                        ", ".join(item["prerequisites"]) or "None",
                    )
                )
        except Exception as e:
            show_error(self, "Error", str(e))


class BottleneckScreen(tk.Frame):
    """Identifies bottleneck courses with high dropout rates."""

    def __init__(self, parent, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._services = services
        self._build()
        self._load_data()

    def _build(self):
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame, text="Bottleneck Analysis",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(side="left")

        # Threshold control
        ctrl_frame = tk.Frame(self, bg=CONTENT_BG)
        ctrl_frame.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(
            ctrl_frame, text="Dropout threshold:",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, fg="#666666",
        ).pack(side="left")
        self._threshold_var = tk.DoubleVar(value=30.0)
        ttk.Spinbox(
            ctrl_frame,
            from_=0, to=100,
            textvariable=self._threshold_var,
            width=6,
        ).pack(side="left", padx=5)
        tk.Button(
            ctrl_frame, text="Apply",
            font=("Segoe UI", 9),
            bg="#1a3a5c", fg="#ffffff",
            relief="flat", cursor="hand2",
            command=self._load_data,
        ).pack(side="left", padx=5)

        # Bottleneck table
        cols = ("code", "name", "enrolled", "completed", "dropout")
        self._tree = ttk.Treeview(
            self, columns=cols, show="headings", height=15
        )
        for col, header, width in [
            ("code",     "Course",       100),
            ("name",     "Name",         180),
            ("enrolled", "Enrolled",      80),
            ("completed","Completed",     80),
            ("dropout",  "Dropout %",     90),
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

        self._tree.tag_configure("critical", background="#fce4ec")

    def _load_data(self):
        """Load bottleneck courses."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        try:
            analytics  = self._services.get("analytics_service")
            threshold  = self._threshold_var.get()
            bottlenecks = analytics.bottleneck_courses(threshold)

            for b in bottlenecks:
                tag = "critical" if b["dropout_rate"] >= 50 else ""
                self._tree.insert(
                    "", "end",
                    values=(
                        b["course_code"],
                        b.get("course_name", b["course_code"]),
                        b["total_enrolled"],
                        b["completed"],
                        f"{b['dropout_rate']}%",
                    ),
                    tags=(tag,),
                )
        except Exception as e:
            show_error(self, "Error", str(e))