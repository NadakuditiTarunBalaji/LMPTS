"""
sidebar.py
----------
Reusable sidebar navigation widget.

Layout:
    ┌──────────────┐
    │   LOGO/TITLE │
    ├──────────────┤
    │  [Nav Item]  │
    │  [Nav Item]  │
    │  [Nav Item]  │
    ├──────────────┤
    │  [Logout]    │
    └──────────────┘
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Callable, Dict


# ── Colour Constants ───────────────────────────────────────────────────────────

SIDEBAR_BG       = "#1a3a5c"   # Dark navy blue
SIDEBAR_FG       = "#ffffff"   # White text
SIDEBAR_HOVER    = "#2d5986"   # Lighter blue on hover
SIDEBAR_SELECTED = "#4a90d9"   # Bright blue when selected
SIDEBAR_WIDTH    = 200


class SidebarButton(tk.Frame):
    """
    A single navigation button in the sidebar.

    Shows hover and selected states.
    """

    def __init__(
        self,
        parent,
        text: str,
        command: Callable,
        icon: str = "▸",
    ):
        super().__init__(parent, bg=SIDEBAR_BG, cursor="hand2")

        self._command  = command
        self._selected = False

        self._label = tk.Label(
            self,
            text=f"  {icon}  {text}",
            bg=SIDEBAR_BG,
            fg=SIDEBAR_FG,
            font=("Segoe UI", 10),
            anchor="w",
            padx=10,
            pady=8,
        )
        self._label.pack(fill="x")

        # Bind hover and click events to both frame and label
        for widget in (self, self._label):
            widget.bind("<Enter>",  self._on_enter)
            widget.bind("<Leave>",  self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def _on_enter(self, event=None):
        if not self._selected:
            self._label.config(bg=SIDEBAR_HOVER)
            self.config(bg=SIDEBAR_HOVER)

    def _on_leave(self, event=None):
        if not self._selected:
            self._label.config(bg=SIDEBAR_BG)
            self.config(bg=SIDEBAR_BG)

    def _on_click(self, event=None):
        self._command()

    def set_selected(self, selected: bool):
        """Highlight this button as the active navigation item."""
        self._selected = selected
        colour = SIDEBAR_SELECTED if selected else SIDEBAR_BG
        self._label.config(bg=colour)
        self.config(bg=colour)


class Sidebar(tk.Frame):
    """
    Full sidebar navigation panel.

    Usage:
        sidebar = Sidebar(
            parent,
            title="LMPTS",
            subtitle="Admin Panel",
            nav_items=[
                ("Dashboard",      dashboard_command),
                ("Courses",        courses_command),
                ("Learners",       learners_command),
            ],
            logout_command=logout_fn,
        )
        sidebar.pack(side="left", fill="y")
    """

    def __init__(
        self,
        parent,
        title: str,
        subtitle: str,
        nav_items: List[tuple],
        logout_command: Callable,
    ):
        super().__init__(parent, bg=SIDEBAR_BG, width=SIDEBAR_WIDTH)
        self.pack_propagate(False)

        self._buttons: Dict[str, SidebarButton] = {}
        self._active_key: str = ""

        self._build_header(title, subtitle)
        self._build_divider()
        self._build_nav(nav_items)
        self._build_footer(logout_command)

    def _build_header(self, title: str, subtitle: str):
        """Logo / title area at top of sidebar."""
        header = tk.Frame(self, bg=SIDEBAR_BG, pady=20)
        header.pack(fill="x")

        tk.Label(
            header,
            text=title,
            bg=SIDEBAR_BG,
            fg="#ffffff",
            font=("Segoe UI", 14, "bold"),
        ).pack()

        tk.Label(
            header,
            text=subtitle,
            bg=SIDEBAR_BG,
            fg="#a8c8e8",
            font=("Segoe UI", 9),
        ).pack()

    def _build_divider(self):
        """Thin horizontal line separator."""
        tk.Frame(
            self,
            bg="#2d5986",
            height=1,
        ).pack(fill="x", padx=10)

        tk.Frame(self, bg=SIDEBAR_BG, height=5).pack()

    def _build_nav(self, nav_items: List[tuple]):
        """Create all navigation buttons."""
        nav_frame = tk.Frame(self, bg=SIDEBAR_BG)
        nav_frame.pack(fill="both", expand=True)

        icons = ["⊞", "📚", "👥", "📊", "🔧", "📋", "⭐", "📈"]

        for i, (text, command) in enumerate(nav_items):
            icon = icons[i] if i < len(icons) else "▸"
            key  = text.lower().replace(" ", "_")

            btn = SidebarButton(
                nav_frame,
                text=text,
                command=lambda k=key, cmd=command: self._on_nav(k, cmd),
                icon=icon,
            )
            btn.pack(fill="x", pady=1)
            self._buttons[key] = btn

        # Select the first item by default
        if self._buttons:
            first_key = list(self._buttons.keys())[0]
            self.set_active(first_key)

    def _build_footer(self, logout_command: Callable):
        """Logout button pinned to bottom."""
        tk.Frame(self, bg="#2d5986", height=1).pack(fill="x", padx=10)

        logout_btn = SidebarButton(
            self,
            text="Logout",
            command=logout_command,
            icon="⏻",
        )
        logout_btn.pack(fill="x", pady=5)

    def _on_nav(self, key: str, command: Callable):
        """Handle navigation button click."""
        self.set_active(key)
        command()

    def set_active(self, key: str):
        """Set the active (selected) navigation item."""
        if self._active_key and self._active_key in self._buttons:
            self._buttons[self._active_key].set_selected(False)

        self._active_key = key
        if key in self._buttons:
            self._buttons[key].set_selected(True)