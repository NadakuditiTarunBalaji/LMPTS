"""
course_manager.py
-----------------
Instructor course creation, editing, and submission for admin review.

Workflow:
    1. Instructor creates course (DRAFT)
    2. Instructor edits course details
    3. Instructor submits for admin review
    4. Admin approves (PUBLISHED) or rejects (back to DRAFT)
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from core.course import Course
from core.enums import DifficultyLevel, CourseStatus
from core.user import User
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"
HEADER_COL = "#1a3a5c"


class CourseFormDialog(tk.Toplevel):
    """Form dialog for creating or editing a course."""

    def __init__(
        self, parent,
        title: str,
        course: Optional[Course] = None
    ):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x500")
        self.resizable(False, False)
        self.configure(bg=CARD_BG)
        self.grab_set()
        self.result: Optional[Course] = None
        self._existing = course
        self._build()
        if course:
            self._populate(course)

        px = parent.winfo_rootx() + (parent.winfo_width()  - 500) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 500) // 2
        self.geometry(f"500x500+{px}+{py}")

    def _build(self):
        title_bar = tk.Frame(self, bg=HEADER_COL, pady=10)
        title_bar.pack(fill="x")
        tk.Label(
            title_bar, text=self.title(),
            font=("Segoe UI", 11, "bold"),
            bg=HEADER_COL, fg="#ffffff",
        ).pack(padx=15)

        form = tk.Frame(self, bg=CARD_BG, padx=25, pady=15)
        form.pack(fill="both", expand=True)
        form.columnconfigure(0, weight=1)

        def field(label: str, row: int,
                  show: str = "") -> ttk.Entry:
            tk.Label(
                form, text=label,
                font=("Segoe UI", 9, "bold"),
                bg=CARD_BG, fg="#333333",
            ).grid(row=row, column=0, sticky="w", pady=(8, 1))
            e = ttk.Entry(
                form, width=36,
                font=("Segoe UI", 10), show=show
            )
            e.grid(row=row + 1, column=0, sticky="ew", ipady=3)
            return e

        self._code  = field("Course Code *", 0)
        self._name  = field("Course Name *", 2)

        tk.Label(
            form, text="Description",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg="#333333",
        ).grid(row=4, column=0, sticky="w", pady=(8, 1))
        self._desc = tk.Text(
            form, width=36, height=3,
            font=("Segoe UI", 10), relief="solid", bd=1,
        )
        self._desc.grid(row=5, column=0, sticky="ew")

        self._duration = field("Duration (hours) *", 6)

        tk.Label(
            form, text="Difficulty *",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg="#333333",
        ).grid(row=8, column=0, sticky="w", pady=(8, 1))
        self._diff_var = tk.StringVar(value="BEGINNER")
        diff_row = tk.Frame(form, bg=CARD_BG)
        diff_row.grid(row=9, column=0, sticky="w")
        for lvl in DifficultyLevel:
            ttk.Radiobutton(
                diff_row, text=lvl.value,
                variable=self._diff_var, value=lvl.value,
            ).pack(side="left", padx=5)

        btn_frame = tk.Frame(self, bg=CARD_BG, pady=12, padx=25)
        btn_frame.pack(fill="x")

        tk.Button(
            btn_frame, text="Cancel",
            font=("Segoe UI", 9),
            bg="#e0e0e0", relief="flat",
            width=10, command=self.destroy,
        ).pack(side="right", padx=(5, 0))

        tk.Button(
            btn_frame, text="Save Course",
            font=("Segoe UI", 9, "bold"),
            bg=HEADER_COL, fg="#ffffff",
            relief="flat", width=12,
            command=self._save,
        ).pack(side="right")

    def _populate(self, c: Course):
        self._code.insert(0, c.code)
        self._code.config(state="disabled")
        self._name.insert(0, c.name)
        self._desc.insert("1.0", c.description)
        self._duration.insert(0, str(c.duration))
        self._diff_var.set(c.difficulty.value)

    def _save(self):
        code     = self._code.get().strip()
        name     = self._name.get().strip()
        desc     = self._desc.get("1.0", "end-1c").strip()
        dur_str  = self._duration.get().strip()
        diff     = self._diff_var.get()

        if not code:
            show_error(self, "Error", "Course code required.")
            return
        if not name:
            show_error(self, "Error", "Course name required.")
            return
        if not dur_str.isdigit() or int(dur_str) <= 0:
            show_error(self, "Error", "Duration must be > 0.")
            return

        self.result = Course(
            code        = code,
            name        = name,
            description = desc,
            difficulty  = DifficultyLevel(diff),
            duration    = int(dur_str),
            status      = (
                self._existing.status
                if self._existing else CourseStatus.DRAFT
            ),
        )
        self.destroy()


class InstructorCourseManager(tk.Frame):
    """
    Instructor course management screen.

    Features:
        - View all courses in the system
        - Create new course (saved as DRAFT)
        - Edit course details
        - Submit course for admin review
        - View submission status (PENDING / APPROVED / REJECTED)
    """

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user     = user
        self._services = services
        self._selected: Optional[Course] = None
        self._all_courses = []
        self._build()
        self._load_courses()

    def _build(self):
        # Title
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame, text="My Courses",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL,
        ).pack(side="left")
        tk.Button(
            title_frame, text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat",
            cursor="hand2", command=self._load_courses,
        ).pack(side="right")

        # Filter
        filter_frame = tk.Frame(self, bg=CONTENT_BG)
        filter_frame.pack(fill="x", padx=20, pady=(0, 8))

        tk.Label(
            filter_frame, text="Filter:",
            font=("Segoe UI", 9), bg=CONTENT_BG, fg="#666666",
        ).pack(side="left")
        self._filter_var = tk.StringVar(value="All")
        ttk.Combobox(
            filter_frame,
            textvariable=self._filter_var,
            values=["All", "DRAFT", "PUBLISHED", "ARCHIVED"],
            state="readonly", width=12,
        ).pack(side="left", padx=5)
        self._filter_var.trace("w", lambda *a: self._apply_filter())

        # Course table
        cols = ("code", "name", "difficulty",
                "duration", "status", "submission")
        self._tree = ttk.Treeview(
            self, columns=cols, show="headings",
            selectmode="browse",
        )
        for col, hdr, width in [
            ("code",       "Code",        80),
            ("name",       "Name",       200),
            ("difficulty", "Difficulty",  100),
            ("duration",   "Hours",        60),
            ("status",     "Status",       90),
            ("submission", "Submission",   110),
        ]:
            self._tree.heading(col, text=hdr)
            self._tree.column(col, width=width)

        self._tree.tag_configure("PUBLISHED", background="#e8f5e9")
        self._tree.tag_configure("DRAFT",     background="#fff8e1")
        self._tree.tag_configure("ARCHIVED",  background="#fce4ec")

        scroll = ttk.Scrollbar(
            self, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(
            side="left", fill="both",
            expand=True, padx=(20, 0)
        )
        scroll.pack(side="left", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # Action buttons
        btn_frame = tk.Frame(self, bg=CONTENT_BG, pady=10)
        btn_frame.pack(fill="x", padx=20)

        for text, colour, cmd in [
            ("➕ Create Course",        "#27ae60", self._create_course),
            ("✏️ Edit Course",           "#3498db", self._edit_course),
            ("📤 Submit for Review",    HEADER_COL, self._submit_for_review),
            ("🗑️ Delete Draft",         "#e74c3c", self._delete_course),
        ]:
            tk.Button(
                btn_frame, text=text,
                font=("Segoe UI", 9),
                bg=colour, fg="#ffffff",
                relief="flat", cursor="hand2",
                padx=10, pady=5, command=cmd,
            ).pack(side="left", padx=(0, 5))

        # Status bar
        self._status_var = tk.StringVar(value="Ready")
        tk.Label(
            self,
            textvariable=self._status_var,
            font=("Segoe UI", 8),
            bg=CONTENT_BG, fg="#888888", anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 5))

    def _load_courses(self):
        """Load all courses from service."""
        try:
            svc = self._services.get("course_service")
            if svc is None:
                return
            self._all_courses = svc.get_all_courses()

            # Get submission statuses
            db   = self._services.get("database")
            self._submission_status = {}
            if db:
                conn = db.get_connection()
                try:
                    cursor = conn.execute(
                        """
                        SELECT course_code, status
                        FROM course_submissions
                        ORDER BY submitted_at DESC
                        """
                    )
                    seen = set()
                    for row in cursor.fetchall():
                        if row["course_code"] not in seen:
                            self._submission_status[
                                row["course_code"]
                            ] = row["status"]
                            seen.add(row["course_code"])
                finally:
                    conn.close()

            self._apply_filter()
            self._status_var.set(
                f"Loaded {len(self._all_courses)} courses"
            )
        except Exception as e:
            show_error(self, "Error", str(e))

    def _apply_filter(self):
        """Apply status filter to course list."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        filt = self._filter_var.get()
        filtered = (
            self._all_courses if filt == "All"
            else [c for c in self._all_courses
                  if c.status.value == filt]
        )

        for course in filtered:
            sub_status = self._submission_status.get(
                course.code, "—"
            )
            self._tree.insert(
                "", "end",
                iid=course.code,
                values=(
                    course.code,
                    course.name,
                    course.difficulty.value,
                    f"{course.duration}h",
                    course.status.value,
                    sub_status,
                ),
                tags=(course.status.value,),
            )

    def _on_select(self, event=None):
        sel = self._tree.selection()
        if not sel:
            return
        code = sel[0]
        self._selected = next(
            (c for c in self._all_courses if c.code == code), None
        )

    def _create_course(self):
        dialog = CourseFormDialog(self, "Create New Course")
        self.wait_window(dialog)
        if dialog.result:
            try:
                svc = self._services["course_service"]
                svc.create_course(dialog.result)
                show_info(self, "Created",
                          f"Course '{dialog.result.code}' created as DRAFT.")
                self._load_courses()
            except Exception as e:
                show_error(self, "Error", str(e))

    def _edit_course(self):
        if self._selected is None:
            show_info(self, "Select", "Please select a course to edit.")
            return
        if self._selected.status != CourseStatus.DRAFT:
            show_error(
                self, "Cannot Edit",
                "Only DRAFT courses can be edited by instructors."
            )
            return

        dialog = CourseFormDialog(
            self,
            f"Edit Course — {self._selected.code}",
            course=self._selected,
        )
        self.wait_window(dialog)
        if dialog.result:
            try:
                svc = self._services["course_service"]
                svc.update_course(dialog.result)
                show_info(self, "Updated", "Course updated successfully.")
                self._load_courses()
            except Exception as e:
                show_error(self, "Error", str(e))

    def _submit_for_review(self):
        """Submit a DRAFT course for admin review."""
        if self._selected is None:
            show_info(self, "Select", "Please select a course to submit.")
            return
        if self._selected.status != CourseStatus.DRAFT:
            show_error(
                self, "Cannot Submit",
                "Only DRAFT courses can be submitted for review."
            )
            return

        sub_status = self._submission_status.get(
            self._selected.code
        )
        if sub_status == "PENDING":
            show_info(
                self, "Already Submitted",
                f"'{self._selected.code}' is already pending admin review."
            )
            return

        if not confirm(
            self, "Submit for Review",
            f"Submit '{self._selected.code} — {self._selected.name}' "
            f"for administrator review?\n\n"
            f"The admin will review and publish or reject the course."
        ):
            return

        try:
            db  = self._services.get("database")
            now = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat()

            with db.transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO course_submissions
                        (course_code, instructor_id, status,
                         instructor_note, submitted_at)
                    VALUES (?, ?, 'PENDING', '', ?)
                    """,
                    (self._selected.code, self._user.id, now)
                )

            # Notify admins
            notif_repo = self._services.get("notification_repo")
            if notif_repo:
                user_repo = self._services.get("user_repo")
                from core.enums import UserRole
                admins = user_repo.find_by_role(UserRole.ADMIN)
                for admin in admins:
                    notif_repo.create(__import__(
                        "core.notification", fromlist=["Notification"]
                    ).Notification(
                        user_id = admin.id,
                        message = (
                            f"Instructor '{self._user.username}' submitted "
                            f"course '{self._selected.code}' for review."
                        ),
                    ))

            show_info(
                self, "Submitted",
                f"Course '{self._selected.code}' submitted for admin review."
            )
            self._load_courses()

        except Exception as e:
            show_error(self, "Error", str(e))

    def _delete_course(self):
        if self._selected is None:
            show_info(self, "Select", "Please select a course to delete.")
            return
        if self._selected.status != CourseStatus.DRAFT:
            show_error(
                self, "Cannot Delete",
                "Only DRAFT courses can be deleted by instructors."
            )
            return

        if confirm(
            self, "Delete Course",
            f"Delete DRAFT course '{self._selected.code}'?"
        ):
            try:
                svc = self._services["course_service"]
                svc.delete_course(self._selected.code)
                show_info(self, "Deleted", "Course deleted.")
                self._selected = None
                self._load_courses()
            except Exception as e:
                show_error(self, "Error", str(e))