"""
login_window.py
---------------
LMPTS Login Screen with self-registration link.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable

BG_OUTER  = "#1a3a5c"
BG_CARD   = "#ffffff"
FG_LABEL  = "#333333"
FG_ERROR  = "#c0392b"
BTN_BG    = "#1a3a5c"
BTN_FG    = "#ffffff"
BTN_HOVER = "#2d5986"


class LoginWindow(tk.Tk):
    """
    LMPTS Login Window.

    Shows login form with username/password fields.
    Includes Register link for new learner self-registration.
    Shows specific messages for PENDING and REJECTED accounts.
    """

    def __init__(self, services: dict, on_login_success: Callable):
        super().__init__()
        self._services         = services
        self._on_login_success = on_login_success
        self._remember_var     = tk.BooleanVar(value=False)

        self.title("LMPTS - Login")
        self.geometry("480x600")
        self.resizable(False, False)
        self.configure(bg=BG_OUTER)

        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 480) // 2
        y = (self.winfo_screenheight() - 600) // 2
        self.geometry(f"480x600+{x}+{y}")

        self._build()

    def _build(self):
        """Construct all UI widgets."""
        outer = tk.Frame(self, bg=BG_OUTER)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        tk.Label(
            outer,
            text="LMPTS",
            font=("Segoe UI", 28, "bold"),
            bg=BG_OUTER, fg="#ffffff",
        ).pack(pady=(0, 4))

        tk.Label(
            outer,
            text="Learning Management and\nPrerequisite Tracking System",
            font=("Segoe UI", 10),
            bg=BG_OUTER, fg="#a8c8e8",
            justify="center",
        ).pack(pady=(0, 20))

        # Card
        card = tk.Frame(outer, bg=BG_CARD, padx=40, pady=35)
        card.pack()

        # Username
        tk.Label(
            card,
            text="Username",
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD, fg=FG_LABEL, anchor="w",
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
            bg=BG_CARD, fg=FG_LABEL, anchor="w",
        ).pack(fill="x", pady=(0, 3))

        self._password_var = tk.StringVar()
        self._password_entry = ttk.Entry(
            card,
            textvariable=self._password_var,
            show="*",
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
            bg=BTN_BG, fg=BTN_FG,
            activebackground=BTN_HOVER,
            activeforeground=BTN_FG,
            relief="flat", cursor="hand2",
            width=24, pady=8,
            command=self._attempt_login,
        )
        self._login_btn.pack(fill="x")

        self._login_btn.bind(
            "<Enter>", lambda e: self._login_btn.config(bg=BTN_HOVER)
        )
        self._login_btn.bind(
            "<Leave>", lambda e: self._login_btn.config(bg=BTN_BG)
        )

        tk.Frame(card, height=12, bg=BG_CARD).pack()

        # Status / error label
        self._error_var = tk.StringVar()
        self._error_label = tk.Label(
            card,
            textvariable=self._error_var,
            font=("Segoe UI", 9),
            bg=BG_CARD, fg=FG_ERROR,
            wraplength=300,
            justify="center",
        )
        self._error_label.pack()

        # Divider
        tk.Frame(card, height=1, bg="#eeeeee").pack(
            fill="x", pady=(12, 0)
        )

        # Register link
        reg_frame = tk.Frame(card, bg=BG_CARD)
        reg_frame.pack(fill="x", pady=(10, 0))

        tk.Label(
            reg_frame,
            text="New to LMPTS?",
            font=("Segoe UI", 9),
            bg=BG_CARD, fg="#666666",
        ).pack(side="left")

        reg_link = tk.Label(
            reg_frame,
            text="  Create Account",
            font=("Segoe UI", 9, "bold", "underline"),
            bg=BG_CARD, fg="#1a3a5c",
            cursor="hand2",
        )
        reg_link.pack(side="left")
        reg_link.bind("<Button-1>", lambda e: self._open_register())

        # Bind Enter key
        self.bind("<Return>", lambda e: self._attempt_login())

        # Focus username
        self._username_entry.focus()

    def _attempt_login(self):
        """Validate credentials and attempt login."""
        self._error_var.set("")
        self._error_label.config(fg=FG_ERROR)

        username = self._username_var.get().strip()
        password = self._password_var.get()

        if not username:
            self._error_var.set("Please enter your username.")
            self._username_entry.focus()
            return

        if not password:
            self._error_var.set("Please enter your password.")
            self._password_entry.focus()
            return

        try:
            auth_service = self._services.get("auth_service")
            if auth_service is None:
                self._error_var.set("Authentication service unavailable.")
                return

            user = auth_service.login(username, password)
            self.destroy()
            self._on_login_success(user, self._services)

        except Exception as e:
            error_msg = str(e)

            if error_msg.startswith("PENDING:"):
                clean = error_msg.replace("PENDING:", "").strip()
                self._error_var.set(clean)
                self._error_label.config(fg="#e67e22")
            elif error_msg.startswith("REJECTED:"):
                clean = error_msg.replace("REJECTED:", "").strip()
                self._error_var.set(clean)
                self._error_label.config(fg=FG_ERROR)
            else:
                self._error_var.set("Invalid username or password.")

            self._password_var.set("")
            try:
                self._password_entry.focus()
            except Exception:
                pass

    def _open_register(self):
        """Open the self-registration window."""
        try:
            from gui.register_window import RegisterWindow

            def on_back():
                try:
                    self.deiconify()
                    self.focus_force()
                    self._username_entry.focus()
                except Exception:
                    pass

            self.iconify()
            RegisterWindow(
                parent=self,
                services=self._services,
                on_back_to_login=on_back,
            )
        except Exception as ex:
            self._error_var.set(f"Could not open registration: {ex}")
