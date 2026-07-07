"""
analytics_dashboard.py
-----------------------
Analytics dashboard for Admin and Analyst roles.
"""

import tkinter as tk
from tkinter import ttk
from gui.dialogs.confirm_dialog import show_error


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


class AnalyticsDashboard(tk.Frame):
    """
    Analytics overview dashboard.

    Displays:
        - System overview stats
        - Most enrolled courses table
        - Bottleneck courses
        - Difficulty distribution
        - matplotlib bar chart (if available)
    """

    def __init__(self, parent, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._services = services
        self._build()
        self._load_data()

    def _build(self):
        """Build the analytics dashboard."""
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame, text="Analytics Dashboard",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(side="left")
        tk.Button(
            title_frame, text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat", cursor="hand2",
            command=self._load_data,
        ).pack(side="right")

        # Notebook with tabs
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(
            fill="both", expand=True, padx=20, pady=(0, 10)
        )

        # Tab 1: Overview
        self._overview_tab = tk.Frame(self._notebook, bg=CONTENT_BG)
        self._notebook.add(self._overview_tab, text="  Overview  ")
        self._build_overview_tab()

        # Tab 2: Course Stats
        self._course_tab = tk.Frame(self._notebook, bg=CONTENT_BG)
        self._notebook.add(self._course_tab, text="  Courses  ")
        self._build_course_tab()

        # Tab 3: Learner Activity
        self._learner_tab = tk.Frame(self._notebook, bg=CONTENT_BG)
        self._notebook.add(self._learner_tab, text="  Learners  ")
        self._build_learner_tab()

        # Tab 4: Chart
        self._chart_tab = tk.Frame(self._notebook, bg=CONTENT_BG)
        self._notebook.add(self._chart_tab, text="  Charts  ")
        self._build_chart_tab()

    def _build_overview_tab(self):
        """Build the system overview tab."""
        frame = tk.Frame(self._overview_tab, bg=CONTENT_BG, padx=20, pady=10)
        frame.pack(fill="both", expand=True)

        # Stat cards
        cards_frame = tk.Frame(frame, bg=CONTENT_BG)
        cards_frame.pack(fill="x", pady=(0, 15))

        self._overview_labels = {}
        stats = [
            ("Total Courses",      "0", "#1a3a5c"),
            ("Total Learners",     "0", "#27ae60"),
            ("Total Enrollments",  "0", "#e67e22"),
            ("Completions",        "0", "#8e44ad"),
            ("Completion Rate",    "0%", "#3498db"),
        ]
        for title, value, colour in stats:
            card = tk.Frame(
                cards_frame, bg=CARD_BG, padx=15, pady=12
            )
            card.pack(side="left", padx=5, fill="x", expand=True)

            val_lbl = tk.Label(
                card, text=value,
                font=("Segoe UI", 20, "bold"),
                bg=CARD_BG, fg=colour,
            )
            val_lbl.pack()
            tk.Label(
                card, text=title,
                font=("Segoe UI", 8),
                bg=CARD_BG, fg="#888888",
            ).pack()
            self._overview_labels[title] = val_lbl

        # Difficulty distribution
        diff_frame = tk.LabelFrame(
            frame, text="  Difficulty Distribution",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c", relief="flat",
        )
        diff_frame.pack(fill="x", pady=10)

        self._diff_bars = {}
        for level, colour in [
            ("BEGINNER",     "#27ae60"),
            ("INTERMEDIATE", "#e67e22"),
            ("ADVANCED",     "#c0392b"),
        ]:
            row = tk.Frame(diff_frame, bg=CONTENT_BG, pady=5)
            row.pack(fill="x", padx=15)

            tk.Label(
                row, text=level,
                font=("Segoe UI", 9),
                bg=CONTENT_BG, fg=colour,
                width=14, anchor="w",
            ).pack(side="left")

            bar = ttk.Progressbar(
                row, length=300, maximum=100, mode="determinate"
            )
            bar.pack(side="left", padx=5)

            count_lbl = tk.Label(
                row, text="0",
                font=("Segoe UI", 9),
                bg=CONTENT_BG, fg="#333333",
            )
            count_lbl.pack(side="left")

            self._diff_bars[level] = (bar, count_lbl)

    def _build_course_tab(self):
        """Build course statistics tab."""
        frame = tk.Frame(self._course_tab, bg=CONTENT_BG, padx=10, pady=10)
        frame.pack(fill="both", expand=True)

        # Most enrolled
        tk.Label(
            frame, text="Most Enrolled Courses",
            font=("Segoe UI", 11, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(anchor="w", pady=(0, 5))

        cols = ("rank", "code", "name", "difficulty", "enrollments", "rate")
        self._course_tree = ttk.Treeview(
            frame, columns=cols, show="headings", height=12
        )
        for col, header, width in [
            ("rank",        "#",           40),
            ("code",        "Code",        80),
            ("name",        "Name",        180),
            ("difficulty",  "Difficulty",  100),
            ("enrollments", "Enrollments",  90),
            ("rate",        "Completion%",  90),
        ]:
            self._course_tree.heading(col, text=header)
            self._course_tree.column(col, width=width)

        scroll = ttk.Scrollbar(
            frame, orient="vertical",
            command=self._course_tree.yview
        )
        self._course_tree.configure(yscrollcommand=scroll.set)
        self._course_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_learner_tab(self):
        """Build learner activity tab."""
        frame = tk.Frame(
            self._learner_tab, bg=CONTENT_BG, padx=10, pady=10
        )
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame, text="Learner Activity Report",
            font=("Segoe UI", 11, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(anchor="w", pady=(0, 5))

        cols = ("name", "enrolled", "completed", "in_progress", "rate", "avg_score")
        self._learner_tree = ttk.Treeview(
            frame, columns=cols, show="headings", height=15
        )
        for col, header, width in [
            ("name",        "Learner",      130),
            ("enrolled",    "Enrolled",      70),
            ("completed",   "Completed",     80),
            ("in_progress", "In Progress",   85),
            ("rate",        "Rate %",        65),
            ("avg_score",   "Avg Score",     80),
        ]:
            self._learner_tree.heading(col, text=header)
            self._learner_tree.column(col, width=width)

        scroll = ttk.Scrollbar(
            frame, orient="vertical",
            command=self._learner_tree.yview
        )
        self._learner_tree.configure(yscrollcommand=scroll.set)
        self._learner_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_chart_tab(self):
        """Build matplotlib chart tab."""
        self._chart_frame = tk.Frame(self._chart_tab, bg=CONTENT_BG)
        self._chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(
            self._chart_frame,
            text="Enrollment Statistics Chart",
            font=("Segoe UI", 11, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(anchor="w")

        self._chart_placeholder = tk.Label(
            self._chart_frame,
            text="Chart will load with data...",
            font=("Segoe UI", 10),
            bg=CONTENT_BG,
            fg="#888888",
        )
        self._chart_placeholder.pack(pady=20)

    # ── Data Loading ───────────────────────────────────────────────────────────

    def _load_data(self):
        """Load all analytics data."""
        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                return

            # Overview
            overview = analytics.system_overview()
            self._overview_labels["Total Courses"].config(
                text=str(overview.get("total_courses", 0))
            )
            self._overview_labels["Total Learners"].config(
                text=str(overview.get("total_learners", 0))
            )
            self._overview_labels["Total Enrollments"].config(
                text=str(overview.get("total_enrollments", 0))
            )
            self._overview_labels["Completions"].config(
                text=str(overview.get("total_completions", 0))
            )
            self._overview_labels["Completion Rate"].config(
                text=f"{overview.get('overall_completion_rate', 0)}%"
            )

            # Difficulty distribution bars
            diff = overview.get("difficulty_distribution", {})
            total = max(diff.get("total", 1), 1)
            for level, (bar, lbl) in self._diff_bars.items():
                count = diff.get(level, 0)
                bar["value"] = count / total * 100
                lbl.config(text=str(count))

            # Course stats
            self._load_course_stats(analytics)

            # Learner activity
            self._load_learner_activity(analytics)

            # Chart
            self._load_chart(analytics)

        except Exception as e:
            show_error(self, "Error", f"Failed to load analytics: {e}")

    def _load_course_stats(self, analytics):
        """Load course statistics table."""
        for item in self._course_tree.get_children():
            self._course_tree.delete(item)

        try:
            most_enrolled = analytics.most_enrolled_courses()
            avg_scores    = analytics.average_score_by_course()
            score_map     = {
                r["course_code"]: r["average_score"]
                for r in avg_scores
            }

            for rank, course in enumerate(most_enrolled, 1):
                code  = course["course_code"]
                stats = analytics.course_completion_rate(code)
                self._course_tree.insert(
                    "", "end",
                    values=(
                        rank,
                        code,
                        course["course_name"],
                        course["difficulty"],
                        course["enrollments"],
                        f"{stats['completion_rate']}%",
                    )
                )
        except Exception as e:
            print(f"Course stats error: {e}")

    def _load_learner_activity(self, analytics):
        """Load learner activity table."""
        for item in self._learner_tree.get_children():
            self._learner_tree.delete(item)

        try:
            report = analytics.learner_activity_report()
            for learner_data in report:
                avg = learner_data.get("average_score")
                avg_str = f"{avg:.1f}" if avg is not None else "—"
                self._learner_tree.insert(
                    "", "end",
                    values=(
                        learner_data["learner_name"],
                        learner_data["total_enrolled"],
                        learner_data["completed"],
                        learner_data["in_progress"],
                        f"{learner_data['completion_rate']}%",
                        avg_str,
                    )
                )
        except Exception as e:
            print(f"Learner activity error: {e}")

    def _load_chart(self, analytics):
        """Load matplotlib bar chart."""
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            # Clear placeholder
            self._chart_placeholder.destroy()

            most_enrolled = analytics.most_enrolled_courses(limit=8)
            if not most_enrolled:
                return

            codes   = [r["course_code"]    for r in most_enrolled]
            counts  = [r["enrollments"]     for r in most_enrolled]
            colours = ["#1a3a5c"] * len(codes)

            fig, ax = plt.subplots(figsize=(7, 4))
            fig.patch.set_facecolor("#f0f4f8")
            ax.set_facecolor("#f0f4f8")

            bars = ax.bar(codes, counts, color=colours, width=0.6)
            ax.set_title(
                "Most Enrolled Courses",
                fontsize=12,
                fontweight="bold",
                color="#1a3a5c",
                pad=10,
            )
            ax.set_xlabel("Course", color="#666666")
            ax.set_ylabel("Enrollments", color="#666666")
            ax.tick_params(colors="#555555")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            # Value labels on bars
            for bar, count in zip(bars, counts):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    str(count),
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    color="#333333",
                )

            plt.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        except ImportError:
            tk.Label(
                self._chart_frame,
                text=(
                    "matplotlib not installed.\n"
                    "Run: pip install matplotlib"
                ),
                font=("Segoe UI", 10),
                bg=CONTENT_BG,
                fg="#888888",
            ).pack(pady=20)
        except Exception as e:
            print(f"Chart error: {e}")