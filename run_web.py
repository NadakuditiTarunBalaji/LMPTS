"""
run_web.py
----------
LMPTS Flask web application entry point.

Run from project root:
    python run_web.py
"""

from webapp import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 50)
    print("  LMPTS - Web Application")
    print("=" * 50)
    print("Default credentials:")
    print("  admin      / admin123")
    print("  learner    / learner123")
    print("  analyst    / analyst123")
    print("  instructor / instructor123")
    print()
    app.run(debug=True)
