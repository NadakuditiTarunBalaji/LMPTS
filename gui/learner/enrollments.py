"""
enrollments.py
--------------
Learner's enrollment management screen.
"""

import tkinter as tk
from tkinter import ttk
from core.user import User
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


class EnrollmentsScreen(tk.Frame):
    """
    Shows a learner's current and past enrollments.
    Allows starting, completing, and cancelling enrollments.
    """

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user       = user
        self._services   = services
        self._learner_id = None
        self._build()
        self._load_data()

    def _build(self):
        # Title
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame, text="My Enrollments",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(side="left")
        tk.Button(
            title_frame, text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat", cursor="hand2",
            command=self._load_data,
        ).pack(side="right")

        # Filter tabs
        filter_frame = tk.Frame(self, bg=CONTENT_BG)
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))
        self._filter_var = tk.StringVar(value="ALL")
        for text, value in [
            ("All", "ALL"),
            ("Active", "ACTIVE"),
            ("Completed", "COMPLETED"),
            ("Cancelled", "CANCELLED"),
        ]:
            ttk.Radiobutton(
                filter_frame, text=text,
                variable=self._filter_var, value=value,
                command=self._apply_filter,
            ).pack(side="left", padx=5)

        # Enrollments table
        cols = ("course", "status", "score", "enrolled", "completed")
        self._tree = ttk.Treeview(
            self, columns=cols, show="headings",
            selectmode="browse",
        )
        for col, header, width in [
            ("course",    "Course Code", 110),
            ("status",    "Status",       100),
            ("score",     "Score",         60),
            ("enrolled",  "Enrolled",     110),
            ("completed", "Completed",    110),
        ]:
            self._tree.heading(col, text=header)
            self._tree.column(col, width=width)

        scroll = ttk.Scrollbar(
            self, orient="vertical",
            command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scroll.set)

        self._tree.pack(side="left", fill="both",
                        expand=True, padx=(20, 0))
        scroll.pack(side="left", fill="y", pady=0)

        # Colour tags
        self._tree.tag_configure("COMPLETED",   background="#e8f5e9")
        self._tree.tag_configure("IN_PROGRESS", background="#fff8e1")
        self._tree.tag_configure("CANCELLED",   background="#fce4ec")
        self._tree.tag_configure("PENDING",     background="#fff3cd")

        # Actions
        btn_frame = tk.Frame(self, bg=CONTENT_BG, pady=10)
        btn_frame.pack(fill="x", padx=20)

        for text, colour, cmd in [
            ("▶ Start Course",      "#3498db", self._start_course),
            ("✅ Complete Course",   "#27ae60", self._complete_course),
            ("❌ Cancel Enrollment", "#e74c3c", self._cancel_enrollment),
        ]:
            tk.Button(
                btn_frame, text=text,
                font=("Segoe UI", 9),
                bg=colour, fg="#ffffff",
                relief="flat", cursor="hand2",
                padx=12, pady=5,
                command=cmd,
            ).pack(side="left", padx=(0, 5))

        self._all_enrollments    = []
        self._pending_by_course  = {}

    def _load_data(self):
        """Load learner ID, enrollments, and pending cancellation requests."""
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

            enrollment_svc = self._services.get("enrollment_service")
            if enrollment_svc:
                self._all_enrollments = (
                    enrollment_svc.get_learner_enrollments(
                        self._learner_id
                    )
                )

                from core.enums import CancellationRequestStatus
                requests = enrollment_svc.get_learner_cancellation_requests(
                    self._learner_id
                )
                self._pending_by_course = {
                    r.course_code: r for r in requests
                    if r.status == CancellationRequestStatus.PENDING
                }

            self._apply_filter()
        except Exception as e:
            show_error(self, "Error", str(e))

    def _apply_filter(self):
        """Filter displayed enrollments."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        filter_val = self._filter_var.get()
        filtered   = self._all_enrollments

        from core.enums import EnrollmentStatus

        if filter_val == "ACTIVE":
            filtered = [
                e for e in filtered
                if e.status in (
                    EnrollmentStatus.ENROLLED,
                    EnrollmentStatus.IN_PROGRESS,
                )
                and e.course_code not in self._pending_by_course
            ]
        elif filter_val == "COMPLETED":
            filtered = [
                e for e in filtered
                if e.status == EnrollmentStatus.COMPLETED
            ]
        elif filter_val == "CANCELLED":
            filtered = [
                e for e in filtered
                if e.status == EnrollmentStatus.CANCELLED
                or e.course_code in self._pending_by_course
            ]

        for e in filtered:
            is_pending = e.course_code in self._pending_by_course
            status_str = "Pending Approval" if is_pending else e.status.value
            tag        = "PENDING" if is_pending else e.status.value

            score_str = f"{e.score:.0f}" if e.score is not None else "—"
            enrolled_str  = str(e.enrolled_at)[:10]  if e.enrolled_at  else "—"
            completed_str = str(e.completed_at)[:10] if e.completed_at else "—"
            self._tree.insert(
                "", "end",
                iid=str(e.id),
                values=(
                    e.course_code,
                    status_str,
                    score_str,
                    enrolled_str,
                    completed_str,
                ),
                tags=(tag,),
            )

    def _get_selected_enrollment(self):
        """Return selected enrollment object."""
        selection = self._tree.selection()
        if not selection:
            show_info(self, "Select", "Please select an enrollment.")
            return None
        eid = int(selection[0])
        for e in self._all_enrollments:
            if e.id == eid:
                return e
        return None

    def _start_course(self):
        e = self._get_selected_enrollment()
        if e is None:
            return
        try:
            enrollment_svc = self._services["enrollment_service"]
            enrollment_svc.start_enrollment(
                self._learner_id, e.course_code
            )
            show_info(self, "Started", f"Started '{e.course_code}'.")
            self._load_data()
        except Exception as ex:
            show_error(self, "Error", str(ex))

    def _complete_course(self):
        e = self._get_selected_enrollment()
        if e is None:
            return

        from tkinter import simpledialog
        score_str = simpledialog.askstring(
            "Score", "Enter final score (0-100):", parent=self
        )
        if score_str is None:
            return
        try:
            score = float(score_str)
            enrollment_svc = self._services["enrollment_service"]
            enrollment_svc.complete_enrollment(
                self._learner_id, e.course_code, score
            )
            show_info(self, "Completed",
                      f"Completed '{e.course_code}' with score {score}.")
            self._load_data()
        except Exception as ex:
            show_error(self, "Error", str(ex))

    def _cancel_enrollment(self):
        e = self._get_selected_enrollment()
        if e is None:
            return

        if e.course_code in self._pending_by_course:
            show_info(
                self, "Already Pending",
                f"A cancellation request for '{e.course_code}' "
                f"is already pending instructor review."
            )
            return

        # Check if already IN_PROGRESS or COMPLETED
        from core.enums import EnrollmentStatus
        if e.status != EnrollmentStatus.ENROLLED:
            show_error(
                self, "Cannot Cancel",
                f"Can only request cancellation before starting the course. "
                f"Current status: {e.status.value}"
            )
            return

        if confirm(self, "Request Course Cancellation",
                   f"Request cancellation of '{e.course_code}'?\n\n"
                   f"The instructor will review your request."):
            from tkinter import simpledialog
            reason = simpledialog.askstring(
                "Cancellation Reason",
                "Why do you want to cancel this course? (optional):",
                parent=self
            )

            try:
                enrollment_svc = self._services["enrollment_service"]
                request = enrollment_svc.request_cancellation(
                    self._learner_id, e.course_code,
                    learner_note=reason or ""
                )
                show_info(
                    self, "Request Submitted",
                    f"Your cancellation request for '{e.course_code}' "
                    f"has been submitted.\nThe instructor will review it shortly."
                )
                self._load_data()
            except Exception as ex:
                show_error(self, "Error", str(ex))