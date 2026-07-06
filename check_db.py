# check_db.py
# Run from C:\LMPTS with: python check_db.py

import os
import sys
import sqlite3

print("=" * 60)
print("LMPTS DATABASE DIAGNOSTIC")
print("=" * 60)
print()

# ── 1. Show working directory ──────────────────────────────────
cwd = os.getcwd()
print(f"Working directory: {cwd}")
print()

# ── 2. Show Python path ────────────────────────────────────────
print(f"Python: {sys.executable}")
print()

# ── 3. Check data folder ───────────────────────────────────────
data_path = os.path.join(cwd, "data")
db_path   = os.path.join(data_path, "lmpts.db")

print(f"Expected data folder : {data_path}")
print(f"Data folder exists   : {os.path.exists(data_path)}")
print()
print(f"Expected DB file     : {db_path}")
print(f"DB file exists       : {os.path.exists(db_path)}")
print()

# ── 4. Check what database.py computes as the path ────────────
try:
    from repository.database import Database, DEFAULT_DB_PATH
    print(f"DEFAULT_DB_PATH      : {DEFAULT_DB_PATH}")
    print(f"DEFAULT path exists  : {os.path.exists(DEFAULT_DB_PATH)}")
    print()
except Exception as e:
    print(f"ERROR importing database.py: {e}")
    print()

# ── 5. Try creating the database manually ─────────────────────
print("Attempting to create database...")
try:
    os.makedirs(data_path, exist_ok=True)
    print(f"  data/ folder ready : {data_path}")

    db = Database(db_path)
    db.initialize()

    print(f"  Database created   : {db_path}")
    print(f"  File exists        : {os.path.exists(db_path)}")
    print(f"  File size          : {os.path.getsize(db_path)} bytes")
    print(f"  Schema version     : {db.get_schema_version()}")
    print()

    # List all tables
    conn = db.get_connection()
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row["name"] for row in cursor.fetchall()]
    conn.close()

    print(f"  Tables created ({len(tables)}):")
    for t in tables:
        print(f"    ✓ {t}")

except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)