"""
progress_service.py
-------------------
Business logic for tracking learner progress through courses.

Responsibilities:
    - Update progress percentages
    - Calculate completion rates
    - Track learning path progress toward goals
    - Mark courses as failed

Used by:
    EnrollmentService (on completion)
    GUI (progress display)
    AnalyticsService (aggregate reports)
"""

from typing import List, Optional, Dict
from datetime import datetime, timezone

from core.course_progress import CourseProgress
from core.enums import CompletionStatus
from core.exceptions import LearnerNotFoundError, CourseNotFoundError
from repository.enrollment_repo import (
    EnrollmentRepositoryInterface,
    ProgressRepositoryInterface,
)
from repository.learner_repo import LearnerRepositoryInterface
from repository.course_repo import CourseRepositoryInterface
from algorithms.graph import CourseGraph
from algorithms.path_finder import PathFinder


class ProgressService:
    """
    Manages progress tracking for learners.

    Dependencies (injected):
        progress_repo   : ProgressRepositoryInterface
        enrollment_repo : EnrollmentRepositoryInterface
        learner_repo    : LearnerRepositoryInterface
        course_repo     : CourseRepositoryInterface
        graph           : CourseGraph
    """

    def __init__(
        self,
        progress_repo:   ProgressRepositoryInterface,
        enrollment_repo: EnrollmentRepositoryInterface,
        learner_repo:    LearnerRepositoryInterface,
        course_repo:     CourseRepositoryInterface,
        graph:           CourseGraph,
    ):
        self._progress_repo   = progress_repo
        self._enrollment_repo = enrollment_repo
        self._learner_repo    = learner_repo
        self._course_repo     = course_repo
        self._graph           = graph

    # ── Progress Updates ───────────────────────────────────────────────────────

    def update_progress(
        self,
        learner_id:     int,
        course_code:    str,
        new_percentage: float,
    ) -> CourseProgress:
        """
        Update a learner's progress percentage for a course.

        Automatically adjusts CompletionStatus:
            0%        → NOT_STARTED
            1%–99%   → IN_PROGRESS
            100%      → COMPLETED

        Args:
            learner_id     : Learner's ID.
            course_code    : Course being progressed.
            new_percentage : New progress value (0.0–100.0).

        Returns:
            CourseProgress: Updated progress record.

        Raises:
            LearnerNotFoundError: If learner not found.
            CourseNotFoundError : If course not found.
            ValidationError     : If percentage out of range.
        """
        if self._learner_repo.get_learner(learner_id) is None:
            raise LearnerNotFoundError(
                f"Learner {learner_id} not found"
            )
        if not self._course_repo.course_exists(course_code):
            raise CourseNotFoundError(
                f"Course '{course_code}' not found"
            )

        progress = self._progress_repo.get_progress(
            learner_id, course_code
        )

        if progress is None:
            # Create new progress record
            progress = CourseProgress(
                learner_id  = learner_id,
                course_code = course_code,
            )
            progress.update_progress(new_percentage)
            self._progress_repo.create_progress(progress)
        else:
            progress.update_progress(new_percentage)
            self._progress_repo.update_progress(progress)

        return progress

    def mark_failed(
        self, learner_id: int, course_code: str
    ) -> CourseProgress:
        """
        Mark a course progress as FAILED.

        Used when a learner does not meet passing criteria.

        Args:
            learner_id  : Learner's ID.
            course_code : Course that was failed.

        Returns:
            CourseProgress: Updated progress record.

        Raises:
            LearnerNotFoundError: If progress record not found.
        """
        progress = self._progress_repo.get_progress(
            learner_id, course_code
        )
        if progress is None:
            raise LearnerNotFoundError(
                f"No progress record for learner {learner_id} "
                f"in '{course_code}'"
            )

        progress.mark_failed()
        self._progress_repo.update_progress(progress)
        return progress

    # ── Progress Queries ───────────────────────────────────────────────────────

    def get_progress(
        self, learner_id: int, course_code: str
    ) -> Optional[CourseProgress]:
        """
        Get progress for a specific learner-course pair.

        Returns:
            CourseProgress if found, None otherwise. (Q10: read → None)
        """
        return self._progress_repo.get_progress(learner_id, course_code)

    def get_learner_progress(
        self, learner_id: int
    ) -> List[CourseProgress]:
        """
        Get all progress records for a learner.

        Args:
            learner_id: Learner to look up.

        Returns:
            list[CourseProgress]: All progress records for this learner.
        """
        return self._progress_repo.get_all_progress_by_learner(learner_id)

    def calculate_completion_rate(self, learner_id: int) -> float:
        """
        Calculate the percentage of enrolled courses completed.

        Formula:
            completed / total_enrolled * 100

        Args:
            learner_id: Learner to calculate for.

        Returns:
            float: 0.0–100.0 completion rate percentage.
        """
        all_progress = self._progress_repo.get_all_progress_by_learner(
            learner_id
        )
        if not all_progress:
            return 0.0

        completed = sum(
            1 for p in all_progress
            if p.completion_status == CompletionStatus.COMPLETED
        )
        return round(completed / len(all_progress) * 100, 2)

    def get_learning_path_progress(
        self,
        learner_id:  int,
        goal_course: str,
    ) -> Dict:
        """
        Calculate how far a learner has progressed toward a goal course.

        Returns a summary showing:
            - Total courses needed
            - Courses completed
            - Remaining courses
            - Percentage complete

        Args:
            learner_id  : Learner to evaluate.
            goal_course : Target course code.

        Returns:
            dict: {
                "goal"         : goal_course,
                "total"        : int,
                "completed"    : int,
                "remaining"    : list[str],
                "percentage"   : float,
            }
        """
        if not self._graph.has_course(goal_course):
            return {
                "goal":       goal_course,
                "total":      0,
                "completed":  0,
                "remaining":  [],
                "percentage": 0.0,
                "error":      f"Course '{goal_course}' not found in graph",
            }

        # Get all courses needed (prerequisites + goal)
        all_prereqs = self._graph.get_all_prerequisites(goal_course)
        all_needed  = all_prereqs | {goal_course}

        # Get completed course codes from enrollment records
        completed_codes = set(
            self._enrollment_repo.get_completed_course_codes(learner_id)
        )

        completed_needed = all_needed & completed_codes
        remaining        = sorted(all_needed - completed_codes)
        total            = len(all_needed)
        completed_count  = len(completed_needed)

        percentage = (
            round(completed_count / total * 100, 2) if total > 0 else 0.0
        )

        return {
            "goal":       goal_course,
            "total":      total,
            "completed":  completed_count,
            "remaining":  remaining,
            "percentage": percentage,
        }

    def get_overall_summary(self, learner_id: int) -> Dict:
        """
        Return an overall learning summary for a learner.

        Returns:
            dict: {
                "learner_id"      : int,
                "total_enrolled"  : int,
                "completed"       : int,
                "in_progress"     : int,
                "not_started"     : int,
                "failed"          : int,
                "completion_rate" : float,
            }
        """
        all_progress = self._progress_repo.get_all_progress_by_learner(
            learner_id
        )

        counts = {
            CompletionStatus.COMPLETED:   0,
            CompletionStatus.IN_PROGRESS: 0,
            CompletionStatus.NOT_STARTED: 0,
            CompletionStatus.FAILED:      0,
        }

        for p in all_progress:
            counts[p.completion_status] = counts.get(
                p.completion_status, 0
            ) + 1

        total = len(all_progress)
        completed = counts[CompletionStatus.COMPLETED]

        return {
            "learner_id":       learner_id,
            "total_enrolled":   total,
            "completed":        completed,
            "in_progress":      counts[CompletionStatus.IN_PROGRESS],
            "not_started":      counts[CompletionStatus.NOT_STARTED],
            "failed":           counts[CompletionStatus.FAILED],
            "completion_rate":  (
                round(completed / total * 100, 2) if total > 0 else 0.0
            ),
        }


# ── Factory Function ───────────────────────────────────────────────────────────

def create_progress_service(database, graph: CourseGraph) -> ProgressService:
    """
    Production factory for ProgressService.

    Args:
        database : Database instance.
        graph    : CourseGraph from CourseService.

    Returns:
        ProgressService: Ready-to-use service.
    """
    from repository.enrollment_repo import (
        SQLiteEnrollmentRepository,
        SQLiteProgressRepository,
    )
    from repository.learner_repo import SQLiteLearnerRepository
    from repository.course_repo import SQLiteCourseRepository

    return ProgressService(
        progress_repo   = SQLiteProgressRepository(database),
        enrollment_repo = SQLiteEnrollmentRepository(database),
        learner_repo    = SQLiteLearnerRepository(database),
        course_repo     = SQLiteCourseRepository(database),
        graph           = graph,
    )