"""diagnose.py — pinpoint the account_status conversion bug"""

from repository.database import Database
from repository.user_repo import SQLiteUserRepository
from core.user import User
from core.enums import AccountStatus

print("=" * 60)
print("TEST 1: Raw SQLite row")
print("=" * 60)
db   = Database()
conn = db.get_connection()
try:
    cursor = conn.execute(
        "SELECT id, username, account_status, is_active, "
        "full_name, email FROM users WHERE username = 'sai'"
    )
    row = cursor.fetchone()
    if row:
        raw = dict(row)
        print(f"  Raw row: {raw}")
        print(f"  account_status type: {type(raw['account_status'])}")
        print(f"  account_status value: {repr(raw['account_status'])}")
    else:
        print("  No 'sai' user found — using first user for testing")
        cursor = conn.execute("SELECT * FROM users LIMIT 1")
        row = cursor.fetchone()
        if row:
            print(f"  {dict(row)}")
finally:
    conn.close()

print()
print("=" * 60)
print("TEST 2: User.from_dict()")
print("=" * 60)
if row:
    test_row = dict(row)
    if "password_hash" not in test_row:
        test_row["password_hash"] = "x"
    if "role" not in test_row:
        test_row["role"] = "LEARNER"
    if "created_at" not in test_row:
        test_row["created_at"] = "2024-01-01T00:00:00"
    user = User.from_dict(test_row)
    print(f"  user.account_status = {user.account_status}")
    print(f"  type = {type(user.account_status).__name__}")
    print(f"  isinstance(AccountStatus) = "
          f"{isinstance(user.account_status, AccountStatus)}")

print()
print("=" * 60)
print("TEST 3: Repository get_pending_users()")
print("=" * 60)
repo    = SQLiteUserRepository(db)
pending = repo.get_pending_users()
print(f"  Found {len(pending)} pending user(s)")
for u in pending:
    print(f"    id={u.id}  {u.username}  "
          f"status={u.account_status}  "
          f"type={type(u.account_status).__name__}")

print()
print("=" * 60)
print("TEST 4: Enum comparison")
print("=" * 60)
if pending:
    u = pending[0]
    print(f"  u.account_status == AccountStatus.PENDING: "
          f"{u.account_status == AccountStatus.PENDING}")
    print(f"  u.account_status == 'PENDING':             "
          f"{u.account_status == 'PENDING'}")
    print(f"  u.account_status.value == 'PENDING':       "
          f"{u.account_status.value == 'PENDING' if hasattr(u.account_status, 'value') else 'NO .value attr'}")