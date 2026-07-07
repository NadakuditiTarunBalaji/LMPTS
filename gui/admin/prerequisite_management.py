"""
prerequisite_management.py
--------------------------
Manage course prerequisite relationships with graph visualization.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from core.exceptions import CourseNotFoundError, CircularDependencyError
from gui.widgets.graph_view import GraphView
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


class PrerequisiteManagementScreen(tk.Frame):
    """
    Prerequisite management with visual graph display.

    Layout:
        Left: Course selector + prerequisite list + add/remove buttons
        Right: Canvas graph visualization + text view
    """

    def __init__(self, parent, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._services = services
        self._selected_course: Optional[str] = None
        self._build()
        self._load_courses()

    def _build(self):
        """Build the prerequisite management UI."""
        # Title
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)

        tk.Label(
            title_frame,
            text="Prerequisite Management",
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
            command=self._refresh,
        ).pack(side="right")

        # Main content: left panel + right graph
        content = tk.Frame(self, bg=CONTENT_BG)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # ── Left panel ──────────────────────────────────────────────────────
        left = tk.Frame(content, bg=CARD_BG, width=320, relief="flat", bd=1)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        tk.Label(
            left,
            text="Select Course",
            font=("Segoe UI", 10, "bold"),
            bg=CARD_BG,
            fg="#1a3a5c",
            pady=10,
        ).pack(fill="x", padx=10)

        # Course combobox
        self._course_var = tk.StringVar()
        self._course_combo = ttk.Combobox(
            left,
            textvariable=self._course_var,
            state="readonly",
            font=("Segoe UI", 10),
            width=30,
        )
        self._course_combo.pack(padx=10, pady=(0, 10))
        self._course_combo.bind(
            "<<ComboboxSelected>>", self._on_course_selected
        )

        ttk.Separator(left, orient="horizontal").pack(fill="x", padx=10)

        # Current prerequisites list
        tk.Label(
            left,
            text="Current Prerequisites",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG,
            fg="#666666",
            pady=5,
        ).pack(fill="x", padx=10)

        self._prereq_listbox = tk.Listbox(
            left,
            font=("Segoe UI", 10),
            height=8,
            selectmode="single",
            relief="flat",
            bd=1,
            highlightthickness=1,
            highlightcolor="#4a90d9",
        )
        self._prereq_listbox.pack(fill="x", padx=10)

        # Add/Remove buttons
        btn_frame = tk.Frame(left, bg=CARD_BG, pady=10)
        btn_frame.pack(fill="x", padx=10)

        tk.Label(
            left,
            text="Add Prerequisite",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG,
            fg="#666666",
        ).pack(fill="x", padx=10, pady=(5, 2))

        self._prereq_add_var = tk.StringVar()
        self._prereq_add_combo = ttk.Combobox(
            left,
            textvariable=self._prereq_add_var,
            state="readonly",
            font=("Segoe UI", 10),
            width=30,
        )
        self._prereq_add_combo.pack(padx=10)

        tk.Frame(left, bg=CARD_BG, height=8).pack()

        tk.Button(
            left,
            text="➕ Add Prerequisite",
            font=("Segoe UI", 9, "bold"),
            bg="#27ae60",
            fg="#ffffff",
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=5,
            command=self._add_prerequisite,
        ).pack(fill="x", padx=10, pady=2)

        tk.Button(
            left,
            text="🗑️ Remove Selected",
            font=("Segoe UI", 9),
            bg="#e74c3c",
            fg="#ffffff",
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=5,
            command=self._remove_prerequisite,
        ).pack(fill="x", padx=10, pady=2)

        # ── Right: Graph view ───────────────────────────────────────────────
        right = tk.Frame(content, bg=CONTENT_BG)
        right.pack(side="left", fill="both", expand=True)

        # Tabs: Graph View | Text View
        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True)

        # Graph tab
        graph_tab = tk.Frame(notebook, bg=CONTENT_BG)
        notebook.add(graph_tab, text="  Graph View  ")

        self._graph_view = GraphView(graph_tab)
        self._graph_view.pack(fill="both", expand=True)

        # Text tab
        text_tab = tk.Frame(notebook, bg=CONTENT_BG)
        notebook.add(text_tab, text="  Text View  ")

        self._text_view = tk.Text(
            text_tab,
            font=("Courier New", 10),
            bg="#ffffff",
            fg="#333333",
            relief="flat",
            state="disabled",
            wrap="word",
        )
        self._text_view.pack(fill="both", expand=True, padx=5, pady=5)

    # ── Data ───────────────────────────────────────────────────────────────────

    def _load_courses(self):
        """Populate course comboboxes."""
        try:
            service = self._services.get("course_service")
            if service is None:
                return

            courses = service.get_all_courses()
            codes   = [c.code for c in courses]

            self._course_combo["values"]    = codes
            self._prereq_add_combo["values"] = codes

            self._update_graph()

        except Exception as e:
            show_error(self, "Error", str(e))

    def _on_course_selected(self, event=None):
        """Load prerequisites for the selected course."""
        self._selected_course = self._course_var.get()
        self._load_prerequisites()
        self._update_graph()

    def _load_prerequisites(self):
        """Load and display current prerequisites."""
        if not self._selected_course:
            return

        try:
            service = self._services.get("course_service")
            if service is None:
                return

            prereqs = service.get_prerequisites(self._selected_course)
            self._prereq_listbox.delete(0, "end")
            for p in sorted(prereqs):
                self._prereq_listbox.insert("end", p)

        except Exception as e:
            show_error(self, "Error", str(e))

    def _update_graph(self):
        """Redraw the prerequisite graph."""
        try:
            service = self._services.get("course_service")
            if service is None:
                return

            graph = service.get_graph()
            self._graph_view.draw_graph(
                graph,
                highlight_course=self._selected_course,
            )

            # Update text view
            text = self._graph_view.draw_text_view(
                graph, self._selected_course
            )
            self._text_view.config(state="normal")
            self._text_view.delete("1.0", "end")
            self._text_view.insert("1.0", text)
            self._text_view.config(state="disabled")

        except Exception as e:
            print(f"Graph update error: {e}")

    def _refresh(self):
        """Reload all data."""
        self._load_courses()
        if self._selected_course:
            self._load_prerequisites()

    # ── Actions ────────────────────────────────────────────────────────────────

    def _add_prerequisite(self):
        """Add the selected prerequisite to the selected course."""
        course_code = self._course_var.get()
        prereq_code = self._prereq_add_var.get()

        if not course_code:
            show_info(self, "Select Course",
                      "Please select a course first.")
            return
        if not prereq_code:
            show_info(self, "Select Prerequisite",
                      "Please select a prerequisite to add.")
            return
        if course_code == prereq_code:
            show_error(self, "Invalid",
                       "A course cannot be its own prerequisite.")
            return

        try:
            service = self._services["course_service"]
            service.add_prerequisite(course_code, prereq_code)
            show_info(
                self, "Added",
                f"'{prereq_code}' added as prerequisite of '{course_code}'."
            )
            self._load_prerequisites()
            self._update_graph()
        except CircularDependencyError as e:
            show_error(
                self, "Circular Dependency",
                f"Cannot add prerequisite:\n{e}"
            )
        except Exception as e:
            show_error(self, "Error", str(e))

    def _remove_prerequisite(self):
        """Remove the selected prerequisite from the listbox."""
        course_code = self._course_var.get()
        selection   = self._prereq_listbox.curselection()

        if not course_code:
            show_info(self, "Select Course", "Please select a course first.")
            return
        if not selection:
            show_info(self, "Select Prerequisite",
                      "Please select a prerequisite to remove.")
            return

        prereq_code = self._prereq_listbox.get(selection[0])

        if confirm(
            self, "Remove Prerequisite",
            f"Remove '{prereq_code}' as prerequisite of '{course_code}'?"
        ):
            try:
                service = self._services["course_service"]
                service.remove_prerequisite(course_code, prereq_code)
                show_info(self, "Removed", "Prerequisite removed.")
                self._load_prerequisites()
                self._update_graph()
            except Exception as e:
                show_error(self, "Error", str(e))