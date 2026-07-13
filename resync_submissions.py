"""
resync_submissions.py
---------------------
Forces every course_submissions row (except REJECTED) to reflect
its course's current status.

Run once:
    python resync_submissions.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repository.database import Database


def resync():
    db = Database()
    with db.transaction() as conn:
        cur = conn.execute(
            """
            UPDATE course_submissions
               SET status = CASE (
                       SELECT status
                         FROM courses
                        WHERE courses.code = course_submissions.course_code
                   )
                       WHEN 'PUBLISHED' THEN 'APPROVED'
                       WHEN 'ARCHIVED'  THEN 'ARCHIVED'
                       WHEN 'DRAFT'     THEN 'PENDING'
                       ELSE status
                   END
             WHERE status != 'REJECTED'
            """
        )
        print(f"[OK] {cur.rowcount} submissions re-synced.")


if __name__ == "__main__":
    resync()