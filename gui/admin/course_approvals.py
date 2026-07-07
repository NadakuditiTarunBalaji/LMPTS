"""
course_approvals.py
-------------------
Admin screen for reviewing and approving instructor course submissions.

Workflow:
    Instructor submits DRAFT course
         ↓
    Admin reviews here
         ↓
    APPROVE → course.status = PUBLISHED
    REJECT  → course stays DRAFT, instructor notified
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from core.user import User
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"
HEADER_COL = "#1a3a5c"


class CourseApprovalScreen(tk.Frame):
    """Admin screen for approving or rejecting course submissions."""

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user     = user
        self._services = services
        self._selected_submission = None
        self._build()
        self._load_submissions()

    def _build(self):
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame,
            text="Course Submission Review",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL,
        ).pack(side="left")
        tk.Button(
            title_frame, text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat",
            cursor="hand2", command=self._load_submissions,
        ).pack(side="right")

        tk.Label(
            self,
            text=(
                "Review courses submitted by instructors. "
                "Approved courses will be published and "
                "available to learners."
            ),
            font=("Segoe UI", 9),
            bg=CONTENT_BG, fg="#666666",
        ).pack(anchor="w", padx=20, pady=(0, 8))

        # Filter
        filter_frame = tk.Frame(self, bg=CONTENT_BG)
        filter_frame.pack(fill="x", padx=20, pady=(0, 8))
        self._filter_var = tk.StringVar(value="PENDING")
        for text, value in [
            ("Pending Review", "PENDING"),
            ("All",            "ALL"),
            ("Approved",       "APPROVED"),
            ("Rejected",       "REJECTED"),
        ]:
            ttk.Radiobutton(
                filter_frame, text=text,
                variable=self._filter_var, value=value,
                command=self._load_submissions,
            ).pack(side="left", padx=5)

        # Submissions table
        cols = ("id", "course", "instructor",
                "status", "submitted", "note")
        self._tree = ttk.Treeview(
            self, columns=cols,
            show="headings", selectmode="browse",
        )
        for col, hdr, w in [
            ("id",         "#",              40),
            ("course",     "Course Code",   110),
            ("instructor", "Instructor ID",  100),
            ("status",     "Status",         90),
            ("submitted",  "Submitted",      110),
            ("note",       "Instructor Note",200),
        ]:
            self._tree.heading(col, text=hdr)
            self._tree.column(col, width=w)

        self._tree.tag_configure("PENDING",  background="#fff8e1")
        self._tree.tag_configure("APPROVED", background="#e8f5e9")
        self._tree.tag_configure("REJECTED", background="#fce4ec")

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

        # Action panel
        right = tk.Frame(
            self, bg=CARD_BG, width=240, relief="flat", bd=1
        )
        right.pack(side="left", fill="y", padx=(5, 20))
        right.pack_propagate(False)

        tk.Label(
            right, text="Review Actions",
            font=("Segoe UI", 11, "bold"),
            bg=CARD_BG, fg=HEADER_COL, pady=12,
        ).pack(fill="x", padx=12)

        ttk.Separator(right, orient="horizontal").pack(
            fill="x", padx=12
        )

        # Course preview
        self._preview_text = tk.Text(
            right,
            font=("Segoe UI", 8),
            height=8, relief="flat",
            bg=CARD_BG, fg="#333333",
            state="disabled",
        )
        self._preview_text.pack(fill="x", padx=12, pady=8)

        ttk.Separator(right, orient="horizontal").pack(
            fill="x", padx=12
        )

        tk.Label(
            right, text="Admin Note:",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg="#333333",
        ).pack(anchor="w", padx=12, pady=(8, 2))

        self._admin_note = tk.Text(
            right,
            font=("Segoe UI", 9),
            height=4, width=26,
            relief="solid", bd=1,
        )
        self._admin_note.pack(padx=12)

        tk.Button(
            right,
            text="✅ Approve & Publish",
            font=("Segoe UI", 9, "bold"),
            bg="#27ae60", fg="#ffffff",
            relief="flat", cursor="hand2",
            pady=7, command=self._approve,
        ).pack(fill="x", padx=12, pady=(8, 3))

        tk.Button(
            right,
            text="❌ Reject Submission",
            font=("Segoe UI", 9),
            bg="#e74c3c", fg="#ffffff",
            relief="flat", cursor="hand2",
            pady=7, command=self._reject,
        ).pack(fill="x", padx=12, pady=3)

    def _load_submissions(self):
        """Load course submissions from database."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        try:
            db   = self._services.get("database")
            filt = self._filter_var.get()

            if db is None:
                return

            conn = db.get_connection()
            try:
                if filt == "ALL":
                    cursor = conn.execute(
                        """
                        SELECT * FROM course_submissions
                        ORDER BY submitted_at DESC
                        """
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM course_submissions
                        WHERE status = ?
                        ORDER BY submitted_at DESC
                        """,
                        (filt,)
                    )
                rows = cursor.fetchall()
            finally:
                conn.close()

            for row in rows:
                self._tree.insert(
                    "", "end",
                    iid=str(row["id"]),
                    values=(
                        row["id"],
                        row["course_code"],
                        row["instructor_id"],
                        row["status"],
                        str(row["submitted_at"])[:10],
                        row["instructor_note"] or "—",
                    ),
                    tags=(row["status"],),
                )

        except Exception as e:
            show_error(self, "Error", str(e))

    def _on_select(self, event=None):
        """Show course preview for selected submission."""
        sel = self._tree.selection()
        if not sel:
            return

        try:
            db   = self._services.get("database")
            conn = db.get_connection()
            try:
                cursor = conn.execute(
                    "SELECT * FROM course_submissions WHERE id = ?",
                    (int(sel[0]),)
                )
                row = cursor.fetchone()
            finally:
                conn.close()

            if row is None:
                return

            self._selected_submission = dict(row)

            # Get course details
            course_svc = self._services.get("course_service")
            course     = None
            if course_svc:
                course = course_svc.get_course(row["course_code"])

            preview = f"Course: {row['course_code']}\n"
            if course:
                preview += (
                    f"Name      : {course.name}\n"
                    f"Difficulty: {course.difficulty.value}\n"
                    f"Duration  : {course.duration}h\n"
                    f"Status    : {course.status.value}\n"
                    f"Description:\n{course.description}\n"
                )

            self._preview_text.config(state="normal")
            self._preview_text.delete("1.0", "end")
            self._preview_text.insert("1.0", preview)
            self._preview_text.config(state="disabled")

        except Exception as e:
            show_error(self, "Error", str(e))

    def _approve(self):
        """Approve the submission and publish the course."""
        if not self._selected_submission:
            show_info(self, "Select", "Please select a submission.")
            return

        course_code = self._selected_submission["course_code"]
        note        = self._admin_note.get("1.0", "end-1c").strip()

        if not confirm(
            self, "Approve Course",
            f"Approve and PUBLISH course '{course_code}'?\n\n"
            f"Learners will be able to enroll immediately."
        ):
            return

        try:
            # Publish the course
            course_svc = self._services["course_service"]
            course_svc.publish_course(course_code)

            # Update submission status
            db  = self._services["database"]
            now = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat()
            with db.transaction() as conn:
                conn.execute(
                    """
                    UPDATE course_submissions
                    SET status = 'APPROVED',
                        admin_note = ?,
                        decided_at = ?
                    WHERE id = ?
                    """,
                    (
                        note,
                        now,
                        self._selected_submission["id"],
                    )
                )

            # Notify instructor
            notif_repo = self._services.get("notification_repo")
            if notif_repo:
                from core.notification import Notification
                notif_repo.create(Notification(
                    user_id = self._selected_submission["instructor_id"],
                    message = (
                        f"✅ Your course '{course_code}' has been "
                        f"APPROVED and published. "
                        f"Learners can now enroll."
                        + (f" Admin note: {note}" if note else "")
                    ),
                ))

            show_info(
                self, "Approved",
                f"Course '{course_code}' approved and published."
            )
            self._selected_submission = None
            self._admin_note.delete("1.0", "end")
            self._load_submissions()

        except Exception as e:
            show_error(self, "Error", str(e))

    def _reject(self):
        """Reject the submission."""
        if not self._selected_submission:
            show_info(self, "Select", "Please select a submission.")
            return

        course_code = self._selected_submission["course_code"]
        note        = self._admin_note.get("1.0", "end-1c").strip()

        if not note:
            show_error(
                self, "Note Required",
                "Please provide a rejection reason for the instructor."
            )
            return

        if not confirm(
            self, "Reject Submission",
            f"Reject course '{course_code}'?\n\n"
            f"The instructor will be notified with your feedback."
        ):
            return

        try:
            db  = self._services["database"]
            now = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat()
            with db.transaction() as conn:
                conn.execute(
                    """
                    UPDATE course_submissions
                    SET status = 'REJECTED',
                        admin_note = ?,
                        decided_at = ?
                    WHERE id = ?
                    """,
                    (
                        note,
                        now,
                        self._selected_submission["id"],
                    )
                )

            # Notify instructor
            notif_repo = self._services.get("notification_repo")
            if notif_repo:
                from core.notification import Notification
                notif_repo.create(Notification(
                    user_id = self._selected_submission["instructor_id"],
                    message = (
                        f"❌ Your course '{course_code}' submission was "
                        f"rejected. Please revise and resubmit. "
                        f"Admin feedback: {note}"
                    ),
                ))

            show_info(
                self, "Rejected",
                f"Submission for '{course_code}' rejected. "
                f"Instructor has been notified."
            )
            self._selected_submission = None
            self._admin_note.delete("1.0", "end")
            self._load_submissions()

        except Exception as e:
            show_error(self, "Error", str(e))