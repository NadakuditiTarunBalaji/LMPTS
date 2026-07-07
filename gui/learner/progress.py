"""
progress.py
-----------
Learner progress tracker and learning path screen.
"""

import tkinter as tk
from tkinter import ttk
from core.user import User
from gui.widgets.graph_view import GraphView
from gui.dialogs.confirm_dialog import show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


class ProgressScreen(tk.Frame):
    """Progress tracking with progress bars per course."""

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user       = user
        self._services   = services
        self._learner_id = None
        self._build()
        self._load_data()

    def _build(self):
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame, text="My Progress",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(side="left")
        tk.Button(
            title_frame, text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat", cursor="hand2",
            command=self._load_data,
        ).pack(side="right")

        # Summary card
        self._summary_frame = tk.Frame(
            self, bg=CARD_BG, padx=20, pady=15
        )
        self._summary_frame.pack(fill="x", padx=20, pady=(0, 10))

        self._summary_var = tk.StringVar(value="Loading...")
        tk.Label(
            self._summary_frame,
            textvariable=self._summary_var,
            font=("Segoe UI", 10),
            bg=CARD_BG,
            fg="#333333",
        ).pack(anchor="w")

        ttk.Separator(self, orient="horizontal").pack(
            fill="x", padx=20, pady=5
        )

        # Scrollable progress list
        container = tk.Frame(self, bg=CONTENT_BG)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        canvas = tk.Canvas(container, bg=CONTENT_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            container, orient="vertical", command=canvas.yview
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._progress_list = tk.Frame(canvas, bg=CONTENT_BG)
        self._canvas_window = canvas.create_window(
            (0, 0), window=self._progress_list, anchor="nw"
        )

        self._progress_list.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(
                self._canvas_window, width=e.width
            )
        )

    def _load_data(self):
        """Load progress data for the learner."""
        try:
            learner_repo = self._services.get("learner_repo")
            if learner_repo:
                learner = learner_repo.get_learner_by_user_id(
                    self._user.id
                )
                if learner:
                    self._learner_id = learner.id

            if self._learner_id is None:
                return

            progress_svc = self._services.get("progress_service")
            if not progress_svc:
                return

            summary = progress_svc.get_overall_summary(self._learner_id)
            self._summary_var.set(
                f"Total Enrolled: {summary['total_enrolled']}  |  "
                f"Completed: {summary['completed']}  |  "
                f"In Progress: {summary['in_progress']}  |  "
                f"Completion Rate: {summary['completion_rate']}%"
            )

            all_progress = progress_svc.get_learner_progress(
                self._learner_id
            )

            # Clear old progress bars
            for widget in self._progress_list.winfo_children():
                widget.destroy()

            # Create a progress bar row for each course
            for p in all_progress:
                self._add_progress_row(p)

        except Exception as e:
            show_error(self, "Error", str(e))

    def _add_progress_row(self, progress):
        """Add one progress bar row for a course."""
        row = tk.Frame(
            self._progress_list,
            bg=CARD_BG,
            padx=15,
            pady=8,
        )
        row.pack(fill="x", pady=3)

        # Course code + status
        info_frame = tk.Frame(row, bg=CARD_BG)
        info_frame.pack(fill="x")

        tk.Label(
            info_frame,
            text=progress.course_code,
            font=("Segoe UI", 10, "bold"),
            bg=CARD_BG,
            fg="#1a3a5c",
            width=10,
            anchor="w",
        ).pack(side="left")

        status_colours = {
            "COMPLETED":   "#27ae60",
            "IN_PROGRESS": "#e67e22",
            "NOT_STARTED": "#95a5a6",
            "FAILED":      "#c0392b",
        }
        status = progress.completion_status.value
        colour = status_colours.get(status, "#333333")

        tk.Label(
            info_frame,
            text=status.replace("_", " "),
            font=("Segoe UI", 8),
            bg=CARD_BG,
            fg=colour,
        ).pack(side="left", padx=10)

        tk.Label(
            info_frame,
            text=f"{progress.percentage:.0f}%",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG,
            fg="#333333",
        ).pack(side="right")

        # Progress bar
        bar = ttk.Progressbar(
            row,
            length=400,
            mode="determinate",
            maximum=100,
            value=progress.percentage,
        )
        bar.pack(fill="x", pady=(4, 0))


