"""
user_management.py
------------------
Manage system user accounts (Admin, Learner, Analyst, Instructor).
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from core.user import User
from core.enums import UserRole
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


class UserManagementScreen(tk.Frame):
    """
    User account management interface.

    Features:
        - View all users in a table
        - Create new user account
        - Delete user account (with confirmation)
        - Change user password
    """

    def __init__(self, parent, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._services = services
        self._build()
        self._load_users()

    def _build(self):
        """Build the user management UI."""
        # Title
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)

        tk.Label(
            title_frame,
            text="User Management",
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
            command=self._load_users,
        ).pack(side="right")

        # Users table
        table_frame = tk.Frame(self, bg=CONTENT_BG)
        table_frame.pack(fill="both", expand=True, padx=20)

        cols = ("id", "username", "role", "created")
        self._tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            selectmode="browse",
        )
        for col, header, width in [
            ("id",       "ID",       50),
            ("username", "Username", 150),
            ("role",     "Role",     120),
            ("created",  "Created",  160),
        ]:
            self._tree.heading(col, text=header)
            self._tree.column(col, width=width)

        scroll = ttk.Scrollbar(
            table_frame, orient="vertical",
            command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Role colour tags
        self._tree.tag_configure("ADMIN",      background="#fff3e0")
        self._tree.tag_configure("LEARNER",    background="#e8f5e9")
        self._tree.tag_configure("ANALYST",    background="#e3f2fd")
        self._tree.tag_configure("INSTRUCTOR", background="#fce4ec")

        # Action buttons
        btn_frame = tk.Frame(self, bg=CONTENT_BG, pady=10)
        btn_frame.pack(fill="x", padx=20)

        buttons = [
            ("➕ Add User",       "#27ae60", self._add_user),
            ("🗑️ Delete User",    "#e74c3c", self._delete_user),
            ("🔑 Change Password", "#3498db", self._change_password),
        ]

        for text, colour, cmd in buttons:
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

    def _load_users(self):
        """Load all users into the table."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        try:
            auth = self._services.get("auth_service")
            if auth is None:
                return

            # Access the repository directly for user listing
            repo = self._services.get("user_repo")
            if repo is None:
                show_error(self, "Error", "User repository not available.")
                return

            users = repo.get_all_users()
            for user in users:
                self._tree.insert(
                    "", "end",
                    iid=str(user.id),
                    values=(
                        user.id,
                        user.username,
                        user.role.value,
                        user.created_at.strftime("%Y-%m-%d %H:%M")
                        if hasattr(user.created_at, "strftime")
                        else str(user.created_at)[:16],
                    ),
                    tags=(user.role.value,),
                )
        except Exception as e:
            show_error(self, "Error", f"Failed to load users: {e}")

    def _get_selected_user_id(self) -> Optional[int]:
        """Return the ID of the selected user."""
        selection = self._tree.selection()
        if not selection:
            show_info(self, "Select User", "Please select a user.")
            return None
        return int(selection[0])

    def _add_user(self):
        """Open add user dialog."""
        dialog = AddUserDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            username, password, role = dialog.result
            try:
                auth = self._services["auth_service"]
                auth.register(username, password, role)
                show_info(self, "Created", f"User '{username}' created.")
                self._load_users()
            except Exception as e:
                show_error(self, "Error", str(e))

    def _delete_user(self):
        """Delete the selected user."""
        user_id = self._get_selected_user_id()
        if user_id is None:
            return

        if confirm(
            self, "Delete User",
            "Permanently delete this user account?\n"
            "All associated data will be removed."
        ):
            try:
                repo = self._services["user_repo"]
                repo.delete_user(user_id)
                show_info(self, "Deleted", "User deleted successfully.")
                self._load_users()
            except Exception as e:
                show_error(self, "Error", str(e))

    def _change_password(self):
        """Change password for selected user."""
        user_id = self._get_selected_user_id()
        if user_id is None:
            return

        dialog = ChangePasswordDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            old_pw, new_pw = dialog.result
            try:
                auth = self._services["auth_service"]
                auth.change_password(user_id, old_pw, new_pw)
                show_info(self, "Success", "Password changed successfully.")
            except Exception as e:
                show_error(self, "Error", str(e))


