"""
plr_approval.py
---------------
Admin screen for final Prior Learning Request decisions.

Admin sees instructor-reviewed requests and makes final decision:
    APPROVED → transfer_credit() called automatically
    REJECTED → learner must complete course normally
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


class PLRApprovalScreen(tk.Frame):
    """
    Admin interface for final Prior Learning Request decisions.
    """

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user     = user
        self._services = services
        self._selected: Optional[PriorLearningRequest] = None
        self._build()
        self._load_requests()

    def _build(self):
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame,
            text="Prior Learning Request Approval",
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
            text=(
                "Review instructor recommendations and make the "
                "final approval decision. "
                "Approved requests automatically grant transfer credit."
            ),
            font=("Segoe UI", 9),
            bg=CONTENT_BG, fg="#666666",
            wraplength=700,
        ).pack(anchor="w", padx=20, pady=(0, 8))

        # Filter
        filter_frame = tk.Frame(self, bg=CONTENT_BG)
        filter_frame.pack(fill="x", padx=20, pady=(0, 8))
        self._filter_var = tk.StringVar(
            value=PLRStatus.INSTRUCTOR_REVIEWED
        )
        for text, value in [
            ("Awaiting My Decision",    PLRStatus.INSTRUCTOR_REVIEWED),
            ("All Requests",             "ALL"),
            ("Approved",                 PLRStatus.APPROVED),
            ("Rejected",                 PLRStatus.REJECTED),
        ]:
            ttk.Radiobutton(
                filter_frame, text=text,
                variable=self._filter_var, value=value,
                command=self._load_requests,
            ).pack(side="left", padx=5)

        # Split pane
        pane = tk.PanedWindow(
            self, orient="vertical",
            bg=CONTENT_BG, sashwidth=4,
        )
        pane.pack(
            fill="both", expand=True, padx=20, pady=(0, 10)
        )

        # ── Top: Request table ──────────────────────────────────────────────
        top = tk.Frame(pane, bg=CONTENT_BG)

        cols = ("id", "learner", "course", "pathway",
                "platform", "rec", "status", "submitted")
        self._tree = ttk.Treeview(
            top, columns=cols,
            show="headings", selectmode="browse",
        )
        for col, hdr, w in [
            ("id",        "#",             40),
            ("learner",   "Learner ID",    80),
            ("course",    "Course",        90),
            ("pathway",   "Pathway",       90),
            ("platform",  "Platform",      120),
            ("rec",       "Instructor Rec",120),
            ("status",    "Status",        120),
            ("submitted", "Submitted",     100),
        ]:
            self._tree.heading(col, text=hdr)
            self._tree.column(col, width=w)

        self._tree.tag_configure(
            PLRStatus.INSTRUCTOR_REVIEWED, background="#e3f2fd"
        )
        self._tree.tag_configure(
            PLRStatus.APPROVED,            background="#e8f5e9"
        )
        self._tree.tag_configure(
            PLRStatus.REJECTED,            background="#fce4ec"
        )
        self._tree.tag_configure(
            PLRStatus.PENDING,             background="#fff8e1"
        )

        ts = ttk.Scrollbar(
            top, orient="vertical",
            command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=ts.set)
        self._tree.pack(side="left", fill="both", expand=True)
        ts.pack(side="right", fill="y")
        self._tree.bind(
            "<<TreeviewSelect>>", self._on_request_selected
        )
        pane.add(top, minsize=200)

        # ── Bottom: Details + Decision ──────────────────────────────────────
        bottom = tk.Frame(pane, bg=CONTENT_BG)
        pane.add(bottom, minsize=220)

        # Evidence + instructor note
        left = tk.LabelFrame(
            bottom, text="  Full Request Details",
            font=("Segoe UI", 9, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL, relief="flat",
        )
        left.pack(side="left", fill="both",
                  expand=True, padx=(0, 8))

        self._details_text = tk.Text(
            left,
            font=("Segoe UI", 9),
            bg=CARD_BG, fg="#333333",
            height=10, relief="flat",
            state="disabled", wrap="word",
        )
        self._details_text.pack(
            fill="both", expand=True, padx=5, pady=5
        )

        # Decision panel
        right = tk.LabelFrame(
            bottom, text="  Final Decision",
            font=("Segoe UI", 9, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL, relief="flat",
        )
        right.pack(side="left", fill="y", ipadx=10)

        tk.Label(
            right,
            text="Admin Decision:",
            font=("Segoe UI", 9, "bold"),
            bg=CONTENT_BG, fg="#333333",
        ).pack(anchor="w", padx=10, pady=(8, 3))

        self._decision_var = tk.StringVar(value=PLRStatus.APPROVED)

        tk.Radiobutton(
            right,
            text="✅ APPROVE — Grant Transfer Credit",
            variable=self._decision_var,
            value=PLRStatus.APPROVED,
            font=("Segoe UI", 9),
            bg=CONTENT_BG, fg="#27ae60",
            activebackground=CONTENT_BG,
            selectcolor=CONTENT_BG,
        ).pack(anchor="w", padx=10, pady=3)

        tk.Radiobutton(
            right,
            text="❌ REJECT — Learner must complete normally",
            variable=self._decision_var,
            value=PLRStatus.REJECTED,
            font=("Segoe UI", 9),
            bg=CONTENT_BG, fg="#e74c3c",
            activebackground=CONTENT_BG,
            selectcolor=CONTENT_BG,
        ).pack(anchor="w", padx=10, pady=3)

        tk.Label(
            right,
            text="Decision Note (required):",
            font=("Segoe UI", 9, "bold"),
            bg=CONTENT_BG, fg="#333333",
        ).pack(anchor="w", padx=10, pady=(10, 3))

        self._admin_note = tk.Text(
            right,
            font=("Segoe UI", 9),
            height=4, width=30,
            relief="solid", bd=1,
        )
        self._admin_note.pack(padx=10)

        tk.Button(
            right,
            text="⚖️ Submit Final Decision",
            font=("Segoe UI", 9, "bold"),
            bg=HEADER_COL, fg="#ffffff",
            relief="flat", cursor="hand2",
            pady=7,
            command=self._submit_decision,
        ).pack(fill="x", padx=10, pady=10)

    def _load_requests(self):
        """Load requests based on filter."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        try:
            plr_svc = self._services.get("prior_learning_service")
            if plr_svc is None:
                return

            filt = self._filter_var.get()
            if filt == PLRStatus.INSTRUCTOR_REVIEWED:
                requests = plr_svc.get_pending_admin_decision()
            elif filt == "ALL":
                requests = plr_svc.get_all_requests()
            else:
                from repository.prior_learning_repo import (
                    PriorLearningRepository
                )
                plr_repo = self._services.get("plr_repo")
                requests = plr_repo.get_by_status(filt) if plr_repo else []

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
                        req.instructor_recommendation or "—",
                        req.status,
                        str(req.submitted_at)[:10],
                    ),
                    tags=(req.status,),
                )
        except Exception as e:
            show_error(self, "Error", str(e))

    def _on_request_selected(self, event=None):
        """Show full details for selected request."""
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

            text = (
                f"REQUEST DETAILS\n"
                f"{'=' * 45}\n"
                f"Request ID     : {req.id}\n"
                f"Learner ID     : {req.learner_id}\n"
                f"Course         : {req.course_code}\n"
                f"Pathway        : {req.pathway}\n"
                f"Platform       : "
                f"{req.external_platform or 'Not specified'}\n"
                f"External Score : "
                f"{req.external_score if req.external_score else 'N/A'}\n"
                f"Submitted      : {str(req.submitted_at)[:16]}\n"
                f"Status         : {req.status}\n"
                f"\nEVIDENCE DESCRIPTION:\n"
                f"{'─' * 45}\n"
                f"{req.evidence_description}\n"
            )

            if req.instructor_recommendation:
                text += (
                    f"\nINSTRUCTOR RECOMMENDATION: "
                    f"{req.instructor_recommendation}\n"
                    f"Reviewed by Instructor ID: {req.instructor_id}\n"
                    f"Reviewed at: "
                    f"{str(req.reviewed_by_instructor_at)[:16]}\n"
                )
                if req.instructor_note:
                    text += (
                        f"Instructor Note:\n{req.instructor_note}\n"
                    )

            if req.admin_note:
                text += (
                    f"\nPREVIOUS ADMIN NOTE:\n{req.admin_note}\n"
                )

            self._details_text.config(state="normal")
            self._details_text.delete("1.0", "end")
            self._details_text.insert("1.0", text)
            self._details_text.config(state="disabled")

        except Exception as e:
            show_error(self, "Error", str(e))

    def _submit_decision(self):
        """Submit the admin's final decision."""
        if self._selected is None:
            show_info(self, "Select", "Please select a request.")
            return

        if self._selected.status != PLRStatus.INSTRUCTOR_REVIEWED:
            show_error(
                self, "Cannot Decide",
                f"This request cannot be decided in its current "
                f"state ({self._selected.status}).\n"
                f"It must be INSTRUCTOR_REVIEWED first."
            )
            return

        decision = self._decision_var.get()
        note     = self._admin_note.get("1.0", "end-1c").strip()

        if not note:
            show_error(
                self, "Note Required",
                "Please provide a decision note explaining your decision."
            )
            return

        decision_text = (
            "APPROVE (transfer credit will be granted automatically)"
            if decision == PLRStatus.APPROVED
            else "REJECT (learner must complete the course normally)"
        )

        if not confirm(
            self, "Final Decision",
            f"You are about to:\n\n"
            f"{decision_text}\n\n"
            f"Request #{self._selected.id} for learner "
            f"{self._selected.learner_id} — "
            f"Course: {self._selected.course_code}\n\n"
            f"Note: {note}\n\n"
            f"This action cannot be undone."
        ):
            return

        try:
            plr_svc = self._services["prior_learning_service"]
            plr_svc.admin_decision(
                request_id = self._selected.id,
                decision   = decision,
                note       = note,
                admin_id   = self._user.id,
            )

            show_info(
                self, "Decision Submitted",
                f"Decision: {decision}\n\n"
                f"The learner has been notified automatically.\n"
                + (
                    "Transfer credit has been granted."
                    if decision == PLRStatus.APPROVED
                    else "The learner must complete the course normally."
                )
            )

            self._admin_note.delete("1.0", "end")
            self._selected = None
            self._load_requests()

        except Exception as e:
            show_error(self, "Error", str(e))