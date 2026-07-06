"""
path_finder.py
--------------
Finds learning paths between courses using BFS.

Provides:
    find_learning_path()     : Shortest path between two courses
    find_all_prerequisites() : Complete prerequisite chain
    get_recommended_path()   : Filtered path excluding completed courses
    get_study_order()        : Topological order for a set of courses

Used by:
    RecommendationEngine
    Service Layer (learning path generation)
    GUI (learning path display)
"""

from collections import deque
from typing import List, Set, Optional, Dict

from algorithms.topological_sort import TopologicalSorter


class PathFinder:
    """
    Finds optimal learning paths through the course prerequisite graph.

    Usage:
        finder = PathFinder(graph)

        path = finder.find_learning_path("CS101", "CS401")
        # → ["CS101", "CS201", "CS301", "CS401"]

        all_prereqs = finder.find_all_prerequisites("CS301")
        # → ["CS101", "CS201"]  (in completion order)

        remaining = finder.get_recommended_path(
            target="CS301",
            completed={"CS101"}
        )
        # → ["CS201", "CS301"]
    """

    def __init__(self, graph):
        """
        Initialize with a CourseGraph object.

        Args:
            graph: CourseGraph instance.
        """
        self._course_graph = graph
        self.graph: Dict[str, Set[str]]         = graph.get_graph()
        self.reverse_graph: Dict[str, Set[str]] = graph.get_reverse_graph()

    def find_learning_path(
        self,
        start_course: str,
        end_course: str
    ) -> Optional[List[str]]:
        """
        Find the shortest path between two courses using BFS.

        The path follows prerequisite edges forward:
            start_course → ... → end_course

        Args:
            start_course: Course to start from.
            end_course:   Course to reach.

        Returns:
            list[str]: Ordered course codes from start to end.
            None:      If no path exists.

        Example:
            CS101 → CS201 → CS301 → CS401

            find_learning_path("CS101", "CS401")
            → ["CS101", "CS201", "CS301", "CS401"]

            find_learning_path("CS301", "CS101")
            → None  (no forward path)
        """
        if start_course not in self.graph:
            return None

        if end_course not in self.graph:
            return None

        if start_course == end_course:
            return [start_course]

        visited: Set[str] = set()
        queue = deque()
        queue.append((start_course, [start_course]))
        visited.add(start_course)

        while queue:
            current_course, path = queue.popleft()

            if current_course == end_course:
                return path

            for neighbor in self.graph.get(current_course, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def find_all_prerequisites(
        self,
        course_code: str
    ) -> List[str]:
        """
        Return all prerequisites in a valid study order.

        Uses BFS on the reverse graph to find all prerequisites,
        then orders them topologically so each course appears
        after its own prerequisites.

        Args:
            course_code: Target course.

        Returns:
            list[str]: Prerequisites in valid completion order,
                       not including the target course itself.

        Example:
            CS101 → CS201 → CS301

            find_all_prerequisites("CS301")
            → ["CS101", "CS201"]
        """
        if course_code not in self.reverse_graph:
            return []

        # Collect all prerequisite nodes
        all_prereqs: Set[str] = self._course_graph.get_all_prerequisites(
            course_code
        )

        if not all_prereqs:
            return []

        # Build a subgraph of just the prerequisites
        # and sort topologically
        subgraph_codes = list(all_prereqs)
        sorter = TopologicalSorter(self._course_graph)
        full_order = sorter.sort()

        # Filter to only prerequisites, preserving topological order
        return [c for c in full_order if c in all_prereqs]

    def get_recommended_path(
        self,
        target: str,
        completed: Set[str],
        transfer_credits: Optional[Set[str]] = None,
        exemptions: Optional[Set[str]] = None
    ) -> List[str]:
        """
        Return the remaining courses needed to reach the target,
        excluding already completed, transferred, and exempted courses.

        Supports transfer credits and prior learning (Admin validation).

        Args:
            target         : Goal course code.
            completed      : Set of normally completed course codes.
            transfer_credits: Set of courses completed by transfer.
            exemptions     : Set of courses exempted by admin approval.

        Returns:
            list[str]: Remaining courses in valid study order.
                       Includes the target course itself.

        Example:
            CS101 → CS201 → CS301

            completed = {"CS101"}

            get_recommended_path("CS301", completed)
            → ["CS201", "CS301"]

        Transfer credit example:
            completed      = {}
            transfer_credits = {"CS101", "CS201"}

            get_recommended_path("CS301", completed, transfer_credits)
            → ["CS301"]
        """
        transfer_credits = transfer_credits or set()
        exemptions       = exemptions or set()

        # All credits that count as "done"
        satisfied: Set[str] = completed | transfer_credits | exemptions

        # Get all prerequisites in order
        prereq_chain = self.find_all_prerequisites(target)

        # Filter out already satisfied courses
        remaining = [c for c in prereq_chain if c not in satisfied]

        # Add target if not already satisfied
        if target not in satisfied:
            remaining.append(target)

        return remaining

    def get_study_order(
        self,
        courses: Optional[Set[str]] = None
    ) -> List[str]:
        """
        Return courses in a valid topological study order.

        If courses is provided, return only those courses in order.
        If courses is None, return ALL graph courses in order.

        Args:
            courses: Optional subset of courses to order.
                     If None, orders all courses in the graph.

        Returns:
            list[str]: Courses in valid study order (prerequisites first).

        Example:
            CS201 → CS301
            CS101 → CS201

            get_study_order()
            → ["CS101", "CS201", "CS301"]

            get_study_order({"CS201", "CS301"})
            → ["CS201", "CS301"]
        """
        sorter     = TopologicalSorter(self._course_graph)
        full_order = sorter.sort()

        if courses is None:
            return full_order

        # Filter and preserve topological order
        course_set = set(courses)
        return [c for c in full_order if c in course_set]

    def get_paths_from(self, start_course: str) -> Dict[str, List[str]]:
        """
        Find shortest paths from start_course to ALL reachable courses.

        Used by the recommendation engine to calculate distance
        from current position to all available courses.

        Args:
            start_course: Starting course code.

        Returns:
            dict: {course_code: path_list} for all reachable courses.

        Example:
            CS101 → CS201 → CS301
            CS101 → CS301  (direct shortcut)

            get_paths_from("CS101")
            → {
                "CS201": ["CS101", "CS201"],
                "CS301": ["CS101", "CS301"]   # shortest
              }
        """
        if start_course not in self.graph:
            return {}

        paths: Dict[str, List[str]] = {}
        visited: Set[str] = set()
        queue = deque()
        queue.append((start_course, [start_course]))
        visited.add(start_course)

        while queue:
            current, path = queue.popleft()

            for neighbor in self.graph.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = path + [neighbor]
                    paths[neighbor] = new_path
                    queue.append((neighbor, new_path))

        return paths