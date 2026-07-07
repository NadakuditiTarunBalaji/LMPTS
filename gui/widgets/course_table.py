"""
course_table.py
---------------
Reusable ttk.Treeview table for displaying courses.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Callable
from core.course import Course


class CourseTable(tk.Frame):
    """
    A scrollable, sortable table for displaying courses.

    Columns: Code | Name | Difficulty | Duration | Status

    Usage:
        table = CourseTable(parent, on_select=my_callback)
        table.pack(fill="both", expand=True)
        table.load_courses(course_list)

        selected = table.get_selected()
    """

    COLUMNS = ("code", "name", "difficulty", "duration", "status")
    HEADERS = {
        "code":       "Code",
        "name":       "Name",
        "difficulty": "Difficulty",
        "duration":   "Duration (h)",
        "status":     "Status",
    }
    WIDTHS = {
        "code":       80,
        "name":       250,
        "difficulty": 100,
        "duration":   90,
        "status":     90,
    }

    STATUS_COLOURS = {
        "PUBLISHED": "#e8f5e9",   # Light green
        "DRAFT":     "#fff8e1",   # Light yellow
        "ARCHIVED":  "#fce4ec",   # Light red
    }

    def __init__(
        self,
        parent,
        on_select: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self._on_select = on_select
        self._courses: List[Course] = []
        self._build()

    def _build(self):
        """Build the Treeview with scrollbars."""
        # Style
        style = ttk.Style()
        style.configure(
            "Course.Treeview",
            rowheight=28,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Course.Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
        )

        # Treeview
        self._tree = ttk.Treeview(
            self,
            columns=self.COLUMNS,
            show="headings",
            style="Course.Treeview",
            selectmode="browse",
        )

        # Configure columns
        for col in self.COLUMNS:
            self._tree.heading(
                col,
                text=self.HEADERS[col],
                command=lambda c=col: self._sort_by(c),
            )
            self._tree.column(col, width=self.WIDTHS[col], minwidth=50)

        # Scrollbars
        v_scroll = ttk.Scrollbar(
            self, orient="vertical", command=self._tree.yview
        )
        h_scroll = ttk.Scrollbar(
            self, orient="horizontal", command=self._tree.xview
        )
        self._tree.configure(
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
        )

        # Layout
        self._tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Row colour tags
        for status, colour in self.STATUS_COLOURS.items():
            self._tree.tag_configure(status, background=colour)
        self._tree.tag_configure(
            "odd", background="#f5f5f5"
        )

        # Events
        if self._on_select:
            self._tree.bind("<<TreeviewSelect>>", self._on_select_event)

    def load_courses(self, courses: List[Course]):
        """
        Populate the table with a list of courses.

        Args:
            courses: List of Course objects to display.
        """
        self._courses = courses
        self._refresh()

    def _refresh(self):
        """Clear and re-populate the table."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        for i, course in enumerate(self._courses):
            tag = course.status.value
            values = (
                course.code,
                course.name,
                course.difficulty.value,
                f"{course.duration}h",
                course.status.value,
            )
            self._tree.insert(
                "", "end", iid=course.code,
                values=values, tags=(tag,)
            )

    def get_selected(self) -> Optional[Course]:
        """
        Return the currently selected Course object.

        Returns:
            Course if one is selected, None otherwise.
        """
        selection = self._tree.selection()
        if not selection:
            return None

        code = selection[0]
        for course in self._courses:
            if course.code == code:
                return course
        return None

    def get_selected_code(self) -> Optional[str]:
        """Return the selected course code string."""
        selection = self._tree.selection()
        return selection[0] if selection else None

    def clear_selection(self):
        """Deselect all rows."""
        for item in self._tree.selection():
            self._tree.selection_remove(item)

    def _sort_by(self, column: str):
        """Sort the table by the clicked column."""
        reverse = False

        if column == "code":
            self._courses.sort(key=lambda c: c.code, reverse=reverse)
        elif column == "name":
            self._courses.sort(key=lambda c: c.name, reverse=reverse)
        elif column == "difficulty":
            order = {"BEGINNER": 0, "INTERMEDIATE": 1, "ADVANCED": 2}
            self._courses.sort(
                key=lambda c: order.get(c.difficulty.value, 0)
            )
        elif column == "duration":
            self._courses.sort(key=lambda c: c.duration)
        elif column == "status":
            self._courses.sort(key=lambda c: c.status.value)

        self._refresh()

    def _on_select_event(self, event):
        """Forward selection event to callback."""
        if self._on_select:
            selected = self.get_selected()
            self._on_select(selected)