"""
recommendation_service.py
--------------------------
Generates personalized course recommendations for learners.

Bridges:
    RecommendationEngine (algorithms) + Repository data

Considers:
    - Completed courses (normal + transfer + exemptions)
    - Difficulty preference
    - Learning goals
    - Course duration
    - Prerequisite readiness
"""

from typing import List, Dict, Optional, Set

from core.exceptions import LearnerNotFoundError
from repository.enrollment_repo import EnrollmentRepositoryInterface
from repository.learner_repo import LearnerRepositoryInterface
from repository.course_repo import CourseRepositoryInterface
from algorithms.graph import CourseGraph
from algorithms.recommendation import RecommendationEngine, CourseInfo
from algorithms.prerequisite_validator import LearnerCredits


class RecommendationService:
    """
    Generates personalized course recommendations.

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

    # ── Recommendations ────────────────────────────────────────────────────────
    def get_recommendations(
        self,
        learner_id:            int,
        difficulty_preference: str = "BEGINNER",
        limit:                 int = 5,
        goals:                 Optional[Set[str]] = None,
    ) -> List[Dict]:
        """
        Generate ranked recommendations, filtered strictly by difficulty.

        If the engine returns no ready-to-take courses at the requested
        difficulty, fall back to showing all courses of that difficulty
        with their remaining prerequisites listed.
        """
        if self._learner_repo.get_learner(learner_id) is None:
            raise LearnerNotFoundError(
                f"Learner {learner_id} not found"
            )

        credits     = self._build_learner_credits(learner_id)
        course_info = self._build_course_info()
        engine      = RecommendationEngine(self._graph)

        normalized = (difficulty_preference or "").strip().upper()

        # ── Step 1: ask engine for a large pool ──────────────────
        recs = engine.recommend(
            learner_credits       = credits,
            course_info           = course_info,
            difficulty_preference = difficulty_preference,
            limit                 = 100,   # get everything
            goals                 = goals,
        )

        # ── Step 2: hard-filter by difficulty ────────────────────
        if normalized in ("BEGINNER", "INTERMEDIATE", "ADVANCED"):
            recs = [
                r for r in recs
                if course_info.get(r.course_code)
                and course_info[r.course_code].difficulty.upper() == normalized
            ]

        # ── Step 3: fallback — show all courses of that level ────
        if not recs and normalized in ("BEGINNER", "INTERMEDIATE", "ADVANCED"):
            completed = credits.completed
            fallback = []

            for code, info in course_info.items():
                if info.difficulty.upper() != normalized:
                    continue
                if code in completed:
                    continue

                # figure out remaining prerequisites
                all_prereqs = self._graph.get_all_prerequisites(code)
                remaining   = sorted(all_prereqs - completed)

                fallback.append({
                    "course_code": info.code,
                    "course_name": info.name,
                    "score":       0.0,
                    "reasons":     (
                        ["Available goal course"] if remaining
                        else ["Ready to enroll"]
                    ),
                    "remaining":   remaining,
                })

            fallback.sort(key=lambda r: (len(r["remaining"]), r["course_code"]))
            return fallback[:limit]

        # ── Step 4: normal path ──────────────────────────────────
        recs = recs[:limit]
        return [
            {
                "course_code": r.course_code,
                "course_name": r.course_name,
                "score":       r.score,
                "reasons":     r.reasons,
                "remaining":   r.remaining,
            }
            for r in recs
        ]
    def get_learning_roadmap(
        self,
        learner_id:   int,
        goal_courses: List[str],
    ) -> Dict[str, List[str]]:
        """
        Generate roadmaps toward multiple goal courses.

        Args:
            learner_id   : Learner to generate roadmaps for.
            goal_courses : List of target course codes.

        Returns:
            dict: {goal_code: [ordered courses to study]}

        Raises:
            LearnerNotFoundError: If learner not found.
        """
        if self._learner_repo.get_learner(learner_id) is None:
            raise LearnerNotFoundError(
                f"Learner {learner_id} not found"
            )

        credits     = self._build_learner_credits(learner_id)
        course_info = self._build_course_info()
        engine      = RecommendationEngine(self._graph)

        return engine.get_learning_roadmap(
            learner_credits = credits,
            goal_courses    = goal_courses,
            course_info     = course_info,
        )

    # ── Internal Helpers ───────────────────────────────────────────────────────

    def _build_learner_credits(self, learner_id: int) -> LearnerCredits:
        """Build LearnerCredits from enrollment records."""
        completed = set(
            self._enrollment_repo.get_completed_course_codes(learner_id)
        )
        return LearnerCredits(completed=completed)

    def _build_course_info(self) -> Dict[str, CourseInfo]:
        """Build CourseInfo dict from all courses in database."""
        courses = self._course_repo.get_all_courses()
        return {
            c.code: CourseInfo(
                code       = c.code,
                name       = c.name,
                difficulty = c.difficulty.value,
                duration   = c.duration,
            )
            for c in courses
        }


# ── Factory Function ───────────────────────────────────────────────────────────

def create_recommendation_service(
    database, graph: CourseGraph
) -> RecommendationService:
    """
    Production factory for RecommendationService.

    Args:
        database : Database instance.
        graph    : CourseGraph from CourseService.

    Returns:
        RecommendationService: Ready-to-use service.
    """
    from repository.enrollment_repo import SQLiteEnrollmentRepository
    from repository.learner_repo import SQLiteLearnerRepository
    from repository.course_repo import SQLiteCourseRepository

    return RecommendationService(
        enrollment_repo = SQLiteEnrollmentRepository(database),
        learner_repo    = SQLiteLearnerRepository(database),
        course_repo     = SQLiteCourseRepository(database),
        graph           = graph,
    )