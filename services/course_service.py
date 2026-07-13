"""
course_service.py
-----------------
Business logic for course lifecycle management.

Responsibilities:
    - Create, read, update, delete courses
    - Manage course status transitions (DRAFT → PUBLISHED → ARCHIVED)
    - Add/remove prerequisites with cycle detection
    - Provide study ordering via topological sort
    - Build and maintain the CourseGraph for algorithm use

Calls algorithms:
    CycleDetector   → prevents circular prerequisites
    TopologicalSorter → get_study_order()

Error handling:
    Read operations  → return None if not found
    Write operations → raise CourseNotFoundError if not found
"""

from typing import List, Optional, Dict, Set

from core.course import Course
from core.enums import CourseStatus, DifficultyLevel
from core.exceptions import (
    CourseNotFoundError,
    ValidationError,
    CircularDependencyError,
)
from repository.course_repo import CourseRepositoryInterface
from algorithms.graph import CourseGraph
from algorithms.cycle_detection import CycleDetector
from algorithms.topological_sort import TopologicalSorter


class CourseService:
    """
    Orchestrates all course-related business operations.

    Dependencies (injected):
        course_repo : CourseRepositoryInterface
        graph       : CourseGraph (shared with other services)

    Usage (production):
        service = create_course_service(db)

    Usage (tests):
        service = CourseService(mock_repo, CourseGraph())
    """

    def __init__(
        self,
        course_repo: CourseRepositoryInterface,
        graph: CourseGraph,
    ):
        self._repo  = course_repo
        self._graph = graph
        # Build the graph from whatever is already in the database
        self._rebuild_graph()

    # ── Graph Management ───────────────────────────────────────────────────────

    def _rebuild_graph(self) -> None:
        """
        Rebuild the CourseGraph from the current database state.

        Called on initialization and after any structural change
        (add/remove course, add/remove prerequisite).
        """
        courses = self._repo.get_all_courses()
        codes   = [c.code for c in courses]
        prereqs = {
            c.code: c.get_prerequisites()
            for c in courses
        }
        self._graph.build_from_courses(codes, prereqs)

    def get_graph(self) -> CourseGraph:
        """
        Return the current CourseGraph.

        Used by EnrollmentService and LearningPathService.

        Returns:
            CourseGraph: Current prerequisite graph.
        """
        return self._graph

    # ── CRUD Operations ────────────────────────────────────────────────────────

    def create_course(self, course: Course) -> Course:
        """
        Persist a new course and add it to the graph.

        Args:
            course: Course object to create.

        Returns:
            Course: Saved course object.

        Raises:
            ValidationError: If code already exists or validation fails.
        """
        course.validate()
        saved = self._repo.create_course(course)
        self._graph.add_course(saved.code)

        # Add any prerequisites already set on the course object
        for prereq in course.get_prerequisites():
            if self._graph.has_course(prereq):
                self._graph.add_edge(prereq, saved.code)

        return saved

    def get_course(self, code: str) -> Optional[Course]:
        """
        Retrieve a course by code.

        Returns:
            Course if found, None otherwise. (Q10: read → None)
        """
        return self._repo.get_course(code)

    def get_all_courses(self) -> List[Course]:
        """
        Retrieve all courses from the database.

        Returns:
            list[Course]: All courses ordered by code.
        """
        return self._repo.get_all_courses()

    def get_available_courses(self) -> List[Course]:
        """
        Return only PUBLISHED courses (visible to learners).

        Returns:
            list[Course]: Published courses.
        """
        return self._repo.find_by_status(CourseStatus.PUBLISHED)

    def get_courses_by_difficulty(
        self, difficulty: DifficultyLevel
    ) -> List[Course]:
        """
        Return courses at a specific difficulty level.

        Args:
            difficulty: DifficultyLevel enum value.

        Returns:
            list[Course]: Matching courses.
        """
        return self._repo.find_by_difficulty(difficulty)

    # ── Submission sync helper ────────────────────────────────────────────────────

    def _sync_submissions(
        self,
        course_code: str,
        course_status: CourseStatus,
    ) -> None:
        """
        Keep course_submissions.status aligned with courses.status.

        Mapping:
            courses.PUBLISHED → course_submissions.APPROVED  (non-rejected rows)
            courses.ARCHIVED  → course_submissions.ARCHIVED  (non-rejected rows)
            courses.DRAFT     → course_submissions.PENDING   (non-rejected rows)

        REJECTED submissions are never touched (rejection is a terminal state).
        Failures are logged but never raised.
        """
        sub_status_map = {
            CourseStatus.PUBLISHED: "APPROVED",
            CourseStatus.ARCHIVED:  "ARCHIVED",
            CourseStatus.DRAFT:     "PENDING",
        }
        new_sub_status = sub_status_map.get(course_status)
        if new_sub_status is None:
            return

        db = getattr(self._repo, "_db", None) or getattr(self._repo, "db", None)
        if db is None:
            return

        try:
            with db.transaction() as conn:
                conn.execute(
                    """
                    UPDATE course_submissions
                    SET status = ?
                    WHERE course_code = ?
                    AND status != 'REJECTED'
                    """,
                    (new_sub_status, course_code),
                )
        except Exception as e:
            # Never fail the core operation because of a sync error
            import logging
            logging.getLogger(__name__).warning(
                f"[_sync_submissions] {course_code} → {new_sub_status}: {e}"
            )


    # ── Status Transitions (patched) ─────────────────────────────────────────────

    def publish_course(self, code: str) -> Course:
        """
        Transition a course from DRAFT → PUBLISHED.
        Idempotent: already-published courses still trigger a submission sync.
        """
        course = self._repo.get_course(code)
        if course is None:
            raise CourseNotFoundError(f"Course '{code}' not found")

        if course.status == CourseStatus.PUBLISHED:
            # Already published — still sync submissions to be safe
            self._sync_submissions(code, CourseStatus.PUBLISHED)
            return course

        if course.status != CourseStatus.DRAFT:
            raise ValidationError(
                f"Only DRAFT courses can be published. "
                f"'{code}' is currently {course.status.value}."
            )

        course.status = CourseStatus.PUBLISHED
        self._repo.update_course(course)

        self._sync_submissions(code, CourseStatus.PUBLISHED)
        self._rebuild_graph()
        return course


    def archive_course(self, code: str) -> Course:
        """
        Transition a course from PUBLISHED → ARCHIVED.
        Idempotent.
        """
        course = self._repo.get_course(code)
        if course is None:
            raise CourseNotFoundError(f"Course '{code}' not found")

        if course.status == CourseStatus.ARCHIVED:
            self._sync_submissions(code, CourseStatus.ARCHIVED)
            return course

        if course.status != CourseStatus.PUBLISHED:
            raise ValidationError(
                f"Only PUBLISHED courses can be archived. "
                f"'{code}' is currently {course.status.value}."
            )

        course.status = CourseStatus.ARCHIVED
        self._repo.update_course(course)

        self._sync_submissions(code, CourseStatus.ARCHIVED)
        self._rebuild_graph()
        return course


    def update_course(self, course: Course) -> None:
        """
        Update an existing course's fields.
        Also syncs course_submissions if the status changed.
        """
        if not self._repo.course_exists(course.code):
            raise CourseNotFoundError(
                f"Course '{course.code}' not found"
            )

        course.validate()
        self._repo.update_course(course)

        self._sync_submissions(course.code, course.status)
        self._rebuild_graph()


    def delete_course(self, code: str) -> None:
        """
        Delete a course; ON DELETE CASCADE also removes matching submissions.
        """
        if not self._repo.course_exists(code):
            raise CourseNotFoundError(f"Course '{code}' not found")

        # Extra safety: delete submissions explicitly in case FK cascade isn't set
        db = getattr(self._repo, "_db", None) or getattr(self._repo, "db", None)
        if db is not None:
            try:
                with db.transaction() as conn:
                    conn.execute(
                        "DELETE FROM course_submissions WHERE course_code = ?",
                        (code,),
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"[delete_course sync] {code}: {e}"
                )

        self._repo.delete_course(code)
        self._rebuild_graph()
    # ── Prerequisite Management ────────────────────────────────────────────────

    def add_prerequisite(
        self, course_code: str, prereq_code: str
    ) -> None:
        """
        Add a prerequisite relationship with cycle detection.

        Process:
            1. Verify both courses exist
            2. Check adding would NOT create a cycle (CycleDetector)
            3. Save to database
            4. Update graph

        Args:
            course_code : Course that will require the prerequisite.
            prereq_code : Course that must be completed first.

        Raises:
            CourseNotFoundError     : If either course not found.
            CircularDependencyError : If would create a cycle.
        """
        if not self._repo.course_exists(course_code):
            raise CourseNotFoundError(
                f"Course '{course_code}' not found"
            )
        if not self._repo.course_exists(prereq_code):
            raise CourseNotFoundError(
                f"Prerequisite course '{prereq_code}' not found"
            )

        # Check for cycle BEFORE modifying anything
        detector = CycleDetector(self._graph)
        if detector.would_create_cycle(prereq_code, course_code):
            raise CircularDependencyError(
                f"Adding '{prereq_code}' as prerequisite of "
                f"'{course_code}' would create a circular dependency."
            )

        self._repo.add_prerequisite(course_code, prereq_code)
        self._graph.add_edge(prereq_code, course_code)

    def remove_prerequisite(
        self, course_code: str, prereq_code: str
    ) -> None:
        """
        Remove a prerequisite relationship.

        Safe to call even if the relationship does not exist.

        Args:
            course_code : Course to modify.
            prereq_code : Prerequisite to remove.
        """
        self._repo.remove_prerequisite(course_code, prereq_code)
        self._graph.remove_edge(prereq_code, course_code)

    def get_prerequisites(self, course_code: str) -> Set[str]:
        """
        Return direct prerequisites for a course.

        Args:
            course_code: Course to look up.

        Returns:
            set[str]: Direct prerequisite codes.
        """
        return self._repo.get_prerequisites(course_code)

    def get_study_order(self) -> List[str]:
        """
        Return all courses in a valid topological study order.

        Uses Kahn's algorithm — prerequisites always appear before
        the courses that require them.

        Returns:
            list[str]: Course codes in valid study order.

        Raises:
            ValueError: If a cycle exists in the graph.
        """
        sorter = TopologicalSorter(self._graph)
        return sorter.sort()

    def get_course_levels(self):
        """
        Group courses into parallel study levels.

        Returns:
            list[list[str]]: Level 0 = no prerequisites, etc.
        """
        sorter = TopologicalSorter(self._graph)
        return sorter.get_levels()

    def course_exists(self, code: str) -> bool:
        """Check whether a course code exists."""
        return self._repo.course_exists(code)

    def count_courses(self) -> int:
        """Return total number of courses."""
        return self._repo.count()


# ── Factory Function ───────────────────────────────────────────────────────────

def create_course_service(database) -> CourseService:
    """
    Production factory — creates CourseService with real SQLite repos.

    Args:
        database: Database instance (from repository.database.Database)

    Returns:
        CourseService: Ready-to-use service.

    Usage:
        db      = Database()
        db.initialize()
        service = create_course_service(db)
    """
    from repository.course_repo import SQLiteCourseRepository
    repo  = SQLiteCourseRepository(database)
    graph = CourseGraph()
    return CourseService(repo, graph)