class LearningPathScreen(tk.Frame):
    """Learning path visualizer toward a goal course."""

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user       = user
        self._services   = services
        self._learner_id = None
        self._build()
        self._find_learner()

    def _build(self):
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame, text="Learning Path",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(side="left")

        # Goal selector
        select_frame = tk.Frame(self, bg=CONTENT_BG)
        select_frame.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(
            select_frame, text="Goal Course:",
            font=("Segoe UI", 9, "bold"),
            bg=CONTENT_BG, fg="#333333",
        ).pack(side="left")

        self._goal_var = tk.StringVar()
        self._goal_combo = ttk.Combobox(
            select_frame,
            textvariable=self._goal_var,
            state="readonly",
            width=20,
            font=("Segoe UI", 10),
        )
        self._goal_combo.pack(side="left", padx=10)

        tk.Button(
            select_frame, text="Show Path",
            font=("Segoe UI", 9),
            bg="#1a3a5c", fg="#ffffff",
            relief="flat", cursor="hand2",
            padx=10, pady=4,
            command=self._show_path,
        ).pack(side="left")

        # Split: left text, right graph
        content = tk.Frame(self, bg=CONTENT_BG)
        content.pack(fill="both", expand=True, padx=20)

        # Roadmap info
        left = tk.LabelFrame(
            content, text="  Roadmap",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c", relief="flat",
        )
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._roadmap_text = tk.Text(
            left,
            font=("Courier New", 10),
            bg=CARD_BG, fg="#333333",
            relief="flat",
            state="disabled",
            wrap="word",
        )
        self._roadmap_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Graph
        right = tk.Frame(content, bg=CONTENT_BG)
        right.pack(side="left", fill="both", expand=True)

        self._graph_view = GraphView(right)
        self._graph_view.pack(fill="both", expand=True)

    def _find_learner(self):
        """Find learner ID and populate course combobox."""
        try:
            learner_repo = self._services.get("learner_repo")
            if learner_repo:
                learner = learner_repo.get_learner_by_user_id(
                    self._user.id
                )
                if learner:
                    self._learner_id = learner.id

            course_svc = self._services.get("course_service")
            if course_svc:
                courses = course_svc.get_available_courses()
                self._goal_combo["values"] = [c.code for c in courses]

        except Exception as e:
            show_error(self, "Error", str(e))

    def _show_path(self):
        """Display the learning path toward the selected goal."""
        goal = self._goal_var.get()
        if not goal:
            show_info(self, "Select Goal",
                      "Please select a goal course.")
            return

        if self._learner_id is None:
            show_error(self, "Error",
                       "Learner profile not found.")
            return

        try:
            path_svc = self._services.get("learning_path_service")
            if path_svc is None:
                return

            roadmap = path_svc.get_learner_roadmap(
                self._learner_id, goal
            )

            # Build text display
            lines = [
                f"Goal: {roadmap['goal']}",
                f"Progress: {roadmap['done']}/{roadmap['total']} "
                f"({roadmap['percentage']}%)",
                "",
                "✅ Completed:",
            ]
            for c in roadmap.get("completed", []):
                lines.append(f"   ✓ {c}")

            lines.append("")
            lines.append("🔄 In Progress:")
            for c in roadmap.get("in_progress", []):
                lines.append(f"   → {c}")

            lines.append("")
            lines.append("📚 Still Required:")
            for c in roadmap.get("remaining", []):
                lines.append(f"   ○ {c}")

            lines.append("")
            lines.append("Full Path:")
            for i, c in enumerate(roadmap.get("full_path", [])):
                prefix = "  └─ " if i == len(roadmap["full_path"])-1 else "  ├─ "
                lines.append(f"{prefix}{c}")

            self._roadmap_text.config(state="normal")
            self._roadmap_text.delete("1.0", "end")
            self._roadmap_text.insert("1.0", "\n".join(lines))
            self._roadmap_text.config(state="disabled")

            # Update graph
            course_svc = self._services.get("course_service")
            if course_svc:
                graph = course_svc.get_graph()
                completed = set(roadmap.get("completed", []))
                self._graph_view.draw_graph(
                    graph,
                    highlight_course=goal,
                    completed_courses=completed,
                )

        except Exception as e:
            show_error(self, "Error", str(e))