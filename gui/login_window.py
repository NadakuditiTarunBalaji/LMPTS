"""
login_window.py
---------------
LMPTS Login Screen.

Layout:
    ┌──────────────────────────────────┐
    │                                  │
    │         LMPTS                    │
    │  Learning Management System      │
    │                                  │
    │  Username: [____________]        │
    │  Password: [____________]        │
    │  [ ] Remember me                 │
    │                                  │
    │        [ LOGIN ]                 │
    │                                  │
    │  ⚠ Error message here            │
    └──────────────────────────────────┘
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


# ── Colour Constants ───────────────────────────────────────────────────────────

BG_OUTER  = "#1a3a5c"   # Dark blue outer background
BG_CARD   = "#ffffff"   # White login card
FG_TITLE  = "#ffffff"
FG_LABEL  = "#333333"
FG_ERROR  = "#c0392b"
BTN_BG    = "#1a3a5c"
BTN_FG    = "#ffffff"
BTN_HOVER = "#2d5986"


class LoginWindow(tk.Tk):
    """
    Standalone login window.

    Displays the LMPTS login form and calls on_login_success
    with the authenticated user when login succeeds.

    Usage:
        def on_login(user, services):
            open_main_window(user, services)

        app = LoginWindow(services, on_login_success=on_login)
        app.mainloop()
    """

    def __init__(self, services: dict, on_login_success: Callable):
        super().__init__()

        self._services         = services
        self._on_login_success = on_login_success
        self._remember_var     = tk.BooleanVar(value=False)

        self.title("LMPTS — Login")
        self.geometry("480x560")
        self.resizable(False, False)
        self.configure(bg=BG_OUTER)

        # Centre window on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 480) // 2
        y = (self.winfo_screenheight() - 560) // 2
        self.geometry(f"480x560+{x}+{y}")

        self._build()

    # ── Build UI ───────────────────────────────────────────────────────────────

    def _build(self):
        """Construct all UI widgets."""

        # Outer padding frame
        outer = tk.Frame(self, bg=BG_OUTER)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        # ── Title above card ──────────────────────────────────────────────────
        tk.Label(
            outer,
            text="LMPTS",
            font=("Segoe UI", 28, "bold"),
            bg=BG_OUTER,
            fg=FG_TITLE,
        ).pack(pady=(0, 4))

        tk.Label(
            outer,
            text="Learning Management &\nPrerequisite Tracking System",
            font=("Segoe UI", 10),
            bg=BG_OUTER,
            fg="#a8c8e8",
            justify="center",
        ).pack(pady=(0, 20))

        # ── White card ────────────────────────────────────────────────────────
        card = tk.Frame(
            outer,
            bg=BG_CARD,
            padx=40,
            pady=35,
            relief="flat",
            bd=0,
        )
        card.pack()

        # Add subtle shadow effect (via border frame)
        shadow = tk.Frame(
            outer,
            bg="#cccccc",
            padx=41,
            pady=1,
        )

        # Username
        tk.Label(
            card,
            text="Username",
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD,
            fg=FG_LABEL,
            anchor="w",
        ).pack(fill="x", pady=(0, 3))

        self._username_var = tk.StringVar()
        self._username_entry = ttk.Entry(
            card,
            textvariable=self._username_var,
            font=("Segoe UI", 11),
            width=28,
        )
        self._username_entry.pack(fill="x", ipady=4)

        tk.Frame(card, height=12, bg=BG_CARD).pack()

        # Password
        tk.Label(
            card,
            text="Password",
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD,
            fg=FG_LABEL,
            anchor="w",
        ).pack(fill="x", pady=(0, 3))

        self._password_var = tk.StringVar()
        self._password_entry = ttk.Entry(
            card,
            textvariable=self._password_var,
            show="•",
            font=("Segoe UI", 11),
            width=28,
        )
        self._password_entry.pack(fill="x", ipady=4)

        tk.Frame(card, height=8, bg=BG_CARD).pack()

        # Remember me
        ttk.Checkbutton(
            card,
            text="Remember me",
            variable=self._remember_var,
        ).pack(anchor="w")

        tk.Frame(card, height=20, bg=BG_CARD).pack()

        # Login button
        self._login_btn = tk.Button(
            card,
            text="LOGIN",
            font=("Segoe UI", 11, "bold"),
            bg=BTN_BG,
            fg=BTN_FG,
            activebackground=BTN_HOVER,
            activeforeground=BTN_FG,
            relief="flat",
            cursor="hand2",
            width=24,
            pady=8,
            command=self._attempt_login,
        )
        self._login_btn.pack(fill="x")

        # Hover effect
        self._login_btn.bind(
            "<Enter>",
            lambda e: self._login_btn.config(bg=BTN_HOVER)
        )
        self._login_btn.bind(
            "<Leave>",
            lambda e: self._login_btn.config(bg=BTN_BG)
        )

        tk.Frame(card, height=12, bg=BG_CARD).pack()

        # Error label
        self._error_var = tk.StringVar()
        self._error_label = tk.Label(
            card,
            textvariable=self._error_var,
            font=("Segoe UI", 9),
            bg=BG_CARD,
            fg=FG_ERROR,
            wraplength=300,
        )
        self._error_label.pack()

        # Bind Enter key to login
        self.bind("<Return>", lambda e: self._attempt_login())

        # Focus username field
        self._username_entry.focus()

    # ── Login Logic ────────────────────────────────────────────────────────────

    def _attempt_login(self):
        """Validate credentials and trigger login."""
        username = self._username_var.get().strip()
        password = self._password_var.get()

        # Clear previous error
        self._error_var.set("")

        if not username:
            self._error_var.set("⚠  Please enter your username.")
            self._username_entry.focus()
            return

        if not password:
            self._error_var.set("⚠  Please enter your password.")
            self._password_entry.focus()
            return

        # Attempt authentication
        try:
            auth_service = self._services.get("auth_service")
            if auth_service is None:
                self._error_var.set("⚠  Authentication service unavailable.")
                return

            user = auth_service.login(username, password)

            # Success — close login window, open main window
            self.destroy()
            self._on_login_success(user, self._services)

        except Exception as e:
            error_msg = str(e)
            if "invalid" in error_msg.lower() or "password" in error_msg.lower():
                self._error_var.set("⚠  Invalid username or password.")
            else:
                self._error_var.set(f"⚠  {error_msg}")

            # Clear password field on failure
            self._password_var.set("")
            self._password_entry.focus()