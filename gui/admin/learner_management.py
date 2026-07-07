"""
learner_management.py
---------------------
View and manage learner profiles, enrollments, and transfer credits.

Added: Add New Learner dialog with user account creation.
"""

import tkinter as tk
from tkinter import ttk, simpledialog
from typing import Optional

from core.user import User
from core.learner import Learner
from core.enums import UserRole
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


# ── Add Learner Dialog ─────────────────────────────────────────────────────────

class AddLearnerDialog(tk.Toplevel):
    """
    Modal dialog for creating a new learner account.

    Creates:
        1. A User account (username + password + LEARNER role)
        2. A Learner profile (name + email linked to that user)

    Both are created atomically — if user creation fails,
    no learner profile is created.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add New Learner")
        self.geometry("420x380")
        self.resizable(False, False)
        self.configure(bg=CARD_BG)
        self.grab_set()          # Modal — blocks parent window
        self.result = None       # Set to (username, password, name, email) on save

        self._build()

        # Centre over parent
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width()  - 420) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 380) // 2
        self.geometry(f"420x380+{px}+{py}")

        # Focus first field
        self._username_entry.focus()

    def _build(self):
        """Build the add learner form."""

        # Title bar inside dialog
        title_bar = tk.Frame(self, bg="#1a3a5c", pady=12)
        title_bar.pack(fill="x")
        tk.Label(
            title_bar,
            text="Add New Learner",
            font=("Segoe UI", 12, "bold"),
            bg="#1a3a5c",
            fg="#ffffff",
        ).pack(padx=20)

        # Form body
        form = tk.Frame(self, bg=CARD_BG, padx=30, pady=15)
        form.pack(fill="both", expand=True)

        def add_field(label_text: str, row: int, show: str = "") -> ttk.Entry:
            tk.Label(
                form,
                text=label_text,
                font=("Segoe UI", 9, "bold"),
                bg=CARD_BG,
                fg="#333333",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=(8, 2))

            entry = ttk.Entry(
                form,
                width=32,
                font=("Segoe UI", 10),
                show=show,
            )
            entry.grid(row=row + 1, column=0, sticky="ew", ipady=3)
            return entry

        form.columnconfigure(0, weight=1)

        # ── Login Account Fields ───────────────────────────────────────────────
        tk.Label(
            form,
            text="LOGIN ACCOUNT",
            font=("Segoe UI", 8, "bold"),
            bg=CARD_BG,
            fg="#888888",
        ).grid(row=0, column=0, sticky="w", pady=(0, 0))

        self._username_entry = add_field("Username *", 1)
        self._password_entry = add_field("Password * (min 8 chars)", 3, show="•")

        # ── Profile Fields ────────────────────────────────────────────────────
        tk.Label(
            form,
            text="LEARNER PROFILE",
            font=("Segoe UI", 8, "bold"),
            bg=CARD_BG,
            fg="#888888",
        ).grid(row=5, column=0, sticky="w", pady=(12, 0))

        self._name_entry  = add_field("Full Name *", 6)
        self._email_entry = add_field("Email Address *", 8)

        # ── Buttons ────────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=CARD_BG, pady=15, padx=30)
        btn_frame.pack(fill="x")

        tk.Button(
            btn_frame,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#e0e0e0",
            fg="#333333",
            relief="flat",
            width=12,
            pady=6,
            cursor="hand2",
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            btn_frame,
            text="Create Learner",
            font=("Segoe UI", 9, "bold"),
            bg="#1a3a5c",
            fg="#ffffff",
            relief="flat",
            width=14,
            pady=6,
            cursor="hand2",
            command=self._save,
        ).pack(side="right")

        # Bind Enter key
        self.bind("<Return>", lambda e: self._save())

    def _save(self):
        """Validate fields and store result."""
        username = self._username_entry.get().strip()
        password = self._password_entry.get()
        name     = self._name_entry.get().strip()
        email    = self._email_entry.get().strip()

        # Validation
        if not username:
            show_error(self, "Validation", "Username is required.")
            self._username_entry.focus()
            return

        if len(password) < 8:
            show_error(self, "Validation",
                       "Password must be at least 8 characters.")
            self._password_entry.focus()
            return

        if not name:
            show_error(self, "Validation", "Full name is required.")
            self._name_entry.focus()
            return

        if not email:
            show_error(self, "Validation", "Email address is required.")
            self._email_entry.focus()
            return

        if "@" not in email:
            show_error(self, "Validation",
                       "Please enter a valid email address.")
            self._email_entry.focus()
            return

        # Store result — parent will use this to create the learner
        self.result = (username, password, name, email)
        self.destroy()


# ── Learner Management Screen ──────────────────────────────────────────────────

class LearnerManagementScreen(tk.Frame):
    """
    Full learner management interface.

    Features:
        - View all learners in a sortable table
        - Add new learner (creates user account + learner profile)
        - View learner's enrollments
        - Grant transfer credit
        - Approve exemption
        - Delete learner
    """

    def __init__(self, parent, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._services             = services
        self._selected_learner_data: Optional[dict] = None
        self._all_learner_data: list = []
        self._build()
        self._load_learners()

    def _build(self):
        """Build the full learner management UI."""

        # ── Title bar ──────────────────────────────────────────────────────────
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)

        tk.Label(
            title_frame,
            text="Learner Management",
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
            command=self._load_learners,
        ).pack(side="right")

        # ── Search bar ─────────────────────────────────────────────────────────
        search_frame = tk.Frame(self, bg=CONTENT_BG)
        search_frame.pack(fill="x", padx=20, pady=(0, 8))

        tk.Label(
            search_frame,
            text="Search:",
            font=("Segoe UI", 9),
            bg=CONTENT_BG,
            fg="#666666",
        ).pack(side="left")

        self._search_var = tk.StringVar()
        self._search_var.trace("w", self._apply_search)
        ttk.Entry(
            search_frame,
            textvariable=self._search_var,
            width=25,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=8)

        # Learner count label
        self._count_var = tk.StringVar(value="0 learners")
        tk.Label(
            search_frame,
            textvariable=self._count_var,
            font=("Segoe UI", 9),
            bg=CONTENT_BG,
            fg="#888888",
        ).pack(side="right")

        # ── Main split: table left, details right ──────────────────────────────
        content = tk.Frame(self, bg=CONTENT_BG)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 5))

        # ── LEFT: Learner table ────────────────────────────────────────────────
        left = tk.Frame(content, bg=CONTENT_BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        cols = ("id", "name", "email", "completed", "active", "rate")
        self._learner_tree = ttk.Treeview(
            left,
            columns=cols,
            show="headings",
            selectmode="browse",
        )

        headers = [
            ("id",        "ID",          45),
            ("name",      "Full Name",   160),
            ("email",     "Email",       190),
            ("completed", "Completed",    80),
            ("active",    "Active",       60),
            ("rate",      "Rate %",       65),
        ]
        for col, header, width in headers:
            self._learner_tree.heading(
                col, text=header,
                command=lambda c=col: self._sort_by(c),
            )
            self._learner_tree.column(col, width=width)

        self._learner_tree.tag_configure("even", background="#f9f9f9")
        self._learner_tree.tag_configure("odd",  background="#ffffff")

        v_scroll = ttk.Scrollbar(
            left, orient="vertical",
            command=self._learner_tree.yview
        )
        self._learner_tree.configure(yscrollcommand=v_scroll.set)
        self._learner_tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        self._learner_tree.bind(
            "<<TreeviewSelect>>", self._on_learner_selected
        )

        # ── Action buttons below table ─────────────────────────────────────────
        btn_frame = tk.Frame(left, bg=CONTENT_BG, pady=8)
        btn_frame.pack(fill="x")

        # ADD LEARNER button — prominent green
        tk.Button(
            btn_frame,
            text="➕  Add New Learner",
            font=("Segoe UI", 9, "bold"),
            bg="#27ae60",
            fg="#ffffff",
            activebackground="#219a52",
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=6,
            command=self._add_learner,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            btn_frame,
            text="🗑️  Delete Learner",
            font=("Segoe UI", 9),
            bg="#e74c3c",
            fg="#ffffff",
            activebackground="#c0392b",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            command=self._delete_learner,
        ).pack(side="left")

        # ── RIGHT: Details panel ───────────────────────────────────────────────
        right = tk.Frame(
            content, bg=CARD_BG,
            width=300, relief="flat", bd=1,
        )
        right.pack(side="left", fill="y")
        right.pack_propagate(False)

        tk.Label(
            right,
            text="Learner Details",
            font=("Segoe UI", 11, "bold"),
            bg=CARD_BG,
            fg="#1a3a5c",
            pady=10,
        ).pack(fill="x", padx=15)

        ttk.Separator(right, orient="horizontal").pack(
            fill="x", padx=10
        )

        # Info rows
        self._info_frame = tk.Frame(right, bg=CARD_BG, padx=15, pady=8)
        self._info_frame.pack(fill="x")

        self._info_vars: dict = {}
        for label in ("Name", "Email", "User ID",
                      "Completed", "In Progress", "Rate"):
            row = tk.Frame(self._info_frame, bg=CARD_BG)
            row.pack(fill="x", pady=2)
            tk.Label(
                row,
                text=f"{label}:",
                font=("Segoe UI", 8, "bold"),
                bg=CARD_BG, fg="#888888",
                width=12, anchor="w",
            ).pack(side="left")
            var = tk.StringVar(value="—")
            tk.Label(
                row,
                textvariable=var,
                font=("Segoe UI", 9),
                bg=CARD_BG, fg="#333333",
                anchor="w",
            ).pack(side="left")
            self._info_vars[label] = var

        ttk.Separator(right, orient="horizontal").pack(
            fill="x", padx=10, pady=6
        )

        # Action buttons on detail panel
        tk.Label(
            right,
            text="Actions",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg="#1a3a5c",
            padx=15,
        ).pack(anchor="w", padx=15)

        detail_actions = [
            ("📜  View Enrollments",      "#3498db", self._view_enrollments),
            ("📥  Grant Transfer Credit", "#8e44ad", self._grant_transfer),
            ("✅  Approve Exemption",     "#27ae60", self._approve_exemption),
        ]
        for text, colour, cmd in detail_actions:
            tk.Button(
                right,
                text=text,
                font=("Segoe UI", 9),
                bg=colour,
                fg="#ffffff",
                activebackground=colour,
                relief="flat",
                cursor="hand2",
                pady=6,
                anchor="w",
                padx=10,
                command=cmd,
            ).pack(fill="x", padx=15, pady=2)

        ttk.Separator(right, orient="horizontal").pack(
            fill="x", padx=10, pady=6
        )

        # Enrollment mini-list
        tk.Label(
            right,
            text="Enrollments",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg="#888888",
        ).pack(anchor="w", padx=15)

        self._enroll_listbox = tk.Listbox(
            right,
            font=("Courier New", 8),
            height=8,
            relief="flat",
            bd=1,
            highlightthickness=0,
            selectmode="single",
        )
        self._enroll_listbox.pack(
            fill="x", padx=15, pady=(2, 10)
        )

        # Status bar
        self._status_var = tk.StringVar(value="Ready")
        tk.Label(
            self,
            textvariable=self._status_var,
            font=("Segoe UI", 8),
            bg=CONTENT_BG,
            fg="#888888",
            anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 3))

    # ── Data Loading ───────────────────────────────────────────────────────────

    def _load_learners(self):
        """Load all learners from analytics service."""
        self._all_learner_data = []

        try:
            analytics = self._services.get("analytics_service")
            if analytics is None:
                self._status_var.set("Analytics service unavailable")
                return

            report = analytics.learner_activity_report()
            self._all_learner_data = report
            self._apply_search()

        except Exception as e:
            show_error(self, "Error", f"Failed to load learners: {e}")

    def _apply_search(self, *args):
        """Filter learners by search text."""
        query = self._search_var.get().lower().strip()

        filtered = [
            d for d in self._all_learner_data
            if not query or query in d.get("learner_name", "").lower()
        ]

        self._populate_table(filtered)
        self._count_var.set(f"{len(filtered)} learner(s)")

    def _populate_table(self, data: list):
        """Fill the Treeview with learner data."""
        for item in self._learner_tree.get_children():
            self._learner_tree.delete(item)

        for i, learner_data in enumerate(data):
            tag = "even" if i % 2 == 0 else "odd"
            rate = learner_data.get("completion_rate", 0)
            self._learner_tree.insert(
                "", "end",
                iid=str(learner_data["learner_id"]),
                values=(
                    learner_data["learner_id"],
                    learner_data.get("learner_name", "—"),
                    "—",                         # email not in analytics
                    learner_data.get("completed", 0),
                    learner_data.get("in_progress", 0),
                    f"{rate}%",
                ),
                tags=(tag,),
            )

    def _sort_by(self, column: str):
        """Sort the learner table by the clicked column."""
        reverse = False
        if column == "id":
            self._all_learner_data.sort(
                key=lambda d: d["learner_id"], reverse=reverse
            )
        elif column == "name":
            self._all_learner_data.sort(
                key=lambda d: d.get("learner_name", ""), reverse=reverse
            )
        elif column == "completed":
            self._all_learner_data.sort(
                key=lambda d: d.get("completed", 0), reverse=True
            )
        elif column == "rate":
            self._all_learner_data.sort(
                key=lambda d: d.get("completion_rate", 0), reverse=True
            )
        self._apply_search()

    def _on_learner_selected(self, event=None):
        """Load details panel for the selected learner."""
        selection = self._learner_tree.selection()
        if not selection:
            return

        learner_id = int(selection[0])

        # Find in cached data
        for d in self._all_learner_data:
            if d["learner_id"] == learner_id:
                self._selected_learner_data = d
                break

        if self._selected_learner_data is None:
            return

        # Update info labels
        self._info_vars["Name"].set(
            self._selected_learner_data.get("learner_name", "—")
        )
        self._info_vars["Email"].set("—")
        self._info_vars["User ID"].set(str(learner_id))
        self._info_vars["Completed"].set(
            str(self._selected_learner_data.get("completed", 0))
        )
        self._info_vars["In Progress"].set(
            str(self._selected_learner_data.get("in_progress", 0))
        )
        self._info_vars["Rate"].set(
            f"{self._selected_learner_data.get('completion_rate', 0)}%"
        )

        # Populate enrollment mini-list
        self._enroll_listbox.delete(0, "end")
        for c in self._selected_learner_data.get("courses", []):
            score = (
                f" ({c['score']:.0f})"
                if c.get("score") is not None else ""
            )
            self._enroll_listbox.insert(
                "end",
                f"  {c['course_code']:8s}  {c['status']}{score}"
            )

        self._status_var.set(
            f"Selected: {self._selected_learner_data.get('learner_name')}"
        )

    # ── Add Learner ────────────────────────────────────────────────────────────

    def _add_learner(self):
        """
        Open the Add Learner dialog and create the account.

        Process:
            1. Open AddLearnerDialog to collect details
            2. Register user account (auth_service)
            3. Create learner profile (learner_repo)
            4. Refresh the table
        """
        dialog = AddLearnerDialog(self)
        self.wait_window(dialog)

        if dialog.result is None:
            return  # User cancelled

        username, password, name, email = dialog.result

        try:
            # Step 1: Create user account with LEARNER role
            auth_service = self._services.get("auth_service")
            if auth_service is None:
                show_error(self, "Error", "Auth service unavailable.")
                return

            new_user = auth_service.register(
                username, password, UserRole.LEARNER
            )

            # Step 2: Create learner profile linked to the user
            learner_repo = self._services.get("learner_repo")
            if learner_repo is None:
                show_error(self, "Error", "Learner repository unavailable.")
                return

            learner = Learner(
                name    = name,
                email   = email,
                user_id = new_user.id,
            )
            learner_repo.create_learner(learner)

            # Step 3: Success feedback and refresh
            show_info(
                self,
                "Learner Created",
                f"Learner account created successfully!\n\n"
                f"Name    : {name}\n"
                f"Username: {username}\n"
                f"Email   : {email}\n\n"
                f"The learner can now log in with their username and password."
            )

            self._status_var.set(
                f"Created learner: {name} ({username})"
            )
            self._load_learners()

        except Exception as e:
            show_error(
                self, "Creation Failed",
                f"Failed to create learner:\n{e}"
            )

    # ── Delete Learner ─────────────────────────────────────────────────────────

    def _delete_learner(self):
        """Delete the selected learner after confirmation."""
        if self._selected_learner_data is None:
            show_info(self, "Select Learner",
                      "Please select a learner to delete.")
            return

        name       = self._selected_learner_data.get("learner_name", "")
        learner_id = self._selected_learner_data["learner_id"]

        if not confirm(
            self, "Delete Learner",
            f"Permanently delete learner '{name}'?\n\n"
            f"This will remove:\n"
            f"  • Their learner profile\n"
            f"  • All their enrollments\n"
            f"  • All their progress records\n\n"
            f"This action cannot be undone."
        ):
            return

        try:
            learner_repo = self._services.get("learner_repo")
            if learner_repo:
                learner_repo.delete_learner(learner_id)

            show_info(self, "Deleted",
                      f"Learner '{name}' deleted successfully.")
            self._selected_learner_data = None
            self._clear_details_panel()
            self._load_learners()

        except Exception as e:
            show_error(self, "Error", f"Failed to delete learner: {e}")

    def _clear_details_panel(self):
        """Reset the details panel to empty state."""
        for var in self._info_vars.values():
            var.set("—")
        self._enroll_listbox.delete(0, "end")

    # ── Transfer Credit / Exemption ────────────────────────────────────────────

    def _view_enrollments(self):
        if not self._selected_learner_data:
            show_info(self, "Select Learner", "Please select a learner.")
            return

        courses = self._selected_learner_data.get("courses", [])
        if not courses:
            show_info(self, "Enrollments", "This learner has no enrollments.")
            return

        lines = [
            f"Enrollments for {self._selected_learner_data['learner_name']}",
            "─" * 40,
        ]
        for c in courses:
            score = (
                f"  Score: {c['score']:.0f}"
                if c.get("score") is not None else ""
            )
            lines.append(f"  {c['course_code']:10s}  {c['status']}{score}")

        show_info(self, "Enrollments", "\n".join(lines))

    def _grant_transfer(self):
        if not self._selected_learner_data:
            show_info(self, "Select Learner", "Please select a learner.")
            return

        course_code = self._prompt_course_code(
            "Grant Transfer Credit",
            "Enter the course code to grant transfer credit:"
        )
        if not course_code:
            return

        try:
            enrollment_svc = self._services.get("enrollment_service")
            if enrollment_svc is None:
                show_error(self, "Error", "Enrollment service unavailable.")
                return

            result = enrollment_svc.transfer_credit(
                self._selected_learner_data["learner_id"],
                course_code,
            )

            if result.success:
                show_info(self, "Transfer Credit Granted", result.message)
                self._load_learners()
            else:
                show_error(self, "Failed", result.message)

        except Exception as e:
            show_error(self, "Error", str(e))

    def _approve_exemption(self):
        if not self._selected_learner_data:
            show_info(self, "Select Learner", "Please select a learner.")
            return

        course_code = self._prompt_course_code(
            "Approve Exemption",
            "Enter the course code to approve exemption:"
        )
        if not course_code:
            return

        try:
            enrollment_svc = self._services.get("enrollment_service")
            if enrollment_svc is None:
                show_error(self, "Error", "Enrollment service unavailable.")
                return

            result = enrollment_svc.approve_exemption(
                self._selected_learner_data["learner_id"],
                course_code,
            )

            if result.success:
                show_info(self, "Exemption Approved", result.message)
                self._load_learners()
            else:
                show_error(self, "Failed", result.message)

        except Exception as e:
            show_error(self, "Error", str(e))

    def _prompt_course_code(self, title: str, prompt: str) -> Optional[str]:
        """Prompt the admin for a course code."""
        code = simpledialog.askstring(title, prompt, parent=self)
        return code.strip().upper() if code and code.strip() else None