class AddUserDialog(tk.Toplevel):
    """Dialog for creating a new user account."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add New User")
        self.geometry("380x300")
        self.resizable(False, False)
        self.configure(bg="#ffffff")
        self.grab_set()
        self.result = None
        self._build()

    def _build(self):
        form = tk.Frame(self, bg="#ffffff", padx=25, pady=20)
        form.pack(fill="both", expand=True)

        # Username
        tk.Label(form, text="Username *",
                 font=("Segoe UI", 9, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w")
        self._username = ttk.Entry(form, width=30, font=("Segoe UI", 10))
        self._username.pack(fill="x", pady=(2, 10))

        # Password
        tk.Label(form, text="Password * (min 8 chars)",
                 font=("Segoe UI", 9, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w")
        self._password = ttk.Entry(
            form, width=30, show="•", font=("Segoe UI", 10)
        )
        self._password.pack(fill="x", pady=(2, 10))

        # Role
        tk.Label(form, text="Role *",
                 font=("Segoe UI", 9, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w")
        self._role_var = tk.StringVar(value="LEARNER")
        role_combo = ttk.Combobox(
            form,
            textvariable=self._role_var,
            values=[r.value for r in UserRole],
            state="readonly",
            width=28,
        )
        role_combo.pack(fill="x", pady=(2, 15))

        # Buttons
        btn_frame = tk.Frame(form, bg="#ffffff")
        btn_frame.pack(fill="x")

        tk.Button(
            btn_frame, text="Cancel",
            bg="#e0e0e0", relief="flat",
            command=self.destroy
        ).pack(side="right", padx=(5, 0))

        tk.Button(
            btn_frame, text="Create User",
            bg="#1a3a5c", fg="#ffffff",
            relief="flat",
            command=self._save
        ).pack(side="right")

    def _save(self):
        username = self._username.get().strip()
        password = self._password.get()
        role_str = self._role_var.get()

        if not username or not password:
            from gui.dialogs.confirm_dialog import show_error
            show_error(self, "Error", "Username and password are required.")
            return

        self.result = (username, password, UserRole(role_str))
        self.destroy()


class ChangePasswordDialog(tk.Toplevel):
    """Dialog for changing a user's password."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Change Password")
        self.geometry("350x220")
        self.resizable(False, False)
        self.configure(bg="#ffffff")
        self.grab_set()
        self.result = None
        self._build()

    def _build(self):
        form = tk.Frame(self, bg="#ffffff", padx=25, pady=20)
        form.pack(fill="both", expand=True)

        tk.Label(form, text="Current Password *",
                 font=("Segoe UI", 9, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w")
        self._old_pw = ttk.Entry(form, show="•", font=("Segoe UI", 10))
        self._old_pw.pack(fill="x", pady=(2, 10))

        tk.Label(form, text="New Password * (min 8 chars)",
                 font=("Segoe UI", 9, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w")
        self._new_pw = ttk.Entry(form, show="•", font=("Segoe UI", 10))
        self._new_pw.pack(fill="x", pady=(2, 15))

        btn_frame = tk.Frame(form, bg="#ffffff")
        btn_frame.pack(fill="x")

        tk.Button(
            btn_frame, text="Cancel",
            bg="#e0e0e0", relief="flat",
            command=self.destroy
        ).pack(side="right", padx=(5, 0))

        tk.Button(
            btn_frame, text="Change Password",
            bg="#1a3a5c", fg="#ffffff",
            relief="flat",
            command=self._save
        ).pack(side="right")

    def _save(self):
        self.result = (self._old_pw.get(), self._new_pw.get())
        self.destroy()