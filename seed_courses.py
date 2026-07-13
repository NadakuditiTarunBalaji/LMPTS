"""
seed_courses.py
---------------
Creates 45 courses with prerequisites by writing directly
through the course repository (bypasses service layer).

Run from project root:
    cd C:\\LMPTS
    python seed_courses.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repository.database import Database
from repository.course_repo import SQLiteCourseRepository
from core.enums import DifficultyLevel
from core.course import Course


# ══════════════════════════════════════════════════════════════════════════════
# 45 COURSES
# ══════════════════════════════════════════════════════════════════════════════

COURSES = [
    # ──────────── BEGINNER (15) ────────────
    {"code": "PY101",    "name": "Python Programming",             "description": "Core Python syntax, data structures, and functions.", "difficulty": "BEGINNER", "duration": 40, "prerequisites": []},
    {"code": "CS101",    "name": "Computer Science Fundamentals",  "description": "Algorithms, logic, and computational thinking.",      "difficulty": "BEGINNER", "duration": 35, "prerequisites": []},
    {"code": "MATH101",  "name": "Mathematics for Computing",      "description": "Sets, logic, functions, and discrete math.",          "difficulty": "BEGINNER", "duration": 45, "prerequisites": []},
    {"code": "WEB101",   "name": "HTML & CSS Basics",              "description": "Build static websites with modern HTML5 and CSS3.",   "difficulty": "BEGINNER", "duration": 25, "prerequisites": []},
    {"code": "JS101",    "name": "JavaScript Fundamentals",        "description": "Variables, functions, DOM manipulation basics.",     "difficulty": "BEGINNER", "duration": 30, "prerequisites": []},
    {"code": "DB101",    "name": "Databases 101",                  "description": "Relational databases and SQL fundamentals.",         "difficulty": "BEGINNER", "duration": 30, "prerequisites": []},
    {"code": "GIT101",   "name": "Version Control with Git",       "description": "Git, GitHub, branching, and collaboration.",         "difficulty": "BEGINNER", "duration": 15, "prerequisites": []},
    {"code": "LINUX101", "name": "Linux Command Line",             "description": "Essential Linux commands and shell usage.",          "difficulty": "BEGINNER", "duration": 25, "prerequisites": []},
    {"code": "NET101",   "name": "Networking Basics",              "description": "How the internet works: TCP/IP, DNS, HTTP.",         "difficulty": "BEGINNER", "duration": 30, "prerequisites": []},
    {"code": "SEC101",   "name": "Cybersecurity Awareness",        "description": "Phishing, passwords, safe computing practices.",     "difficulty": "BEGINNER", "duration": 20, "prerequisites": []},
    {"code": "JAVA101",  "name": "Java Programming Basics",        "description": "Java syntax and OOP fundamentals.",                  "difficulty": "BEGINNER", "duration": 40, "prerequisites": []},
    {"code": "STAT101",  "name": "Statistics Basics",              "description": "Descriptive statistics and data interpretation.",    "difficulty": "BEGINNER", "duration": 30, "prerequisites": []},
    {"code": "EXCEL101", "name": "Data Analysis with Excel",       "description": "Formulas, charts, and pivot tables.",                "difficulty": "BEGINNER", "duration": 20, "prerequisites": []},
    {"code": "C101",     "name": "C Programming",                  "description": "Memory management, pointers, low-level programming.", "difficulty": "BEGINNER", "duration": 45, "prerequisites": []},
    {"code": "LOGIC101", "name": "Introduction to Logic",          "description": "Propositional and predicate logic.",                 "difficulty": "BEGINNER", "duration": 25, "prerequisites": []},

    # ──────────── INTERMEDIATE (18) ────────────
    {"code": "PY201",     "name": "Object-Oriented Python",          "description": "Classes, inheritance, decorators, design patterns.", "difficulty": "INTERMEDIATE", "duration": 40, "prerequisites": ["PY101"]},
    {"code": "DS201",     "name": "Data Structures & Algorithms",    "description": "Arrays, trees, graphs, sorting, complexity.",       "difficulty": "INTERMEDIATE", "duration": 55, "prerequisites": ["PY101", "CS101"]},
    {"code": "WEB201",    "name": "Responsive Web Design",           "description": "Flexbox, CSS Grid, modern layouts.",                "difficulty": "INTERMEDIATE", "duration": 35, "prerequisites": ["WEB101"]},
    {"code": "JS201",     "name": "Modern JavaScript (ES6+)",        "description": "Async, promises, modules, advanced JS.",            "difficulty": "INTERMEDIATE", "duration": 40, "prerequisites": ["JS101"]},
    {"code": "DB201",     "name": "Advanced SQL & Database Design",  "description": "Joins, indexing, normalization.",                   "difficulty": "INTERMEDIATE", "duration": 40, "prerequisites": ["DB101"]},
    {"code": "STAT201",   "name": "Statistics & Probability",        "description": "Distributions, hypothesis testing, regression.",    "difficulty": "INTERMEDIATE", "duration": 45, "prerequisites": ["MATH101", "STAT101"]},
    {"code": "DA201",     "name": "Data Analysis with Pandas",       "description": "Data cleaning, transformation, exploration.",       "difficulty": "INTERMEDIATE", "duration": 40, "prerequisites": ["PY101"]},
    {"code": "REACT201",  "name": "React Fundamentals",              "description": "Components, hooks, state management.",              "difficulty": "INTERMEDIATE", "duration": 45, "prerequisites": ["JS201", "WEB201"]},
    {"code": "NODE201",   "name": "Node.js & Express",               "description": "Build REST APIs with Node and Express.",            "difficulty": "INTERMEDIATE", "duration": 40, "prerequisites": ["JS201"]},
    {"code": "LIN201",    "name": "Linux & Shell Scripting",         "description": "Bash scripting and system automation.",             "difficulty": "INTERMEDIATE", "duration": 35, "prerequisites": ["LINUX101"]},
    {"code": "NET201",    "name": "Computer Networks",               "description": "TCP/IP, sockets, HTTP protocol deep dive.",         "difficulty": "INTERMEDIATE", "duration": 40, "prerequisites": ["NET101"]},
    {"code": "SE201",     "name": "Software Engineering Principles", "description": "Agile, testing, SDLC, design principles.",         "difficulty": "INTERMEDIATE", "duration": 40, "prerequisites": ["CS101"]},
    {"code": "JAVA201",   "name": "Advanced Java Programming",       "description": "Collections, streams, concurrency.",                "difficulty": "INTERMEDIATE", "duration": 45, "prerequisites": ["JAVA101"]},
    {"code": "NOSQL201",  "name": "NoSQL Databases",                 "description": "MongoDB, Redis, document stores.",                  "difficulty": "INTERMEDIATE", "duration": 35, "prerequisites": ["DB101"]},
    {"code": "OS201",     "name": "Operating Systems Concepts",      "description": "Processes, threads, memory management.",            "difficulty": "INTERMEDIATE", "duration": 50, "prerequisites": ["C101", "LINUX101"]},
    {"code": "VIZ201",    "name": "Data Visualization",              "description": "Matplotlib, Seaborn, interactive dashboards.",      "difficulty": "INTERMEDIATE", "duration": 30, "prerequisites": ["PY101", "STAT101"]},
    {"code": "LINALG201", "name": "Linear Algebra",                  "description": "Vectors, matrices, eigenvalues for ML.",            "difficulty": "INTERMEDIATE", "duration": 45, "prerequisites": ["MATH101"]},
    {"code": "ARCH201",   "name": "Software Architecture Basics",    "description": "Layered architecture, MVC, microservices intro.",   "difficulty": "INTERMEDIATE", "duration": 40, "prerequisites": ["SE201"]},

    # ──────────── ADVANCED (12) ────────────
    {"code": "ML301",     "name": "Machine Learning",                "description": "Supervised, unsupervised learning, evaluation.",    "difficulty": "ADVANCED", "duration": 60, "prerequisites": ["PY201", "STAT201", "LINALG201", "DA201"]},
    {"code": "DL301",     "name": "Deep Learning",                   "description": "Neural networks, CNNs, RNNs, transformers.",        "difficulty": "ADVANCED", "duration": 65, "prerequisites": ["ML301"]},
    {"code": "NLP301",    "name": "Natural Language Processing",     "description": "Text classification, embeddings, LLMs.",            "difficulty": "ADVANCED", "duration": 55, "prerequisites": ["ML301", "PY201"]},
    {"code": "BIG301",    "name": "Big Data Engineering",            "description": "Spark, Hadoop, distributed systems.",               "difficulty": "ADVANCED", "duration": 60, "prerequisites": ["DB201", "DA201"]},
    {"code": "WEB301",    "name": "Full-Stack Web Development",      "description": "Full-stack with React, Node, databases.",           "difficulty": "ADVANCED", "duration": 70, "prerequisites": ["REACT201", "NODE201", "DB201"]},
    {"code": "CLOUD301",  "name": "Cloud Computing & Architecture",  "description": "AWS, Docker, Kubernetes, serverless.",              "difficulty": "ADVANCED", "duration": 55, "prerequisites": ["LIN201", "NET201"]},
    {"code": "DEVOPS301", "name": "DevOps & CI/CD",                  "description": "Infrastructure as code, pipelines, monitoring.",    "difficulty": "ADVANCED", "duration": 50, "prerequisites": ["LIN201", "GIT101", "SE201"]},
    {"code": "SEC301",    "name": "Cybersecurity & Ethical Hacking", "description": "Pen testing, cryptography, secure coding.",         "difficulty": "ADVANCED", "duration": 55, "prerequisites": ["NET201", "SEC101"]},
    {"code": "AI301",     "name": "Artificial Intelligence",         "description": "Search algorithms, knowledge representation.",      "difficulty": "ADVANCED", "duration": 60, "prerequisites": ["DS201", "LOGIC101"]},
    {"code": "ARCH301",   "name": "Advanced Software Architecture",  "description": "Microservices, DDD, event-driven design.",          "difficulty": "ADVANCED", "duration": 50, "prerequisites": ["SE201", "DS201"]},
    {"code": "MOBILE301", "name": "Cross-Platform Mobile Dev",       "description": "React Native and Flutter advanced concepts.",       "difficulty": "ADVANCED", "duration": 50, "prerequisites": ["REACT201"]},
    {"code": "BLOCK301",  "name": "Blockchain & Distributed Systems","description": "Smart contracts, consensus algorithms.",            "difficulty": "ADVANCED", "duration": 45, "prerequisites": ["SEC301", "NET201"]},
]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _build_course(data):
    """
    Build a Course object from a dict.
    Tries several possible constructor signatures to match your model.
    """
    difficulty = DifficultyLevel(data["difficulty"])

    # Try full constructor first
    try:
        return Course(
            code=data["code"],
            name=data["name"],
            description=data["description"],
            difficulty=difficulty,
            duration=data["duration"],
            prerequisites=data["prerequisites"],
        )
    except TypeError:
        pass

    # Without prerequisites (may be added separately)
    try:
        return Course(
            code=data["code"],
            name=data["name"],
            description=data["description"],
            difficulty=difficulty,
            duration=data["duration"],
        )
    except TypeError:
        pass

    # Positional fallback
    return Course(
        data["code"],
        data["name"],
        data["description"],
        difficulty,
        data["duration"],
    )


def _save_course(course_repo, course, prerequisites):
    """
    Save a course + its prerequisites, trying multiple repo APIs.
    """
    # Try add_course
    save_method = None
    for name in ("add_course", "create_course", "save_course", "insert_course", "save"):
        if hasattr(course_repo, name):
            save_method = getattr(course_repo, name)
            break

    if save_method is None:
        raise RuntimeError(
            "Could not find a save method on SQLiteCourseRepository "
            "(tried add_course, create_course, save_course, insert_course, save)."
        )

    save_method(course)

    # Add prerequisites if any
    if not prerequisites:
        return

    for prereq_code in prerequisites:
        added = False
        for name in ("add_prerequisite", "create_prerequisite", "link_prerequisite"):
            if hasattr(course_repo, name):
                try:
                    getattr(course_repo, name)(course.code, prereq_code)
                    added = True
                    break
                except Exception:
                    continue
        if not added:
            print(
                f"    [warn] Could not attach prerequisite "
                f"{prereq_code} → {course.code}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def seed():
    print("=" * 80)
    print("LMPTS — SEEDING 45 COURSES WITH PREREQUISITES")
    print("=" * 80)

    database = Database()
    course_repo = SQLiteCourseRepository(database)

    created = skipped = failed = 0

    # BEGINNER → INTERMEDIATE → ADVANCED
    order = {"BEGINNER": 0, "INTERMEDIATE": 1, "ADVANCED": 2}
    sorted_courses = sorted(COURSES, key=lambda c: order[c["difficulty"]])

    for c in sorted_courses:
        if course_repo.get_course(c["code"]) is not None:
            print(f"  [SKIP]    {c['code']:10} already exists")
            skipped += 1
            continue

        try:
            course = _build_course(c)
            _save_course(course_repo, course, c["prerequisites"])

            prereqs = ", ".join(c["prerequisites"]) if c["prerequisites"] else "—"
            print(f"  [OK]      {c['code']:10} {c['difficulty']:12} prereqs: {prereqs}")
            created += 1

        except Exception as e:
            print(f"  [ERROR]   {c['code']}: {e}")
            failed += 1

    print("=" * 80)
    print(f"  Created  : {created}")
    print(f"  Skipped  : {skipped}")
    print(f"  Failed   : {failed}")
    print(f"  Total    : {len(COURSES)}")
    print("=" * 80)


if __name__ == "__main__":
    seed()