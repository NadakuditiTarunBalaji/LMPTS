"""
recommendation.py
-----------------
Recommends the next courses a learner should take based on:

    - Prerequisites satisfied
    - Transfer credits / exemptions / placement tests
    - Difficulty level preference
    - Shortest remaining path to goals
    - Estimated completion time

Scoring formula:
    score = (
        prerequisite_score   +   # all prereqs met = higher score
        difficulty_score     +   # matches learner level
        path_length_score    +   # shorter remaining path = higher score
        duration_score           # shorter course = higher score
    )

Used by:
    Service Layer (learning path generation)
    GUI (course recommendation panel)
"""

from typing import List, Set, Dict, Optional
from dataclasses import dataclass, field

from algorithms.prerequisite_validator import LearnerCredits


@dataclass
class CourseInfo:
    """
    Metadata about a course used for scoring.

    Attributes:
        code       : Unique course code.
        name       : Human-readable title.
        difficulty : "BEGINNER" / "INTERMEDIATE" / "ADVANCED"
        duration   : Estimated hours to complete.
    """
    code:       str
    name:       str
    difficulty: str   = "BEGINNER"
    duration:   int   = 0


@dataclass
class Recommendation:
    """
    A single course recommendation with its score and reasoning.

    Attributes:
        course_code : Recommended course code.
        course_name : Human-readable title.
        score       : Composite recommendation score (higher = better).
        reasons     : List of human-readable justifications.
        remaining   : Courses still needed after this one.
    """
    course_code: str
    course_name: str
    score:       float
    reasons:     List[str] = field(default_factory=list)
    remaining:   List[str] = field(default_factory=list)


