"""
password_change_form.py
-----------------------
Reusable form component for changing password.

Features:
    - Old password + new password + confirm fields
    - Live password strength meter
    - Complexity requirements displayed
    - After success, triggers logout for security
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable

from gui.widgets.password_strength import PasswordStrengthMeter
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CARD_BG    = "#ffffff"
HEADER_COL = "#1a3a5c"
LABEL_COL  = "#333333"
HINT_COL   = "#888888"
BTN_BG     = "#1a3a5c"


class PasswordChangeForm(tk.Frame):
    """
    Password change form with live strength meter.

    Usage:
        form = PasswordChangeForm(
            parent,
            on_submit=change_password_callback,
        )
        form.pack(fill="both", expand=True)
    """

    def __init__(
        self,
        parent,
        on_submit: Callable[[str, str], None],
        **kwargs,
    ):
        super().__init__(parent, bg=CARD_BG, **kwargs)
        self._on_submit = on_submit
        self._build()

    def _build(self):
        """Build the password change form."""

        # Section title
        tk.Label(
            self,
            text="Change Password",
            font=("Segoe UI", 13, "bold"),
            bg=CARD_BG, fg=HEADER_COL,
        ).pack(anchor="w", padx=20, pady=(15, 5))

        tk.Label(
            self,
            text=(
                "For security, you will be logged out after "
                "changing your password."
            ),
            font=("Segoe UI", 9),
            bg=CARD_BG, fg="#e67e22",
        ).pack(anchor="w", padx=20, pady=(0, 15))

        # Form container
        form = tk.Frame(self, bg=CARD_BG, padx=20)
        form.pack(fill="x")

        # ── Old Password ───────────────────────────────────────────────────────
        tk.Label(
            form, text="Current Password *",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg=LABEL_COL, anchor="w",
        ).pack(fill="x", pady=(0, 2))

        self._old_entry = ttk.Entry(
            form, show="•",
            font=("Segoe UI", 10), width=40,
        )
        self._old_entry.pack(fill="x", ipady=4)

        tk.Frame(form, height=12, bg=CARD_BG).pack()

        # ── New Password ───────────────────────────────────────────────────────
        tk.Label(
            form, text="New Password *",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg=LABEL_COL, anchor="w",
        ).pack(fill="x", pady=(0, 2))

        self._new_entry = ttk.Entry(
            form, show="•",
            font=("Segoe UI", 10), width=40,
        )
        self._new_entry.pack(fill="x", ipady=4)

        # ── Password Strength Meter ────────────────────────────────────────────
        self._strength_meter = PasswordStrengthMeter(form, bg=CARD_BG)
        self._strength_meter.pack(fill="x", pady=(4, 8))

        self._new_entry.bind(
            "<KeyRelease>",
            lambda e: self._strength_meter.update_strength(
                self._new_entry.get()
            )
        )

        tk.Frame(form, height=8, bg=CARD_BG).pack()

        # ── Confirm New Password ───────────────────────────────────────────────
        tk.Label(
            form, text="Confirm New Password *",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg=LABEL_COL, anchor="w",
        ).pack(fill="x", pady=(0, 2))

        self._confirm_entry = ttk.Entry(
            form, show="•",
            font=("Segoe UI", 10), width=40,
        )
        self._confirm_entry.pack(fill="x", ipady=4)

        # Live confirm match indicator
        self._match_label = tk.Label(
            form, text="",
            font=("Segoe UI", 8),
            bg=CARD_BG, fg=HINT_COL, anchor="w",
        )
        self._match_label.pack(fill="x", pady=(2, 0))

        self._confirm_entry.bind(
            "<KeyRelease>", lambda e: self._check_match()
        )

        # ── Password Requirements ──────────────────────────────────────────────
        req_frame = tk.LabelFrame(
            form,
            text="  Password Requirements",
            font=("Segoe UI", 8, "bold"),
            bg=CARD_BG, fg=HINT_COL,
            relief="flat", padx=10, pady=6,
        )
        req_frame.pack(fill="x", pady=(15, 0))

        requirements = [
            "• At least 8 characters",
            "• At least one uppercase letter (A-Z)",
            "• At least one digit (0-9)",
            "• Must differ from your current password",
        ]
        for req in requirements:
            tk.Label(
                req_frame, text=req,
                font=("Segoe UI", 8),
                bg=CARD_BG, fg="#666666", anchor="w",
            ).pack(fill="x", pady=1)

        # ── Buttons ────────────────────────────────────────────────────────────
        button_row = tk.Frame(self, bg=CARD_BG, pady=20, padx=20)
        button_row.pack(fill="x")

        tk.Button(
            button_row,
            text="Clear",
            font=("Segoe UI", 9),
            bg="#e0e0e0", fg="#333333",
            relief="flat", cursor="hand2",
            padx=15, pady=6,
            command=self._clear,
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            button_row,
            text="🔒  Change Password",
            font=("Segoe UI", 9, "bold"),
            bg=BTN_BG, fg="#ffffff",
            activebackground="#2d5986",
            relief="flat", cursor="hand2",
            padx=20, pady=6,
            command=self._submit,
        ).pack(side="right")

    def _check_match(self):
        """Show whether confirm password matches new password."""
        new     = self._new_entry.get()
        confirm = self._confirm_entry.get()

        if not confirm:
            self._match_label.config(text="", fg=HINT_COL)
        elif new == confirm:
            self._match_label.config(
                text="✓ Passwords match",
                fg="#27ae60",
            )
        else:
            self._match_label.config(
                text="✗ Passwords do not match",
                fg="#e74c3c",
            )

    def _clear(self):
        """Clear all password fields."""
        self._old_entry.delete(0, "end")
        self._new_entry.delete(0, "end")
        self._confirm_entry.delete(0, "end")
        self._strength_meter.reset()
        self._match_label.config(text="")

    def _submit(self):
        """Validate and submit password change."""
        old_pw     = self._old_entry.get()
        new_pw     = self._new_entry.get()
        confirm_pw = self._confirm_entry.get()

        # Client-side validation
        if not old_pw:
            show_error(self, "Required", "Please enter your current password.")
            self._old_entry.focus()
            return

        if not new_pw:
            show_error(self, "Required", "Please enter a new password.")
            self._new_entry.focus()
            return

        if not confirm_pw:
            show_error(self, "Required",
                       "Please confirm your new password.")
            self._confirm_entry.focus()
            return

        if new_pw != confirm_pw:
            show_error(
                self, "Passwords Do Not Match",
                "The new password and confirmation do not match."
            )
            self._confirm_entry.delete(0, "end")
            self._confirm_entry.focus()
            return

        if not self._strength_meter.is_valid():
            show_error(
                self, "Weak Password",
                "Your new password does not meet the requirements. "
                "Please choose a stronger password."
            )
            self._new_entry.focus()
            return

        # Confirmation dialog
        if not confirm(
            self, "Change Password",
            "You are about to change your password.\n\n"
            "After the change, you will be logged out for security "
            "and must log in again with your new password.\n\n"
            "Continue?"
        ):
            return

        # Delegate to parent screen
        self._on_submit(old_pw, new_pw)