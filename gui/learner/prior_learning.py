"""
prior_learning.py
-----------------
Learner screen for submitting Prior Learning / Transfer Credit Requests.

Features:
    - Submit new request with evidence
    - Track request status
    - View admin/instructor notes
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from core.user import User
from core.prior_learning_request import PLRPathway, PLRStatus
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"
HEADER_COL = "#1a3a5c"


class PriorLearningScreen(tk.Frame):
    """
    Learner interface for Prior Learning / Transfer Credit Requests.
    """

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user       = user
        self._services   = services
        self._learner_id: Optional[int] = None
        self._build()
        self._find_learner()
        self._load_requests()

    def _build(self):
        # Title
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame,
            text="Prior Learning / Transfer Credit",
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
                "Have you completed courses on another platform? "
                "Submit a request to have your prior learning recognized."
            ),
            font=("Segoe UI", 9),
            bg=CONTENT_BG, fg="#666666",
            wraplength=700, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        # Notebook: My Requests | Submit New
        notebook = ttk.Notebook(self)
        notebook.pack(
            fill="both", expand=True, padx=20, pady=(0, 10)
        )

        # ── Tab 1: My Requests ──────────────────────────────────────────────
        requests_tab = tk.Frame(notebook, bg=CONTENT_BG)
        notebook.add(requests_tab, text="  My Requests  ")
        self._build_requests_tab(requests_tab)

        # ── Tab 2: Submit New Request ───────────────────────────────────────
        submit_tab = tk.Frame(notebook, bg=CONTENT_BG)
        notebook.add(submit_tab, text="  Submit New Request  ")
        self._build_submit_tab(submit_tab)

    def _build_requests_tab(self, parent):
        """Build the requests tracking tab."""
        # Status summary
        summary_frame = tk.Frame(parent, bg=CONTENT_BG)
        summary_frame.pack(fill="x", padx=10, pady=8)

        self._status_counts = {}
        for status, colour, label in [
            (PLRStatus.PENDING,             "#e67e22", "Pending"),
            (PLRStatus.INSTRUCTOR_REVIEWED, "#3498db", "Under Review"),
            (PLRStatus.APPROVED,            "#27ae60", "Approved"),
            (PLRStatus.REJECTED,            "#e74c3c", "Rejected"),
        ]:
            card = tk.Frame(
                summary_frame, bg=CARD_BG, padx=15, pady=8
            )
            card.pack(side="left", padx=5, fill="x", expand=True)
            lbl = tk.Label(
                card, text="0",
                font=("Segoe UI", 16, "bold"),
                bg=CARD_BG, fg=colour,
            )
            lbl.pack()
            tk.Label(
                card, text=label,
                font=("Segoe UI", 8),
                bg=CARD_BG, fg="#888888",
            ).pack()
            self._status_counts[status] = lbl

        # Requests table
        cols = ("id", "course", "pathway",
                "status", "recommendation", "submitted")
        self._req_tree = ttk.Treeview(
            parent, columns=cols,
            show="headings", selectmode="browse",
        )
        for col, hdr, w in [
            ("id",             "#",              40),
            ("course",         "Course",         90),
            ("pathway",        "Pathway",         90),
            ("status",         "Status",         120),
            ("recommendation", "Instructor Rec", 130),
            ("submitted",      "Submitted",      110),
        ]:
            self._req_tree.heading(col, text=hdr)
            self._req_tree.column(col, width=w)

        self._req_tree.tag_configure(
            PLRStatus.PENDING,             background="#fff8e1"
        )
        self._req_tree.tag_configure(
            PLRStatus.INSTRUCTOR_REVIEWED, background="#e3f2fd"
        )
        self._req_tree.tag_configure(
            PLRStatus.APPROVED,            background="#e8f5e9"
        )
        self._req_tree.tag_configure(
            PLRStatus.REJECTED,            background="#fce4ec"
        )
        self._req_tree.tag_configure(
            PLRStatus.INFO_REQUESTED,      background="#fff3e0"
        )

        rs = ttk.Scrollbar(
            parent, orient="vertical",
            command=self._req_tree.yview
        )
        self._req_tree.configure(yscrollcommand=rs.set)
        self._req_tree.pack(
            side="left", fill="both",
            expand=True, padx=(10, 0), pady=5
        )
        rs.pack(side="left", fill="y", pady=5)
        self._req_tree.bind(
            "<<TreeviewSelect>>", self._on_request_selected
        )

        # Notes display
        self._notes_text = tk.Text(
            parent,
            font=("Segoe UI", 9),
            height=5, relief="flat",
            bg=CARD_BG, fg="#333333",
            state="disabled", wrap="word",
        )
        self._notes_text.pack(
            fill="x", padx=10, pady=(0, 5)
        )

    def _build_submit_tab(self, parent):
        """Build the new request submission form."""
        form = tk.Frame(parent, bg=CONTENT_BG, padx=20, pady=15)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)

        def labeled(label: str, row: int, colspan: int = 1):
            tk.Label(
                form, text=label,
                font=("Segoe UI", 9, "bold"),
                bg=CONTENT_BG, fg="#333333",
                anchor="e",
            ).grid(
                row=row, column=0,
                sticky="e", padx=(0, 10), pady=5
            )

        # Course code
        labeled("Course Code *", 0)
        self._sub_course_var = tk.StringVar()
        course_combo = ttk.Combobox(
            form,
            textvariable=self._sub_course_var,
            state="readonly",
            width=20,
            font=("Segoe UI", 10),
        )
        course_combo.grid(row=0, column=1, sticky="w")
        self._sub_course_combo = course_combo

        # Pathway
        labeled("Pathway *", 1)
        self._sub_pathway_var = tk.StringVar(value=PLRPathway.TRANSFER)
        pathway_frame = tk.Frame(form, bg=CONTENT_BG)
        pathway_frame.grid(row=1, column=1, sticky="w")
        for text, value, hint in [
            ("Transfer Credit",
             PLRPathway.TRANSFER,
             "Credit from another institution"),
            ("Prior Assessment",
             PLRPathway.ASSESSMENT,
             "Passed an external assessment"),
            ("Exemption Request",
             PLRPathway.EXEMPTION,
             "Significant work/life experience"),
        ]:
            tk.Radiobutton(
                pathway_frame, text=f"{text}  ({hint})",
                variable=self._sub_pathway_var, value=value,
                font=("Segoe UI", 9),
                bg=CONTENT_BG, fg="#333333",
                activebackground=CONTENT_BG,
                selectcolor=CONTENT_BG,
            ).pack(anchor="w")

        # Platform
        labeled("Platform / Institution", 2)
        self._sub_platform = ttk.Entry(
            form, width=35, font=("Segoe UI", 10)
        )
        self._sub_platform.grid(
            row=2, column=1, sticky="w", ipady=3
        )
        tk.Label(
            form, text="(e.g. Coursera, edX, MIT, Harvard)",
            font=("Segoe UI", 8),
            bg=CONTENT_BG, fg="#888888",
        ).grid(row=2, column=2, sticky="w", padx=5)

        # External score
        labeled("External Score (if any)", 3)
        self._sub_score = ttk.Entry(
            form, width=10, font=("Segoe UI", 10)
        )
        self._sub_score.grid(row=3, column=1, sticky="w", ipady=3)
        tk.Label(
            form, text="(0 – 100, leave blank if not applicable)",
            font=("Segoe UI", 8),
            bg=CONTENT_BG, fg="#888888",
        ).grid(row=3, column=2, sticky="w", padx=5)

        # Evidence description
        labeled("Evidence Description *", 4)
        self._sub_evidence = tk.Text(
            form, width=45, height=5,
            font=("Segoe UI", 10),
            relief="solid", bd=1, wrap="word",
        )
        self._sub_evidence.grid(
            row=4, column=1, columnspan=2,
            sticky="ew", pady=5
        )
        tk.Label(
            form,
            text=(
                "Describe your prior learning evidence in detail.\n"
                "Include: course name, completion date, grade achieved,\n"
                "and any certificate or transcript details."
            ),
            font=("Segoe UI", 8),
            bg=CONTENT_BG, fg="#888888",
            justify="left",
        ).grid(row=5, column=1, sticky="w")

        # Submit button
        tk.Button(
            form,
            text="📤  Submit Prior Learning Request",
            font=("Segoe UI", 10, "bold"),
            bg="#1a3a5c", fg="#ffffff",
            activebackground="#2d5986",
            relief="flat", cursor="hand2",
            pady=8, padx=20,
            command=self._submit_request,
        ).grid(row=6, column=1, sticky="w", pady=15)

    # ── Data ───────────────────────────────────────────────────────────────────

    def _find_learner(self):
        """Find learner ID for current user."""
        try:
            learner_repo = self._services.get("learner_repo")
            if learner_repo:
                learner = learner_repo.get_learner_by_user_id(
                    self._user.id
                )
                if learner:
                    self._learner_id = learner.id

            # Populate course combobox
            course_svc = self._services.get("course_service")
            if course_svc:
                courses = course_svc.get_all_courses()
                self._sub_course_combo["values"] = [
                    c.code for c in courses
                ]

        except Exception as e:
            print(f"Find learner error: {e}")

    def _load_requests(self):
        """Load the learner's prior learning requests."""
        for item in self._req_tree.get_children():
            self._req_tree.delete(item)

        if self._learner_id is None:
            return

        try:
            plr_svc = self._services.get("prior_learning_service")
            if plr_svc is None:
                return

            requests = plr_svc.get_learner_requests(self._learner_id)

            # Reset status counts
            counts = {
                PLRStatus.PENDING:            0,
                PLRStatus.INSTRUCTOR_REVIEWED: 0,
                PLRStatus.APPROVED:           0,
                PLRStatus.REJECTED:           0,
            }

            for req in requests:
                if req.status in counts:
                    counts[req.status] += 1

                submitted_str = str(req.submitted_at)[:10]
                self._req_tree.insert(
                    "", "end",
                    iid=str(req.id),
                    values=(
                        req.id,
                        req.course_code,
                        req.pathway,
                        req.status,
                        req.instructor_recommendation or "—",
                        submitted_str,
                    ),
                    tags=(req.status,),
                )

            for status, lbl in self._status_counts.items():
                lbl.config(text=str(counts.get(status, 0)))

        except Exception as e:
            show_error(self, "Error", str(e))

    def _on_request_selected(self, event=None):
        """Show notes for selected request."""
        sel = self._req_tree.selection()
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

            notes = []
            if req.instructor_note:
                notes.append(
                    f"Instructor Note:\n{req.instructor_note}"
                )
            if req.admin_note:
                notes.append(
                    f"\nAdmin Decision Note:\n{req.admin_note}"
                )
            if not notes:
                notes.append(
                    "No notes yet. Your request is being reviewed."
                )

            self._notes_text.config(state="normal")
            self._notes_text.delete("1.0", "end")
            self._notes_text.insert("1.0", "\n".join(notes))
            self._notes_text.config(state="disabled")

        except Exception as e:
            show_error(self, "Error", str(e))

    def _submit_request(self):
        """Submit a new prior learning request."""
        if self._learner_id is None:
            show_error(
                self, "Profile Not Found",
                "Your learner profile was not found. "
                "Please contact an administrator."
            )
            return

        course_code  = self._sub_course_var.get().strip()
        pathway      = self._sub_pathway_var.get()
        platform     = self._sub_platform.get().strip()
        score_str    = self._sub_score.get().strip()
        evidence     = self._sub_evidence.get("1.0", "end-1c").strip()

        # Validation
        if not course_code:
            show_error(self, "Required", "Please select a course.")
            return
        if not evidence or len(evidence) < 30:
            show_error(
                self, "Required",
                "Please provide a detailed evidence description "
                "(at least 30 characters)."
            )
            return

        # Parse optional score
        external_score = None
        if score_str:
            try:
                external_score = float(score_str)
                if not 0 <= external_score <= 100:
                    show_error(self, "Invalid",
                               "Score must be between 0 and 100.")
                    return
            except ValueError:
                show_error(self, "Invalid",
                           "Score must be a number.")
                return

        if not confirm(
            self, "Submit Request",
            f"Submit prior learning request for:\n\n"
            f"Course  : {course_code}\n"
            f"Pathway : {pathway}\n"
            f"Platform: {platform or 'Not specified'}\n\n"
            f"An instructor will review your evidence and "
            f"provide a recommendation to the administrator."
        ):
            return

        try:
            plr_svc = self._services["prior_learning_service"]
            request = plr_svc.submit_request(
                learner_id           = self._learner_id,
                course_code          = course_code,
                pathway              = pathway,
                evidence_description = evidence,
                external_platform    = platform,
                external_score       = external_score,
            )

            show_info(
                self, "Request Submitted",
                f"Your prior learning request for '{course_code}' "
                f"has been submitted successfully.\n\n"
                f"Request ID: {request.id}\n\n"
                f"An instructor will review your evidence. "
                f"You can track the status in 'My Requests' tab."
            )

            # Clear form
            self._sub_course_var.set("")
            self._sub_platform.delete(0, "end")
            self._sub_score.delete(0, "end")
            self._sub_evidence.delete("1.0", "end")

            self._load_requests()

        except ValueError as e:
            show_error(self, "Duplicate Request", str(e))
        except Exception as e:
            show_error(self, "Error", str(e))