"""
fix_nullbytes.py
----------------
Fixes corrupted Python source files by removing null bytes.
Creates a .bak backup before modifying any file.

Usage:
    python fix_nullbytes.py
"""

import os
import sys
import shutil


# ── Files to check and fix ────────────────────────────────────────────────────
GUI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui")

TARGET_FILES = [
    os.path.join(GUI_DIR, "main_window.py"),
    os.path.join(GUI_DIR, "login_window.py"),
    os.path.join(GUI_DIR, "app.py"),
]


def fix_file(filepath: str) -> dict:
    """
    Remove null bytes from a single Python source file.

    Steps:
        1. Read raw bytes.
        2. Count null bytes.
        3. If found → backup original → write cleaned version.
        4. Verify the cleaned file compiles without errors.

    Args:
        filepath: Absolute path to the .py file.

    Returns:
        dict with keys:
            exists      (bool)
            null_count  (int)
            fixed       (bool)
            backup_path (str | None)
            compile_ok  (bool)
            error       (str | None)
    """
    result = {
        "exists"      : False,
        "null_count"  : 0,
        "fixed"       : False,
        "backup_path" : None,
        "compile_ok"  : False,
        "error"       : None,
    }

    # ── Check file exists ─────────────────────────────────────────────────────
    if not os.path.exists(filepath):
        result["error"] = "File not found"
        return result

    result["exists"] = True

    # ── Read raw bytes ────────────────────────────────────────────────────────
    try:
        with open(filepath, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        result["error"] = f"Cannot read file: {exc}"
        return result

    # ── Count null bytes ──────────────────────────────────────────────────────
    null_count = raw.count(b"\x00")
    result["null_count"] = null_count

    if null_count == 0:
        # No null bytes — just verify it compiles
        result["compile_ok"], result["error"] = _try_compile(raw, filepath)
        return result

    # ── Backup original ───────────────────────────────────────────────────────
    backup_path = filepath + ".bak"
    try:
        shutil.copy2(filepath, backup_path)
        result["backup_path"] = backup_path
    except OSError as exc:
        result["error"] = f"Cannot create backup: {exc}"
        return result

    # ── Remove null bytes ─────────────────────────────────────────────────────
    cleaned = raw.replace(b"\x00", b"")

    try:
        with open(filepath, "wb") as fh:
            fh.write(cleaned)
        result["fixed"] = True
    except OSError as exc:
        result["error"] = f"Cannot write cleaned file: {exc}"
        return result

    # ── Verify the cleaned file compiles ──────────────────────────────────────
    result["compile_ok"], result["error"] = _try_compile(cleaned, filepath)
    return result


def _try_compile(raw_bytes: bytes, filepath: str) -> tuple[bool, str | None]:
    """
    Attempt to compile raw bytes as Python source.

    Args:
        raw_bytes : Raw file contents (null bytes already removed).
        filepath  : Used only for error messages.

    Returns:
        (ok: bool, error_message: str | None)
    """
    try:
        source = raw_bytes.decode("utf-8", errors="replace")
        compile(source, filepath, "exec")
        return True, None
    except SyntaxError as exc:
        return False, f"SyntaxError after fix: {exc}"
    except Exception as exc:
        return False, f"Compile error: {exc}"


def print_report(filepath: str, result: dict) -> None:
    """Print a formatted result for one file."""
    name = os.path.basename(filepath)
    print(f"\n  {'─' * 56}")
    print(f"  File       : {name}")

    if not result["exists"]:
        print(f"  Status     : ✗ NOT FOUND")
        return

    print(f"  Null bytes : {result['null_count']}")

    if result["null_count"] == 0:
        print(f"  Status     : ✓ Clean (no null bytes)")
    elif result["fixed"]:
        print(f"  Status     : ✓ Fixed")
        print(f"  Backup     : {result['backup_path']}")
    else:
        print(f"  Status     : ✗ Fix FAILED")

    if result["compile_ok"]:
        print(f"  Compile    : ✓ OK")
    else:
        print(f"  Compile    : ✗ FAILED — {result['error']}")

    if result["error"] and result["fixed"]:
        # Fixed but still has compile error
        print(f"\n  ⚠ WARNING: File was fixed but still has errors.")
        print(f"    This means the file content itself is corrupted,")
        print(f"    not just the null bytes.")
        print(f"    You must restore from backup or Git.")


def main() -> None:
    print("=" * 60)
    print("  LMPTS — Null Byte Fixer")
    print("=" * 60)

    all_ok       = True
    needs_restore = []

    for filepath in TARGET_FILES:
        result = fix_file(filepath)
        print_report(filepath, result)

        # Track files that are still broken after fix
        if result["exists"] and not result["compile_ok"]:
            all_ok = False
            needs_restore.append(os.path.basename(filepath))

    print(f"\n  {'─' * 56}")

    if all_ok:
        print("\n  ✓ All files are clean and compile successfully.")
        print("  You can now restart LMPTS:\n")
        print("      python gui/app.py\n")
    else:
        print("\n  ✗ Some files still have errors after fixing:\n")
        for name in needs_restore:
            print(f"      - {name}")

        print("""
  These files are too corrupted to auto-fix.
  You need to restore them from Git:

      git checkout HEAD -- gui/main_window.py
      git checkout HEAD -- gui/login_window.py

  Or restore from your last known good backup.
        """)

    print("=" * 60)


if __name__ == "__main__":
    main()