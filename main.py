# Core
from core.user import User
from core.learner import Learner
from core.course import Course
from core.enrollment import Enrollment

# Auth
from auth.password_manager import PasswordManager
from auth.auth_service import AuthService

# Algorithms
from algorithms.graph import CourseGraph
from algorithms.path_finder import PathFinder
from algorithms.cycle_detection import CycleDetector


def main():
    print("===================================")
    print(" LMS Project Started Successfully ")
    print("===================================")

    print("✅ Core modules imported")
    print("✅ Auth modules imported")
    print("✅ Algorithm modules imported")


if __name__ == "__main__":
    main()