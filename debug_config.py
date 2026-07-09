"""
debug_config.py
---------------
Comprehensive logging for the LMPTS application.

Usage:
    Add to top of gui/app.py:
        import debug_config

Features:
    - Colored console output
    - Full log file in C:\\LMPTS\\logs\\
    - Optional SQL query tracing (opt-in — see Database class change below)
    - Different colors per log level
    - Icons for quick visual scanning
"""

import logging
import sys
import os
from datetime import datetime

# ── Log file location ─────────────────────────────────────────────────────────

LOG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "logs"
)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(
    LOG_DIR,
    f"lmpts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)


# ── Terminal Colors ───────────────────────────────────────────────────────────

class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    GRAY    = "\033[90m"


# Enable ANSI colors on Windows terminals
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


# ── Log Formatters ────────────────────────────────────────────────────────────

class ColoredFormatter(logging.Formatter):
    """Colored terminal output with icons."""

    COLORS = {
        logging.DEBUG:    Colors.GRAY,
        logging.INFO:     Colors.CYAN,
        logging.WARNING:  Colors.YELLOW,
        logging.ERROR:    Colors.RED,
        logging.CRITICAL: Colors.RED + Colors.BOLD,
    }

    ICONS = {
        logging.DEBUG:    "[DEBUG]",
        logging.INFO:     "[INFO ]",
        logging.WARNING:  "[WARN ]",
        logging.ERROR:    "[ERROR]",
        logging.CRITICAL: "[CRIT ]",
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, Colors.RESET)
        icon  = self.ICONS.get(record.levelno, "")
        # Extract short module name
        module = record.name.replace("__main__", "app")
        if len(module) > 35:
            module = "..." + module[-32:]

        # Timestamp — HH:MM:SS
        timestamp = self.formatTime(record, "%H:%M:%S")

        return (
            f"{color}"
            f"{icon} "
            f"{timestamp}  "
            f"{module:35s}  "
            f"{record.getMessage()}"
            f"{Colors.RESET}"
        )


class FileFormatter(logging.Formatter):
    """Plain text formatter for log file."""

    def format(self, record):
        return (
            f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')}  "
            f"{record.levelname:8s}  "
            f"{record.name:40s}  "
            f"{record.getMessage()}"
        )


# ── Setup Function ────────────────────────────────────────────────────────────

def setup_logging(level: str = "INFO") -> None:
    """
    Configure application-wide logging.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger — clear existing handlers
    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()

    # ── Console handler (colored) ─────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(ColoredFormatter())
    root.addHandler(console)

    # ── File handler (always DEBUG level for file) ────────────────────────────
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(FileFormatter())
    root.addHandler(file_handler)

    # ── Reduce noise from libraries ───────────────────────────────────────────
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    # ── Startup message ───────────────────────────────────────────────────────
    root.info("=" * 70)
    root.info(f"LMPTS Logging Initialized")
    root.info(f"Console Level: {level}")
    root.info(f"File Level:    DEBUG")
    root.info(f"Log File:      {LOG_FILE}")
    root.info("=" * 70)


# ── SQL Query Tracing (Optional — enabled via Database class) ────────────────

def attach_sql_tracer(connection):
    """
    Attach a SQL query tracer to a specific SQLite connection.

    Args:
        connection: sqlite3.Connection object to trace.

    Usage in database.py get_connection():
        conn = sqlite3.connect(self.db_path, ...)
        from debug_config import attach_sql_tracer
        attach_sql_tracer(conn)
        return conn
    """
    sql_logger = logging.getLogger("sql.query")

    def trace_callback(sql):
        # Truncate very long queries
        display = sql.strip().replace("\n", " ")
        while "  " in display:
            display = display.replace("  ", " ")
        if len(display) > 200:
            display = display[:200] + "..."
        sql_logger.debug(f"SQL: {display}")

    try:
        connection.set_trace_callback(trace_callback)
    except Exception as e:
        sql_logger.warning(f"Could not attach SQL tracer: {e}")


# ── Auto-run on import ────────────────────────────────────────────────────────

setup_logging(level="INFO")