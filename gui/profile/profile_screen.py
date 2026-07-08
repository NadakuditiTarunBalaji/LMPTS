"""
profile_screen.py
-----------------
Main profile screen with tabbed sections.

Tabs:
    1. Personal Information — name, email, bio, difficulty
    2. Change Password     — with strength meter and validation
    3. Account Details     — read-only account info

Available to all roles (Admin, Learner, Instructor, Analyst).
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable

from core.user import User
from core.exceptions import (
    ValidationError,
    AuthenticationError,
    LearnerNotFoundError,
)
from gui.profile.personal_info_form import PersonalInfoForm
from gui.profile.password_change_form import PasswordChangeForm
from gui.dialogs.confirm_dialog import show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"
HEADER_COL = "#1a3a5c"


class ProfileScreen(tk.Frame):
    """
    Profile management screen for all user roles.

    Layout:
        Header (user avatar + name)
        Tabs: Personal Info | Change Password | Account Details
    """

    def __init__(
        self,
        parent,
        user:             User,
        services:         dict,
        on_password_change: Callable = None,
    ):
        """
        Args:
            parent             : Parent frame.
            user               : Currently logged-in user.
            services           : Global service container.
            on_password_change : Callback triggered after successful
                                 password change (usually forces logout).
        """
        super().__init__(parent, bg=CONTENT_BG)
        self._user               = user
        self._services           = services
        self._on_password_change = on_password_change
        self._current_user_data  = user
        self._build()
        self._reload_user()

    def _build(self):
        """Build the profile screen layout."""

        # ── Page Title ─────────────────────────────────────────────────────────
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)

        tk.Label(
            title_frame,
            text="👤  My Profile",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg=HEADER_COL,
        ).pack(side="left")

        tk.Button(
            title_frame, text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat",
            cursor="hand2",
            command=self._reload_user,
        ).pack(side="right")

        # ── User Card Header ───────────────────────────────────────────────────
        header_card = tk.Frame(self, bg=CARD_BG, padx=25, pady=15)
        header_card.pack(fill="x", padx=20, pady=(0, 15))

        # Avatar (large circle with initial)
        avatar_frame = tk.Frame(
            header_card, bg=HEADER_COL,
            width=70, height=70,
        )
        avatar_frame.pack(side="left")
        avatar_frame.pack_propagate(False)

        initial = (
            self._user.full_name[0].upper()
            if self._user.full_name
            else self._user.username[0].upper()
        )
        tk.Label(
            avatar_frame, text=initial,
            font=("Segoe UI", 28, "bold"),
            bg=HEADER_COL, fg="#ffffff",
        ).place(relx=0.5, rely=0.5, anchor="center")

        # User info
        info_frame = tk.Frame(header_card, bg=CARD_BG)
        info_frame.pack(side="left", fill="both",
                        expand=True, padx=20)

        self._name_label = tk.Label(
            info_frame,
            text=self._user.full_name or self._user.username,
            font=("Segoe UI", 14, "bold"),
            bg=CARD_BG, fg=HEADER_COL, anchor="w",
        )
        self._name_label.pack(fill="x", anchor="w")

        tk.Label(
            info_frame,
            text=f"@{self._user.username}  •  {self._user.role.value}",
            font=("Segoe UI", 10),
            bg=CARD_BG, fg="#888888", anchor="w",
        ).pack(fill="x", anchor="w")

        self._email_label = tk.Label(
            info_frame,
            text=self._user.email or "No email set",
            font=("Segoe UI", 9),
            bg=CARD_BG, fg="#666666", anchor="w",
        )
        self._email_label.pack(fill="x", anchor="w", pady=(4, 0))

        # ── Notebook Tabs ──────────────────────────────────────────────────────
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(
            fill="both", expand=True,
            padx=20, pady=(0, 10)
        )

        # Tab 1: Personal Information
        self._personal_tab = tk.Frame(self._notebook, bg=CARD_BG)
        self._notebook.add(
            self._personal_tab, text="  📝  Personal Information  "
        )
        self._render_personal_tab()

        # Tab 2: Change Password
        self._password_tab = tk.Frame(self._notebook, bg=CARD_BG)
        self._notebook.add(
            self._password_tab, text="  🔒  Change Password  "
        )
        self._render_password_tab()

        # Tab 3: Account Details
        self._account_tab = tk.Frame(self._notebook, bg=CARD_BG)
        self._notebook.add(
            self._account_tab, text="  ⚙️  Account Details  "
        )
        self._render_account_tab()

    def _reload_user(self):
        """Reload user data from database."""
        try:
            profile_svc = self._services.get("profile_service")
            if profile_svc:
                self._current_user_data = profile_svc.get_profile(
                    self._user.id
                )
                # Update header
                self._name_label.config(
                    text=self._current_user_data.full_name
                         or self._current_user_data.username
                )
                self._email_label.config(
                    text=self._current_user_data.email or "No email set"
                )
                # Re-render tabs with fresh data
                self._render_personal_tab()
                self._render_account_tab()
        except Exception as e:
            show_error(self, "Error", f"Could not reload profile: {e}")

    # ── Personal Info Tab ──────────────────────────────────────────────────────

    def _render_personal_tab(self):
        """Render the personal information tab."""
        for widget in self._personal_tab.winfo_children():
            widget.destroy()

        PersonalInfoForm(
            self._personal_tab,
            user=self._current_user_data,
            on_save=self._handle_save_personal,
        ).pack(fill="both", expand=True)

    def _handle_save_personal(self, payload: dict):
        """Save personal information changes."""
        try:
            profile_svc = self._services.get("profile_service")
            if profile_svc is None:
                show_error(self, "Error", "Profile service unavailable.")
                return

            profile_svc.update_personal_info(
                user_id              = self._user.id,
                full_name            = payload["full_name"],
                email                = payload["email"],
                bio                  = payload.get("bio", ""),
                preferred_difficulty = payload.get(
                    "preferred_difficulty"
                ),
            )

            show_info(
                self, "Saved",
                "Your personal information has been updated successfully."
            )
            self._reload_user()

        except (ValidationError, LearnerNotFoundError) as e:
            show_error(self, "Error", str(e))
        except Exception as e:
            show_error(self, "Error", f"Failed to save: {e}")

    # ── Password Change Tab ────────────────────────────────────────────────────

    def _render_password_tab(self):
        """Render the change password tab."""
        for widget in self._password_tab.winfo_children():
            widget.destroy()

        PasswordChangeForm(
            self._password_tab,
            on_submit=self._handle_password_change,
        ).pack(fill="both", expand=True)

    def _handle_password_change(self, old_pw: str, new_pw: str):
        """Change password and trigger logout."""
        try:
            profile_svc = self._services.get("profile_service")
            if profile_svc is None:
                show_error(self, "Error", "Profile service unavailable.")
                return

            profile_svc.change_password(
                user_id      = self._user.id,
                old_password = old_pw,
                new_password = new_pw,
            )

            show_info(
                self, "Password Changed",
                "Your password has been changed successfully.\n\n"
                "You will now be logged out. "
                "Please log in again with your new password."
            )

            # Trigger logout callback
            if self._on_password_change:
                self._on_password_change()

        except AuthenticationError as e:
            show_error(self, "Wrong Password", str(e))
        except ValidationError as e:
            show_error(self, "Invalid Password", str(e))
        except Exception as e:
            show_error(self, "Error", f"Failed to change password: {e}")

    # ── Account Details Tab ────────────────────────────────────────────────────

    def _render_account_tab(self):
        """Render the read-only account details tab."""
        for widget in self._account_tab.winfo_children():
            widget.destroy()

        container = tk.Frame(self._account_tab, bg=CARD_BG, padx=20, pady=15)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="Account Details",
            font=("Segoe UI", 13, "bold"),
            bg=CARD_BG, fg=HEADER_COL,
        ).pack(anchor="w", pady=(0, 5))

        tk.Label(
            container,
            text="These details are managed by the system administrator.",
            font=("Segoe UI", 9),
            bg=CARD_BG, fg="#888888",
        ).pack(anchor="w", pady=(0, 15))

        u = self._current_user_data
        details = [
            ("User ID",           str(u.id)),
            ("Username",          u.username),
            ("Role",              u.role.value),
            ("Account Status",    u.account_status.value),
            ("Active",            "Yes" if u.is_active else "No"),
            ("Member Since",      str(u.created_at)[:16]),
            ("Last Profile Edit", str(u.profile_updated_at)[:16]
                                  if u.profile_updated_at
                                  else "Never"),
        ]

        for label, value in details:
            row = tk.Frame(container, bg=CARD_BG, pady=4)
            row.pack(fill="x")

            tk.Label(
                row, text=f"{label}:",
                font=("Segoe UI", 9, "bold"),
                bg=CARD_BG, fg="#888888",
                width=20, anchor="w",
            ).pack(side="left")

            tk.Label(
                row, text=value,
                font=("Segoe UI", 10),
                bg=CARD_BG, fg="#333333", anchor="w",
            ).pack(side="left")