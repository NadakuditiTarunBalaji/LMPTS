"""
register_window.py
------------------
Self-registration window for new learners.

Opened from the login screen via "Register" button.
Creates account with PENDING status — admin must approve.

Layout:
    ┌──────────────────────────────────┐
    │   Create Your LMPTS Account      │
    ├──────────────────────────────────┤
    │  Full Name     [______________]  │
    │  Email         [______________]  │
    │  Username      [______________]  │
    │  Password      [______________]  │
    │  Confirm Pass  [______________]  │
    │                                  │
    │  Password strength: ████░░ Fair  │
    │                                  │
    │         [ REGISTER ]             │
    │                                  │
    │  ⚠ Error message here            │
    │                                  │
    │  Already have an account? Login  │
    └──────────────────────────────────┘
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


BG_OUTER  = "#1a3a5c"
BG_CARD   = "#ffffff"
FG_LABEL  = "#333333"
FG_ERROR  = "#c0392b"
FG_SUCCESS = "#27ae60"
FG_HINT   = "#888888"
BTN_BG    = "#1a3a5c"
BTN_FG    = "#ffffff"
BTN_HOVER = "#2d5986"


class RegisterWindow(tk.Toplevel):
    """
    Self-registration window for new learners.

    Opened from the LoginWindow.
    On successful registration, shows pending message.
    Account requires admin approval before first login.

    Args:
        parent           : Parent window (LoginWindow).
        services         : Global service container.
        on_back_to_login : Callback to return to login screen.
    """

    def __init__(
        self,
        parent,
        services:          dict,
        on_back_to_login:  Callable,
    ):
        super().__init__(parent)
        self._services        = services
        self._on_back         = on_back_to_login

        self.title("LMPTS — Create Account")
        self.geometry("500x660")
        self.resizable(False, False)
        self.configure(bg=BG_OUTER)

        # Centre on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 500) // 2
        y = (self.winfo_screenheight() - 660) // 2
        self.geometry(f"500x660+{x}+{y}")

        # Make modal relative to parent
        self.grab_set()
        self.focus_set()

        self._build()

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build(self):
        """Build the registration form."""

        # Outer wrapper centred in window
        outer = tk.Frame(self, bg=BG_OUTER)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        # ── Header ────────────────────────────────────────────────────────────
        tk.Label(
            outer,
            text="LMPTS",
            font=("Segoe UI", 22, "bold"),
            bg=BG_OUTER, fg="#ffffff",
        ).pack(pady=(0, 4))

        tk.Label(
            outer,
            text="Create Your Learner Account",
            font=("Segoe UI", 10),
            bg=BG_OUTER, fg="#a8c8e8",
        ).pack(pady=(0, 18))

        # ── White card ────────────────────────────────────────────────────────
        card = tk.Frame(
            outer, bg=BG_CARD,
            padx=35, pady=25,
        )
        card.pack()

        def labeled_entry(
            label_text: str,
            show: str = "",
            hint: str = "",
        ) -> ttk.Entry:
            """Create a labeled entry field."""
            tk.Label(
                card,
                text=label_text,
                font=("Segoe UI", 9, "bold"),
                bg=BG_CARD, fg=FG_LABEL,
                anchor="w",
            ).pack(fill="x", pady=(6, 1))

            entry = ttk.Entry(
                card,
                font=("Segoe UI", 10),
                width=32,
                show=show,
            )
            entry.pack(fill="x", ipady=4)

            if hint:
                tk.Label(
                    card,
                    text=hint,
                    font=("Segoe UI", 7),
                    bg=BG_CARD, fg=FG_HINT,
                    anchor="w",
                ).pack(fill="x")

            return entry

        # Form fields
        self._name_entry  = labeled_entry(
            "Full Name *",
            hint="Your real name as it will appear on certificates",
        )
        self._email_entry = labeled_entry(
            "Email Address *",
            hint="Used for notifications and account recovery",
        )
        self._user_entry  = labeled_entry(
            "Username *",
            hint="3–20 characters, letters and numbers only",
        )
        self._pass_entry  = labeled_entry(
            "Password *",
            show="•",
            hint="At least 8 characters",
        )
        self._conf_entry  = labeled_entry(
            "Confirm Password *",
            show="•",
        )

        # Bind password field to strength indicator
        self._pass_entry.bind("<KeyRelease>", self._update_strength)

        # Password strength bar
        strength_frame = tk.Frame(card, bg=BG_CARD)
        strength_frame.pack(fill="x", pady=(6, 0))

        tk.Label(
            strength_frame,
            text="Strength:",
            font=("Segoe UI", 8),
            bg=BG_CARD, fg=FG_HINT,
        ).pack(side="left")

        self._strength_bar = ttk.Progressbar(
            strength_frame,
            length=120,
            maximum=100,
            mode="determinate",
        )
        self._strength_bar.pack(side="left", padx=6)

        self._strength_label = tk.Label(
            strength_frame,
            text="",
            font=("Segoe UI", 8),
            bg=BG_CARD, fg=FG_HINT,
        )
        self._strength_label.pack(side="left")

        tk.Frame(card, height=12, bg=BG_CARD).pack()

        # Register button
        self._register_btn = tk.Button(
            card,
            text="CREATE ACCOUNT",
            font=("Segoe UI", 10, "bold"),
            bg=BTN_BG, fg=BTN_FG,
            activebackground=BTN_HOVER,
            activeforeground=BTN_FG,
            relief="flat", cursor="hand2",
            width=26, pady=8,
            command=self._attempt_register,
        )
        self._register_btn.pack(fill="x")

        self._register_btn.bind(
            "<Enter>",
            lambda e: self._register_btn.config(bg=BTN_HOVER)
        )
        self._register_btn.bind(
            "<Leave>",
            lambda e: self._register_btn.config(bg=BTN_BG)
        )

        tk.Frame(card, height=8, bg=BG_CARD).pack()

        # Error / status label
        self._status_var = tk.StringVar()
        self._status_label = tk.Label(
            card,
            textvariable=self._status_var,
            font=("Segoe UI", 9),
            bg=BG_CARD, fg=FG_ERROR,
            wraplength=320,
            justify="center",
        )
        self._status_label.pack()

        # Back to login link
        back_frame = tk.Frame(outer, bg=BG_OUTER)
        back_frame.pack(pady=(12, 0))

        tk.Label(
            back_frame,
            text="Already have an account?",
            font=("Segoe UI", 9),
            bg=BG_OUTER, fg="#a8c8e8",
        ).pack(side="left")

        back_btn = tk.Label(
            back_frame,
            text=" Log In",
            font=("Segoe UI", 9, "bold", "underline"),
            bg=BG_OUTER, fg="#ffffff",
            cursor="hand2",
        )
        back_btn.pack(side="left")
        back_btn.bind("<Button-1>", lambda e: self._go_back())

        # Bind Enter key
        self.bind("<Return>", lambda e: self._attempt_register())

        # Focus first field
        self._name_entry.focus()

    # ── Password Strength ──────────────────────────────────────────────────────

    def _update_strength(self, event=None):
        """Update password strength indicator as user types."""
        password = self._pass_entry.get()
        score, label, colour = self._calculate_strength(password)

        self._strength_bar["value"] = score
        self._strength_label.config(text=label, fg=colour)

    def _calculate_strength(self, password: str) -> tuple:
        """
        Calculate password strength score.

        Returns:
            tuple: (score 0-100, label text, colour hex)
        """
        if not password:
            return 0, "", FG_HINT

        score = 0

        # Length scoring
        if len(password) >= 8:  score += 25
        if len(password) >= 12: score += 15
        if len(password) >= 16: score += 10

        # Complexity scoring
        if any(c.isupper()  for c in password): score += 15
        if any(c.islower()  for c in password): score += 15
        if any(c.isdigit()  for c in password): score += 10
        if any(not c.isalnum() for c in password): score += 10

        score = min(score, 100)

        if score < 30:
            return score, "Weak",   "#e74c3c"
        elif score < 60:
            return score, "Fair",   "#e67e22"
        elif score < 80:
            return score, "Good",   "#3498db"
        else:
            return score, "Strong", "#27ae60"

    # ── Registration Logic ─────────────────────────────────────────────────────

    def _attempt_register(self):
        """Validate form and attempt registration."""
        self._status_var.set("")

        # Collect values
        full_name = self._name_entry.get().strip()
        email     = self._email_entry.get().strip()
        username  = self._user_entry.get().strip()
        password  = self._pass_entry.get()
        confirm   = self._conf_entry.get()

        # ── Client-side validation ─────────────────────────────────────────────

        if not full_name:
            self._show_error("Please enter your full name.")
            self._name_entry.focus()
            return

        if not email:
            self._show_error("Please enter your email address.")
            self._email_entry.focus()
            return

        if "@" not in email or "." not in email:
            self._show_error(
                "Please enter a valid email address (e.g. user@example.com)."
            )
            self._email_entry.focus()
            return

        if not username:
            self._show_error("Please enter a username.")
            self._user_entry.focus()
            return

        if len(username) < 3:
            self._show_error("Username must be at least 3 characters.")
            self._user_entry.focus()
            return

        if len(username) > 20:
            self._show_error("Username must be 20 characters or less.")
            self._user_entry.focus()
            return

        if not username.replace("_", "").isalnum():
            self._show_error(
                "Username can only contain letters, numbers, and underscores."
            )
            self._user_entry.focus()
            return

        if len(password) < 8:
            self._show_error("Password must be at least 8 characters.")
            self._pass_entry.focus()
            return

        if password != confirm:
            self._show_error(
                "Passwords do not match. Please re-enter your password."
            )
            self._conf_entry.delete(0, "end")
            self._conf_entry.focus()
            return

        # ── Server-side registration ───────────────────────────────────────────

        try:
            auth = self._services.get("auth_service")
            if auth is None:
                self._show_error("Authentication service unavailable.")
                return

            user = auth.register_learner(
                username  = username,
                password  = password,
                full_name = full_name,
                email     = email,
            )

            # Notify all admins of new registration
            self._notify_admins_of_registration(user)

            # Show success screen
            self._show_success(username)

        except Exception as e:
            error_msg = str(e)
            if "already taken" in error_msg.lower():
                self._show_error(
                    f"Username '{username}' is already taken. "
                    f"Please choose a different username."
                )
                self._user_entry.select_range(0, "end")
                self._user_entry.focus()
            else:
                self._show_error(f"Registration failed: {error_msg}")

    def _notify_admins_of_registration(self, user) -> None:
        """Send notification to all admins about new registration."""
        try:
            notif_repo = self._services.get("notification_repo")
            user_repo  = self._services.get("user_repo")
            if not notif_repo or not user_repo:
                return

            from core.enums import UserRole
            from core.notification import Notification, NotificationType

            admins = user_repo.find_by_role(UserRole.ADMIN)
            for admin in admins:
                notif_repo.create(Notification(
                    user_id           = admin.id,
                    message           = (
                        f"🔔 New learner registration pending approval: "
                        f"'{user.username}' "
                        f"({user.full_name}, {user.email}). "
                        f"Go to Pending Registrations to review."
                    ),
                    notification_type = NotificationType.INFO,
                ))
        except Exception as e:
            print(f"Admin notification error: {e}")

    def _show_success(self, username: str):
        """Replace form with success message after registration."""
        # Clear the window
        for widget in self.winfo_children():
            widget.destroy()

        self.configure(bg=BG_OUTER)

        # Success content
        success_frame = tk.Frame(self, bg=BG_OUTER)
        success_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Big checkmark
        tk.Label(
            success_frame,
            text="✓",
            font=("Segoe UI", 60),
            bg=BG_OUTER, fg="#27ae60",
        ).pack(pady=(0, 10))

        tk.Label(
            success_frame,
            text="Registration Successful!",
            font=("Segoe UI", 18, "bold"),
            bg=BG_OUTER, fg="#ffffff",
        ).pack()

        tk.Label(
            success_frame,
            text=f"Welcome, {username}!",
            font=("Segoe UI", 12),
            bg=BG_OUTER, fg="#a8c8e8",
        ).pack(pady=(4, 20))

        # Pending message card
        card = tk.Frame(
            success_frame, bg=BG_CARD,
            padx=30, pady=20,
        )
        card.pack()

        tk.Label(
            card,
            text="⏳  Account Pending Approval",
            font=("Segoe UI", 12, "bold"),
            bg=BG_CARD, fg="#e67e22",
        ).pack(pady=(0, 10))

        tk.Label(
            card,
            text=(
                "Your account has been created and is pending\n"
                "administrator approval.\n\n"
                "Please wait for the administrator to review\n"
                "your registration. You will be able to log in\n"
                "once your account is approved.\n\n"
                "If you have questions, please contact the\n"
                "LMPTS administrator."
            ),
            font=("Segoe UI", 10),
            bg=BG_CARD, fg="#333333",
            justify="center",
        ).pack()

        tk.Frame(card, height=15, bg=BG_CARD).pack()

        # Back to login button
        tk.Button(
            card,
            text="Back to Login",
            font=("Segoe UI", 10, "bold"),
            bg=BTN_BG, fg=BTN_FG,
            relief="flat", cursor="hand2",
            width=20, pady=8,
            command=self._go_back,
        ).pack(fill="x")

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _show_error(self, message: str):
        """Display an error message below the register button."""
        self._status_var.set(f"⚠  {message}")
        self._status_label.config(fg=FG_ERROR)

    def _go_back(self):
        """Close registration window and return to login."""
        self.destroy()
        self._on_back()