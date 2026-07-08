"""
pending_registrations.py
------------------------
Admin screen for reviewing and activating pending learner registrations.

Features:
    - View all pending registrations with registration details
    - Approve (account activated + learner profile created)
    - Reject with mandatory reason
    - Request additional information
    - View all users with their account status
    - Reactivate rejected/deactivated accounts
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional



from core.user import User
from core.enums import AccountStatus
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG  = "#f0f4f8"
CARD_BG     = "#ffffff"
HEADER_COL  = "#1a3a5c"
PENDING_COL = "#e67e22"
APPROVE_COL = "#27ae60"
REJECT_COL  = "#e74c3c"


class PendingRegistrationsScreen(tk.Frame):
    """
    Admin interface for managing learner account activations.

    Tabs:
        Pending  → Accounts waiting for review
        All      → All user accounts with status
    """

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user               = user
        self._services           = services
        self._selected_user_data: Optional[User] = None
        self._build()
        self._load_data()

    def _build(self):
        """Build the pending registrations UI."""

        # ── Title bar ──────────────────────────────────────────────────────────
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)

        tk.Label(
            title_frame,
            text="Pending Registrations",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL,
        ).pack(side="left")

        # Pending count badge
        self._badge_var = tk.StringVar(value="0 pending")
        tk.Label(
            title_frame,
            textvariable=self._badge_var,
            font=("Segoe UI", 10, "bold"),
            bg=PENDING_COL, fg="#ffffff",
            padx=10, pady=3,
        ).pack(side="left", padx=10)

        tk.Button(
            title_frame,
            text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat",
            cursor="hand2",
            command=self._load_data,
        ).pack(side="right")

        tk.Label(
            self,
            text=(
                "Review learner registration requests. "
                "Approved learners can immediately log in to LMPTS."
            ),
            font=("Segoe UI", 9),
            bg=CONTENT_BG, fg="#666666",
        ).pack(anchor="w", padx=20, pady=(0, 8))

        # ── Notebook: Pending / All Users ──────────────────────────────────────
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(
            fill="both", expand=True, padx=20, pady=(0, 5)
        )

        # Tab 1: Pending registrations
        pending_tab = tk.Frame(self._notebook, bg=CONTENT_BG)
        self._notebook.add(pending_tab, text="  ⏳ Pending Review  ")
        self._build_pending_tab(pending_tab)

        # Tab 2: All users
        all_tab = tk.Frame(self._notebook, bg=CONTENT_BG)
        self._notebook.add(all_tab, text="  👥 All Users  ")
        self._build_all_users_tab(all_tab)

    def _build_pending_tab(self, parent):
        """Build the pending registrations tab."""

        # Split: table left, detail right
        split = tk.Frame(parent, bg=CONTENT_BG)
        split.pack(fill="both", expand=True, padx=5, pady=5)

        # ── Left: Pending table ────────────────────────────────────────────────
        left = tk.Frame(split, bg=CONTENT_BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(
            left,
            text="Pending Accounts",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL,
        ).pack(anchor="w", pady=(0, 5))

        cols = ("id", "username", "full_name", "email", "registered")
        self._pending_tree = ttk.Treeview(
            left,
            columns=cols,
            show="headings",
            selectmode="browse",
        )
        for col, hdr, w in [
            ("id",         "ID",          45),
            ("username",   "Username",   110),
            ("full_name",  "Full Name",  140),
            ("email",      "Email",      180),
            ("registered", "Registered", 110),
        ]:
            self._pending_tree.heading(col, text=hdr)
            self._pending_tree.column(col, width=w)

        self._pending_tree.tag_configure(
            "pending", background="#fff8e1"
        )

        ps = ttk.Scrollbar(
            left, orient="vertical",
            command=self._pending_tree.yview
        )
        self._pending_tree.configure(yscrollcommand=ps.set)
        self._pending_tree.pack(
            side="left", fill="both", expand=True
        )
        ps.pack(side="right", fill="y")

        self._pending_tree.bind(
            "<<TreeviewSelect>>", self._on_pending_selected
        )

        # ── Right: Detail + Action panel ───────────────────────────────────────
        right = tk.Frame(
            split, bg=CARD_BG,
            width=300, relief="flat", bd=1,
        )
        right.pack(side="left", fill="y")
        right.pack_propagate(False)

        tk.Label(
            right,
            text="Registration Details",
            font=("Segoe UI", 11, "bold"),
            bg=CARD_BG, fg=HEADER_COL, pady=12,
        ).pack(fill="x", padx=12)

        ttk.Separator(right, orient="horizontal").pack(
            fill="x", padx=12
        )

        # Info fields
        self._detail_frame = tk.Frame(
            right, bg=CARD_BG, padx=12, pady=8
        )
        self._detail_frame.pack(fill="x")

        self._detail_vars: dict = {}
        for label in ("Username", "Full Name", "Email", "Registered"):
            row = tk.Frame(self._detail_frame, bg=CARD_BG)
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
                anchor="w", wraplength=160,
            ).pack(side="left", fill="x")
            self._detail_vars[label] = var

        ttk.Separator(right, orient="horizontal").pack(
            fill="x", padx=12, pady=5
        )

        # ── Action section ─────────────────────────────────────────────────────
        tk.Label(
            right,
            text="Action",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg=HEADER_COL,
        ).pack(anchor="w", padx=12)

        # Approve button
        tk.Button(
            right,
            text="✅  Approve Registration",
            font=("Segoe UI", 9, "bold"),
            bg=APPROVE_COL, fg="#ffffff",
            activebackground="#219a52",
            relief="flat", cursor="hand2",
            pady=8, anchor="w", padx=12,
            command=self._approve_selected,
        ).pack(fill="x", padx=12, pady=(6, 3))

        # Optional note for approval
        tk.Label(
            right,
            text="Welcome note (optional):",
            font=("Segoe UI", 8),
            bg=CARD_BG, fg="#888888",
        ).pack(anchor="w", padx=12)

        self._approve_note = tk.Text(
            right,
            font=("Segoe UI", 9),
            height=2, relief="solid", bd=1,
        )
        self._approve_note.pack(fill="x", padx=12)

        ttk.Separator(right, orient="horizontal").pack(
            fill="x", padx=12, pady=8
        )

        # Reject section
        tk.Label(
            right,
            text="Rejection Reason (required):",
            font=("Segoe UI", 8, "bold"),
            bg=CARD_BG, fg="#333333",
        ).pack(anchor="w", padx=12)

        self._reject_reason = tk.Text(
            right,
            font=("Segoe UI", 9),
            height=3, relief="solid", bd=1,
        )
        self._reject_reason.pack(fill="x", padx=12, pady=(2, 4))

        tk.Button(
            right,
            text="❌  Reject Registration",
            font=("Segoe UI", 9),
            bg=REJECT_COL, fg="#ffffff",
            activebackground="#c0392b",
            relief="flat", cursor="hand2",
            pady=6, anchor="w", padx=12,
            command=self._reject_selected,
        ).pack(fill="x", padx=12, pady=(0, 4))

        tk.Button(
            right,
            text="ℹ️  Request More Information",
            font=("Segoe UI", 9),
            bg="#e67e22", fg="#ffffff",
            activebackground="#d35400",
            relief="flat", cursor="hand2",
            pady=6, anchor="w", padx=12,
            command=self._request_info,
        ).pack(fill="x", padx=12)

    def _build_all_users_tab(self, parent):
        """Build the all users tab with status overview."""

        tk.Label(
            parent,
            text="All User Accounts",
            font=("Segoe UI", 10, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL,
        ).pack(anchor="w", padx=5, pady=(5, 3))

        cols = ("id", "username", "full_name",
                "role", "status", "email", "registered")
        self._all_tree = ttk.Treeview(
            parent,
            columns=cols,
            show="headings",
            selectmode="browse",
        )
        for col, hdr, w in [
            ("id",         "ID",          45),
            ("username",   "Username",   110),
            ("full_name",  "Full Name",  140),
            ("role",       "Role",        90),
            ("status",     "Status",      90),
            ("email",      "Email",      170),
            ("registered", "Registered", 100),
        ]:
            self._all_tree.heading(col, text=hdr)
            self._all_tree.column(col, width=w)

        # Status colour tags
        self._all_tree.tag_configure("ACTIVE",   background="#e8f5e9")
        self._all_tree.tag_configure("PENDING",  background="#fff8e1")
        self._all_tree.tag_configure("REJECTED", background="#fce4ec")
        self._all_tree.tag_configure("INACTIVE", background="#eeeeee")

        alls = ttk.Scrollbar(
            parent, orient="vertical",
            command=self._all_tree.yview
        )
        self._all_tree.configure(yscrollcommand=alls.set)
        self._all_tree.pack(
            side="left", fill="both",
            expand=True, padx=(5, 0), pady=5
        )
        alls.pack(side="left", fill="y", pady=5)
        self._all_tree.bind(
            "<<TreeviewSelect>>", self._on_all_user_selected
        )

        # Action buttons for all users tab
        btn_frame = tk.Frame(parent, bg=CONTENT_BG, pady=5)
        btn_frame.pack(fill="x", padx=5)

        for text, colour, cmd in [
            ("✅ Reactivate",    APPROVE_COL, self._reactivate_user),
            ("🚫 Deactivate",    "#7f8c8d",   self._deactivate_user),
        ]:
            tk.Button(
                btn_frame,
                text=text,
                font=("Segoe UI", 9),
                bg=colour, fg="#ffffff",
                relief="flat", cursor="hand2",
                padx=10, pady=5,
                command=cmd,
            ).pack(side="left", padx=(0, 5))

    # ── Data Loading ───────────────────────────────────────────────────────────

    def _load_data(self):
        """Reload both pending and all users tables."""
        self._load_pending()
        self._load_all_users()
        self._update_badge()

    def _update_badge(self):
        """Update the pending count badge."""
        try:
            account_svc = self._services.get("account_service")
            if account_svc:
                count = account_svc.count_pending()
                self._badge_var.set(
                    f"{count} pending"
                    if count > 0 else "0 pending"
                )
        except Exception as e:
            print(f"Badge update error: {e}")

    def _load_pending(self):
        """Load pending registrations into the pending table."""
        for item in self._pending_tree.get_children():
            self._pending_tree.delete(item)

        try:
            account_svc = self._services.get("account_service")
            if account_svc is None:
                return

            pending_users = account_svc.get_pending_registrations()

            for user in pending_users:
                self._pending_tree.insert(
                    "", "end",
                    iid=str(user.id),
                    values=(
                        user.id,
                        user.username,
                        user.full_name or "—",
                        user.email    or "—",
                        str(user.created_at)[:10],
                    ),
                    tags=("pending",),
                )

        except Exception as e:
            show_error(self, "Error", f"Failed to load pending: {e}")

    def _load_all_users(self):
        """Load all users into the all users table."""
        for item in self._all_tree.get_children():
            self._all_tree.delete(item)

        try:
            account_svc = self._services.get("account_service")
            if account_svc is None:
                return

            all_users = account_svc.get_all_users_with_status()

            for user in all_users:
                self._all_tree.insert(
                    "", "end",
                    iid=f"all_{user.id}",
                    values=(
                        user.id,
                        user.username,
                        user.full_name or "—",
                        user.role.value,
                        user.account_status,
                        user.email or "—",
                        str(user.created_at)[:10],
                    ),
                    tags=(user.account_status,),
                )

        except Exception as e:
            show_error(self, "Error", f"Failed to load users: {e}")

    def _on_pending_selected(self, event=None):
        """Update detail panel when a pending user is selected."""
        sel = self._pending_tree.selection()
        if not sel:
            return

        user_id = int(sel[0])
        try:
            user_repo = self._services.get("user_repo")
            if user_repo:
                user = user_repo.get_user(user_id)
                if user:
                    self._selected_user_data = user
                    self._detail_vars["Username"].set(user.username)
                    self._detail_vars["Full Name"].set(
                        user.full_name or "—"
                    )
                    self._detail_vars["Email"].set(user.email or "—")
                    self._detail_vars["Registered"].set(
                        str(user.created_at)[:16]
                    )
        except Exception as e:
            show_error(self, "Error", str(e))

    def _on_all_user_selected(self, event=None):
        """Store selected user from all users tab."""
        sel = self._all_tree.selection()
        if not sel:
            return

        # Extract user_id from "all_123" format iid
        user_id = int(sel[0].replace("all_", ""))
        try:
            user_repo = self._services.get("user_repo")
            if user_repo:
                self._selected_user_data = user_repo.get_user(user_id)
        except Exception as e:
            show_error(self, "Error", str(e))

    # ── Actions ────────────────────────────────────────────────────────────────

    def _approve_selected(self):
        """Approve the selected pending registration."""
        if not self._selected_user_data:
            show_info(
                self, "Select Account",
                "Please select a pending registration to approve."
            )
            return

        user = self._selected_user_data
        if user.account_status != AccountStatus.PENDING:
            show_error(
                self, "Not Pending",
                f"'{user.username}' is not in PENDING state."
            )
            return

        note = self._approve_note.get("1.0", "end-1c").strip()

        if not confirm(
            self, "Approve Registration",
            f"Approve registration for:\n\n"
            f"Username : {user.username}\n"
            f"Name     : {user.full_name or '—'}\n"
            f"Email    : {user.email or '—'}\n\n"
            f"This will:\n"
            f"  • Activate the account\n"
            f"  • Create their learner profile\n"
            f"  • Send them a welcome notification\n\n"
            f"The learner will be able to log in immediately."
        ):
            return

        try:
            account_svc = self._services.get("account_service")
            if account_svc is None:
                show_error(self, "Error", "Account service unavailable.")
                return

            account_svc.approve_registration(
                user_id  = user.id,
                admin_id = self._user.id,
                note     = note,
            )

            show_info(
                self, "Approved",
                f"✅ Registration for '{user.username}' approved.\n\n"
                f"The learner can now log in to LMPTS."
            )

            self._selected_user_data = None
            self._clear_detail_panel()
            self._approve_note.delete("1.0", "end")
            self._load_data()

        except Exception as e:
            show_error(self, "Error", str(e))

    def _reject_selected(self):
        """Reject the selected pending registration."""
        if not self._selected_user_data:
            show_info(
                self, "Select Account",
                "Please select a pending registration to reject."
            )
            return

        user   = self._selected_user_data
        reason = self._reject_reason.get("1.0", "end-1c").strip()

        if not reason:
            show_error(
                self, "Reason Required",
                "Please enter a rejection reason.\n\n"
                "The learner will see this reason when they "
                "attempt to log in."
            )
            self._reject_reason.focus()
            return

        if user.account_status != AccountStatus.PENDING:
            show_error(
                self, "Not Pending",
                f"'{user.username}' is not in PENDING state."
            )
            return

        if not confirm(
            self, "Reject Registration",
            f"Reject registration for '{user.username}'?\n\n"
            f"Rejection reason:\n{reason}\n\n"
            f"The learner will see this reason when they try to log in.\n"
            f"Their account data will be kept in case of reactivation."
        ):
            return

        try:
            account_svc = self._services.get("account_service")
            if account_svc is None:
                show_error(self, "Error", "Account service unavailable.")
                return

            account_svc.reject_registration(
                user_id          = user.id,
                admin_id         = self._user.id,
                rejection_reason = reason,
            )

            show_info(
                self, "Rejected",
                f"Registration for '{user.username}' has been rejected.\n"
                f"The rejection reason has been recorded."
            )

            self._selected_user_data = None
            self._clear_detail_panel()
            self._reject_reason.delete("1.0", "end")
            self._load_data()

        except Exception as e:
            show_error(self, "Error", str(e))

    def _request_info(self):
        """Request additional information from the pending learner."""
        if not self._selected_user_data:
            show_info(
                self, "Select Account",
                "Please select a pending registration."
            )
            return

        user    = self._selected_user_data
        message = self._reject_reason.get("1.0", "end-1c").strip()

        if not message:
            show_error(
                self, "Message Required",
                "Please enter a message describing what "
                "additional information is needed."
            )
            return

        try:
            account_svc = self._services.get("account_service")
            if account_svc:
                account_svc.request_more_information(
                    user_id  = user.id,
                    admin_id = self._user.id,
                    message  = message,
                )

            show_info(
                self, "Information Requested",
                f"A message has been sent to '{user.username}' "
                f"requesting more information.\n\n"
                f"Their account remains PENDING until you approve or reject."
            )

            self._reject_reason.delete("1.0", "end")

        except Exception as e:
            show_error(self, "Error", str(e))

    def _reactivate_user(self):
        """Reactivate a rejected or deactivated user."""
        if not self._selected_user_data:
            show_info(self, "Select User",
                      "Please select a user from the All Users tab.")
            return

        user = self._selected_user_data
        if user.account_status == AccountStatus.ACTIVE and user.is_active:
            show_info(self, "Already Active",
                      f"'{user.username}' is already active.")
            return

        if not confirm(
            self, "Reactivate Account",
            f"Reactivate account for '{user.username}'?\n\n"
            f"Current status: {user.account_status}\n\n"
            f"The user will be able to log in immediately."
        ):
            return

        try:
            account_svc = self._services.get("account_service")
            if account_svc:
                account_svc.reactivate_user(
                    user_id  = user.id,
                    admin_id = self._user.id,
                )
            show_info(
                self, "Reactivated",
                f"Account '{user.username}' reactivated successfully."
            )
            self._load_data()
        except Exception as e:
            show_error(self, "Error", str(e))

    def _deactivate_user(self):
        """Deactivate an active user account."""
        if not self._selected_user_data:
            show_info(self, "Select User",
                      "Please select a user from the All Users tab.")
            return

        user = self._selected_user_data

        if not user.is_active:
            show_info(self, "Already Inactive",
                      f"'{user.username}' is already inactive.")
            return

        if not confirm(
            self, "Deactivate Account",
            f"Deactivate account for '{user.username}'?\n\n"
            f"The user will not be able to log in until reactivated."
        ):
            return

        try:
            account_svc = self._services.get("account_service")
            if account_svc:
                account_svc.deactivate_user(
                    user_id  = user.id,
                    admin_id = self._user.id,
                )
            show_info(
                self, "Deactivated",
                f"Account '{user.username}' deactivated."
            )
            self._load_data()
        except Exception as e:
            show_error(self, "Error", str(e))

    def _clear_detail_panel(self):
        """Reset the detail panel to empty state."""
        for var in self._detail_vars.values():
            var.set("—")