"""
confirm_dialog.py
-----------------
Reusable confirmation and error dialogs.
"""

import tkinter as tk
from tkinter import messagebox


def confirm(parent, title: str, message: str) -> bool:
    """
    Show a Yes/No confirmation dialog.

    Args:
        parent  : Parent window.
        title   : Dialog title.
        message : Question to display.

    Returns:
        bool: True if user clicked Yes.

    Usage:
        if confirm(root, "Delete Course", "Delete CS101?"):
            service.delete_course("CS101")
    """
    return messagebox.askyesno(title, message, parent=parent)


def show_error(parent, title: str, message: str) -> None:
    """
    Show an error message dialog.

    Args:
        parent  : Parent window.
        title   : Dialog title.
        message : Error message.
    """
    messagebox.showerror(title, message, parent=parent)


def show_info(parent, title: str, message: str) -> None:
    """
    Show an information message dialog.

    Args:
        parent  : Parent window.
        title   : Dialog title.
        message : Info message.
    """
    messagebox.showinfo(title, message, parent=parent)


def show_warning(parent, title: str, message: str) -> None:
    """
    Show a warning message dialog.
    """
    messagebox.showwarning(title, message, parent=parent)