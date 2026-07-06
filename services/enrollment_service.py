"""
enrollment_service.py
---------------------
Business logic for learner enrollment, transfer credits, and exemptions.

Responsibilities:
    - Validate prerequisites before enrollment
    - Create enrollment records atomically
    - Process completions (update enrollment + progress + learner)
    - Handle transfer credits and admin-approved exemptions
    - Cancel enrollments

Algorithm integration:
    PrerequisiteValidator → checks prerequisites before enrollment
    LearnerCredits        → unifies normal + transfer + exemption credits

Error handling (Q9 — Both):
    Hard failures  → raise LearnerNotFoundError / CourseNotFoundError
    Soft validation → return EnrollmentResult(success=False, ...)
"""

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Optional, Set

from core.enrollment import Enrollment
from core.course_progress import CourseProgress
from core.enums import EnrollmentStatus, CompletionStatus
from core.exceptions import (
    LearnerNotFoundError,
    CourseNotFoundError,
    DuplicateEnrollmentError,
    PrerequisiteNotMetError,
)
from repository.enrollment_repo import (
    EnrollmentRepositoryInterface,
    ProgressRepositoryInterface,
)
from repository.learner_repo import LearnerRepositoryInterface
from repository.course_repo import CourseRepositoryInterface
from algorithms.graph import CourseGraph
from algorithms.prerequisite_validator import (
    PrerequisiteValidator,
    LearnerCredits,
)


@dataclass
class EnrollmentResult:
    """
    Result of an enrollment attempt.

    Used for soft validation failures (Q9: result object).
    Hard failures (learner not found, etc.) raise exceptions.

    Attributes:
        success              : True if enrollment succeeded.
        enrollment           : The created enrollment (if success).
        missing_prerequisites: List of unmet prerequisites.
        message              : Human-readable explanation.
    """
    success:               bool
    enrollment:            Optional[Enrollment] = None
    missing_prerequisites: List[str]            = field(default_factory=list)
    message:               str                  = ""

    def __bool__(self) -> bool:
        return self.success