class RecommendationEngine:
    """
    Recommends the best next courses for a learner.

    Usage:
        engine = RecommendationEngine(graph)

        credits = LearnerCredits(
            completed={"CS101"},
            transfer_credits={"MATH101"},
        )

        course_info = {
            "CS201": CourseInfo("CS201", "Data Structures",
                                "INTERMEDIATE", 40),
            "CS202": CourseInfo("CS202", "Databases",
                                "BEGINNER", 20),
        }

        recs = engine.recommend(
            learner_credits    = credits,
            course_info        = course_info,
            difficulty_preference = "INTERMEDIATE",
            limit              = 5,
        )

        for rec in recs:
            print(rec.course_code, rec.score)
    """

    # Scoring weights
    WEIGHT_PREREQ_SATISFIED = 40.0
    WEIGHT_DIFFICULTY_MATCH = 30.0
    WEIGHT_PATH_LENGTH      = 20.0
    WEIGHT_DURATION         = 10.0

    def __init__(self, graph):
        """
        Initialize with a CourseGraph object.

        Args:
            graph: CourseGraph instance.
        """
        self._course_graph = graph
        self.graph         = graph.get_graph()
        self.reverse_graph = graph.get_reverse_graph()

    def recommend(
        self,
        learner_credits:       LearnerCredits,
        course_info:           Dict[str, CourseInfo],
        difficulty_preference: str = "BEGINNER",
        limit:                 int = 5,
        exclude:               Optional[Set[str]] = None,
        goals:                 Optional[Set[str]] = None,
    ) -> List[Recommendation]:
        """
        Generate ranked course recommendations.

        Steps:
            1. Find all courses the learner CAN enroll in now
            2. Exclude already satisfied + excluded courses
            3. Score each candidate course
            4. Return top N sorted by score descending

        Args:
            learner_credits      : All credits the learner holds.
            course_info          : Metadata dict for scoring.
            difficulty_preference: Target difficulty level.
            limit                : Maximum recommendations to return.
            exclude              : Additional courses to exclude.
            goals                : If set, prioritize paths toward goals.

        Returns:
            list[Recommendation]: Sorted by score descending.
        """
        exclude    = exclude or set()
        satisfied  = learner_credits.all_satisfied
        candidates = self._get_candidates(learner_credits, satisfied, exclude)

        if not candidates:
            return []

        scored: List[Recommendation] = []

        for course_code in candidates:
            info  = course_info.get(
                course_code,
                CourseInfo(course_code, course_code)
            )
            score, reasons = self._score_course(
                course_code           = course_code,
                info                  = info,
                satisfied             = satisfied,
                difficulty_preference = difficulty_preference,
                goals                 = goals,
            )

            remaining = self._get_remaining_path(
                course_code, satisfied
            )

            scored.append(Recommendation(
                course_code = course_code,
                course_name = info.name,
                score       = score,
                reasons     = reasons,
                remaining   = remaining,
            ))

        # Sort by score descending, then alphabetically for ties
        scored.sort(key=lambda r: (-r.score, r.course_code))

        return scored[:limit]

    def _get_candidates(
        self,
        learner_credits: LearnerCredits,
        satisfied: Set[str],
        exclude: Set[str]
    ) -> List[str]:
        """
        Find all courses the learner can currently enroll in.

        A course is a candidate if:
            - It exists in the graph
            - All direct prerequisites are satisfied
            - It is not already satisfied
            - It is not in the exclude set

        Returns:
            list[str]: Candidate course codes.
        """
        candidates: List[str] = []

        for course in self._course_graph.get_courses():
            if course in satisfied:
                continue
            if course in exclude:
                continue

            required = self.reverse_graph.get(course, set())
            if required.issubset(satisfied):
                candidates.append(course)

        return candidates

    def _score_course(
        self,
        course_code:           str,
        info:                  CourseInfo,
        satisfied:             Set[str],
        difficulty_preference: str,
        goals:                 Optional[Set[str]]
    ) -> tuple:
        """
        Compute composite score and reasons for one course.

        Returns:
            tuple: (float score, list[str] reasons)
        """
        score   = 0.0
        reasons = []

        # ── 1. Prerequisite satisfaction score ────────────────────────────────
        required = self.reverse_graph.get(course_code, set())
        if required:
            satisfied_count = len(required & satisfied)
            prereq_ratio    = satisfied_count / len(required)
            prereq_score    = prereq_ratio * self.WEIGHT_PREREQ_SATISFIED
            score += prereq_score
            if prereq_ratio == 1.0:
                reasons.append("All prerequisites satisfied")
            else:
                reasons.append(
                    f"{satisfied_count}/{len(required)} "
                    f"prerequisites satisfied"
                )
        else:
            # No prerequisites — full score
            score += self.WEIGHT_PREREQ_SATISFIED
            reasons.append("No prerequisites required")

        # ── 2. Difficulty match score ──────────────────────────────────────────
        difficulty_score = self._score_difficulty(
            info.difficulty, difficulty_preference
        )
        score += difficulty_score
        if difficulty_score == self.WEIGHT_DIFFICULTY_MATCH:
            reasons.append(
                f"Matches difficulty preference ({info.difficulty})"
            )
        elif difficulty_score > 0:
            reasons.append(
                f"Near difficulty preference "
                f"({info.difficulty} vs {difficulty_preference})"
            )

        # ── 3. Path length score (shorter = higher score) ─────────────────────
        remaining = self._get_remaining_path(course_code, satisfied)
        if goals:
            path_to_goal = self._path_score_toward_goals(
                course_code, goals, satisfied
            )
            score += path_to_goal * self.WEIGHT_PATH_LENGTH
            if path_to_goal > 0.5:
                reasons.append("On path to learning goal")
        else:
            # Fewer remaining courses = higher score
            remaining_count = len(remaining)
            if remaining_count == 0:
                path_score = 1.0
            else:
                path_score = 1.0 / (1.0 + remaining_count)
            score += path_score * self.WEIGHT_PATH_LENGTH

        # ── 4. Duration score (shorter = higher score) ────────────────────────
        if info.duration > 0:
            # Normalize: assume max reasonable duration = 100 hours
            duration_score = max(0, 1.0 - (info.duration / 100.0))
            score += duration_score * self.WEIGHT_DURATION
            if info.duration <= 20:
                reasons.append(f"Short course ({info.duration}h)")
            elif info.duration <= 40:
                reasons.append(f"Medium course ({info.duration}h)")
            else:
                reasons.append(f"Comprehensive course ({info.duration}h)")
        else:
            score += self.WEIGHT_DURATION * 0.5

        return round(score, 2), reasons

    def _score_difficulty(
        self,
        course_difficulty: str,
        preference: str
    ) -> float:
        """
        Score how well a course difficulty matches the learner preference.

        Exact match   → full score
        One level off → half score
        Two levels off → zero score

        Returns:
            float: 0.0 to WEIGHT_DIFFICULTY_MATCH
        """
        levels = ["BEGINNER", "INTERMEDIATE", "ADVANCED"]

        try:
            course_idx = levels.index(course_difficulty.upper())
            pref_idx   = levels.index(preference.upper())
        except ValueError:
            return 0.0

        diff = abs(course_idx - pref_idx)

        if diff == 0:
            return self.WEIGHT_DIFFICULTY_MATCH
        elif diff == 1:
            return self.WEIGHT_DIFFICULTY_MATCH * 0.5
        else:
            return 0.0

    def _get_remaining_path(
        self,
        course_code: str,
        satisfied: Set[str]
    ) -> List[str]:
        """
        Get the remaining courses after completing this course.

        Returns courses that this course unlocks but whose other
        prerequisites are not yet satisfied.

        Args:
            course_code: The course being evaluated.
            satisfied  : Currently satisfied courses.

        Returns:
            list[str]: Courses that would become available next.
        """
        future_satisfied = satisfied | {course_code}
        remaining: List[str] = []

        for dependent in self.graph.get(course_code, set()):
            if dependent not in future_satisfied:
                required = self.reverse_graph.get(dependent, set())
                if required.issubset(future_satisfied):
                    remaining.append(dependent)

        return sorted(remaining)

    def _path_score_toward_goals(
        self,
        course_code: str,
        goals: Set[str],
        satisfied: Set[str]
    ) -> float:
        """
        Score how useful a course is for reaching stated goals.

        Higher score if the course is on the path to a goal.

        Returns:
            float: 0.0 to 1.0
        """
        score = 0.0

        for goal in goals:
            if goal in satisfied:
                continue

            all_prereqs = self._course_graph.get_all_prerequisites(goal)
            if course_code in all_prereqs:
                score = max(score, 0.8)
            elif course_code == goal:
                score = max(score, 1.0)

        return score

    def get_learning_roadmap(
        self,
        learner_credits: LearnerCredits,
        goal_courses:    List[str],
        course_info:     Dict[str, CourseInfo],
    ) -> Dict[str, List[str]]:
        """
        Generate a complete roadmap showing what to study
        to reach each goal.

        Args:
            learner_credits: All learner credits.
            goal_courses   : Target courses to reach.
            course_info    : Course metadata.

        Returns:
            dict: {goal_code: [ordered list of courses to study]}

        Example:
            goal = "CS301"
            completed = {"CS101"}

            roadmap → {
                "CS301": ["CS201", "CS301"]
            }
        """
        satisfied = learner_credits.all_satisfied
        roadmap: Dict[str, List[str]] = {}

        from algorithms.path_finder import PathFinder
        finder = PathFinder(self._course_graph)

        for goal in goal_courses:
            remaining = finder.get_recommended_path(
                target           = goal,
                completed        = learner_credits.completed,
                transfer_credits = learner_credits.transfer_credits,
                exemptions       = learner_credits.exemptions
                                   | learner_credits.placement_tests,
            )
            roadmap[goal] = remaining

        return roadmap