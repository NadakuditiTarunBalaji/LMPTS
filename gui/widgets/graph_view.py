"""
graph_view.py
-------------
Canvas-based prerequisite graph visualizer.

Draws course nodes as boxes with arrows between them.

Usage:
    gv = GraphView(parent)
    gv.pack(fill="both", expand=True)
    gv.draw_graph(graph, highlight_course="CS201")
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Set, List, Optional, Tuple
from algorithms.graph import CourseGraph


# ── Colours ────────────────────────────────────────────────────────────────────

NODE_BG         = "#1a3a5c"
NODE_FG         = "#ffffff"
NODE_HIGHLIGHT  = "#4a90d9"
NODE_COMPLETED  = "#27ae60"
ARROW_COLOUR    = "#555555"
CANVAS_BG       = "#f8f9fa"

NODE_W  = 100   # node box width
NODE_H  = 40    # node box height
H_GAP   = 60    # horizontal gap between nodes
V_GAP   = 80    # vertical gap between levels


class GraphView(tk.Frame):
    """
    Displays the course prerequisite graph on a Canvas.

    Shows:
        - Course nodes as rounded rectangles
        - Prerequisite arrows between nodes
        - Level-based layout (root courses at top)
        - Highlighted node for selected course
        - Completed courses in green
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        """Build the canvas with scrollbars."""
        # Label
        tk.Label(
            self,
            text="Prerequisite Graph",
            font=("Segoe UI", 10, "bold"),
            fg="#1a3a5c",
        ).pack(anchor="w", padx=5, pady=(5, 0))

        # Canvas frame
        canvas_frame = tk.Frame(self, relief="sunken", bd=1)
        canvas_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._canvas = tk.Canvas(
            canvas_frame,
            bg=CANVAS_BG,
            highlightthickness=0,
        )
        v_scroll = ttk.Scrollbar(
            canvas_frame, orient="vertical",
            command=self._canvas.yview
        )
        h_scroll = ttk.Scrollbar(
            canvas_frame, orient="horizontal",
            command=self._canvas.xview
        )
        self._canvas.configure(
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
        )

        self._canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

    def draw_graph(
        self,
        graph: CourseGraph,
        highlight_course: Optional[str] = None,
        completed_courses: Optional[Set[str]] = None,
    ):
        """
        Draw the prerequisite graph on the canvas.

        Layout algorithm:
            1. Compute levels using topological sort
            2. Arrange nodes in a grid (level × position)
            3. Draw arrows from prerequisite → dependent

        Args:
            graph            : CourseGraph to visualize.
            highlight_course : Course code to highlight in blue.
            completed_courses: Courses to show in green.
        """
        self._canvas.delete("all")
        completed_courses = completed_courses or set()

        if graph.number_of_courses() == 0:
            self._canvas.create_text(
                200, 100,
                text="No courses in graph",
                font=("Segoe UI", 12),
                fill="#888888",
            )
            return

        # Get level layout
        try:
            from algorithms.topological_sort import TopologicalSorter
            sorter = TopologicalSorter(graph)
            levels = sorter.get_levels()
        except ValueError:
            # Graph has a cycle — just show nodes in a list
            levels = [[c] for c in graph.get_courses()]

        # Calculate node positions
        positions: Dict[str, Tuple[int, int]] = {}
        max_per_level = max(len(level) for level in levels) if levels else 1

        canvas_width = max(
            max_per_level * (NODE_W + H_GAP) + H_GAP, 600
        )
        canvas_height = len(levels) * (NODE_H + V_GAP) + V_GAP

        for level_idx, level_courses in enumerate(levels):
            n     = len(level_courses)
            total = n * NODE_W + (n - 1) * H_GAP
            start = (canvas_width - total) // 2

            y = V_GAP + level_idx * (NODE_H + V_GAP)

            for node_idx, course_code in enumerate(sorted(level_courses)):
                x = start + node_idx * (NODE_W + H_GAP)
                positions[course_code] = (x + NODE_W // 2, y + NODE_H // 2)

        # Draw arrows first (behind nodes)
        fg_graph = graph.get_graph()
        for prereq, dependents in fg_graph.items():
            if prereq not in positions:
                continue
            px, py = positions[prereq]
            for dep in dependents:
                if dep not in positions:
                    continue
                dx, dy = positions[dep]
                self._draw_arrow(px, py, dx, dy)

        # Draw nodes
        for course_code, (cx, cy) in positions.items():
            if course_code in completed_courses:
                colour = NODE_COMPLETED
            elif course_code == highlight_course:
                colour = NODE_HIGHLIGHT
            else:
                colour = NODE_BG

            self._draw_node(cx, cy, course_code, colour)

        # Update scroll region
        self._canvas.configure(
            scrollregion=(0, 0, canvas_width, canvas_height + V_GAP)
        )

    def _draw_node(self, cx: int, cy: int, text: str, colour: str):
        """Draw a rounded rectangle node."""
        x1, y1 = cx - NODE_W // 2, cy - NODE_H // 2
        x2, y2 = cx + NODE_W // 2, cy + NODE_H // 2
        r = 8   # corner radius

        # Rounded rectangle (polygon approximation)
        self._canvas.create_rectangle(
            x1 + r, y1, x2 - r, y2,
            fill=colour, outline="", width=0
        )
        self._canvas.create_rectangle(
            x1, y1 + r, x2, y2 - r,
            fill=colour, outline="", width=0
        )
        # Corners
        self._canvas.create_oval(
            x1, y1, x1 + 2*r, y1 + 2*r,
            fill=colour, outline=""
        )
        self._canvas.create_oval(
            x2 - 2*r, y1, x2, y1 + 2*r,
            fill=colour, outline=""
        )
        self._canvas.create_oval(
            x1, y2 - 2*r, x1 + 2*r, y2,
            fill=colour, outline=""
        )
        self._canvas.create_oval(
            x2 - 2*r, y2 - 2*r, x2, y2,
            fill=colour, outline=""
        )

        # Text
        self._canvas.create_text(
            cx, cy,
            text=text,
            font=("Segoe UI", 8, "bold"),
            fill="#ffffff",
        )

    def _draw_arrow(self, x1: int, y1: int, x2: int, y2: int):
        """Draw an arrow from (x1,y1) to (x2,y2)."""
        # Adjust start/end to node edges
        dy = y2 - y1
        dx = x2 - x1
        length = max((dx**2 + dy**2) ** 0.5, 1)

        # Start at bottom of source node
        sx = x1
        sy = y1 + NODE_H // 2

        # End at top of target node
        ex = x2
        ey = y2 - NODE_H // 2

        self._canvas.create_line(
            sx, sy, ex, ey,
            arrow=tk.LAST,
            fill=ARROW_COLOUR,
            width=2,
            arrowshape=(10, 12, 4),
        )

    def clear(self):
        """Clear the canvas."""
        self._canvas.delete("all")

    def draw_text_view(
        self,
        graph: CourseGraph,
        selected_course: Optional[str] = None,
    ) -> str:
        """
        Return a text representation of prerequisites.

        Used alongside the canvas view.

        Args:
            graph           : CourseGraph.
            selected_course : Show prerequisites for this course.

        Returns:
            str: Formatted text showing prerequisite chain.
        """
        if selected_course is None:
            lines = []
            for course in sorted(graph.get_courses()):
                prereqs = graph.get_prerequisites(course)
                if prereqs:
                    lines.append(
                        f"{course} requires: "
                        f"{', '.join(sorted(prereqs))}"
                    )
                else:
                    lines.append(f"{course} (no prerequisites)")
            return "\n".join(lines)

        prereqs = graph.get_all_prerequisites(selected_course)
        if not prereqs:
            return f"{selected_course} has no prerequisites."

        try:
            from algorithms.topological_sort import TopologicalSorter
            sorter = TopologicalSorter(graph)
            order  = sorter.sort()
            ordered_prereqs = [p for p in order if p in prereqs]
        except ValueError:
            ordered_prereqs = sorted(prereqs)

        lines = [f"Prerequisites for {selected_course}:"]
        for i, p in enumerate(ordered_prereqs):
            prefix = "  └─ " if i == len(ordered_prereqs) - 1 else "  ├─ "
            lines.append(f"{prefix}{p}")
        lines.append(f"  → {selected_course}")
        return "\n".join(lines)