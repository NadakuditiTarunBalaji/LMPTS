# Core
from core.user import User
from core.learner import Learner
from core.course import Course
from core.enrollment import Enrollment
from core.enums import (
    UserRole,
    DifficultyLevel,
    CourseStatus,
)

# Algorithms
from algorithms.graph import CourseGraph
from algorithms.path_finder import PathFinder
from algorithms.cycle_detection import CycleDetector

# Auth
from auth.password_manager import PasswordManager


def main():

    print("\n========== CORE TEST ==========")

    # Password
    password_hash = PasswordManager.hash_password("admin123")

    # User
    user = User(
        username="nirmal",
        password_hash=password_hash,
        role=UserRole.LEARNER
    )
    user.validate()

    print("✅ User Created")
    print(user)

    # Learner
    learner = Learner(
        name="Nirmal",
        email="nirmal@gmail.com",
        user_id=1
    )

    learner.validate()

    print("\n✅ Learner Created")
    print(learner)

    # Course
    python = Course(
        code="PY101",
        name="Python Basics",
        difficulty=DifficultyLevel.BEGINNER,
        duration=40,
        status=CourseStatus.PUBLISHED
    )

    python.validate()

    print("\n✅ Course Created")
    print(python)

    # Enrollment
    enrollment = Enrollment(
        learner_id=1,
        course_code="PY101"
    )

    enrollment.validate()

    print("\n✅ Enrollment Created")
    print(enrollment)

    # ----------------------------------------------------
    # NEW FEATURE
    # PRIOR LEARNING RECOGNITION (External Completion)
    # ----------------------------------------------------

    print("\n========== EXTERNAL COURSE COMPLETION TEST ==========")

    print("Completed Courses :", learner.completed_courses)
    print("External Courses  :", learner.external_completed_courses)

    print("\nLearner says:")
    print("'I already studied PY101 outside LMPTS.'")

    learner.mark_external_completion("PY101")

    print("\nAfter External Completion")

    print("Completed Courses :", learner.completed_courses)
    print("External Courses  :", learner.external_completed_courses)

    print("\nChecking PY102 Eligibility...")

    if "PY101" in learner.completed_courses or \
       "PY101" in learner.external_completed_courses:

        print("✅ Eligible to Enroll in PY102")

    else:

        print("❌ Complete PY101 First")

    # ----------------------------------------------------
    # GRAPH TEST
    # ----------------------------------------------------

    print("\n========== ALGORITHM TEST ==========")

    graph = CourseGraph()

    graph.add_edge("PY101", "PY102")
    graph.add_edge("PY102", "PY201")
    graph.add_edge("PY201", "ML101")

    graph.display()

    pathfinder = PathFinder(graph)

    path = pathfinder.find_learning_path(
        "PY101",
        "ML101"
    )

    print("\nShortest Learning Path")

    print(path)

    detector = CycleDetector(graph)

    print("\nCycle Exists ?")

    print(detector.detect_cycle())

    # ----------------------------------------------------
    # PASSWORD TEST
    # ----------------------------------------------------

    print("\n========== PASSWORD TEST ==========")

    print(
        PasswordManager.verify_password(
            "admin123",
            password_hash
        )
    )


if __name__ == "__main__":
    main()