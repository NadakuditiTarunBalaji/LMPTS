"""
learning_path_service.py
------------------------
Generates and manages learning paths for learners.

Responsibilities:
    - Find the shortest path between two courses
    - Generate a complete learning roadmap toward a goal
    - Calculate what a learner still needs to complete
    - Support transfer credits and exemptions in path calculation

Calls algorithms:
    PathFinder           → BFS learning paths
    TopologicalSorter    → Valid study ordering
    PrerequisiteValidator → Credit-aware filtering
"""

from typing import List, Dict, Optional, Set

from core.exceptions import CourseNotFoundError, LearnerNotFoundError
from repository.enrollment_repo import EnrollmentRepositoryInterface
from repository.learner_repo import LearnerRepositoryInterface
from repository.course_repo import CourseRepositoryInterface
from algorithms.graph import CourseGraph
from algorithms.path_finder import PathFinder
from algorithms.topological_sort import TopologicalSorter
from algorithms.prerequisite_validator import (
    PrerequisiteValidator,
    LearnerCredits,
)


class LearningPathService:
    """
    Generates personalized learning paths.

    Dependencies (injected):
        enrollment_repo : EnrollmentRepositoryInterface
        learner_repo    : LearnerRepositoryInterface
        course_repo     : CourseRepositoryInterface
        graph           : CourseGraph
    """

    def __init__(
        self,
        enrollment_repo: EnrollmentRepositoryInterface,
        learner_repo:    LearnerRepositoryInterface,
        course_repo:     CourseRepositoryInterface,
        graph:           CourseGraph,
    ):
        self._enrollment_repo = enrollment_repo
        self._learner_repo    = learner_repo
        self._course_repo     = course_repo
        self._graph           = graph

    # ── Learning Path Generation ───────────────────────────────────────────────

    def get_path_to_course(
        self,
        start_course: str,
        end_course:   str,
    ) -> Optional[List[str]]:
        """
        Find the shortest path between two courses.

        Args:
            start_course: Course to begin from.
            end_course  : Target course.

        Returns:
            list[str]: Ordered course codes, or None if no path.

        Raises:
            CourseNotFoundError: If either course not in graph.
        """
        if not self._graph.has_course(start_course):
            raise CourseNotFoundError(
                f"Course '{start_course}' not found in graph"
            )
        if not self._graph.has_course(end_course):
            raise CourseNotFoundError(
                f"Course '{end_course}' not found in graph"
            )

        finder = PathFinder(self._graph)
        return finder.find_learning_path(start_course, end_course)

    def get_learner_roadmap(
        self,
        learner_id:   int,
        goal_course:  str,
    ) -> Dict:
        """
        Generate a personalized roadmap for a learner toward a goal.

        Accounts for:
            - Already completed courses (excluded from path)
            - Currently enrolled courses (marked as in_progress)

        Args:
            learner_id  : Learner to generate path for.
            goal_course : Target course code.

        Returns:
            dict: {
                "goal"         : str,
                "completed"    : list[str],
                "in_progress"  : list[str],
                "remaining"    : list[str],
                "full_path"    : list[str],
                "total"        : int,
                "done"         : int,
                "percentage"   : float,
            }

        Raises:
            LearnerNotFoundError: If learner not found.
            CourseNotFoundError : If goal course not found.
        """
        if self._learner_repo.get_learner(learner_id) is None:
            raise LearnerNotFoundError(
                f"Learner {learner_id} not found"
            )
        if not self._graph.has_course(goal_course):
            raise CourseNotFoundError(
                f"Course '{goal_course}' not found in graph"
            )

        completed_codes = set(
            self._enrollment_repo.get_completed_course_codes(learner_id)
        )
        active_codes = set(
            self._enrollment_repo.get_active_course_codes(learner_id)
        )

        credits = LearnerCredits(completed=completed_codes)
        finder  = PathFinder(self._graph)

        remaining = finder.get_recommended_path(
            target    = goal_course,
            completed = completed_codes,
        )

        all_needed = (
            self._graph.get_all_prerequisites(goal_course) | {goal_course}
        )
        full_path_order = finder.get_study_order(all_needed)

        in_progress_on_path = [
            c for c in remaining if c in active_codes
        ]
        still_remaining = [
            c for c in remaining if c not in active_codes
        ]

        total   = len(all_needed)
        done    = len(completed_codes & all_needed)
        pct     = round(done / total * 100, 2) if total else 0.0

        return {
            "goal":        goal_course,
            "completed":   sorted(completed_codes & all_needed),
            "in_progress": in_progress_on_path,
            "remaining":   still_remaining,
            "full_path":   full_path_order,
            "total":       total,
            "done":        done,
            "percentage":  pct,
        }

    def get_available_next_courses(
        self, learner_id: int
    ) -> List[str]:
        """
        Return all courses the learner can enroll in right now.

        A course is available if all direct prerequisites are completed.

        Args:
            learner_id: Learner to check.

        Returns:
            list[str]: Sorted list of enrollable course codes.

        Raises:
            LearnerNotFoundError: If learner not found.
        """
        if self._learner_repo.get_learner(learner_id) is None:
            raise LearnerNotFoundError(
                f"Learner {learner_id} not found"
            )

        completed_codes = set(
            self._enrollment_repo.get_completed_course_codes(learner_id)
        )
        credits   = LearnerCredits(completed=completed_codes)
        validator = PrerequisiteValidator(self._graph)
        return validator.what_can_enroll(credits)

    def get_full_curriculum_order(self) -> List[str]:
        """
        Return all courses in a valid topological study order.

        Useful for displaying the full curriculum structure.

        Returns:
            list[str]: All courses in valid study order.
        """
        sorter = TopologicalSorter(self._graph)
        return sorter.sort()

    def get_curriculum_levels(self) -> List[List[str]]:
        """
        Group all courses into parallel study levels.

        Returns:
            list[list[str]]: Each list is one study level.
        """
        sorter = TopologicalSorter(self._graph)
        return sorter.get_levels()

    def get_prerequisites_for(self, course_code: str) -> List[str]:
        """
        Return all prerequisites in valid study order.

        Args:
            course_code: Target course.

        Returns:
            list[str]: Prerequisites in order (must-do-first first).
        """
        if not self._graph.has_course(course_code):
            raise CourseNotFoundError(
                f"Course '{course_code}' not found"
            )

        finder = PathFinder(self._graph)
        return finder.find_all_prerequisites(course_code)


# ── Factory Function ───────────────────────────────────────────────────────────

def create_learning_path_service(
    database, graph: CourseGraph
) -> LearningPathService:
    """
    Production factory for LearningPathService.

    Args:
        database : Database instance.
        graph    : CourseGraph from CourseService.

    Returns:
        LearningPathService: Ready-to-use service.
    """
    from repository.enrollment_repo import (
        SQLiteEnrollmentRepository,
        SQLiteProgressRepository,
    )
    from repository.learner_repo import SQLiteLearnerRepository
    from repository.course_repo import SQLiteCourseRepository

    return LearningPathService(
        enrollment_repo = SQLiteEnrollmentRepository(database),
        learner_repo    = SQLiteLearnerRepository(database),
        course_repo     = SQLiteCourseRepository(database),
        graph           = graph,
    )