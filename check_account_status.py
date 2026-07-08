"""
check_account_status.py
Find any place still using string values for account_status.
"""

import os
import re

pattern = re.compile(r'account_status\s*=\s*["\']([A-Z_]+)["\']')

for root, dirs, files in os.walk(r"C:\LMPTS"):
    # skip venv and cache
    if ".venv" in root or "__pycache__" in root:
        continue
    for name in files:
        if name.endswith(".py"):
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8") as f:
                    for lineno, line in enumerate(f, 1):
                        m = pattern.search(line)
                        if m:
                            rel = os.path.relpath(path, r"C:\LMPTS")
                            print(f"{rel}:{lineno}")
                            print(f"  {line.strip()}")
            except Exception:
                pass

print("Done. Any results above should use AccountStatus.XXXX enum instead.")