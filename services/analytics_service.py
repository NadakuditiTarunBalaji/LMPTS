"""
analytics_service.py
--------------------
Aggregate reporting and analytics for the LMPTS system.

Responsibilities:
    - Course completion rates
    - Learner progress summaries
    - Most/least popular courses
    - Bottleneck identification
    - Score analytics
    - Difficulty distribution
    - Prerequisite chain analysis

Used by:
    GUI (analytics dashboard)
    Analyst role reports
"""

from typing import List, Dict, Optional
from collections import defaultdict

from core.enums import EnrollmentStatus, DifficultyLevel, CompletionStatus
from repository.enrollment_repo import (
    EnrollmentRepositoryInterface,
    ProgressRepositoryInterface,
)
from repository.learner_repo import LearnerRepositoryInterface
from repository.course_repo import CourseRepositoryInterface
from algorithms.graph import CourseGraph
from algorithms.topological_sort import TopologicalSorter


class AnalyticsService:
    """
    Provides aggregate analytics and reports.

    Dependencies (injected):
        enrollment_repo : EnrollmentRepositoryInterface
        progress_repo   : ProgressRepositoryInterface
        learner_repo    : LearnerRepositoryInterface
        course_repo     : CourseRepositoryInterface
        graph           : CourseGraph
    """

    def __init__(
        self,
        enrollment_repo: EnrollmentRepositoryInterface,
        progress_repo:   ProgressRepositoryInterface,
        learner_repo:    LearnerRepositoryInterface,
        course_repo:     CourseRepositoryInterface,
        graph:           CourseGraph,
    ):
        self._enrollment_repo = enrollment_repo
        self._progress_repo   = progress_repo
        self._learner_repo    = learner_repo
        self._course_repo     = course_repo
        self._graph           = graph

    # ── Course Analytics ───────────────────────────────────────────────────────

    def course_completion_rate(self, course_code: str) -> Dict:
        """
        Calculate completion statistics for a specific course.

        Returns:
            dict: {
                "course_code"    : str,
                "total_enrolled" : int,
                "completed"      : int,
                "in_progress"    : int,
                "cancelled"      : int,
                "completion_rate": float (percentage),
                "dropout_rate"   : float (percentage),
            }
        """
        enrollments = self._enrollment_repo.get_enrollments_by_course(
            course_code
        )
        total     = len(enrollments)
        completed = sum(
            1 for e in enrollments
            if e.status == EnrollmentStatus.COMPLETED
        )
        in_progress = sum(
            1 for e in enrollments
            if e.status == EnrollmentStatus.IN_PROGRESS
        )
        cancelled = sum(
            1 for e in enrollments
            if e.status == EnrollmentStatus.CANCELLED
        )

        completion_rate = round(completed / total * 100, 2) if total else 0.0
        dropout_rate    = round(cancelled / total * 100, 2) if total else 0.0

        return {
            "course_code":     course_code,
            "total_enrolled":  total,
            "completed":       completed,
            "in_progress":     in_progress,
            "cancelled":       cancelled,
            "completion_rate": completion_rate,
            "dropout_rate":    dropout_rate,
        }

    def most_enrolled_courses(self, limit: int = 10) -> List[Dict]:
        """
        Return the most enrolled courses ranked by enrollment count.

        Args:
            limit: Maximum number of results.

        Returns:
            list[dict]: Ranked courses with enrollment counts.
        """
        courses = self._course_repo.get_all_courses()
        ranked  = []

        for course in courses:
            count = self._enrollment_repo.count_by_course(course.code)
            ranked.append({
                "course_code": course.code,
                "course_name": course.name,
                "difficulty":  course.difficulty.value,
                "enrollments": count,
            })

        ranked.sort(key=lambda x: x["enrollments"], reverse=True)
        return ranked[:limit]

    def bottleneck_courses(self, dropout_threshold: float = 30.0) -> List[Dict]:
        """
        Identify courses with high dropout rates.

        A course is a bottleneck if its dropout rate exceeds
        the threshold percentage.

        Args:
            dropout_threshold: Percentage above which a course is flagged.

        Returns:
            list[dict]: Bottleneck courses sorted by dropout rate.
        """
        courses      = self._course_repo.get_all_courses()
        bottlenecks  = []

        for course in courses:
            stats = self.course_completion_rate(course.code)
            if stats["dropout_rate"] >= dropout_threshold:
                bottlenecks.append({
                    "course_code":   course.code,
                    "course_name":   course.name,
                    "dropout_rate":  stats["dropout_rate"],
                    "total_enrolled":stats["total_enrolled"],
                    "completed":     stats["completed"],
                })

        bottlenecks.sort(key=lambda x: x["dropout_rate"], reverse=True)
        return bottlenecks

    def average_score_by_course(self) -> List[Dict]:
        """
        Calculate average completion score for each course.

        Only includes learners who have COMPLETED the course.

        Returns:
            list[dict]: Courses with average score, sorted by code.
        """
        courses = self._course_repo.get_all_courses()
        results = []

        for course in courses:
            enrollments = self._enrollment_repo.get_enrollments_by_course(
                course.code
            )
            completed_scores = [
                e.score for e in enrollments
                if e.status == EnrollmentStatus.COMPLETED
                and e.score is not None
            ]

            if completed_scores:
                avg_score = round(
                    sum(completed_scores) / len(completed_scores), 2
                )
            else:
                avg_score = None

            results.append({
                "course_code":    course.code,
                "course_name":    course.name,
                "completions":    len(completed_scores),
                "average_score":  avg_score,
            })

        return results

    def difficulty_distribution(self) -> Dict:
        """
        Count courses per difficulty level.

        Returns:
            dict: {
                "BEGINNER"    : int,
                "INTERMEDIATE": int,
                "ADVANCED"    : int,
                "total"       : int,
            }
        """
        distribution = {
            "BEGINNER":     0,
            "INTERMEDIATE": 0,
            "ADVANCED":     0,
            "total":        0,
        }

        for level in DifficultyLevel:
            count = len(self._course_repo.find_by_difficulty(level))
            distribution[level.value] = count
            distribution["total"]    += count

        return distribution

    def prerequisite_chain_length(self) -> List[Dict]:
        """
        Calculate the prerequisite chain depth for every course.

        The chain length is the number of courses that must be
        completed before a learner can enroll.

        Returns:
            list[dict]: Courses sorted by chain length (longest first).
        """
        sorter = TopologicalSorter(self._graph)
        try:
            levels = sorter.get_levels()
        except ValueError:
            return []

        results = []
        for level_index, level_courses in enumerate(levels):
            for course_code in level_courses:
                all_prereqs = self._graph.get_all_prerequisites(course_code)
                results.append({
                    "course_code":    course_code,
                    "chain_length":   len(all_prereqs),
                    "study_level":    level_index,
                    "prerequisites":  sorted(all_prereqs),
                })

        results.sort(key=lambda x: x["chain_length"], reverse=True)
        return results

    # ── Learner Analytics ──────────────────────────────────────────────────────

    def learner_progress_summary(self, learner_id: int) -> Dict:
        """
        Complete progress summary for a specific learner.

        Returns:
            dict: {
                "learner_id"     : int,
                "learner_name"   : str,
                "total_enrolled" : int,
                "completed"      : int,
                "in_progress"    : int,
                "completion_rate": float,
                "average_score"  : float | None,
                "courses"        : list[dict],
            }
        """
        learner = self._learner_repo.get_learner(learner_id)
        name    = learner.name if learner else f"Learner {learner_id}"

        enrollments = self._enrollment_repo.get_enrollments_by_learner(
            learner_id
        )

        completed   = [
            e for e in enrollments
            if e.status == EnrollmentStatus.COMPLETED
        ]
        in_progress = [
            e for e in enrollments
            if e.status == EnrollmentStatus.IN_PROGRESS
        ]

        scores = [
            e.score for e in completed if e.score is not None
        ]
        avg_score = (
            round(sum(scores) / len(scores), 2) if scores else None
        )

        total = len(enrollments)

        return {
            "learner_id":      learner_id,
            "learner_name":    name,
            "total_enrolled":  total,
            "completed":       len(completed),
            "in_progress":     len(in_progress),
            "completion_rate": (
                round(len(completed) / total * 100, 2) if total else 0.0
            ),
            "average_score":   avg_score,
            "courses":         [
                {
                    "course_code": e.course_code,
                    "status":      e.status.value,
                    "score":       e.score,
                }
                for e in enrollments
            ],
        }

    def learner_activity_report(self) -> List[Dict]:
        """
        Activity summary for ALL learners in the system.

        Returns:
            list[dict]: One entry per learner, sorted by completion rate.
        """
        learners = self._learner_repo.get_all_learners()
        report   = []

        for learner in learners:
            summary = self.learner_progress_summary(learner.id)
            report.append(summary)

        report.sort(
            key=lambda x: x["completion_rate"], reverse=True
        )
        return report

    def system_overview(self) -> Dict:
        """
        High-level system statistics for the admin dashboard.

        Returns:
            dict: {
                "total_courses"  : int,
                "total_learners" : int,
                "total_enrollments": int,
                "overall_completion_rate": float,
                "difficulty_distribution": dict,
            }
        """
        courses     = self._course_repo.get_all_courses()
        learners    = self._learner_repo.get_all_learners()
        all_reports = self.learner_activity_report()

        total_enrolled = sum(r["total_enrolled"] for r in all_reports)
        total_completed = sum(r["completed"] for r in all_reports)

        overall_rate = (
            round(total_completed / total_enrolled * 100, 2)
            if total_enrolled else 0.0
        )

        return {
            "total_courses":           len(courses),
            "total_learners":          len(learners),
            "total_enrollments":       total_enrolled,
            "total_completions":       total_completed,
            "overall_completion_rate": overall_rate,
            "difficulty_distribution": self.difficulty_distribution(),
        }


# ── Factory Function ───────────────────────────────────────────────────────────

def create_analytics_service(database, graph: CourseGraph) -> AnalyticsService:
    """
    Production factory for AnalyticsService.

    Args:
        database : Database instance.
        graph    : CourseGraph from CourseService.

    Returns:
        AnalyticsService: Ready-to-use service.
    """
    from repository.enrollment_repo import (
        SQLiteEnrollmentRepository,
        SQLiteProgressRepository,
    )
    from repository.learner_repo import SQLiteLearnerRepository
    from repository.course_repo import SQLiteCourseRepository

    return AnalyticsService(
        enrollment_repo = SQLiteEnrollmentRepository(database),
        progress_repo   = SQLiteProgressRepository(database),
        learner_repo    = SQLiteLearnerRepository(database),
        course_repo     = SQLiteCourseRepository(database),
        graph           = graph,
    )