"""
analytics_dashboard.py
-----------------------
Tkinter analytics dashboard — mirrors Flask analyst/dashboard exactly.
Calls the same service methods with the same arguments.
"""

import tkinter as tk
from tkinter import ttk
from collections import defaultdict

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MPL = True
except ImportError:
    MPL = False

from gui.dialogs.confirm_dialog import show_error
from core.enums import UserRole

CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


class AnalyticsDashboard(tk.Frame):
    """
    Analytics dashboard — identical data as Flask analyst/dashboard.

    Methods called (same as analyst.py):
        analytics.system_overview()
        analytics.student_performance_report()
        analytics.score_bucket_distribution()
        analytics.performance_trend(months=6)
        analytics.course_completion_breakdown()
        analytics.course_completion_by_course()
        analytics.enrollment_summary_metrics()
        analytics.enrollment_monthly_trend(months=6)
        analytics.instructor_analytics(instructors, instructor_courses)
    """

    def __init__(self, parent, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._services = services
        self._style_widgets()
        self._build_ui()
        self._load_data()

    # ──────────────────────────────────────────────────────────────────────
    # Style
    # ──────────────────────────────────────────────────────────────────────
    def _style_widgets(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("TNotebook",           background=CONTENT_BG)
        s.configure("TNotebook.Tab",       font=("Segoe UI", 9))
        s.configure("Treeview",            font=("Segoe UI", 9),
                                           rowheight=24)
        s.configure("Treeview.Heading",    font=("Segoe UI", 9, "bold"))
        s.configure("Horizontal.TProgressbar", thickness=12)

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def _get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _clear(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    def _stat_card(self, parent, title, value, colour):
        """Create one stat card and return its value label."""
        card = tk.Frame(parent, bg=CARD_BG, padx=15, pady=12,
                        relief="solid", bd=1)
        card.pack(side="left", padx=5, fill="x", expand=True)
        val = tk.Label(card, text=value,
                       font=("Segoe UI", 20, "bold"),
                       bg=CARD_BG, fg=colour)
        val.pack()
        tk.Label(card, text=title,
                 font=("Segoe UI", 8),
                 bg=CARD_BG, fg="#888888").pack()
        return val

    def _chart_slot(self, parent, title, height=280):
        """
        Create a titled panel that holds a matplotlib canvas.
        Returns the inner container frame.
        """
        outer = tk.Frame(parent, bg=CARD_BG, relief="solid", bd=1)
        outer.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        tk.Label(outer, text=title,
                 font=("Segoe UI", 10, "bold"),
                 bg=CARD_BG, fg="#1a3a5c",
                 anchor="w").pack(fill="x", padx=10, pady=(8, 4))
        inner = tk.Frame(outer, bg=CARD_BG, height=height)
        inner.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        inner.pack_propagate(False)
        return inner

    def _embed_fig(self, container, fig):
        """Embed a matplotlib figure into a Tkinter frame."""
        self._clear(container)
        if not MPL:
            tk.Label(container,
                     text="pip install matplotlib",
                     bg=CARD_BG, fg="#888").pack(expand=True)
            return
        canvas = FigureCanvasTkAgg(fig, master=container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    def _no_data(self, container, msg="No Data Available"):
        self._clear(container)
        tk.Label(container, text=msg,
                 font=("Segoe UI", 9, "italic"),
                 bg=CARD_BG, fg="#aaaaaa").pack(expand=True)

    def _fig(self, w=6, h=3.2):
        """Return a pre-styled figure + axes."""
        fig, ax = plt.subplots(figsize=(w, h))
        fig.patch.set_facecolor(CONTENT_BG)
        ax.set_facecolor(CONTENT_BG)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(colors="#555555")
        return fig, ax

    def _make_tree(self, parent, columns, height=10):
        """
        Build a Treeview with scrollbar.
        columns = list of (col_id, header, width)
        Returns the Treeview widget.
        """
        frame = tk.Frame(parent, bg=CONTENT_BG)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame,
                            columns=[c[0] for c in columns],
                            show="headings",
                            height=height)
        for col_id, header, width in columns:
            tree.heading(col_id, text=header)
            tree.column(col_id, width=width, anchor="w")

        sb = ttk.Scrollbar(frame, orient="vertical",
                           command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return tree

    # ──────────────────────────────────────────────────────────────────────
    # Build UI skeleton
    # ──────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=CONTENT_BG, pady=15)
        hdr.pack(fill="x", padx=20)
        tk.Label(hdr, text="Analytics Dashboard",
                 font=("Segoe UI", 16, "bold"),
                 bg=CONTENT_BG, fg="#1a3a5c").pack(side="left")
        tk.Button(hdr, text="🔄 Refresh",
                  font=("Segoe UI", 9),
                  bg=CONTENT_BG, relief="flat", cursor="hand2",
                  command=self._load_data).pack(side="right")

        # ── Notebook ──────────────────────────────────────────────────────
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        tabs = [
            ("  Overview  ",            "_tab_overview"),
            ("  Student Performance  ", "_tab_performance"),
            ("  Course Completion  ",   "_tab_completion"),
            ("  Enrollment  ",          "_tab_enrollment"),
            ("  Instructor  ",          "_tab_instructor"),
        ]
        for label, attr in tabs:
            frame = tk.Frame(nb, bg=CONTENT_BG)
            setattr(self, attr, frame)
            nb.add(frame, text=label)

        self._build_overview()
        self._build_performance()
        self._build_completion()
        self._build_enrollment()
        self._build_instructor()

    # ── Tab 1: Overview ───────────────────────────────────────────────────
    def _build_overview(self):
        p = tk.Frame(self._tab_overview, bg=CONTENT_BG, padx=20, pady=10)
        p.pack(fill="both", expand=True)

        # Stat cards row
        cards = tk.Frame(p, bg=CONTENT_BG)
        cards.pack(fill="x", pady=(0, 15))
        self._ov = {}  # overview value labels
        for title, colour in [
            ("Total Courses",     "#1a3a5c"),
            ("Total Learners",    "#27ae60"),
            ("Total Enrollments", "#e67e22"),
            ("Completions",       "#8e44ad"),
            ("Completion Rate",   "#3498db"),
        ]:
            self._ov[title] = self._stat_card(cards, title, "0", colour)

        # Difficulty distribution
        diff = tk.LabelFrame(p, text="  Difficulty Distribution",
                             font=("Segoe UI", 10, "bold"),
                             bg=CONTENT_BG, fg="#1a3a5c", relief="flat")
        diff.pack(fill="x", pady=10)
        self._diff_bars = {}
        for level, colour in [
            ("BEGINNER",     "#27ae60"),
            ("INTERMEDIATE", "#e67e22"),
            ("ADVANCED",     "#c0392b"),
        ]:
            row = tk.Frame(diff, bg=CONTENT_BG, pady=5)
            row.pack(fill="x", padx=15)
            tk.Label(row, text=level, font=("Segoe UI", 9),
                     bg=CONTENT_BG, fg=colour,
                     width=14, anchor="w").pack(side="left")
            bar = ttk.Progressbar(row, length=300,
                                  maximum=100, mode="determinate")
            bar.pack(side="left", padx=5)
            lbl = tk.Label(row, text="0", font=("Segoe UI", 9),
                           bg=CONTENT_BG, fg="#333333")
            lbl.pack(side="left")
            self._diff_bars[level] = (bar, lbl)

    # ── Tab 2: Student Performance ────────────────────────────────────────
    def _build_performance(self):
        p = tk.Frame(self._tab_performance, bg=CONTENT_BG,
                     padx=10, pady=10)
        p.pack(fill="both", expand=True)

        tk.Label(p, text="Student Performance",
                 font=("Segoe UI", 11, "bold"),
                 bg=CONTENT_BG, fg="#1a3a5c").pack(anchor="w", pady=(0, 5))

        # Table — same columns as Flask template
        self._perf_tree = self._make_tree(p, [
            ("student_name", "Student Name",  180),
            ("course",       "Course",        200),
            ("score",        "Marks",          80),
            ("grade",        "Grade",          70),
            ("status",       "Status",        110),
        ], height=9)

        # Three chart slots side by side
        chart_row = tk.Frame(p, bg=CONTENT_BG)
        chart_row.pack(fill="both", expand=True, pady=(12, 0))
        self._c_marks   = self._chart_slot(chart_row, "Marks by Student")
        self._c_buckets = self._chart_slot(chart_row, "Performance Distribution")
        self._c_trend   = self._chart_slot(chart_row, "Performance Over Time")

    # ── Tab 3: Course Completion ──────────────────────────────────────────
    def _build_completion(self):
        p = tk.Frame(self._tab_completion, bg=CONTENT_BG,
                     padx=10, pady=10)
        p.pack(fill="both", expand=True)

        tk.Label(p, text="Course Completion Analytics",
                 font=("Segoe UI", 11, "bold"),
                 bg=CONTENT_BG, fg="#1a3a5c").pack(anchor="w", pady=(0, 5))

        # Stat cards
        cards = tk.Frame(p, bg=CONTENT_BG)
        cards.pack(fill="x", pady=(0, 12))
        self._cmp = {}
        for title, colour in [
            ("Completed",    "#0ca30c"),
            ("In Progress",  "#2a78d6"),
            ("Not Started",  "#898781"),
            ("Completion %", "#3498db"),
        ]:
            self._cmp[title] = self._stat_card(cards, title, "0", colour)

        # Two chart slots
        chart_row = tk.Frame(p, bg=CONTENT_BG)
        chart_row.pack(fill="both", expand=True)
        self._c_donut = self._chart_slot(chart_row, "Completion Breakdown")
        self._c_stack = self._chart_slot(chart_row,
                                         "Completion by Course", height=340)

    # ── Tab 4: Enrollment ─────────────────────────────────────────────────
    def _build_enrollment(self):
        p = tk.Frame(self._tab_enrollment, bg=CONTENT_BG,
                     padx=10, pady=10)
        p.pack(fill="both", expand=True)

        tk.Label(p, text="Enrollment Analytics",
                 font=("Segoe UI", 11, "bold"),
                 bg=CONTENT_BG, fg="#1a3a5c").pack(anchor="w", pady=(0, 5))

        # Stat cards
        cards = tk.Frame(p, bg=CONTENT_BG)
        cards.pack(fill="x", pady=(0, 12))
        self._enr = {}
        for title, colour in [
            ("Total Enrollments",   "#1a3a5c"),
            ("New This Week",       "#27ae60"),
            ("Monthly Enrollments", "#e67e22"),
            ("Growth %",            "#3498db"),
        ]:
            self._enr[title] = self._stat_card(cards, title, "0", colour)

        # Two chart slots
        chart_row = tk.Frame(p, bg=CONTENT_BG)
        chart_row.pack(fill="both", expand=True)
        self._c_monthly = self._chart_slot(chart_row, "Monthly Enrollments")
        self._c_etrend  = self._chart_slot(chart_row, "Enrollment Trend")

    # ── Tab 5: Instructor ─────────────────────────────────────────────────
    def _build_instructor(self):
        p = tk.Frame(self._tab_instructor, bg=CONTENT_BG,
                     padx=10, pady=10)
        p.pack(fill="both", expand=True)

        tk.Label(p, text="Instructor Analytics",
                 font=("Segoe UI", 11, "bold"),
                 bg=CONTENT_BG, fg="#1a3a5c").pack(anchor="w", pady=(0, 5))

        self._instr_tree = self._make_tree(p, [
            ("instructor_name",  "Instructor Name",  180),
            ("courses_created",  "Courses Created",  110),
            ("students_assigned","Students Assigned", 120),
            ("average_rating",   "Avg Rating",        90),
            ("completion_rate",  "Completion Rate",   110),
        ], height=8)

        chart_row = tk.Frame(p, bg=CONTENT_BG)
        chart_row.pack(fill="both", expand=True, pady=(12, 0))
        self._c_instr = self._chart_slot(
            chart_row, "Students Assigned per Instructor", height=360)

    # ──────────────────────────────────────────────────────────────────────
    # Data loading — mirrors analyst.py exactly
    # ──────────────────────────────────────────────────────────────────────
    def _load_data(self):
        try:
            svc       = self._services
            analytics = svc.get("analytics_service")
            if analytics is None:
                show_error(self, "Error", "analytics_service not found.")
                return

            # ── Section 1: Overview ───────────────────────────────────────
            overview = analytics.system_overview()
            self._ov["Total Courses"].config(
                text=str(overview.get("total_courses", 0)))
            self._ov["Total Learners"].config(
                text=str(overview.get("total_learners", 0)))
            self._ov["Total Enrollments"].config(
                text=str(overview.get("total_enrollments", 0)))
            self._ov["Completions"].config(
                text=str(overview.get("total_completions", 0)))
            self._ov["Completion Rate"].config(
                text=f"{overview.get('overall_completion_rate', 0)}%")

            diff  = overview.get("difficulty_distribution", {})
            total = max(diff.get("total", 1), 1)
            for level, (bar, lbl) in self._diff_bars.items():
                count = diff.get(level, 0)
                bar["value"] = count / total * 100
                lbl.config(text=str(count))

            # ── Section 2: Student Performance ───────────────────────────
            # Same call as Flask analyst.py
            performance_report = analytics.student_performance_report()
            score_buckets      = analytics.score_bucket_distribution()
            performance_trend  = analytics.performance_trend(months=6)

            self._fill_performance_table(performance_report)
            self._fill_performance_charts(
                performance_report, score_buckets, performance_trend)

            # ── Section 3: Course Completion ──────────────────────────────
            # Same calls as Flask analyst.py
            completion_breakdown = analytics.course_completion_breakdown()
            completion_by_course = analytics.course_completion_by_course()

            self._fill_completion(completion_breakdown, completion_by_course)

            # ── Section 4: Enrollment ─────────────────────────────────────
            # Same calls as Flask analyst.py
            enrollment_metrics = analytics.enrollment_summary_metrics()
            enrollment_trend   = analytics.enrollment_monthly_trend(months=6)

            self._fill_enrollment(enrollment_metrics, enrollment_trend)

            # ── Section 5: Instructor ─────────────────────────────────────
            # Same logic as Flask analyst.py
            user_repo   = svc.get("user_repo")
            database    = svc.get("database")
            instructors = user_repo.find_by_role(UserRole.INSTRUCTOR) \
                if user_repo else []

            instructor_courses = defaultdict(set)
            if database:
                try:
                    with database.get_connection() as conn:
                        rows = conn.execute(
                            "SELECT DISTINCT instructor_id, course_code "
                            "FROM course_submissions "
                            "WHERE status != 'REJECTED'"
                        ).fetchall()
                    for r in rows:
                        instructor_courses[r["instructor_id"]].add(
                            r["course_code"])
                except Exception as e:
                    print(f"[Instructor query] {e}")

            instructor_report = analytics.instructor_analytics(
                instructors, instructor_courses)
            self._fill_instructor(instructor_report)

        except Exception as e:
            show_error(self, "Error", f"Failed to load analytics:\n{e}")

    # ──────────────────────────────────────────────────────────────────────
    # Fill: Student Performance
    # ──────────────────────────────────────────────────────────────────────
    def _fill_performance_table(self, report):
        """
        Fills the performance Treeview.
        report rows have same keys as student_performance_report():
            student_name, course_code, course_name, score, grade, status
        """
        for row in self._perf_tree.get_children():
            self._perf_tree.delete(row)

        for r in report or []:
            score  = r.get("score")
            course = f"{r.get('course_code','')} — {r.get('course_name','')}"
            self._perf_tree.insert("", "end", values=(
                r.get("student_name", "—"),
                course,
                "—" if score is None else score,
                r.get("grade", "—"),
                r.get("status", "—"),
            ))

    def _fill_performance_charts(self, report, buckets, trend):
        if not MPL:
            for c in (self._c_marks, self._c_buckets, self._c_trend):
                self._no_data(c, "pip install matplotlib")
            return

        # ── Marks bar chart ───────────────────────────────────────────────
        scored = [r for r in report if r.get("score") is not None]
        if scored:
            # Group by student — average if multiple courses
            from collections import defaultdict as dd
            by_student = dd(list)
            for r in scored:
                by_student[r["student_name"]].append(r["score"])
            names  = list(by_student.keys())
            scores = [round(sum(v)/len(v), 1) for v in by_student.values()]

            fig, ax = self._fig(6, 3.2)
            ax.bar(names, scores, color="#2a78d6", width=0.6)
            for i, (n, s) in enumerate(zip(names, scores)):
                ax.text(i, s + 0.5, str(s),
                        ha="center", va="bottom",
                        fontsize=8, color="#333")
            ax.set_ylim(0, 110)
            ax.set_ylabel("Marks")
            ax.set_title("Marks by Student",
                         fontsize=10, color="#1a3a5c")
            ax.tick_params(axis="x", rotation=30)
            plt.tight_layout()
            self._embed_fig(self._c_marks, fig)
        else:
            self._no_data(self._c_marks)

        # ── Score bucket pie ──────────────────────────────────────────────
        # Uses analytics.score_bucket_distribution() — same as Flask
        if buckets and buckets.get("total", 0):
            fig, ax = self._fig(5, 3.2)
            ax.pie(
                [buckets["Excellent"], buckets["Good"],
                 buckets["Average"],   buckets["Poor"]],
                labels=["Excellent", "Good", "Average", "Poor"],
                colors=["#0ca30c", "#2a78d6", "#fab219", "#d03b3b"],
                autopct="%1.0f%%",
                startangle=90,
            )
            ax.set_title("Performance Distribution",
                         fontsize=10, color="#1a3a5c")
            plt.tight_layout()
            self._embed_fig(self._c_buckets, fig)
        else:
            self._no_data(self._c_buckets)

        # ── Trend line ────────────────────────────────────────────────────
        # Uses analytics.performance_trend(months=6) — same as Flask
        has_data = any(r.get("average_score") is not None for r in trend)
        if trend and has_data:
            labels = [r["label"] for r in trend]
            values = [r.get("average_score") for r in trend]

            fig, ax = self._fig(6, 3.2)
            ax.plot(labels, values, marker="o",
                    color="#2a78d6", linewidth=2)
            ax.set_ylim(0, 100)
            ax.set_ylabel("Average Score")
            ax.set_title("Performance Over Time",
                         fontsize=10, color="#1a3a5c")
            ax.tick_params(axis="x", rotation=30)
            plt.tight_layout()
            self._embed_fig(self._c_trend, fig)
        else:
            self._no_data(self._c_trend)

    # ──────────────────────────────────────────────────────────────────────
    # Fill: Course Completion
    # ──────────────────────────────────────────────────────────────────────
    def _fill_completion(self, breakdown, by_course):
        self._cmp["Completed"].config(
            text=str(breakdown.get("completed", 0)))
        self._cmp["In Progress"].config(
            text=str(breakdown.get("in_progress", 0)))
        self._cmp["Not Started"].config(
            text=str(breakdown.get("not_started", 0)))
        self._cmp["Completion %"].config(
            text=f"{breakdown.get('completion_rate', 0)}%")

        if not MPL:
            self._no_data(self._c_donut, "pip install matplotlib")
            self._no_data(self._c_stack, "pip install matplotlib")
            return

        # ── Doughnut / pie ────────────────────────────────────────────────
        total = breakdown.get("total", 0)
        if total:
            fig, ax = self._fig(5, 3.4)
            ax.pie(
                [breakdown["completed"],
                 breakdown["in_progress"],
                 breakdown["not_started"]],
                labels=["Completed", "In Progress", "Not Started"],
                colors=["#0ca30c", "#2a78d6", "#898781"],
                autopct="%1.0f%%",
                startangle=90,
                wedgeprops={"width": 0.45},
            )
            ax.set_title("Completion Breakdown",
                         fontsize=10, color="#1a3a5c")
            plt.tight_layout()
            self._embed_fig(self._c_donut, fig)
        else:
            self._no_data(self._c_donut)

        # ── Stacked bar — course_completion_by_course() ───────────────────
        labels = by_course.get("labels", [])
        if labels:
            completed   = by_course.get("completed", [])
            in_progress = by_course.get("in_progress", [])
            not_started = by_course.get("not_started", [])

            fig, ax = self._fig(6.5, 3.8)
            ax.bar(labels, completed,   color="#0ca30c",
                   label="Completed")
            ax.bar(labels, in_progress, color="#2a78d6",
                   label="In Progress",
                   bottom=completed)
            bottom2 = [c + i for c, i in zip(completed, in_progress)]
            ax.bar(labels, not_started, color="#898781",
                   label="Not Started",
                   bottom=bottom2)
            ax.set_title("Completion by Course",
                         fontsize=10, color="#1a3a5c")
            ax.set_ylabel("Students")
            ax.tick_params(axis="x", rotation=30)
            ax.legend(loc="upper right", fontsize=8)
            plt.tight_layout()
            self._embed_fig(self._c_stack, fig)
        else:
            self._no_data(self._c_stack)

    # ──────────────────────────────────────────────────────────────────────
    # Fill: Enrollment
    # ──────────────────────────────────────────────────────────────────────
    def _fill_enrollment(self, metrics, trend):
        self._enr["Total Enrollments"].config(
            text=str(metrics.get("total_enrollments", 0)))
        self._enr["New This Week"].config(
            text=str(metrics.get("new_this_week", 0)))
        self._enr["Monthly Enrollments"].config(
            text=str(metrics.get("monthly_enrollments", 0)))
        self._enr["Growth %"].config(
            text=f"{metrics.get('growth_rate', 0)}%")

        if not MPL:
            self._no_data(self._c_monthly, "pip install matplotlib")
            self._no_data(self._c_etrend,  "pip install matplotlib")
            return

        total = sum(r.get("count", 0) for r in trend)
        if trend and total:
            labels = [r["label"] for r in trend]
            counts = [r["count"] for r in trend]

            # Monthly bar
            fig, ax = self._fig(6, 3.2)
            ax.bar(labels, counts, color="#2a78d6", width=0.6)
            ax.set_ylabel("Enrollments")
            ax.set_title("Monthly Enrollments",
                         fontsize=10, color="#1a3a5c")
            ax.tick_params(axis="x", rotation=30)
            plt.tight_layout()
            self._embed_fig(self._c_monthly, fig)

            # Trend line
            fig, ax = self._fig(6, 3.2)
            ax.plot(labels, counts, marker="o",
                    color="#1baf7a", linewidth=2)
            ax.set_ylabel("Enrollments")
            ax.set_title("Enrollment Trend",
                         fontsize=10, color="#1a3a5c")
            ax.tick_params(axis="x", rotation=30)
            plt.tight_layout()
            self._embed_fig(self._c_etrend, fig)
        else:
            self._no_data(self._c_monthly)
            self._no_data(self._c_etrend)

    # ──────────────────────────────────────────────────────────────────────
    # Fill: Instructor
    # ──────────────────────────────────────────────────────────────────────
    def _fill_instructor(self, report):
        for row in self._instr_tree.get_children():
            self._instr_tree.delete(row)

        for r in report or []:
            self._instr_tree.insert("", "end", values=(
                r.get("instructor_name",   "—"),
                r.get("courses_created",    0),
                r.get("students_assigned",  0),
                r.get("average_rating",    "N/A"),
                f"{r.get('completion_rate', 0)}%",
            ))

        if not MPL:
            self._no_data(self._c_instr, "pip install matplotlib")
            return

        if report:
            names  = [r.get("instructor_name", "") for r in report]
            counts = [r.get("students_assigned", 0) for r in report]

            fig, ax = self._fig(6.5, 3.8)
            ax.barh(names, counts, color="#2a78d6")
            ax.set_xlabel("Students Assigned")
            ax.set_title("Students Assigned per Instructor",
                         fontsize=10, color="#1a3a5c")
            plt.tight_layout()
            self._embed_fig(self._c_instr, fig)
        else:
            self._no_data(self._c_instr)