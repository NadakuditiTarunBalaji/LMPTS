"""
prerequisite_validator.py
--------------------------
Validates whether a learner can enroll in a course,
considering all forms of course credit.

Credit types supported:
    NORMAL    : Standard course completion within LMPTS
    TRANSFER  : Credit from another institution
    EXEMPTION : Admin-approved prior learning / exemption
    PLACEMENT : Placement test result

Validation formula:
    can_enroll = required_prerequisites ⊆ satisfied_credits

    satisfied_credits = completed ∪ transfer ∪ exemptions ∪ placement

Used by:
    RecommendationEngine
    EnrollmentService (Person 4 service layer)
    GUI enrollment forms
"""

from typing import Set, List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum


class CreditType(Enum):
    """
    How a prerequisite was satisfied.

    NORMAL    : Completed normally inside LMPTS
    TRANSFER  : Credit transferred from another institution
    EXEMPTION : Admin-approved prior learning
    PLACEMENT : Passed a placement / challenge exam
    """
    NORMAL    = "NORMAL"
    TRANSFER  = "TRANSFER"
    EXEMPTION = "EXEMPTION"
    PLACEMENT = "PLACEMENT"


@dataclass
class LearnerCredits:
    """
    All academic credits a learner holds across all credit types.

    Attributes:
        completed        : Courses completed normally in LMPTS
        transfer_credits : Courses credited by transfer
        exemptions       : Courses exempted by admin approval
        placement_tests  : Courses passed via placement exam

    Usage:
        credits = LearnerCredits(
            completed        = {"CS101", "CS102"},
            transfer_credits = {"MATH101"},
            exemptions       = {"COMM101"},
        )
        print(credits.all_satisfied)
        # → {"CS101", "CS102", "MATH101", "COMM101"}
    """
    completed:        Set[str] = field(default_factory=set)
    transfer_credits: Set[str] = field(default_factory=set)
    exemptions:       Set[str] = field(default_factory=set)
    placement_tests:  Set[str] = field(default_factory=set)

    @property
    def all_satisfied(self) -> Set[str]:
        """
        Union of all credit types.

        This is the complete set of courses that count as
        satisfied for prerequisite validation purposes.

        Returns:
            set[str]: All satisfied course codes.
        """
        return (
            self.completed
            | self.transfer_credits
            | self.exemptions
            | self.placement_tests
        )


@dataclass
class ValidationResult:
    """
    Result of a prerequisite validation check.

    Attributes:
        can_enroll            : True if enrollment is allowed.
        missing_prerequisites : Prerequisites not yet satisfied.
        satisfied_by          : How each satisfied prerequisite was met.
        message               : Human-readable explanation.

    Usage:
        result = validator.can_enroll(credits, "CS201")
        if result:
            enroll()
        else:
            print(result.message)
            print(result.missing_prerequisites)
    """
    can_enroll:            bool
    missing_prerequisites: List[str]
    satisfied_by:          Dict[str, CreditType]
    message:               str

    def __bool__(self) -> bool:
        """Allow: if result: ..."""
        return self.can_enroll


