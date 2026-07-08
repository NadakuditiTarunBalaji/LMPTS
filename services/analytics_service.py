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

from typing import List, Dict, Optional, Set
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from core.enums import EnrollmentStatus, DifficultyLevel, CompletionStatus
from repository.enrollment_repo import (
    EnrollmentRepositoryInterface,
    ProgressRepositoryInterface,
)
from repository.learner_repo import LearnerRepositoryInterface
from repository.course_repo import CourseRepositoryInterface
from algorithms.graph import CourseGraph
from algorithms.topological_sort import TopologicalSorter


def _score_to_grade(score: Optional[float]) -> str:
    """Letter grade from a 0-100 score. None (not yet scored) -> 'N/A'."""
    if score is None:
        return "N/A"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _score_to_bucket(score: Optional[float]) -> Optional[str]:
    """Performance bucket from a 0-100 score. None -> None (excluded)."""
    if score is None:
        return None
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 50:
        return "Average"
    return "Poor"


def _last_n_months(n: int, now: Optional[datetime] = None) -> List[datetime]:
    """
    Return the last n calendar months (oldest first), ending at the
    current month, as datetimes normalized to the 1st of each month.

    Used to build continuous chart x-axes with no gaps, even for
    months that have zero underlying data.
    """
    now = now or datetime.now(timezone.utc)
    months = []
    year, month = now.year, now.month
    for _ in range(n):
        months.append(datetime(year, month, 1, tzinfo=timezone.utc))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()
    return months


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

    # ── Student Performance ─────────────────────────────────────────────────────

    def student_performance_report(self) -> List[Dict]:
        """
        Per-enrollment performance rows for every student in the system.

        Returns:
            list[dict]: {
                "learner_id"  : int,
                "student_name": str,
                "course_code" : str,
                "course_name" : str,
                "score"       : float | None,
                "grade"       : str,
                "status"      : str,
            }
            Sorted by student name, then course code.
        """
        learner_names = {
            l.id: l.name for l in self._learner_repo.get_all_learners()
        }
        course_names = {
            c.code: c.name for c in self._course_repo.get_all_courses()
        }

        rows = []
        for e in self._enrollment_repo.get_all_enrollments():
            rows.append({
                "learner_id":   e.learner_id,
                "student_name": learner_names.get(e.learner_id, f"Learner {e.learner_id}"),
                "course_code":  e.course_code,
                "course_name":  course_names.get(e.course_code, e.course_code),
                "score":        e.score,
                "grade":        _score_to_grade(e.score),
                "status":       e.status.value,
            })

        rows.sort(key=lambda r: (r["student_name"], r["course_code"]))
        return rows

    def score_bucket_distribution(self) -> Dict:
        """
        Count scored enrollments into performance buckets.

        Returns:
            dict: {"Excellent": int, "Good": int, "Average": int,
                   "Poor": int, "total": int}
        """
        buckets = {"Excellent": 0, "Good": 0, "Average": 0, "Poor": 0}
        for e in self._enrollment_repo.get_all_enrollments():
            bucket = _score_to_bucket(e.score)
            if bucket is not None:
                buckets[bucket] += 1

        buckets["total"] = sum(buckets.values())
        return buckets

    def performance_trend(self, months: int = 6) -> List[Dict]:
        """
        Average completion score per month, over the last N months.

        Returns:
            list[dict]: {
                "period"        : str ("YYYY-MM"),
                "label"         : str ("Mon YYYY"),
                "average_score" : float | None,
                "completions"   : int,
            }
            One entry per month, oldest first, with no gaps.
        """
        month_starts = _last_n_months(months)
        scores_by_period: Dict[str, List[float]] = defaultdict(list)

        for e in self._enrollment_repo.get_all_enrollments():
            if e.status != EnrollmentStatus.COMPLETED or e.completed_at is None:
                continue
            period = e.completed_at.strftime("%Y-%m")
            if e.score is not None:
                scores_by_period[period].append(e.score)

        results = []
        for month_start in month_starts:
            period = month_start.strftime("%Y-%m")
            scores = scores_by_period.get(period, [])
            results.append({
                "period":         period,
                "label":          month_start.strftime("%b %Y"),
                "average_score":  round(sum(scores) / len(scores), 2) if scores else None,
                "completions":    len(scores),
            })
        return results

    # ── Course Completion Analytics ─────────────────────────────────────────────

    def course_completion_breakdown(self) -> Dict:
        """
        System-wide course_progress status counts.

        NOTE: CompletionStatus.FAILED is folded into "not_started" —
        the dashboard exposes 3 buckets (Completed/In Progress/Not
        Started) plus a rate, not the full 4-value enum.

        Returns:
            dict: {"completed": int, "in_progress": int,
                   "not_started": int, "total": int,
                   "completion_rate": float}
        """
        counts = {"completed": 0, "in_progress": 0, "not_started": 0}
        for p in self._progress_repo.get_all_progress():
            if p.completion_status == CompletionStatus.COMPLETED:
                counts["completed"] += 1
            elif p.completion_status == CompletionStatus.IN_PROGRESS:
                counts["in_progress"] += 1
            else:
                counts["not_started"] += 1

        total = sum(counts.values())
        counts["total"] = total
        counts["completion_rate"] = (
            round(counts["completed"] / total * 100, 2) if total else 0.0
        )
        return counts

    def course_completion_by_course(self) -> Dict:
        """
        Per-course breakdown of course_progress status counts, shaped
        for a Chart.js stacked bar chart.

        Returns:
            dict: {"labels": list[str], "completed": list[int],
                   "in_progress": list[int], "not_started": list[int]}
        """
        course_names = {
            c.code: c.name for c in self._course_repo.get_all_courses()
        }
        by_course: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"completed": 0, "in_progress": 0, "not_started": 0}
        )

        for p in self._progress_repo.get_all_progress():
            bucket = by_course[p.course_code]
            if p.completion_status == CompletionStatus.COMPLETED:
                bucket["completed"] += 1
            elif p.completion_status == CompletionStatus.IN_PROGRESS:
                bucket["in_progress"] += 1
            else:
                bucket["not_started"] += 1

        codes = sorted(by_course.keys())
        return {
            "labels":      [course_names.get(code, code) for code in codes],
            "completed":   [by_course[code]["completed"] for code in codes],
            "in_progress": [by_course[code]["in_progress"] for code in codes],
            "not_started": [by_course[code]["not_started"] for code in codes],
        }

    # ── Enrollment Analytics ─────────────────────────────────────────────────────

    def enrollment_monthly_trend(self, months: int = 6) -> List[Dict]:
        """
        Enrollment counts per month, over the last N months.

        Returns:
            list[dict]: {"period": str, "label": str, "count": int}
            One entry per month, oldest first, with no gaps.
        """
        month_starts = _last_n_months(months)
        counts_by_period: Dict[str, int] = defaultdict(int)

        for e in self._enrollment_repo.get_all_enrollments():
            period = e.enrolled_at.strftime("%Y-%m")
            counts_by_period[period] += 1

        results = []
        for month_start in month_starts:
            period = month_start.strftime("%Y-%m")
            results.append({
                "period": period,
                "label":  month_start.strftime("%b %Y"),
                "count":  counts_by_period.get(period, 0),
            })
        return results

    def enrollment_summary_metrics(self) -> Dict:
        """
        High-level enrollment counters for the dashboard stat cards.

        Returns:
            dict: {"total_enrollments": int, "new_this_week": int,
                   "monthly_enrollments": int, "growth_rate": float}
        """
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        current_period = now.strftime("%Y-%m")
        if now.month == 1:
            previous_period = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc).strftime("%Y-%m")
        else:
            previous_period = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc).strftime("%Y-%m")

        enrollments = self._enrollment_repo.get_all_enrollments()

        total = len(enrollments)
        new_this_week = sum(1 for e in enrollments if e.enrolled_at >= week_ago)
        current_month_count = sum(
            1 for e in enrollments if e.enrolled_at.strftime("%Y-%m") == current_period
        )
        previous_month_count = sum(
            1 for e in enrollments if e.enrolled_at.strftime("%Y-%m") == previous_period
        )

        if previous_month_count:
            growth_rate = round(
                (current_month_count - previous_month_count) / previous_month_count * 100, 2
            )
        else:
            growth_rate = 100.0 if current_month_count > 0 else 0.0

        return {
            "total_enrollments":   total,
            "new_this_week":       new_this_week,
            "monthly_enrollments": current_month_count,
            "growth_rate":         growth_rate,
        }

    # ── Instructor Analytics ─────────────────────────────────────────────────────

    def instructor_analytics(
        self,
        instructors: List,
        instructor_courses: Dict[int, Set[str]],
    ) -> List[Dict]:
        """
        Per-instructor teaching stats.

        Args:
            instructors        : List of User objects with role=INSTRUCTOR.
            instructor_courses : Map of instructor_id -> set of course
                                  codes they created (supplied by the
                                  caller, since course ownership lives
                                  in course_submissions, not in this
                                  service's dependencies).

        Returns:
            list[dict]: {
                "instructor_id"    : int,
                "instructor_name"  : str,
                "courses_created"  : int,
                "students_assigned": int,
                "completion_rate"  : float,
                "average_rating"   : "N/A",
            }
            Sorted by courses_created desc, then instructor_name.
            No ratings data exists anywhere in this system, so
            average_rating is always the literal "N/A".
        """
        results = []
        for instructor in instructors:
            codes = instructor_courses.get(instructor.id, set())

            learner_ids: Set[int] = set()
            total_enrolled = 0
            total_completed = 0
            for code in codes:
                enrollments = self._enrollment_repo.get_enrollments_by_course(code)
                learner_ids.update(e.learner_id for e in enrollments)
                stats = self.course_completion_rate(code)
                total_enrolled += stats["total_enrolled"]
                total_completed += stats["completed"]

            completion_rate = (
                round(total_completed / total_enrolled * 100, 2)
                if total_enrolled else 0.0
            )

            name = instructor.full_name or instructor.username
            results.append({
                "instructor_id":     instructor.id,
                "instructor_name":   name,
                "courses_created":   len(codes),
                "students_assigned": len(learner_ids),
                "completion_rate":   completion_rate,
                "average_rating":    "N/A",
            })

        results.sort(key=lambda r: (-r["courses_created"], r["instructor_name"]))
        return results


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