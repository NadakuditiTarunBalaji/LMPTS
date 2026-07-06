"""
graph.py
--------
Core directed graph data structure for the LMPTS course prerequisite system.

Architecture:
    CourseGraph is a PURE data structure.
    It has NO database dependency.
    The service layer builds the graph from repository data.

Edge direction:
    prerequisite → dependent
    CS101 → CS201 means "CS101 must be completed before CS201"

Two internal structures maintained simultaneously:
    self.graph         : prerequisite → set of dependents
    self.reverse_graph : dependent   → set of prerequisites

Example:
    CS101 → CS201 → CS301

    graph:
        CS101 → {CS201}
        CS201 → {CS301}
        CS301 → {}

    reverse_graph:
        CS101 → {}
        CS201 → {CS101}
        CS301 → {CS201}

Used by:
    CycleDetector         (reads graph)
    PathFinder            (reads graph)
    TopologicalSorter     (reads graph)
    RecommendationEngine  (reads graph + reverse_graph)
    PrerequisiteValidator (reads reverse_graph)
    Service Layer         (builds graph from repository)
"""

from collections import defaultdict, deque
from typing import List, Set, Dict, Optional


class CourseGraph:
    """
    Directed graph representing course prerequisite relationships.

    Attributes:
        graph         : Dict[str, Set[str]] — forward edges
                        prerequisite → dependents
        reverse_graph : Dict[str, Set[str]] — reverse edges
                        dependent → prerequisites
    """

    def __init__(self):
        # Forward: prerequisite → set of courses that require it
        self.graph: Dict[str, Set[str]] = defaultdict(set)

        # Reverse: course → set of its direct prerequisites
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    # ── Course Management ──────────────────────────────────────────────────────

    def add_course(self, course_code: str) -> None:
        """
        Add a course node to the graph with no edges.

        Idempotent — safe to call if course already exists.

        Args:
            course_code: Unique course identifier e.g. "CS101"

        Raises:
            ValueError: If course_code is empty.

        Example:
            graph.add_course("CS101")
        """
        if not course_code or not course_code.strip():
            raise ValueError("Course code cannot be empty.")

        # Ensure the course exists in both graphs
        # defaultdict creates it automatically but we touch it explicitly
        # so get_courses() returns it even with no edges
        if course_code not in self.graph:
            self.graph[course_code] = set()

        if course_code not in self.reverse_graph:
            self.reverse_graph[course_code] = set()

    def remove_course(self, course_code: str) -> None:
        """
        Remove a course and all its edges from both graphs.

        Args:
            course_code: Course to remove.

        Example:
            graph.remove_course("CS101")
            # Also removes CS101 from all prerequisite lists
        """
        # Remove from forward graph
        if course_code in self.graph:
            # For each course that CS101 points to,
            # remove CS101 from their reverse_graph entry
            for dependent in self.graph[course_code]:
                self.reverse_graph[dependent].discard(course_code)
            del self.graph[course_code]

        # Remove from reverse graph
        if course_code in self.reverse_graph:
            # For each prerequisite of CS101,
            # remove CS101 from their forward graph entry
            for prereq in self.reverse_graph[course_code]:
                self.graph[prereq].discard(course_code)
            del self.reverse_graph[course_code]

    def has_course(self, course_code: str) -> bool:
        """
        Check whether a course exists in the graph.

        Args:
            course_code: Course to check.

        Returns:
            bool: True if the course exists.
        """
        return course_code in self.graph

    def get_courses(self) -> List[str]:
        """
        Return all course codes in the graph.

        Returns:
            list[str]: Sorted list of all course codes.
        """
        return sorted(self.graph.keys())

    def number_of_courses(self) -> int:
        """Return total number of courses in the graph."""
        return len(self.graph)

    def number_of_relationships(self) -> int:
        """Return total number of prerequisite edges."""
        return sum(len(neighbors) for neighbors in self.graph.values())

    def clear_graph(self) -> None:
        """Remove all courses and edges from both graphs."""
        self.graph.clear()
        self.reverse_graph.clear()

    # ── Edge Management ────────────────────────────────────────────────────────

    def add_edge(self, prerequisite: str, dependent: str) -> None:
        """
        Add a prerequisite relationship.

        Direction: prerequisite → dependent
        Meaning:   prerequisite must be completed before dependent

        Both graphs are updated atomically:
            graph[prerequisite].add(dependent)
            reverse_graph[dependent].add(prerequisite)

        Args:
            prerequisite: Course that must be completed first.
            dependent:    Course that requires the prerequisite.

        Raises:
            ValueError: If either code is empty or they are equal.

        Example:
            graph.add_edge("CS101", "CS201")
            # CS101 must be done before CS201
        """
        if not prerequisite or not prerequisite.strip():
            raise ValueError("Prerequisite course code cannot be empty.")

        if not dependent or not dependent.strip():
            raise ValueError("Dependent course code cannot be empty.")

        if prerequisite == dependent:
            raise ValueError(
                f"A course cannot be its own prerequisite: '{prerequisite}'"
            )

        # Ensure both nodes exist
        self.add_course(prerequisite)
        self.add_course(dependent)

        # Update both directions
        self.graph[prerequisite].add(dependent)
        self.reverse_graph[dependent].add(prerequisite)

    def remove_edge(self, prerequisite: str, dependent: str) -> None:
        """
        Remove a prerequisite relationship.

        Safe to call even if the edge does not exist.

        Args:
            prerequisite: The prerequisite course.
            dependent:    The course that required it.

        Example:
            graph.remove_edge("CS101", "CS201")
        """
        if prerequisite in self.graph:
            self.graph[prerequisite].discard(dependent)

        if dependent in self.reverse_graph:
            self.reverse_graph[dependent].discard(prerequisite)

    def has_edge(self, prerequisite: str, dependent: str) -> bool:
        """
        Check whether a prerequisite relationship exists.

        Args:
            prerequisite: The prerequisite course.
            dependent:    The dependent course.

        Returns:
            bool: True if the edge exists.
        """
        return (
            prerequisite in self.graph
            and dependent in self.graph[prerequisite]
        )

    # ── Neighbor Queries ───────────────────────────────────────────────────────

    def get_neighbors(self, course_code: str) -> Set[str]:
        """
        Return courses that DEPEND ON this course.
        (Forward direction — courses this unlocks)

        Args:
            course_code: The prerequisite course to look up.

        Returns:
            set[str]: Courses that require this course.

        Example:
            graph.add_edge("CS101", "CS201")
            graph.get_neighbors("CS101")  → {"CS201"}
        """
        return set(self.graph.get(course_code, set()))

    def get_prerequisites(self, course_code: str) -> Set[str]:
        """
        Return DIRECT prerequisites of a course.
        (Reverse direction — what must be done first)

        Args:
            course_code: The course to look up.

        Returns:
            set[str]: Direct prerequisite course codes.

        Example:
            graph.add_edge("CS101", "CS201")
            graph.get_prerequisites("CS201")  → {"CS101"}
        """
        return set(self.reverse_graph.get(course_code, set()))

    def get_all_prerequisites(self, course_code: str) -> Set[str]:
        """
        Return ALL prerequisites (direct + transitive) using BFS
        on the reverse graph.

        This answers: "What is the complete set of courses I must
        finish before I can take this course?"

        Args:
            course_code: Target course.

        Returns:
            set[str]: All prerequisite course codes (not including target).

        Example:
            CS101 → CS201 → CS301

            graph.get_all_prerequisites("CS301")
            → {"CS101", "CS201"}
        """
        if course_code not in self.reverse_graph:
            return set()

        all_prereqs: Set[str] = set()
        queue = deque(self.reverse_graph[course_code])

        while queue:
            current = queue.popleft()
            if current not in all_prereqs:
                all_prereqs.add(current)
                # Add this course's prerequisites to explore
                for prereq in self.reverse_graph.get(current, set()):
                    if prereq not in all_prereqs:
                        queue.append(prereq)

        return all_prereqs

    def get_all_dependents(self, course_code: str) -> Set[str]:
        """
        Return ALL courses that (directly or transitively) depend
        on this course using BFS on the forward graph.

        This answers: "What courses become available after completing
        this course?"

        Args:
            course_code: The prerequisite course.

        Returns:
            set[str]: All dependent course codes.

        Example:
            CS101 → CS201 → CS301

            graph.get_all_dependents("CS101")
            → {"CS201", "CS301"}
        """
        if course_code not in self.graph:
            return set()

        all_dependents: Set[str] = set()
        queue = deque(self.graph[course_code])

        while queue:
            current = queue.popleft()
            if current not in all_dependents:
                all_dependents.add(current)
                for dependent in self.graph.get(current, set()):
                    if dependent not in all_dependents:
                        queue.append(dependent)

        return all_dependents

    # ── Graph Building ─────────────────────────────────────────────────────────

    def build_from_courses(
        self,
        course_codes: List[str],
        prerequisites: Dict[str, Set[str]]
    ) -> None:
        """
        Build the graph from course data provided by the service layer.

        The service layer retrieves data from repositories and passes
        it here. This keeps algorithms DB-independent (Q5: Answer B).

        Args:
            course_codes : List of all course codes to add as nodes.
            prerequisites: Dict mapping course_code → set of its
                           direct prerequisite codes.

        Example:
            courses = ["CS101", "CS201", "CS301"]
            prereqs = {
                "CS201": {"CS101"},
                "CS301": {"CS201"},
            }
            graph.build_from_courses(courses, prereqs)

            # Result:
            # CS101 → CS201 → CS301
        """
        self.clear_graph()

        # Add all course nodes first
        for code in course_codes:
            self.add_course(code)

        # Add prerequisite edges
        # prerequisites[CS201] = {CS101}
        # means CS101 → CS201
        for course_code, prereq_set in prerequisites.items():
            for prereq_code in prereq_set:
                if prereq_code in self.graph:
                    self.add_edge(prereq_code, course_code)

    # ── Internal Access ────────────────────────────────────────────────────────

    def get_graph(self) -> Dict[str, Set[str]]:
        """
        Return the forward graph dictionary.

        Used by CycleDetector, PathFinder, TopologicalSorter.

        Returns:
            Dict[str, Set[str]]: prerequisite → set of dependents
        """
        return self.graph

    def get_reverse_graph(self) -> Dict[str, Set[str]]:
        """
        Return the reverse graph dictionary.

        Used by PrerequisiteValidator, RecommendationEngine.

        Returns:
            Dict[str, Set[str]]: course → set of its prerequisites
        """
        return self.reverse_graph

    # ── Display ────────────────────────────────────────────────────────────────

    def display(self) -> None:
        """Print a human-readable representation of the graph."""
        print("\n========== COURSE GRAPH ==========")

        if not self.graph:
            print("Graph is Empty")
            print("==================================")
            return

        for course in sorted(self.graph.keys()):
            neighbors = sorted(self.graph[course])
            prereqs   = sorted(self.reverse_graph.get(course, set()))
            print(f"  {course}")
            print(f"    requires : {prereqs}")
            print(f"    unlocks  : {neighbors}")

        print(f"\n  Courses      : {self.number_of_courses()}")
        print(f"  Relationships: {self.number_of_relationships()}")
        print("==================================\n")

    def __repr__(self) -> str:
        return (
            f"CourseGraph("
            f"courses={self.number_of_courses()}, "
            f"edges={self.number_of_relationships()})"
        )