class PrerequisiteValidator:
    """
    Validates enrollment eligibility considering all credit types.

    Usage:
        validator = PrerequisiteValidator(graph)

        credits = LearnerCredits(
            completed={"CS101"},
            transfer_credits={"CS102"},
        )

        result = validator.can_enroll(
            learner_credits=credits,
            target_course="CS201",
        )

        if result:
            enroll_learner()
        else:
            show_missing(result.missing_prerequisites)
    """

    def __init__(self, graph):
        """
        Initialize with a CourseGraph object.

        Args:
            graph: CourseGraph instance.
        """
        self._course_graph = graph
        self.reverse_graph = graph.get_reverse_graph()
        self.graph         = graph.get_graph()

    def can_enroll(
        self,
        learner_credits: LearnerCredits,
        target_course: str,
    ) -> ValidationResult:
        """
        Check whether a learner can enroll in a target course.

        Checks only DIRECT prerequisites (one level).

        Validation:
            required  = direct prerequisites of target_course
            satisfied = learner_credits.all_satisfied
            can_enroll = required ⊆ satisfied

        Args:
            learner_credits : All credits the learner holds.
            target_course   : Course the learner wants to enroll in.

        Returns:
            ValidationResult: Contains decision + details.

        Example:
            graph: CS101 → CS201

            credits = LearnerCredits(completed={"CS101"})
            can_enroll(credits, "CS201")
            → ValidationResult(can_enroll=True, ...)

            credits = LearnerCredits()
            can_enroll(credits, "CS201")
            → ValidationResult(can_enroll=False, missing=["CS101"], ...)
        """
        if not self._course_graph.has_course(target_course):
            return ValidationResult(
                can_enroll=False,
                missing_prerequisites=[],
                satisfied_by={},
                message=(
                    f"Course '{target_course}' not found in the system."
                ),
            )

        required = self.reverse_graph.get(target_course, set())

        if not required:
            return ValidationResult(
                can_enroll=True,
                missing_prerequisites=[],
                satisfied_by={},
                message=(
                    f"'{target_course}' has no prerequisites. "
                    f"Enrollment allowed."
                ),
            )

        satisfied    = learner_credits.all_satisfied
        missing      = sorted(required - satisfied)
        satisfied_by = self._map_satisfied_by(
            required & satisfied, learner_credits
        )

        if missing:
            return ValidationResult(
                can_enroll=False,
                missing_prerequisites=missing,
                satisfied_by=satisfied_by,
                message=(
                    f"Cannot enroll in '{target_course}'. "
                    f"Missing prerequisites: {', '.join(missing)}"
                ),
            )

        return ValidationResult(
            can_enroll=True,
            missing_prerequisites=[],
            satisfied_by=satisfied_by,
            message=(
                f"All prerequisites satisfied for '{target_course}'. "
                f"Enrollment allowed."
            ),
        )

    def can_enroll_full_chain(
        self,
        learner_credits: LearnerCredits,
        target_course: str,
    ) -> ValidationResult:
        """
        Check enrollment eligibility using the FULL prerequisite chain.

        Stricter than can_enroll() — checks ALL transitive prerequisites,
        not just direct ones.

        Args:
            learner_credits : All credits the learner holds.
            target_course   : Target course.

        Returns:
            ValidationResult: With full chain analysis.

        Example:
            CS101 → CS201 → CS301

            credits = LearnerCredits(completed={"CS201"})

            can_enroll(credits, "CS301")
            → True  (CS201 is direct prereq and is satisfied)

            can_enroll_full_chain(credits, "CS301")
            → False (CS101 is also needed — CS201 requires CS101)
        """
        if not self._course_graph.has_course(target_course):
            return ValidationResult(
                can_enroll=False,
                missing_prerequisites=[],
                satisfied_by={},
                message=f"Course '{target_course}' not found.",
            )

        all_required = self._course_graph.get_all_prerequisites(
            target_course
        )

        if not all_required:
            return ValidationResult(
                can_enroll=True,
                missing_prerequisites=[],
                satisfied_by={},
                message=(
                    f"'{target_course}' has no prerequisites. "
                    f"Enrollment allowed."
                ),
            )

        satisfied    = learner_credits.all_satisfied
        missing      = sorted(all_required - satisfied)
        satisfied_by = self._map_satisfied_by(
            all_required & satisfied, learner_credits
        )

        if missing:
            return ValidationResult(
                can_enroll=False,
                missing_prerequisites=missing,
                satisfied_by=satisfied_by,
                message=(
                    f"Cannot enroll in '{target_course}'. "
                    f"Missing prerequisites (full chain): "
                    f"{', '.join(missing)}"
                ),
            )

        return ValidationResult(
            can_enroll=True,
            missing_prerequisites=[],
            satisfied_by=satisfied_by,
            message=(
                f"All prerequisites satisfied for '{target_course}'. "
                f"Enrollment allowed."
            ),
        )

    def get_missing_prerequisites(
        self,
        learner_credits: LearnerCredits,
        target_course: str,
    ) -> List[str]:
        """
        Return only the list of missing prerequisites.

        Convenience wrapper around can_enroll().

        Args:
            learner_credits : Learner credits.
            target_course   : Course to check.

        Returns:
            list[str]: Missing prerequisite codes (sorted).
                       Empty list if all satisfied.
        """
        result = self.can_enroll(learner_credits, target_course)
        return result.missing_prerequisites

    def what_can_enroll(
        self,
        learner_credits: LearnerCredits,
    ) -> List[str]:
        """
        Return all courses the learner can currently enroll in.

        A course is enrollable if:
            1. All direct prerequisites are satisfied
            2. The learner has not already completed it

        Args:
            learner_credits: All credits the learner holds.

        Returns:
            list[str]: Sorted list of enrollable course codes.

        Example:
            graph: CS101 → CS201 → CS301
            completed: {CS101}

            what_can_enroll(credits) → ["CS201"]
        """
        satisfied  = learner_credits.all_satisfied
        enrollable: List[str] = []

        for course in self._course_graph.get_courses():
            if course in satisfied:
                continue
            required = self.reverse_graph.get(course, set())
            if required.issubset(satisfied):
                enrollable.append(course)

        return sorted(enrollable)

    def can_add_prerequisite(
        self,
        course_code: str,
        new_prereq: str,
    ) -> bool:
        """
        Check whether adding a new prerequisite would create a cycle.

        Args:
            course_code : Course to add prerequisite to.
            new_prereq  : The proposed new prerequisite.

        Returns:
            bool: True if safe (no cycle), False if it would create a cycle.

        Example:
            graph: CS101 → CS201 → CS301

            can_add_prerequisite("CS101", "CS301")
            → False  (CS301 → CS101 closes the cycle)

            can_add_prerequisite("CS201", "CS102")
            → True   (safe)
        """
        from algorithms.cycle_detection import CycleDetector
        detector = CycleDetector(self._course_graph)
        return not detector.would_create_cycle(new_prereq, course_code)

    def _map_satisfied_by(
        self,
        satisfied_courses: Set[str],
        learner_credits: LearnerCredits,
    ) -> Dict[str, CreditType]:
        """
        Map each satisfied course code to how it was satisfied.

        Args:
            satisfied_courses : Courses that are satisfied.
            learner_credits   : Learner's credit breakdown.

        Returns:
            dict: {course_code: CreditType}
        """
        result: Dict[str, CreditType] = {}

        for course in satisfied_courses:
            if course in learner_credits.completed:
                result[course] = CreditType.NORMAL
            elif course in learner_credits.transfer_credits:
                result[course] = CreditType.TRANSFER
            elif course in learner_credits.exemptions:
                result[course] = CreditType.EXEMPTION
            elif course in learner_credits.placement_tests:
                result[course] = CreditType.PLACEMENT

        return result