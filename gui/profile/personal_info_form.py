"""
personal_info_form.py
---------------------
Reusable form component for editing personal information.

Handles:
    - Full name
    - Email
    - Bio / About Me
    - Preferred Difficulty (learners only)

Read-only fields:
    - Username (cannot be changed)
    - Role
    - Account created date
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from core.user import User
from core.enums import UserRole, DifficultyLevel
from gui.dialogs.confirm_dialog import confirm, show_error, show_info


CARD_BG    = "#ffffff"
HEADER_COL = "#1a3a5c"
LABEL_COL  = "#333333"
HINT_COL   = "#888888"
BTN_BG     = "#1a3a5c"


class PersonalInfoForm(tk.Frame):
    """
    Form for editing personal profile information.

    Usage:
        form = PersonalInfoForm(
            parent,
            user=current_user,
            on_save=save_callback,
        )
        form.pack(fill="both", expand=True)
    """

    def __init__(
        self,
        parent,
        user:    User,
        on_save: Callable[[dict], None],
        **kwargs,
    ):
        super().__init__(parent, bg=CARD_BG, **kwargs)
        self._user    = user
        self._on_save = on_save
        self._build()
        self._populate()

    def _build(self):
        """Build the personal info form."""

        # Section title
        tk.Label(
            self,
            text="Personal Information",
            font=("Segoe UI", 13, "bold"),
            bg=CARD_BG, fg=HEADER_COL,
        ).pack(anchor="w", padx=20, pady=(15, 5))

        tk.Label(
            self,
            text="Update your name, email, and personal details.",
            font=("Segoe UI", 9),
            bg=CARD_BG, fg=HINT_COL,
        ).pack(anchor="w", padx=20, pady=(0, 15))

        # Form container
        form = tk.Frame(self, bg=CARD_BG, padx=20)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        # ── Username (read-only) ──────────────────────────────────────────────
        self._add_readonly_field(form, 0, "Username", self._user.username)

        # ── Role (read-only) ───────────────────────────────────────────────────
        self._add_readonly_field(form, 1, "Role", self._user.role.value)

        # ── Account Created (read-only) ───────────────────────────────────────
        self._add_readonly_field(
            form, 2, "Member Since",
            str(self._user.created_at)[:10]
        )

        ttk.Separator(form, orient="horizontal").grid(
            row=3, column=0, columnspan=2,
            sticky="ew", pady=15
        )

        # ── Full Name (editable) ───────────────────────────────────────────────
        self._name_entry = self._add_editable_field(
            form, 4,
            label="Full Name *",
            hint="Your real name as it appears on certificates"
        )

        # ── Email (editable) ───────────────────────────────────────────────────
        self._email_entry = self._add_editable_field(
            form, 6,
            label="Email Address *",
            hint="Used for notifications and account communications"
        )

        # ── Bio (editable) ─────────────────────────────────────────────────────
        tk.Label(
            form, text="Bio / About Me",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg=LABEL_COL, anchor="w",
        ).grid(row=8, column=0, sticky="w", pady=(8, 2))

        self._bio_text = tk.Text(
            form, width=40, height=4,
            font=("Segoe UI", 10),
            relief="solid", bd=1, wrap="word",
        )
        self._bio_text.grid(
            row=9, column=0, columnspan=2,
            sticky="ew", padx=(0, 20)
        )

        # Bio character counter
        self._bio_counter = tk.Label(
            form, text="0 / 500 characters",
            font=("Segoe UI", 8),
            bg=CARD_BG, fg=HINT_COL, anchor="e",
        )
        self._bio_counter.grid(row=10, column=1, sticky="e")
        self._bio_text.bind("<KeyRelease>", self._update_bio_counter)

        # ── Preferred Difficulty (learners only) ──────────────────────────────
        if self._user.role == UserRole.LEARNER:
            tk.Label(
                form, text="Preferred Difficulty Level",
                font=("Segoe UI", 9, "bold"),
                bg=CARD_BG, fg=LABEL_COL, anchor="w",
            ).grid(row=11, column=0, sticky="w", pady=(15, 2))

            tk.Label(
                form,
                text="Used to personalize course recommendations",
                font=("Segoe UI", 8),
                bg=CARD_BG, fg=HINT_COL, anchor="w",
            ).grid(row=12, column=0, sticky="w")

            self._difficulty_var = tk.StringVar(
                value=self._user.preferred_difficulty.value
            )
            diff_frame = tk.Frame(form, bg=CARD_BG)
            diff_frame.grid(
                row=13, column=0, columnspan=2,
                sticky="w", pady=5
            )
            for level in DifficultyLevel:
                ttk.Radiobutton(
                    diff_frame,
                    text=level.value.title(),
                    variable=self._difficulty_var,
                    value=level.value,
                ).pack(side="left", padx=10)
        else:
            self._difficulty_var = None

        # ── Buttons ────────────────────────────────────────────────────────────
        button_row = tk.Frame(self, bg=CARD_BG, pady=20, padx=20)
        button_row.pack(fill="x")

        tk.Button(
            button_row,
            text="Reset Changes",
            font=("Segoe UI", 9),
            bg="#e0e0e0", fg="#333333",
            relief="flat", cursor="hand2",
            padx=15, pady=6,
            command=self._reset,
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            button_row,
            text="💾  Save Changes",
            font=("Segoe UI", 9, "bold"),
            bg=BTN_BG, fg="#ffffff",
            activebackground="#2d5986",
            relief="flat", cursor="hand2",
            padx=20, pady=6,
            command=self._save,
        ).pack(side="right")

    def _add_readonly_field(self, parent, row, label, value):
        """Add a labeled read-only field."""
        tk.Label(
            parent, text=f"{label}:",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg=HINT_COL, anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=3)

        tk.Label(
            parent, text=value,
            font=("Segoe UI", 10),
            bg=CARD_BG, fg="#333333", anchor="w",
        ).grid(row=row, column=1, sticky="w", pady=3, padx=(20, 0))

    def _add_editable_field(
        self, parent, row, label, hint=""
    ) -> ttk.Entry:
        """Add a labeled editable field with optional hint."""
        tk.Label(
            parent, text=label,
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, fg=LABEL_COL, anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(8, 2))

        entry = ttk.Entry(
            parent, width=40,
            font=("Segoe UI", 10),
        )
        entry.grid(
            row=row + 1, column=0, columnspan=2,
            sticky="ew", padx=(0, 20), ipady=3
        )

        if hint:
            tk.Label(
                parent, text=hint,
                font=("Segoe UI", 8),
                bg=CARD_BG, fg=HINT_COL, anchor="w",
            ).grid(row=row + 1, column=2, sticky="w", padx=5)

        return entry

    def _populate(self):
        """Fill form fields with current user data."""
        self._name_entry.insert(0, self._user.full_name or "")
        self._email_entry.insert(0, self._user.email or "")
        self._bio_text.insert("1.0", self._user.bio or "")
        self._update_bio_counter()

    def _reset(self):
        """Reset form to original values."""
        self._name_entry.delete(0, "end")
        self._email_entry.delete(0, "end")
        self._bio_text.delete("1.0", "end")
        if self._difficulty_var:
            self._difficulty_var.set(
                self._user.preferred_difficulty.value
            )
        self._populate()

    def _update_bio_counter(self, event=None):
        """Update the bio character counter."""
        text = self._bio_text.get("1.0", "end-1c")
        length = len(text)
        colour = "#e74c3c" if length > 500 else HINT_COL
        self._bio_counter.config(
            text=f"{length} / 500 characters",
            fg=colour,
        )

    def _save(self):
        """Validate and save changes."""
        full_name = self._name_entry.get().strip()
        email     = self._email_entry.get().strip()
        bio       = self._bio_text.get("1.0", "end-1c").strip()

        if not full_name:
            show_error(self, "Validation", "Full name is required.")
            self._name_entry.focus()
            return

        if not email:
            show_error(self, "Validation", "Email is required.")
            self._email_entry.focus()
            return

        if len(bio) > 500:
            show_error(
                self, "Validation",
                "Bio must be 500 characters or less."
            )
            return

        # Confirmation
        if not confirm(
            self, "Save Changes",
            "Save changes to your personal information?"
        ):
            return

        # Build payload
        payload = {
            "full_name": full_name,
            "email":     email,
            "bio":       bio,
        }

        if self._difficulty_var:
            payload["preferred_difficulty"] = DifficultyLevel(
                self._difficulty_var.get()
            )

        # Delegate to parent screen
        self._on_save(payload)