"""
cancellation_review.py
---------------------
Instructor course cancellation request review screen.

Instructor can:
    - View all pending cancellation requests
    - See learner's reason for cancellation
    - Approve (unenroll learner) or Reject (keep enrollment)
    - Add decision notes
"""

import tkinter as tk
from tkinter import ttk, simpledialog
from typing import Optional, List

from core.user import User
from core.cancellation_request import CancellationRequest
from core.enums import CancellationRequestStatus
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG = "#ffffff"
HEADER_COL = "#1a3a5c"


class CancellationReviewScreen(tk.Frame):
    """
    Instructor interface for reviewing course cancellation requests.
    """

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user = user
        self._services = services
        self._selected: Optional[CancellationRequest] = None
        self._instructor_id = None
        self._all_requests = []
        self._build()
        self._load_instructor_id()
        self._load_requests()

    def _build(self):
        # Title
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame,
            text="Course Cancellation Requests",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG,
            fg=HEADER_COL,
        ).pack(side="left")
        tk.Button(
            title_frame,
            text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG,
            relief="flat",
            cursor="hand2",
            command=self._load_requests,
        ).pack(side="right")

        tk.Label(
            self,
            text="Review learner cancellation requests and approve or reject them.",
            font=("Segoe UI", 9),
            bg=CONTENT_BG,
            fg="#666666",
        ).pack(anchor="w", padx=20, pady=(0, 8))

        # Filter tabs
        filter_frame = tk.Frame(self, bg=CONTENT_BG)
        filter_frame.pack(fill="x", padx=20, pady=(0, 8))
        self._filter_var = tk.StringVar(value="PENDING")
        for text, value in [
            ("Pending Review", "PENDING"),
            ("All Requests", "ALL"),
            ("My Decisions", "REVIEWED"),
        ]:
            ttk.Radiobutton(
                filter_frame,
                text=text,
                variable=self._filter_var,
                value=value,
                command=self._load_requests,
            ).pack(side="left", padx=5)

        # Split: list top, details bottom
        pane = tk.PanedWindow(
            self,
            orient="vertical",
            bg=CONTENT_BG,
            sashwidth=4,
        )
        pane.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # ── Top: Request list ──────────────────────────────────────────────
        top_frame = tk.Frame(pane, bg=CONTENT_BG)

        cols = ("id", "learner", "course", "status", "submitted")
        self._tree = ttk.Treeview(
            top_frame,
            columns=cols,
            show="headings",
            selectmode="browse",
        )
        for col, hdr, w in [
            ("id", "#", 40),
            ("learner", "Learner", 100),
            ("course", "Course", 100),
            ("status", "Status", 90),
            ("submitted", "Submitted", 130),
        ]:
            self._tree.heading(col, text=hdr)
            self._tree.column(col, width=w)

        scroll_v = ttk.Scrollbar(
            top_frame, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scroll_v.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll_v.pack(side="right", fill="y")

        self._tree.tag_configure("PENDING", background="#fff8e1")
        self._tree.tag_configure("APPROVED", background="#e8f5e9")
        self._tree.tag_configure("REJECTED", background="#fce4ec")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        pane.add(top_frame, height=150)

        # ── Bottom: Details panel ──────────────────────────────────────────
        bottom_frame = tk.Frame(pane, bg=CARD_BG)

        self._detail_text = tk.Text(
            bottom_frame, height=15, width=60, bg=CARD_BG, fg="#333333"
        )
        self._detail_text.pack(fill="both", expand=True, padx=10, pady=10)
        self._detail_text.config(state="disabled")

        pane.add(bottom_frame, height=200)

        # ── Action buttons ──────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=CONTENT_BG, pady=10)
        btn_frame.pack(fill="x", padx=20)

        for text, colour, cmd in [
            ("✅ Approve", "#27ae60", self._approve),
            ("❌ Reject", "#e74c3c", self._reject),
            ("🔙 Withdraw", "#95a5a6", self._withdraw),
        ]:
            tk.Button(
                btn_frame,
                text=text,
                font=("Segoe UI", 9),
                bg=colour,
                fg="#ffffff",
                relief="flat",
                cursor="hand2",
                padx=12,
                pady=5,
                command=cmd,
            ).pack(side="left", padx=(0, 5))

    def _load_instructor_id(self):
        """Load instructor ID from current user."""
        self._instructor_id = self._user.id

    def _load_requests(self):
        """Load cancellation requests from the service."""
        try:
            enrollment_svc = self._services.get("enrollment_service")
            if enrollment_svc:
                self._all_requests = (
                    enrollment_svc.get_pending_cancellation_requests()
                )
            self._apply_filter()
        except Exception as e:
            show_error(self, "Error", str(e))

    def _apply_filter(self):
        """Filter displayed requests."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        filter_val = self._filter_var.get()
        filtered = self._all_requests

        if filter_val == "PENDING":
            filtered = [
                r
                for r in filtered
                if r.status == CancellationRequestStatus.PENDING
            ]
        elif filter_val == "REVIEWED":
            filtered = [
                r
                for r in filtered
                if r.status != CancellationRequestStatus.PENDING
                and r.instructor_id == self._instructor_id
            ]

        for r in filtered:
            submitted_str = str(r.submitted_at)[:10] if r.submitted_at else "—"
            self._tree.insert(
                "",
                "end",
                iid=str(r.id),
                values=(
                    r.id,
                    r.learner_id,
                    r.course_code,
                    r.status.value,
                    submitted_str,
                ),
                tags=(r.status.value,),
            )

    def _on_select(self, event):
        """Handle request selection."""
        selection = self._tree.selection()
        if not selection:
            self._selected = None
            return

        request_id = int(selection[0])
        for r in self._all_requests:
            if r.id == request_id:
                self._selected = r
                self._display_details()
                return

    def _display_details(self):
        """Display selected request details."""
        if self._selected is None:
            return

        details = (
            f"ID: {self._selected.id}\n"
            f"Learner: {self._selected.learner_id}\n"
            f"Course: {self._selected.course_code}\n"
            f"Status: {self._selected.status.value}\n"
            f"Submitted: {self._selected.submitted_at}\n"
            f"\n--- Learner's Reason ---\n"
            f"{self._selected.learner_note or '(No reason provided)'}\n"
        )

        if self._selected.reviewed_by_instructor_at:
            details += (
                f"\n--- Instructor Decision ---\n"
                f"Decided by: {self._selected.instructor_id}\n"
                f"Decision: {self._selected.status.value}\n"
                f"Notes: {self._selected.instructor_note or '(No notes)'}\n"
            )

        self._detail_text.config(state="normal")
        self._detail_text.delete("1.0", "end")
        self._detail_text.insert("1.0", details)
        self._detail_text.config(state="disabled")

    def _approve(self):
        """Approve the selected cancellation request."""
        if self._selected is None:
            show_info(self, "Select", "Please select a request.")
            return

        if self._selected.status != CancellationRequestStatus.PENDING:
            show_error(
                self,
                "Invalid Status",
                f"Can only approve PENDING requests. "
                f"Current status: {self._selected.status.value}",
            )
            return

        notes = simpledialog.askstring(
            "Decision Notes",
            "Add optional notes for your decision:",
            parent=self,
        )

        if confirm(
            self,
            "Approve Cancellation",
            f"Approve cancellation for learner {self._selected.learner_id} "
            f"in '{self._selected.course_code}'?\n\n"
            f"The learner will be unenrolled and can re-enroll if desired.",
        ):
            try:
                enrollment_svc = self._services["enrollment_service"]
                enrollment_svc.approve_cancellation(
                    self._selected.id,
                    instructor_id=self._instructor_id,
                    instructor_note=notes or "",
                )
                show_info(
                    self,
                    "Approved",
                    f"Cancellation request approved. "
                    f"Learner {self._selected.learner_id} has been unenrolled.",
                )
                self._load_requests()
            except Exception as ex:
                show_error(self, "Error", str(ex))

    def _reject(self):
        """Reject the selected cancellation request."""
        if self._selected is None:
            show_info(self, "Select", "Please select a request.")
            return

        if self._selected.status != CancellationRequestStatus.PENDING:
            show_error(
                self,
                "Invalid Status",
                f"Can only reject PENDING requests. "
                f"Current status: {self._selected.status.value}",
            )
            return

        notes = simpledialog.askstring(
            "Decision Notes",
            "Why are you rejecting this request?",
            parent=self,
        )

        if confirm(
            self,
            "Reject Cancellation",
            f"Reject cancellation for learner {self._selected.learner_id} "
            f"in '{self._selected.course_code}'?\n\n"
            f"The learner will remain enrolled.",
        ):
            try:
                enrollment_svc = self._services["enrollment_service"]
                enrollment_svc.reject_cancellation(
                    self._selected.id,
                    instructor_id=self._instructor_id,
                    instructor_note=notes or "",
                )
                show_info(
                    self,
                    "Rejected",
                    f"Cancellation request rejected. "
                    f"Learner remains enrolled.",
                )
                self._load_requests()
            except Exception as ex:
                show_error(self, "Error", str(ex))

    def _withdraw(self):
        """Mark the selected request as withdrawn."""
        if self._selected is None:
            show_info(self, "Select", "Please select a request.")
            return

        if self._selected.status != CancellationRequestStatus.PENDING:
            show_error(
                self,
                "Invalid Status",
                "Can only withdraw PENDING requests.",
            )
            return

        if confirm(
            self, "Withdraw Request",
            f"Mark this cancellation request as withdrawn?"
        ):
            try:
                # Create a temporary object to hold the withdrawal
                self._selected.status = CancellationRequestStatus.WITHDRAWN
                enrollment_svc = self._services["enrollment_service"]
                # Get cancellation request repo to update
                from repository.cancellation_request_repo import (
                    SQLiteCancellationRequestRepository,
                )

                db = self._services.get("database")
                repo = SQLiteCancellationRequestRepository(db)
                repo.update_request(self._selected)
                show_info(self, "Withdrawn", "Request marked as withdrawn.")
                self._load_requests()
            except Exception as ex:
                show_error(self, "Error", str(ex))