class EnrollmentService:
    """
    Orchestrates all enrollment operations.

    Dependencies (injected):
        enrollment_repo : EnrollmentRepositoryInterface
        progress_repo   : ProgressRepositoryInterface
        learner_repo    : LearnerRepositoryInterface
        course_repo     : CourseRepositoryInterface
        graph           : CourseGraph (from CourseService)
        database        : Database (for cross-repo transactions)

    Usage (production):
        service = create_enrollment_service(db)

    Usage (tests):
        service = EnrollmentService(
            enrollment_repo, progress_repo,
            learner_repo, course_repo,
            graph, database
        )
    """

    def __init__(
        self,
        enrollment_repo: EnrollmentRepositoryInterface,
        progress_repo:   ProgressRepositoryInterface,
        learner_repo:    LearnerRepositoryInterface,
        course_repo:     CourseRepositoryInterface,
        graph:           CourseGraph,
        database,
    ):
        self._enrollment_repo = enrollment_repo
        self._progress_repo   = progress_repo
        self._learner_repo    = learner_repo
        self._course_repo     = course_repo
        self._graph           = graph
        self._db              = database

    # ── Enrollment ─────────────────────────────────────────────────────────────

    def enroll_learner(
        self,
        learner_id:       int,
        course_code:      str,
        bypass_prereqs:   bool = False,
    ) -> EnrollmentResult:
        """
        Enroll a learner in a course after validating prerequisites.

        Process:
            1. Verify learner exists (hard fail)
            2. Verify course exists and is PUBLISHED (hard fail)
            3. Check for duplicate enrollment (soft fail)
            4. Validate prerequisites using LearnerCredits (soft fail)
            5. Create enrollment record
            6. Create initial progress record
            All steps 5+6 are atomic (transaction).

        Args:
            learner_id     : ID of the learner to enroll.
            course_code    : Code of the course to enroll in.
            bypass_prereqs : If True, skip prerequisite check
                             (used by admin for special cases).

        Returns:
            EnrollmentResult: success=True with enrollment,
                              or success=False with reason.

        Raises:
            LearnerNotFoundError: If learner does not exist.
            CourseNotFoundError : If course does not exist.
        """
        # ── Step 1: Verify learner exists ──────────────────────────────────────
        learner = self._learner_repo.get_learner(learner_id)
        if learner is None:
            raise LearnerNotFoundError(
                f"Learner {learner_id} not found"
            )

        # ── Step 2: Verify course exists and is published ──────────────────────
        course = self._course_repo.get_course(course_code)
        if course is None:
            raise CourseNotFoundError(
                f"Course '{course_code}' not found"
            )

        from core.enums import CourseStatus
        if course.status != CourseStatus.PUBLISHED:
            return EnrollmentResult(
                success=False,
                message=(
                    f"Course '{course_code}' is not available for enrollment "
                    f"(status: {course.status.value})."
                ),
            )

        # ── Step 3: Check duplicate enrollment ────────────────────────────────
        existing = self._enrollment_repo.get_enrollment_by_learner_course(
            learner_id, course_code
        )
        if existing is not None:
            if existing.status in (
                EnrollmentStatus.ENROLLED,
                EnrollmentStatus.IN_PROGRESS,
            ):
                return EnrollmentResult(
                    success=False,
                    message=(
                        f"Learner {learner_id} is already enrolled in "
                        f"'{course_code}' "
                        f"(status: {existing.status.value})."
                    ),
                )

        # ── Step 4: Validate prerequisites ────────────────────────────────────
        if not bypass_prereqs:
            credits   = self._build_learner_credits(learner_id)
            validator = PrerequisiteValidator(self._graph)
            result    = validator.can_enroll(credits, course_code)

            if not result:
                return EnrollmentResult(
                    success=False,
                    missing_prerequisites=result.missing_prerequisites,
                    message=result.message,
                )

        # ── Steps 5+6: Create enrollment + progress atomically ─────────────────
        enrollment = Enrollment(
            learner_id  = learner_id,
            course_code = course_code,
            status      = EnrollmentStatus.ENROLLED,
        )

        with self._db.transaction() as conn:
            # Insert enrollment
            cursor = conn.execute(
                """
                INSERT INTO enrollments
                    (learner_id, course_code, status,
                     score, enrolled_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    learner_id,
                    course_code,
                    EnrollmentStatus.ENROLLED.value,
                    None,
                    datetime.now(timezone.utc).isoformat(),
                    None,
                )
            )
            enrollment.id = cursor.lastrowid

            # Insert initial progress record
            conn.execute(
                """
                INSERT OR REPLACE INTO course_progress
                    (learner_id, course_code, percentage,
                     completion_status, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    learner_id,
                    course_code,
                    0.0,
                    CompletionStatus.NOT_STARTED.value,
                    datetime.now(timezone.utc).isoformat(),
                )
            )

        return EnrollmentResult(
            success    = True,
            enrollment = enrollment,
            message    = (
                f"Successfully enrolled learner {learner_id} "
                f"in '{course_code}'."
            ),
        )

    def cancel_enrollment(
        self, learner_id: int, course_code: str
    ) -> None:
        """
        Cancel a learner's enrollment in a course.

        Args:
            learner_id  : Learner's ID.
            course_code : Course code to cancel.

        Raises:
            LearnerNotFoundError: If enrollment not found.
        """
        enrollment = self._enrollment_repo.get_enrollment_by_learner_course(
            learner_id, course_code
        )
        if enrollment is None:
            raise LearnerNotFoundError(
                f"No enrollment found for learner {learner_id} "
                f"in '{course_code}'"
            )

        enrollment.cancel()
        self._enrollment_repo.update_enrollment(enrollment)

    def complete_enrollment(
        self,
        learner_id:  int,
        course_code: str,
        score:       float,
    ) -> Enrollment:
        """
        Mark an enrollment as completed with a score.

        Atomically:
            - Sets enrollment status to COMPLETED
            - Sets score and completed_at
            - Updates course_progress to COMPLETED / 100%

        Args:
            learner_id  : Learner's ID.
            course_code : Course completed.
            score       : Final score (0–100).

        Returns:
            Enrollment: Updated enrollment record.

        Raises:
            LearnerNotFoundError: If enrollment not found.
            ValidationError     : If score out of range.
        """
        enrollment = self._enrollment_repo.get_enrollment_by_learner_course(
            learner_id, course_code
        )
        if enrollment is None:
            raise LearnerNotFoundError(
                f"No enrollment found for learner {learner_id} "
                f"in '{course_code}'"
            )

        # Apply state transition (validates score, checks status)
        enrollment.complete(score)

        # Atomically update enrollment + progress
        with self._db.transaction() as conn:
            conn.execute(
                """
                UPDATE enrollments
                SET status = ?, score = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    EnrollmentStatus.COMPLETED.value,
                    score,
                    datetime.now(timezone.utc).isoformat(),
                    enrollment.id,
                )
            )
            conn.execute(
                """
                UPDATE course_progress
                SET percentage = ?, completion_status = ?, updated_at = ?
                WHERE learner_id = ? AND course_code = ?
                """,
                (
                    100.0,
                    CompletionStatus.COMPLETED.value,
                    datetime.now(timezone.utc).isoformat(),
                    learner_id,
                    course_code,
                )
            )

        return enrollment

    def start_enrollment(
        self, learner_id: int, course_code: str
    ) -> Enrollment:
        """
        Transition enrollment from ENROLLED → IN_PROGRESS.

        Called when a learner starts working on course content.

        Args:
            learner_id  : Learner's ID.
            course_code : Course code.

        Returns:
            Enrollment: Updated enrollment.

        Raises:
            LearnerNotFoundError: If enrollment not found.
        """
        enrollment = self._enrollment_repo.get_enrollment_by_learner_course(
            learner_id, course_code
        )
        if enrollment is None:
            raise LearnerNotFoundError(
                f"No enrollment found for learner {learner_id} "
                f"in '{course_code}'"
            )

        enrollment.start()
        self._enrollment_repo.update_enrollment(enrollment)

        # Update progress status to IN_PROGRESS
        with self._db.transaction() as conn:
            conn.execute(
                """
                UPDATE course_progress
                SET completion_status = ?, updated_at = ?
                WHERE learner_id = ? AND course_code = ?
                """,
                (
                    CompletionStatus.IN_PROGRESS.value,
                    datetime.now(timezone.utc).isoformat(),
                    learner_id,
                    course_code,
                )
            )

        return enrollment

    # ── Transfer Credits and Exemptions ────────────────────────────────────────

    def transfer_credit(
        self,
        learner_id:  int,
        course_code: str,
        admin_note:  str = "",
    ) -> EnrollmentResult:
        """
        Record a transfer credit for a learner.

        Creates a COMPLETED enrollment with score 100 to indicate
        the course was completed at another institution.

        Args:
            learner_id  : Learner receiving the credit.
            course_code : Course being credited.
            admin_note  : Optional admin justification note.

        Returns:
            EnrollmentResult: success=True on success.

        Raises:
            LearnerNotFoundError: If learner not found.
            CourseNotFoundError : If course not found.
        """
        learner = self._learner_repo.get_learner(learner_id)
        if learner is None:
            raise LearnerNotFoundError(
                f"Learner {learner_id} not found"
            )

        course = self._course_repo.get_course(course_code)
        if course is None:
            raise CourseNotFoundError(
                f"Course '{course_code}' not found"
            )

        # Check if already credited
        existing = self._enrollment_repo.get_enrollment_by_learner_course(
            learner_id, course_code
        )
        if existing is not None and existing.status == EnrollmentStatus.COMPLETED:
            return EnrollmentResult(
                success=False,
                message=(
                    f"Learner {learner_id} already has credit "
                    f"for '{course_code}'."
                ),
            )

        now = datetime.now(timezone.utc).isoformat()

        with self._db.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO enrollments
                    (learner_id, course_code, status,
                     score, enrolled_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    learner_id,
                    course_code,
                    EnrollmentStatus.COMPLETED.value,
                    100.0,   # Transfer = full credit
                    now,
                    now,
                )
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO course_progress
                    (learner_id, course_code, percentage,
                     completion_status, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    learner_id,
                    course_code,
                    100.0,
                    CompletionStatus.COMPLETED.value,
                    now,
                )
            )

        return EnrollmentResult(
            success=True,
            message=(
                f"Transfer credit recorded for learner {learner_id} "
                f"in '{course_code}'."
            ),
        )

    def approve_exemption(
        self,
        learner_id:  int,
        course_code: str,
        admin_note:  str = "",
    ) -> EnrollmentResult:
        """
        Record an admin-approved exemption for a learner.

        Similar to transfer_credit but marks as exempt.
        Creates a COMPLETED enrollment with score 0
        (exempted, not graded).

        Args:
            learner_id  : Learner receiving the exemption.
            course_code : Course being exempted.
            admin_note  : Admin justification.

        Returns:
            EnrollmentResult: success=True on success.
        """
        learner = self._learner_repo.get_learner(learner_id)
        if learner is None:
            raise LearnerNotFoundError(
                f"Learner {learner_id} not found"
            )

        course = self._course_repo.get_course(course_code)
        if course is None:
            raise CourseNotFoundError(
                f"Course '{course_code}' not found"
            )

        now = datetime.now(timezone.utc).isoformat()

        with self._db.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO enrollments
                    (learner_id, course_code, status,
                     score, enrolled_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    learner_id,
                    course_code,
                    EnrollmentStatus.COMPLETED.value,
                    0.0,     # Exempted = no grade
                    now,
                    now,
                )
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO course_progress
                    (learner_id, course_code, percentage,
                     completion_status, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    learner_id,
                    course_code,
                    100.0,
                    CompletionStatus.COMPLETED.value,
                    now,
                )
            )

        return EnrollmentResult(
            success=True,
            message=(
                f"Exemption approved for learner {learner_id} "
                f"in '{course_code}'."
            ),
        )

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_enrollment(self, enrollment_id: int) -> Optional[Enrollment]:
        """Get enrollment by primary key. Returns None if not found."""
        return self._enrollment_repo.get_enrollment(enrollment_id)

    def get_learner_enrollments(
        self, learner_id: int
    ) -> List[Enrollment]:
        """All enrollments for a learner."""
        return self._enrollment_repo.get_enrollments_by_learner(learner_id)

    def get_course_enrollments(
        self, course_code: str
    ) -> List[Enrollment]:
        """All enrollments for a course."""
        return self._enrollment_repo.get_enrollments_by_course(course_code)

    def get_completed_courses(self, learner_id: int) -> List[str]:
        """Return course codes the learner has completed."""
        return self._enrollment_repo.get_completed_course_codes(learner_id)

    def get_active_courses(self, learner_id: int) -> List[str]:
        """Return course codes the learner is currently enrolled in."""
        return self._enrollment_repo.get_active_course_codes(learner_id)

    # ── Internal Helpers ───────────────────────────────────────────────────────

    def _build_learner_credits(self, learner_id: int) -> LearnerCredits:
        """
        Build a LearnerCredits object from database enrollment records.

        All COMPLETED enrollments count as satisfied prerequisites,
        regardless of how they were completed (normal, transfer, exemption).

        Args:
            learner_id: Learner to build credits for.

        Returns:
            LearnerCredits: With completed set populated from DB.
        """
        completed_codes = self._enrollment_repo.get_completed_course_codes(
            learner_id
        )
        return LearnerCredits(completed=set(completed_codes))


# ── Factory Function ───────────────────────────────────────────────────────────

def create_enrollment_service(database, graph: CourseGraph) -> "EnrollmentService":
    """
    Production factory for EnrollmentService.

    Args:
        database : Database instance.
        graph    : CourseGraph (usually from create_course_service).

    Returns:
        EnrollmentService: Ready-to-use service.

    Usage:
        db             = Database()
        course_svc     = create_course_service(db)
        enrollment_svc = create_enrollment_service(db, course_svc.get_graph())
    """
    from repository.enrollment_repo import (
        SQLiteEnrollmentRepository,
        SQLiteProgressRepository,
    )
    from repository.learner_repo import SQLiteLearnerRepository
    from repository.course_repo import SQLiteCourseRepository

    return EnrollmentService(
        enrollment_repo = SQLiteEnrollmentRepository(database),
        progress_repo   = SQLiteProgressRepository(database),
        learner_repo    = SQLiteLearnerRepository(database),
        course_repo     = SQLiteCourseRepository(database),
        graph           = graph,
        database        = database,
    )