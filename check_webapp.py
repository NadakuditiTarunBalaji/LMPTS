"""
check_webapp.py
Verify the current webapp structure and imports.
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

WEBAPP_DIR = os.path.join(ROOT, "webapp")

print("=" * 60)
print("LMPTS WEBAPP STRUCTURE CHECK")
print("=" * 60)

# 1. List all Python files
print("\nPython files in webapp/:")
for name in sorted(os.listdir(WEBAPP_DIR)):
    path = os.path.join(WEBAPP_DIR, name)
    if os.path.isfile(path) and name.endswith(".py"):
        size = os.path.getsize(path)
        print(f"  {name:25s}  {size:6d} bytes")

# 2. List templates
templates_dir = os.path.join(WEBAPP_DIR, "templates")
if os.path.exists(templates_dir):
    print("\nTemplates:")
    for root, dirs, files in os.walk(templates_dir):
        rel = os.path.relpath(root, templates_dir)
        for f in files:
            if f.endswith(".html"):
                print(f"  templates/{rel}/{f}" if rel != "." else f"  templates/{f}")

# 3. Check static files
static_dir = os.path.join(WEBAPP_DIR, "static")
if os.path.exists(static_dir):
    print("\nStatic files:")
    for root, dirs, files in os.walk(static_dir):
        rel = os.path.relpath(root, static_dir)
        for f in files:
            print(f"  static/{rel}/{f}" if rel != "." else f"  static/{f}")

# 4. Try importing
print("\n" + "=" * 60)
print("Import Test")
print("=" * 60)

try:
    from webapp import __init__ as webapp_init
    print("[OK] webapp/__init__.py imports")
except Exception as e:
    print(f"[ERROR] webapp/__init__.py: {e}")

for module in ["auth", "admin", "learner", "instructor", "analyst", "profile"]:
    try:
        __import__(f"webapp.{module}")
        print(f"[OK] webapp.{module} imports")
    except Exception as e:
        print(f"[ERROR] webapp.{module}: {e}")

# 5. Check Flask installed
print("\n" + "=" * 60)
print("Dependencies")
print("=" * 60)
try:
    import flask
    print(f"[OK] Flask installed: {flask.__version__}")
except ImportError:
    print("[ERROR] Flask NOT installed — run: pip install flask")