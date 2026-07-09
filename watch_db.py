"""
watch_db.py
-----------
Live database monitor — shows any changes as they happen.

Usage:
    Terminal 1:  python watch_db.py         ← monitor
    Terminal 2:  python gui/app.py          ← use the app
    Watch changes appear in Terminal 1 in real time.
"""

import sqlite3
import time
import os
import hashlib

DB_PATH = r"C:\LMPTS\data\lmpts.db"

TABLES = [
    "users", "learners", "courses", "enrollments",
    "prerequisites", "course_progress",
    "prior_learning_requests", "notifications",
]


class Colors:
    RESET = "\033[0m"
    GREEN = "\033[92m"
    RED   = "\033[91m"
    CYAN  = "\033[96m"
    YELLOW = "\033[93m"


def get_table_signature(conn, table):
    """Get a hash of the table contents to detect changes."""
    try:
        cursor = conn.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        content = str([dict(row) for row in rows])
        return hashlib.md5(content.encode()).hexdigest(), len(rows), rows
    except Exception as e:
        return None, 0, []


def get_table_counts(conn):
    """Get row count for every table."""
    counts = {}
    for table in TABLES:
        try:
            cursor = conn.execute(f"SELECT COUNT(*) as c FROM {table}")
            counts[table] = cursor.fetchone()["c"]
        except Exception:
            counts[table] = -1
    return counts


def print_header():
    print("\033[2J\033[H")   # Clear screen
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.CYAN}  LMPTS Database Monitor — {DB_PATH}{Colors.RESET}")
    print(f"{Colors.CYAN}  Press Ctrl+C to stop{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")


def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return

    previous_signatures = {}

    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row

            print_header()

            # Show table counts
            counts = get_table_counts(conn)
            print(f"\n{Colors.YELLOW}Table Row Counts:{Colors.RESET}")
            for table, count in counts.items():
                bar = "█" * min(count, 30)
                print(f"  {table:30s} {count:4d}  {bar}")

            # Check for changes
            print(f"\n{Colors.YELLOW}Changes Detected:{Colors.RESET}")
            changes_found = False

            for table in TABLES:
                sig, count, rows = get_table_signature(conn, table)
                if sig is None:
                    continue

                if table in previous_signatures:
                    old_sig, old_count, old_rows = previous_signatures[table]
                    if sig != old_sig:
                        changes_found = True
                        diff = count - old_count
                        symbol = "+" if diff > 0 else ("=" if diff == 0 else "-")
                        color = Colors.GREEN if diff > 0 else (
                            Colors.CYAN if diff == 0 else Colors.RED
                        )
                        print(
                            f"  {color}[{symbol}] {table:25s}  "
                            f"{old_count} → {count}"
                            f"{Colors.RESET}"
                        )
                        # Show the newest row if inserted
                        if diff > 0 and rows:
                            newest = dict(rows[-1])
                            display = {
                                k: v for k, v in newest.items()
                                if k not in ("password_hash",)
                            }
                            print(
                                f"      NEW: {display}"[:150]
                            )

                previous_signatures[table] = (sig, count, rows)

            if not changes_found:
                print(f"  {Colors.CYAN}(no changes since last check){Colors.RESET}")

            print(f"\n{Colors.YELLOW}Last checked: {time.strftime('%H:%M:%S')}{Colors.RESET}")
            print(f"{Colors.CYAN}Refreshing in 2 seconds...{Colors.RESET}")

            conn.close()
            time.sleep(2)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Monitor stopped.{Colors.RESET}")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()