"""
trace_dashboard.py
------------------
Live GUI dashboard showing everything happening in LMPTS.

Displays:
    - Recent log entries (color-coded)
    - Recent database changes
    - Active sessions
    - Notification stream
    - Query counter

Usage:
    Terminal 1: python trace_dashboard.py
    Terminal 2: python gui/app.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import sqlite3
import os
import threading
import time
from datetime import datetime


DB_PATH  = r"C:\LMPTS\data\lmpts.db"
LOG_DIR  = r"C:\LMPTS\logs"

# Colors
BG_MAIN   = "#1e1e1e"
BG_PANEL  = "#252526"
FG_TEXT   = "#d4d4d4"
FG_INFO   = "#4ec9b0"
FG_WARN   = "#dcdcaa"
FG_ERROR  = "#f48771"
FG_DEBUG  = "#808080"
FG_SUCCESS = "#89d185"


class TraceDashboard(tk.Tk):
    """Live trace dashboard for LMPTS debugging."""

    def __init__(self):
        super().__init__()
        self.title("LMPTS Trace Dashboard")
        self.geometry("1400x800")
        self.configure(bg=BG_MAIN)

        self._log_file    = None
        self._last_pos    = 0
        self._query_count = 0
        self._prev_counts = {}
        self._running     = True

        self._build_ui()
        self._start_monitors()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#007acc", height=40)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="⚡  LMPTS Live Trace Dashboard",
            font=("Segoe UI", 14, "bold"),
            bg="#007acc", fg="#ffffff",
        ).pack(side="left", padx=15, pady=8)

        self._status_var = tk.StringVar(value="●  Monitoring...")
        tk.Label(
            header,
            textvariable=self._status_var,
            font=("Segoe UI", 10),
            bg="#007acc", fg="#ffffff",
        ).pack(side="right", padx=15, pady=8)

        # Body: 3 panels
        body = tk.Frame(self, bg=BG_MAIN)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: Log stream
        left = tk.LabelFrame(
            body,
            text=" 📜 Application Log Stream ",
            font=("Segoe UI", 10, "bold"),
            bg=BG_PANEL, fg=FG_INFO,
        )
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self._log_view = scrolledtext.ScrolledText(
            left,
            font=("Consolas", 9),
            bg=BG_MAIN, fg=FG_TEXT,
            insertbackground=FG_TEXT,
            wrap="none",
        )
        self._log_view.pack(fill="both", expand=True, padx=5, pady=5)

        # Configure text tags for coloring
        self._log_view.tag_config("INFO",    foreground=FG_INFO)
        self._log_view.tag_config("WARNING", foreground=FG_WARN)
        self._log_view.tag_config("ERROR",   foreground=FG_ERROR)
        self._log_view.tag_config("DEBUG",   foreground=FG_DEBUG)
        self._log_view.tag_config("SQL",     foreground="#569cd6")

        # Right: Two stacked panels
        right = tk.Frame(body, bg=BG_MAIN)
        right.pack(side="left", fill="both", expand=True, padx=(5, 0))

        # Database changes
        db_frame = tk.LabelFrame(
            right,
            text=" 🗃️  Database Changes ",
            font=("Segoe UI", 10, "bold"),
            bg=BG_PANEL, fg=FG_INFO,
        )
        db_frame.pack(fill="both", expand=True, pady=(0, 5))

        self._db_view = scrolledtext.ScrolledText(
            db_frame,
            font=("Consolas", 9),
            bg=BG_MAIN, fg=FG_TEXT,
            wrap="word",
        )
        self._db_view.pack(fill="both", expand=True, padx=5, pady=5)
        self._db_view.tag_config("insert", foreground=FG_SUCCESS)
        self._db_view.tag_config("update", foreground=FG_WARN)
        self._db_view.tag_config("delete", foreground=FG_ERROR)

        # Statistics panel
        stats_frame = tk.LabelFrame(
            right,
            text=" 📊 Live Statistics ",
            font=("Segoe UI", 10, "bold"),
            bg=BG_PANEL, fg=FG_INFO,
        )
        stats_frame.pack(fill="both", expand=True)

        self._stats_view = scrolledtext.ScrolledText(
            stats_frame,
            font=("Consolas", 9),
            bg=BG_MAIN, fg=FG_TEXT,
            wrap="word",
            height=15,
        )
        self._stats_view.pack(fill="both", expand=True, padx=5, pady=5)

        # Bottom toolbar
        toolbar = tk.Frame(self, bg="#333333", height=30)
        toolbar.pack(fill="x", side="bottom")
        toolbar.pack_propagate(False)

        tk.Button(
            toolbar,
            text="Clear Logs",
            font=("Segoe UI", 8),
            bg="#3c3c3c", fg=FG_TEXT,
            relief="flat", cursor="hand2",
            command=self._clear_logs,
        ).pack(side="left", padx=5, pady=4)

        self._log_file_var = tk.StringVar(value="Log file: waiting...")
        tk.Label(
            toolbar,
            textvariable=self._log_file_var,
            font=("Consolas", 8),
            bg="#333333", fg=FG_TEXT,
        ).pack(side="left", padx=15)

    def _clear_logs(self):
        self._log_view.delete("1.0", "end")
        self._db_view.delete("1.0", "end")

    def _start_monitors(self):
        """Start background threads for monitoring."""
        threading.Thread(target=self._monitor_logs,      daemon=True).start()
        threading.Thread(target=self._monitor_database,  daemon=True).start()
        threading.Thread(target=self._update_stats,      daemon=True).start()

    def _find_latest_log(self):
        """Find the most recent LMPTS log file."""
        if not os.path.exists(LOG_DIR):
            return None
        logs = sorted(
            [f for f in os.listdir(LOG_DIR) if f.endswith(".log")],
            reverse=True
        )
        return os.path.join(LOG_DIR, logs[0]) if logs else None

    def _monitor_logs(self):
        """Tail the latest log file."""
        while self._running:
            try:
                if self._log_file is None:
                    self._log_file = self._find_latest_log()
                    if self._log_file:
                        self._log_file_var.set(
                            f"Log file: {os.path.basename(self._log_file)}"
                        )
                        self._last_pos = 0

                if self._log_file and os.path.exists(self._log_file):
                    with open(self._log_file, "r", encoding="utf-8") as f:
                        f.seek(self._last_pos)
                        new_content = f.read()
                        self._last_pos = f.tell()

                    if new_content:
                        for line in new_content.splitlines():
                            tag = "INFO"
                            if "SQL:" in line:
                                tag = "SQL"
                                self._query_count += 1
                            elif "ERROR" in line:
                                tag = "ERROR"
                            elif "WARNING" in line:
                                tag = "WARNING"
                            elif "DEBUG" in line:
                                tag = "DEBUG"

                            self.after(0, self._append_log, line, tag)

                time.sleep(0.3)

            except Exception as e:
                time.sleep(1)

    def _append_log(self, line, tag):
        self._log_view.insert("end", line + "\n", tag)
        self._log_view.see("end")

    def _monitor_database(self):
        """Detect database changes."""
        tables = [
            "users", "learners", "courses", "enrollments",
            "prerequisites", "course_progress",
            "prior_learning_requests", "notifications",
        ]

        while self._running:
            try:
                if not os.path.exists(DB_PATH):
                    time.sleep(1)
                    continue

                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row

                for table in tables:
                    try:
                        cursor = conn.execute(
                            f"SELECT COUNT(*) as c FROM {table}"
                        )
                        count = cursor.fetchone()["c"]
                    except Exception:
                        continue

                    prev = self._prev_counts.get(table, count)

                    if count != prev:
                        diff = count - prev
                        if diff > 0:
                            action = "insert"
                            symbol = "➕"
                            # Get the newest row
                            try:
                                cursor = conn.execute(
                                    f"SELECT * FROM {table} "
                                    f"ORDER BY rowid DESC LIMIT 1"
                                )
                                row = cursor.fetchone()
                                if row:
                                    data = {
                                        k: v for k, v in dict(row).items()
                                        if k != "password_hash"
                                    }
                                    msg = (
                                        f"[{time.strftime('%H:%M:%S')}] "
                                        f"{symbol} INSERT into {table}: "
                                        f"{data}"
                                    )
                                    self.after(
                                        0, self._append_db, msg, "insert"
                                    )
                            except Exception:
                                pass
                        else:
                            action = "delete"
                            symbol = "➖"
                            msg = (
                                f"[{time.strftime('%H:%M:%S')}] "
                                f"{symbol} DELETE from {table} "
                                f"({prev} → {count})"
                            )
                            self.after(0, self._append_db, msg, "delete")

                    self._prev_counts[table] = count

                conn.close()
                time.sleep(1)

            except Exception:
                time.sleep(2)

    def _append_db(self, msg, tag):
        self._db_view.insert("end", msg + "\n\n", tag)
        self._db_view.see("end")

    def _update_stats(self):
        """Update live statistics."""
        while self._running:
            try:
                if os.path.exists(DB_PATH):
                    conn = sqlite3.connect(DB_PATH)
                    conn.row_factory = sqlite3.Row

                    stats = {
                        "users":                  0,
                        "  ├─ active":            0,
                        "  ├─ pending":           0,
                        "  └─ rejected":          0,
                        "learners":               0,
                        "courses":                0,
                        "  ├─ published":         0,
                        "  ├─ draft":             0,
                        "  └─ archived":          0,
                        "enrollments":            0,
                        "  ├─ enrolled":          0,
                        "  ├─ in_progress":       0,
                        "  ├─ completed":         0,
                        "  └─ cancelled":         0,
                        "prerequisites":          0,
                        "prior_learning_req":     0,
                        "notifications":          0,
                    }

                    try:
                        stats["users"] = conn.execute(
                            "SELECT COUNT(*) as c FROM users"
                        ).fetchone()["c"]
                        stats["  ├─ active"] = conn.execute(
                            "SELECT COUNT(*) as c FROM users "
                            "WHERE account_status='ACTIVE'"
                        ).fetchone()["c"]
                        stats["  ├─ pending"] = conn.execute(
                            "SELECT COUNT(*) as c FROM users "
                            "WHERE account_status='PENDING'"
                        ).fetchone()["c"]
                        stats["  └─ rejected"] = conn.execute(
                            "SELECT COUNT(*) as c FROM users "
                            "WHERE account_status='REJECTED'"
                        ).fetchone()["c"]

                        stats["learners"] = conn.execute(
                            "SELECT COUNT(*) as c FROM learners"
                        ).fetchone()["c"]

                        stats["courses"] = conn.execute(
                            "SELECT COUNT(*) as c FROM courses"
                        ).fetchone()["c"]
                        stats["  ├─ published"] = conn.execute(
                            "SELECT COUNT(*) as c FROM courses "
                            "WHERE status='PUBLISHED'"
                        ).fetchone()["c"]
                        stats["  ├─ draft"] = conn.execute(
                            "SELECT COUNT(*) as c FROM courses "
                            "WHERE status='DRAFT'"
                        ).fetchone()["c"]
                        stats["  └─ archived"] = conn.execute(
                            "SELECT COUNT(*) as c FROM courses "
                            "WHERE status='ARCHIVED'"
                        ).fetchone()["c"]

                        stats["enrollments"] = conn.execute(
                            "SELECT COUNT(*) as c FROM enrollments"
                        ).fetchone()["c"]
                        for status in ("enrolled", "in_progress",
                                       "completed", "cancelled"):
                            key = f"  ├─ {status}" if status != "cancelled" \
                                  else f"  └─ {status}"
                            stats[key] = conn.execute(
                                "SELECT COUNT(*) as c FROM enrollments "
                                "WHERE status=?",
                                (status.upper(),)
                            ).fetchone()["c"]

                        stats["prerequisites"] = conn.execute(
                            "SELECT COUNT(*) as c FROM prerequisites"
                        ).fetchone()["c"]

                        try:
                            stats["prior_learning_req"] = conn.execute(
                                "SELECT COUNT(*) as c "
                                "FROM prior_learning_requests"
                            ).fetchone()["c"]
                        except Exception:
                            pass

                        try:
                            stats["notifications"] = conn.execute(
                                "SELECT COUNT(*) as c FROM notifications"
                            ).fetchone()["c"]
                        except Exception:
                            pass
                    except Exception:
                        pass

                    conn.close()

                    # Build display
                    lines = [
                        f"═══ Database Statistics ═══\n",
                        f"Time: {time.strftime('%H:%M:%S')}",
                        f"Queries traced: {self._query_count}",
                        "",
                    ]
                    for key, value in stats.items():
                        bar = "█" * min(value, 20)
                        lines.append(f"{key:25s} {value:4d}  {bar}")

                    self.after(0, self._update_stats_display,
                               "\n".join(lines))

                time.sleep(1)

            except Exception as e:
                time.sleep(2)

    def _update_stats_display(self, text):
        self._stats_view.delete("1.0", "end")
        self._stats_view.insert("1.0", text)


if __name__ == "__main__":
    dashboard = TraceDashboard()
    dashboard.mainloop()