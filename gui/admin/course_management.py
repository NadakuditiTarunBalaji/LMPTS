"""
course_management.py
--------------------
Full CRUD interface for course management.

Features:
    - View all courses in a sortable table
    - Add new course (dialog form)
    - Edit existing course
    - Delete course (with confirmation)
    - Publish course (DRAFT → PUBLISHED)
    - Archive course (PUBLISHED → ARCHIVED)
    - Filter by status and difficulty
"""

import tkinter as tk
from tkinter import ttk, simpledialog
from typing import Optional

from core.course import Course
from core.enums import DifficultyLevel, CourseStatus
from core.exceptions import ValidationError, CourseNotFoundError
from gui.widgets.course_table import CourseTable
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


class CourseFormDialog(tk.Toplevel):
    """
    Modal dialog for adding or editing a course.

    Returns the created/edited Course via self.result.
    """

    def __init__(self, parent, title: str, course: Optional[Course] = None):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x480")
        self.resizable(False, False)
        self.configure(bg=CARD_BG)
        self.grab_set()   # Modal
        self.result: Optional[Course] = None

        self._existing = course
        self._build()

        if course:
            self._populate(course)

        # Centre over parent
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width()  - 500) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 480) // 2
        self.geometry(f"500x480+{px}+{py}")

    def _build(self):
        """Build the form fields."""
        form = tk.Frame(self, bg=CARD_BG, padx=30, pady=20)
        form.pack(fill="both", expand=True)

        def labeled_field(label_text: str, row: int) -> ttk.Entry:
            tk.Label(
                form,
                text=label_text,
                font=("Segoe UI", 9, "bold"),
                bg=CARD_BG,
                fg="#333333",
            ).grid(row=row, column=0, sticky="w", pady=(10, 2))
            entry = ttk.Entry(form, width=35, font=("Segoe UI", 10))
            entry.grid(row=row + 1, column=0, sticky="ew")
            return entry

        # Code
        self._code_entry = labeled_field("Course Code *", 0)

        # Name
        self._name_entry = labeled_field("Course Name *", 2)

        # Description
        tk.Label(
            form, text="Description",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg="#333333",
        ).grid(row=4, column=0, sticky="w", pady=(10, 2))

        self._desc_text = tk.Text(
            form, width=35, height=3,
            font=("Segoe UI", 10),
            relief="solid", bd=1,
        )
        self._desc_text.grid(row=5, column=0, sticky="ew")

        # Duration
        self._duration_entry = labeled_field("Duration (hours) *", 6)

        # Difficulty
        tk.Label(
            form, text="Difficulty *",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg="#333333",
        ).grid(row=8, column=0, sticky="w", pady=(10, 2))

        self._difficulty_var = tk.StringVar(value="BEGINNER")
        diff_frame = tk.Frame(form, bg=CARD_BG)
        diff_frame.grid(row=9, column=0, sticky="w")
        for level in DifficultyLevel:
            ttk.Radiobutton(
                diff_frame,
                text=level.value,
                variable=self._difficulty_var,
                value=level.value,
            ).pack(side="left", padx=5)

        form.columnconfigure(0, weight=1)

        # Buttons
        btn_frame = tk.Frame(self, bg=CARD_BG, pady=15)
        btn_frame.pack(fill="x", padx=30)

        tk.Button(
            btn_frame,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#e0e0e0",
            relief="flat",
            width=10,
            command=self.destroy,
        ).pack(side="right", padx=(5, 0))

        tk.Button(
            btn_frame,
            text="Save",
            font=("Segoe UI", 9, "bold"),
            bg="#1a3a5c",
            fg="#ffffff",
            relief="flat",
            width=10,
            command=self._save,
        ).pack(side="right")

    def _populate(self, course: Course):
        """Pre-fill form fields when editing."""
        self._code_entry.insert(0, course.code)
        self._code_entry.config(state="disabled")  # Code cannot change
        self._name_entry.insert(0, course.name)
        self._desc_text.insert("1.0", course.description)
        self._duration_entry.insert(0, str(course.duration))
        self._difficulty_var.set(course.difficulty.value)

    def _save(self):
        """Validate and build the Course object."""
        code     = self._code_entry.get().strip()
        name     = self._name_entry.get().strip()
        desc     = self._desc_text.get("1.0", "end-1c").strip()
        duration_str = self._duration_entry.get().strip()
        difficulty   = self._difficulty_var.get()

        if not code:
            show_error(self, "Validation Error", "Course code is required.")
            return
        if not name:
            show_error(self, "Validation Error", "Course name is required.")
            return
        if not duration_str.isdigit() or int(duration_str) <= 0:
            show_error(
                self, "Validation Error",
                "Duration must be a positive integer."
            )
            return

        self.result = Course(
            code        = code,
            name        = name,
            description = desc,
            difficulty  = DifficultyLevel(difficulty),
            duration    = int(duration_str),
            status      = (
                self._existing.status
                if self._existing else CourseStatus.DRAFT
            ),
        )
        self.destroy()


