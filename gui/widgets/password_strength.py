"""
password_strength.py
--------------------
Reusable password strength meter widget.

Shows a coloured progress bar and text label that update as the
user types. Used in registration, password change, and any other
password entry form.
"""

import tkinter as tk
from tkinter import ttk
from services.profile_service import ProfileService


BG_DEFAULT = "#ffffff"


class PasswordStrengthMeter(tk.Frame):
    """
    Live password strength meter.

    Usage:
        meter = PasswordStrengthMeter(parent)
        meter.pack(fill="x")

        # Attach to an entry:
        entry = ttk.Entry(parent, show="*")
        entry.pack()
        entry.bind("<KeyRelease>",
            lambda e: meter.update_strength(entry.get())
        )

        # Check validity before submitting:
        if meter.is_valid():
            submit_password(entry.get())
    """

    def __init__(self, parent, bg: str = BG_DEFAULT, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self._bg = bg
        self._last_result: dict = {}
        self._build()

    def _build(self):
        """Build the strength meter widgets."""
        # Top row: label + progress bar + score label
        top = tk.Frame(self, bg=self._bg)
        top.pack(fill="x")

        tk.Label(
            top,
            text="Strength:",
            font=("Segoe UI", 8),
            bg=self._bg, fg="#666666",
        ).pack(side="left")

        self._bar = ttk.Progressbar(
            top,
            length=140,
            maximum=100,
            mode="determinate",
        )
        self._bar.pack(side="left", padx=6)

        self._score_label = tk.Label(
            top,
            text="",
            font=("Segoe UI", 8, "bold"),
            bg=self._bg, fg="#888888",
        )
        self._score_label.pack(side="left")

        # Bottom row: issues / hints
        self._issues_label = tk.Label(
            self,
            text="",
            font=("Segoe UI", 7),
            bg=self._bg, fg="#888888",
            anchor="w", justify="left",
            wraplength=280,
        )
        self._issues_label.pack(fill="x", pady=(2, 0))

    def update_strength(self, password: str) -> None:
        """
        Recalculate and display strength for the given password.

        Called on every keystroke in the password field.
        """
        result = ProfileService.calculate_password_strength(password)
        self._last_result = result

        self._bar["value"] = result["score"]
        self._score_label.config(
            text   = result["label"],
            fg     = result["colour"],
        )

        # Show issues if any
        if result["issues"]:
            issues_text = "  •  ".join(result["issues"])
            self._issues_label.config(
                text = f"⚠ {issues_text}",
                fg   = "#e67e22",
            )
        elif password and result["is_valid"]:
            self._issues_label.config(
                text = "✓ Password meets all requirements",
                fg   = "#27ae60",
            )
        else:
            self._issues_label.config(text="", fg="#888888")

    def is_valid(self) -> bool:
        """Return True if the last-checked password meets all rules."""
        return self._last_result.get("is_valid", False)

    def get_score(self) -> int:
        """Return the last calculated strength score (0-100)."""
        return self._last_result.get("score", 0)

    def reset(self) -> None:
        """Reset the meter to empty state."""
        self._bar["value"] = 0
        self._score_label.config(text="")
        self._issues_label.config(text="")
        self._last_result = {}