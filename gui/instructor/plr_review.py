"""
plr_review.py
-------------
Instructor Prior Learning Request review screen.

Instructor can:
    - View all pending PLR requests
    - Review evidence description
    - Recommend: APPROVE / REJECT / INFO_REQUESTED
    - Add review notes
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from core.user import User
from core.prior_learning_request import PriorLearningRequest, PLRStatus
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"
HEADER_COL = "#1a3a5c"


class PLRReviewScreen(tk.Frame):
    """
    Instructor interface for reviewing Prior Learning Requests.
    """

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user     = user
        self._services = services
        self._selected: Optional[PriorLearningRequest] = None
        self._build()
        self._load_requests()

    def _build(self):
        # Title
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame,
            text="Prior Learning Request Review",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL,
        ).pack(side="left")
        tk.Button(
            title_frame, text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat",
            cursor="hand2", command=self._load_requests,
        ).pack(side="right")

        tk.Label(
            self,
            text="Review learner evidence and provide your recommendation "
                 "to the administrator.",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, fg="#666666",
        ).pack(anchor="w", padx=20, pady=(0, 8))

        # Filter tabs
        filter_frame = tk.Frame(self, bg=CONTENT_BG)
        filter_frame.pack(fill="x", padx=20, pady=(0, 8))
        self._filter_var = tk.StringVar(value="PENDING")
        for text, value in [
            ("Pending Review",     "PENDING"),
            ("All Requests",       "ALL"),
            ("My Reviews",         "REVIEWED"),
        ]:
            ttk.Radiobutton(
                filter_frame, text=text,
                variable=self._filter_var, value=value,
                command=self._load_requests,
            ).pack(side="left", padx=5)

        # Split: list top, details bottom
        pane = tk.PanedWindow(
            self, orient="vertical",
            bg=CONTENT_BG, sashwidth=4,
        )
        pane.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # ── Top: Request list ───────────────────────────────────────────────
        top_frame = tk.Frame(pane, bg=CONTENT_BG)

        cols = ("id", "learner", "course",
                "pathway", "platform", "score", "status")
        self._tree = ttk.Treeview(
            top_frame, columns=cols,
            show="headings", selectmode="browse",
        )
        for col, hdr, w in [
            ("id",       "#",          40),
            ("learner",  "Learner ID", 80),
            ("course",   "Course",     90),
            ("pathway",  "Pathway",    90),
            ("platform", "Platform",  120),
            ("score",    "Ext Score",  80),
            ("status",   "Status",    110),
        ]:
            self._tree.heading(col, text=hdr)
            self._tree.column(col, width=w)

        self._tree.tag_configure(
            "PENDING",             background="#fff8e1"
        )
        self._tree.tag_configure(
            "INSTRUCTOR_REVIEWED", background="#e3f2fd"
        )
        self._tree.tag_configure(
            "APPROVED",            background="#e8f5e9"
        )
        self._tree.tag_configure(
            "REJECTED",            background="#fce4ec"
        )

        ts = ttk.Scrollbar(
            top_frame, orient="vertical",
            command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=ts.set)
        self._tree.pack(side="left", fill="both", expand=True)
        ts.pack(side="right", fill="y")
        self._tree.bind(
            "<<TreeviewSelect>>", self._on_request_selected
        )
        pane.add(top_frame, minsize=180)

        # ── Bottom: Details + Review form ───────────────────────────────────
        bottom_frame = tk.Frame(pane, bg=CONTENT_BG)
        pane.add(bottom_frame, minsize=220)

        # Left: evidence display
        evidence_frame = tk.LabelFrame(
            bottom_frame,
            text="  Evidence / Description",
            font=("Segoe UI", 9, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL, relief="flat",
        )
        evidence_frame.pack(
            side="left", fill="both",
            expand=True, padx=(0, 8)
        )

        self._evidence_text = tk.Text(
            evidence_frame,
            font=("Segoe UI", 9),
            bg=CARD_BG, fg="#333333",
            height=8, relief="flat",
            state="disabled", wrap="word",
        )
        self._evidence_text.pack(
            fill="both", expand=True, padx=5, pady=5
        )

        # Right: review form
        review_frame = tk.LabelFrame(
            bottom_frame,
            text="  My Recommendation",
            font=("Segoe UI", 9, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL, relief="flat",
        )
        review_frame.pack(side="left", fill="y", ipadx=10)

        tk.Label(
            review_frame,
            text="Recommendation:",
            font=("Segoe UI", 9, "bold"),
            bg=CONTENT_BG, fg="#333333",
        ).pack(anchor="w", padx=10, pady=(8, 3))

        self._recommendation_var = tk.StringVar(value="APPROVE")
        for text, value, colour in [
            ("✅ Recommend Approve",            "APPROVE",        "#27ae60"),
            ("❌ Recommend Reject",             "REJECT",         "#e74c3c"),
            ("ℹ️ Request More Information",     "INFO_REQUESTED", "#e67e22"),
        ]:
            tk.Radiobutton(
                review_frame,
                text=text,
                variable=self._recommendation_var,
                value=value,
                font=("Segoe UI", 9),
                bg=CONTENT_BG,
                fg=colour,
                activebackground=CONTENT_BG,
                selectcolor=CONTENT_BG,
            ).pack(anchor="w", padx=10, pady=2)

        tk.Label(
            review_frame,
            text="Review Notes:",
            font=("Segoe UI", 9, "bold"),
            bg=CONTENT_BG, fg="#333333",
        ).pack(anchor="w", padx=10, pady=(8, 3))

        self._note_text = tk.Text(
            review_frame,
            font=("Segoe UI", 9),
            height=4, width=28,
            relief="solid", bd=1,
        )
        self._note_text.pack(padx=10)

        tk.Button(
            review_frame,
            text="📤 Submit Review",
            font=("Segoe UI", 9, "bold"),
            bg=HEADER_COL, fg="#ffffff",
            relief="flat", cursor="hand2",
            pady=6,
            command=self._submit_review,
        ).pack(fill="x", padx=10, pady=10)

    # ── Data ───────────────────────────────────────────────────────────────────

    def _load_requests(self):
        """Load PLR requests based on filter."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        try:
            plr_svc = self._services.get("prior_learning_service")
            if plr_svc is None:
                return

            filt = self._filter_var.get()
            if filt == "PENDING":
                requests = plr_svc.get_pending_instructor_review()
            elif filt == "REVIEWED":
                all_r = plr_svc.get_all_requests()
                requests = [
                    r for r in all_r
                    if r.instructor_id == self._user.id
                ]
            else:
                requests = plr_svc.get_all_requests()

            for req in requests:
                self._tree.insert(
                    "", "end",
                    iid=str(req.id),
                    values=(
                        req.id,
                        req.learner_id,
                        req.course_code,
                        req.pathway,
                        req.external_platform or "—",
                        (f"{req.external_score:.0f}"
                         if req.external_score else "—"),
                        req.status,
                    ),
                    tags=(req.status,),
                )

        except Exception as e:
            show_error(self, "Error", str(e))

    def _on_request_selected(self, event=None):
        """Display evidence for selected request."""
        sel = self._tree.selection()
        if not sel:
            return

        req_id = int(sel[0])

        try:
            plr_repo = self._services.get("plr_repo")
            if plr_repo is None:
                return

            req = plr_repo.get_request(req_id)
            if req is None:
                return

            self._selected = req

            # Display evidence
            text = (
                f"Request ID     : {req.id}\n"
                f"Learner ID     : {req.learner_id}\n"
                f"Course         : {req.course_code}\n"
                f"Pathway        : {req.pathway}\n"
                f"Platform       : {req.external_platform or 'Not specified'}\n"
                f"External Score : "
                f"{req.external_score if req.external_score else 'Not provided'}\n"
                f"Submitted      : {str(req.submitted_at)[:16]}\n"
                f"Status         : {req.status}\n"
                f"\nEvidence Description:\n"
                f"{'─' * 40}\n"
                f"{req.evidence_description}\n"
            )

            if req.instructor_note:
                text += (
                    f"\nInstructor Note (previous):\n"
                    f"{'─' * 40}\n"
                    f"{req.instructor_note}\n"
                )

            if req.admin_note:
                text += (
                    f"\nAdmin Note:\n"
                    f"{'─' * 40}\n"
                    f"{req.admin_note}\n"
                )

            self._evidence_text.config(state="normal")
            self._evidence_text.delete("1.0", "end")
            self._evidence_text.insert("1.0", text)
            self._evidence_text.config(state="disabled")

        except Exception as e:
            show_error(self, "Error", str(e))

    def _submit_review(self):
        """Submit instructor recommendation."""
        if self._selected is None:
            show_info(self, "Select", "Please select a request to review.")
            return

        if self._selected.status != PLRStatus.PENDING:
            show_error(
                self, "Already Reviewed",
                f"This request has already been reviewed "
                f"(status: {self._selected.status})."
            )
            return

        recommendation = self._recommendation_var.get()
        note           = self._note_text.get("1.0", "end-1c").strip()

        if not note:
            show_error(
                self, "Note Required",
                "Please add a review note explaining your recommendation."
            )
            return

        action_text = {
            "APPROVE":        "recommend APPROVAL of",
            "REJECT":         "recommend REJECTION of",
            "INFO_REQUESTED": "request more information for",
        }.get(recommendation, "review")

        if not confirm(
            self, "Submit Review",
            f"You are about to {action_text} request #{self._selected.id} "
            f"for course '{self._selected.course_code}'.\n\n"
            f"Note: {note}\n\n"
            f"This will be sent to the administrator for final decision."
        ):
            return

        try:
            plr_svc = self._services["prior_learning_service"]
            plr_svc.instructor_review(
                request_id     = self._selected.id,
                recommendation = recommendation,
                note           = note,
                instructor_id  = self._user.id,
            )

            show_info(
                self, "Review Submitted",
                f"Your recommendation ({recommendation}) has been submitted.\n"
                f"The administrator will make the final decision."
            )

            self._note_text.delete("1.0", "end")
            self._selected = None
            self._load_requests()

        except Exception as e:
            show_error(self, "Error", str(e))