class CourseManagementScreen(tk.Frame):
    """
    Full course management interface.

    Layout:
        ┌──────────────────────────────────────┐
        │  Title + Filter bar                  │
        ├──────────────────────────────────────┤
        │                                      │
        │  Course Table (Treeview)             │
        │                                      │
        ├──────────────────────────────────────┤
        │  [Add] [Edit] [Delete]  [Publish]    │
        │  [Archive]                           │
        └──────────────────────────────────────┘
    """

    def __init__(self, parent, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._services = services
        self._selected: Optional[Course] = None
        self._all_courses = []
        self._build()
        self._load_courses()

    def _build(self):
        """Build the course management UI."""
        # Title bar
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)

        tk.Label(
            title_frame,
            text="Course Management",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG,
            fg="#1a3a5c",
        ).pack(side="left")

        # Refresh button
        tk.Button(
            title_frame,
            text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG,
            relief="flat",
            cursor="hand2",
            command=self._load_courses,
        ).pack(side="right")

        # Filter bar
        filter_frame = tk.Frame(self, bg=CONTENT_BG)
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(
            filter_frame,
            text="Filter by Status:",
            font=("Segoe UI", 9),
            bg=CONTENT_BG,
            fg="#666666",
        ).pack(side="left")

        self._status_filter = ttk.Combobox(
            filter_frame,
            values=["All", "DRAFT", "PUBLISHED", "ARCHIVED"],
            state="readonly",
            width=12,
            font=("Segoe UI", 9),
        )
        self._status_filter.set("All")
        self._status_filter.pack(side="left", padx=(5, 15))
        self._status_filter.bind("<<ComboboxSelected>>", self._apply_filter)

        tk.Label(
            filter_frame,
            text="Difficulty:",
            font=("Segoe UI", 9),
            bg=CONTENT_BG,
            fg="#666666",
        ).pack(side="left")

        self._diff_filter = ttk.Combobox(
            filter_frame,
            values=["All", "BEGINNER", "INTERMEDIATE", "ADVANCED"],
            state="readonly",
            width=14,
            font=("Segoe UI", 9),
        )
        self._diff_filter.set("All")
        self._diff_filter.pack(side="left", padx=5)
        self._diff_filter.bind("<<ComboboxSelected>>", self._apply_filter)

        # Course table
        self._table = CourseTable(
            self,
            on_select=self._on_course_selected,
            bg=CONTENT_BG,
        )
        self._table.pack(fill="both", expand=True, padx=20)

        # Action buttons
        btn_frame = tk.Frame(self, bg=CONTENT_BG, pady=10)
        btn_frame.pack(fill="x", padx=20)

        buttons = [
            ("➕ Add Course",    "#27ae60", "#ffffff", self._add_course),
            ("✏️ Edit",          "#3498db", "#ffffff", self._edit_course),
            ("🗑️ Delete",        "#e74c3c", "#ffffff", self._delete_course),
            ("✅ Publish",       "#1a3a5c", "#ffffff", self._publish_course),
            ("📦 Archive",       "#7f8c8d", "#ffffff", self._archive_course),
        ]

        for text, bg, fg, cmd in buttons:
            tk.Button(
                btn_frame,
                text=text,
                font=("Segoe UI", 9),
                bg=bg,
                fg=fg,
                activebackground=bg,
                relief="flat",
                cursor="hand2",
                padx=12,
                pady=5,
                command=cmd,
            ).pack(side="left", padx=(0, 5))

        # Status bar
        self._status_var = tk.StringVar(value="Ready")
        tk.Label(
            self,
            textvariable=self._status_var,
            font=("Segoe UI", 8),
            bg=CONTENT_BG,
            fg="#666666",
            anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 5))

    # ── Data ───────────────────────────────────────────────────────────────────

    def _load_courses(self):
        """Load all courses from the service."""
        try:
            service = self._services.get("course_service")
            if service is None:
                self._status_var.set("Course service unavailable")
                return

            self._all_courses = service.get_all_courses()
            self._apply_filter()
            self._status_var.set(
                f"Loaded {len(self._all_courses)} courses"
            )
        except Exception as e:
            show_error(self, "Error", f"Failed to load courses: {e}")

    def _apply_filter(self, event=None):
        """Filter the displayed courses."""
        status_filter = self._status_filter.get()
        diff_filter   = self._diff_filter.get()

        filtered = self._all_courses

        if status_filter != "All":
            filtered = [
                c for c in filtered
                if c.status.value == status_filter
            ]
        if diff_filter != "All":
            filtered = [
                c for c in filtered
                if c.difficulty.value == diff_filter
            ]

        self._table.load_courses(filtered)

    def _on_course_selected(self, course: Optional[Course]):
        """Update selected course reference."""
        self._selected = course

    # ── Actions ────────────────────────────────────────────────────────────────

    def _add_course(self):
        """Open add course dialog."""
        dialog = CourseFormDialog(self, "Add New Course")
        self.wait_window(dialog)

        if dialog.result:
            try:
                service = self._services["course_service"]
                service.create_course(dialog.result)
                show_info(
                    self, "Success",
                    f"Course '{dialog.result.code}' created successfully."
                )
                self._load_courses()
            except (ValidationError, Exception) as e:
                show_error(self, "Error", str(e))

    def _edit_course(self):
        """Open edit dialog for selected course."""
        if self._selected is None:
            show_info(self, "Select Course", "Please select a course to edit.")
            return

        dialog = CourseFormDialog(
            self, f"Edit Course — {self._selected.code}",
            course=self._selected
        )
        self.wait_window(dialog)

        if dialog.result:
            try:
                service = self._services["course_service"]
                service.update_course(dialog.result)
                show_info(self, "Success", "Course updated successfully.")
                self._load_courses()
            except Exception as e:
                show_error(self, "Error", str(e))

    def _delete_course(self):
        """Delete the selected course after confirmation."""
        if self._selected is None:
            show_info(self, "Select Course", "Please select a course to delete.")
            return

        if confirm(
            self, "Delete Course",
            f"Permanently delete '{self._selected.code} — "
            f"{self._selected.name}'?\n\n"
            f"This will also remove all enrollments for this course."
        ):
            try:
                service = self._services["course_service"]
                service.delete_course(self._selected.code)
                show_info(self, "Deleted", "Course deleted successfully.")
                self._selected = None
                self._load_courses()
            except Exception as e:
                show_error(self, "Error", str(e))

    def _publish_course(self):
        """Publish the selected course (DRAFT → PUBLISHED)."""
        if self._selected is None:
            show_info(self, "Select Course", "Please select a course to publish.")
            return

        if confirm(
            self, "Publish Course",
            f"Publish '{self._selected.code}'?\n"
            f"Learners will be able to enroll after publishing."
        ):
            try:
                service = self._services["course_service"]
                service.publish_course(self._selected.code)
                show_info(self, "Published", "Course published successfully.")
                self._load_courses()
            except Exception as e:
                show_error(self, "Error", str(e))

    def _archive_course(self):
        """Archive the selected course (PUBLISHED → ARCHIVED)."""
        if self._selected is None:
            show_info(self, "Select Course", "Please select a course to archive.")
            return

        if confirm(
            self, "Archive Course",
            f"Archive '{self._selected.code}'?\n"
            f"No new enrollments will be accepted."
        ):
            try:
                service = self._services["course_service"]
                service.archive_course(self._selected.code)
                show_info(self, "Archived", "Course archived successfully.")
                self._load_courses()
            except Exception as e:
                show_error(self, "Error", str(e))