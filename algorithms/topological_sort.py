"""
topological_sort.py
-------------------
Produces a valid study order for courses using Kahn's Algorithm
(BFS-based topological sort).

Why Kahn's algorithm?
    - Iterative (no recursion limit issues for large graphs)
    - Naturally detects cycles (remaining nodes after sort = cycle members)
    - Produces a deterministic order (alphabetical among equal-priority nodes)
    - O(V + E) time complexity

What topological order means for LMPTS:
    Given:  CS101 → CS201 → CS301

    Valid order:  CS101, CS201, CS301
    Invalid:      CS201, CS101, CS301  (CS201 before CS101)

Used by:
    PathFinder.get_study_order()
    PathFinder.find_all_prerequisites()
    RecommendationEngine (course ordering)
    Service Layer (curriculum planning)
"""

from collections import deque
from typing import List, Dict, Set, Optional


class TopologicalSorter:
    """
    Produces a valid topological ordering of courses.

    Courses with no prerequisites appear first.
    Courses appear after ALL their prerequisites.

    Usage:
        sorter = TopologicalSorter(graph)
        order  = sorter.sort()
        # → ["CS101", "CS201", "CS301", "CS401"]

        # With a cycle:
        order = sorter.sort()
        # → raises ValueError with cycle information
    """

    def __init__(self, graph):
        """
        Initialize with a CourseGraph object.

        Args:
            graph: CourseGraph instance.
        """
        self._course_graph  = graph
        self.graph: Dict[str, Set[str]]         = graph.get_graph()
        self.reverse_graph: Dict[str, Set[str]] = graph.get_reverse_graph()

    def sort(self) -> List[str]:
        """
        Perform topological sort using Kahn's Algorithm.

        Algorithm:
            1. Compute in-degree for every node
               (in-degree = number of prerequisites)
            2. Add all nodes with in-degree 0 to a priority queue
               (alphabetical order for determinism)
            3. Repeatedly:
               a. Take the smallest node from the queue
               b. Add it to the result
               c. Reduce in-degree of its dependents
               d. Add any dependent that reaches in-degree 0 to queue
            4. If result contains all nodes → success
               If result is shorter → cycle exists

        Returns:
            list[str]: All courses in valid study order.

        Raises:
            ValueError: If the graph contains a cycle.

        Example:
            graph:
                CS101 → CS201 → CS301
                CS102 → CS201

            sort() → ["CS101", "CS102", "CS201", "CS301"]
            (CS101 and CS102 both have in-degree 0, alphabetical)
        """
        # Step 1: Calculate in-degree for every node
        in_degree: Dict[str, int] = {
            course: 0 for course in self.graph
        }

        for course in self.graph:
            for dependent in self.graph[course]:
                if dependent in in_degree:
                    in_degree[dependent] += 1
                else:
                    in_degree[dependent] = 1

        # Ensure all nodes appear in in_degree
        for course in self.graph:
            if course not in in_degree:
                in_degree[course] = 0

        # Step 2: Add all zero-in-degree nodes to priority queue
        # Using sorted list as priority queue for alphabetical order
        queue = deque(
            sorted(
                course for course, degree in in_degree.items()
                if degree == 0
            )
        )

        result: List[str] = []

        # Step 3: Process nodes
        while queue:
            # Take from the front (already sorted)
            course = queue.popleft()
            result.append(course)

            # Reduce in-degree for all dependents
            new_zero: List[str] = []
            for dependent in self.graph.get(course, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    new_zero.append(dependent)

            # Insert new zero-degree nodes in sorted order
            for node in sorted(new_zero):
                queue.append(node)

        # Step 4: Check for cycles
        if len(result) != len(in_degree):
            # Find which nodes were not processed (cycle members)
            processed = set(result)
            cycle_members = [
                c for c in in_degree if c not in processed
            ]
            raise ValueError(
                f"Graph contains a cycle. "
                f"Affected courses: {sorted(cycle_members)}"
            )

        return result

    def sort_subset(self, courses: Set[str]) -> List[str]:
        """
        Sort only a subset of courses, preserving prerequisite order.

        Useful for ordering a learner's course plan without
        processing the entire graph.

        Args:
            courses: Set of course codes to sort.

        Returns:
            list[str]: Subset in topological order.

        Example:
            graph: CS101 → CS201 → CS301 → CS401

            sort_subset({"CS301", "CS101", "CS401"})
            → ["CS101", "CS301", "CS401"]
            (CS201 excluded, but relative order preserved)
        """
        # Get full order and filter
        full_order = self.sort()
        return [c for c in full_order if c in courses]

    def get_levels(self) -> List[List[str]]:
        """
        Group courses into levels where courses in the same level
        can be studied in parallel (all prerequisites in previous levels).

        Returns:
            list[list[str]]: Each inner list is one level.
                             Level 0 = no prerequisites.

        Example:
            CS101 → CS201 → CS301
            CS102 → CS201

            get_levels()
            → [
                ["CS101", "CS102"],   # Level 0: no prerequisites
                ["CS201"],             # Level 1: needs CS101, CS102
                ["CS301"],             # Level 2: needs CS201
              ]

        Used by:
            GUI (visual curriculum map)
            Analytics (parallel learning analysis)
        """
        # Calculate in-degrees
        in_degree: Dict[str, int] = {
            course: len(self.reverse_graph.get(course, set()))
            for course in self.graph
        }

        # Initialize with level 0 nodes
        current_level = sorted(
            course for course, deg in in_degree.items() if deg == 0
        )
        levels: List[List[str]] = []
        remaining_in_degree = dict(in_degree)

        while current_level:
            levels.append(current_level)
            next_level: List[str] = []

            for course in current_level:
                for dependent in self.graph.get(course, set()):
                    remaining_in_degree[dependent] -= 1
                    if remaining_in_degree[dependent] == 0:
                        next_level.append(dependent)

            current_level = sorted(next_level)

        return levels

    def get_course_level(self, course_code: str) -> int:
        """
        Return the level (depth) of a specific course.

        Level 0 = no prerequisites.
        Level n = must complete n levels of prerequisites first.

        Args:
            course_code: Course to look up.

        Returns:
            int: Level number (0-indexed).
            -1 : If course not in graph.

        Example:
            CS101 (level 0) → CS201 (level 1) → CS301 (level 2)

            get_course_level("CS301") → 2
        """
        levels = self.get_levels()
        for level_index, level_courses in enumerate(levels):
            if course_code in level_courses:
                return level_index
        return -1