"""
cycle_detection.py
------------------
Detects circular dependencies in the course prerequisite graph
using Depth First Search (DFS).

Why cycle detection matters:
    CS101 → CS201 → CS301 → CS101  ← INVALID (circular)

    If this were allowed:
        - A learner could never satisfy prerequisites
        - Topological sort would be impossible
        - Enrollment would deadlock

DFS approach:
    Track two sets:
        visited       : courses already fully processed
        recursion_stack: courses in the current DFS path

    If we reach a course already in recursion_stack,
    we have found a back edge → cycle exists.

Used by:
    PrerequisiteValidator.can_add_prerequisite()
    Service layer before saving new prerequisite relationships
"""

from typing import Dict, Set, List, Optional, Tuple


class CycleDetector:
    """
    Detects cycles in a directed course prerequisite graph.

    Usage:
        detector = CycleDetector(graph)

        # Check if any cycle exists
        if detector.detect_cycle():
            print("Cycle found!")

        # Check before adding a specific edge
        if detector.would_create_cycle("CS301", "CS101"):
            raise CircularDependencyError(...)

        # Find which courses form the cycle
        path = detector.find_cycle_path()
    """

    def __init__(self, graph):
        """
        Initialize with a CourseGraph object.

        Args:
            graph: CourseGraph instance (not the raw dict)
        """
        self._course_graph = graph
        self.graph: Dict[str, Set[str]] = graph.get_graph()

    def detect_cycle(self) -> bool:
        """
        Check whether any cycle exists in the graph.

        Algorithm: DFS with recursion stack tracking.
            For each unvisited node, run DFS.
            If DFS finds a back edge (node in recursion stack),
            a cycle exists.

        Returns:
            bool: True if a cycle exists, False otherwise.

        Time complexity:  O(V + E)
        Space complexity: O(V)

        Example:
            CS101 → CS201 → CS301            → False (no cycle)
            CS101 → CS201 → CS301 → CS101    → True  (cycle!)
        """
        visited: Set[str]         = set()
        recursion_stack: Set[str] = set()

        for course in self.graph:
            if course not in visited:
                if self._dfs(course, visited, recursion_stack):
                    return True

        return False

    def _dfs(
        self,
        course: str,
        visited: Set[str],
        recursion_stack: Set[str]
    ) -> bool:
        """
        Recursive DFS helper.

        Args:
            course         : Current node being visited.
            visited        : Set of fully processed nodes.
            recursion_stack: Set of nodes in current DFS path.

        Returns:
            bool: True if a cycle is found.
        """
        visited.add(course)
        recursion_stack.add(course)

        for neighbor in self.graph.get(course, set()):
            if neighbor not in visited:
                if self._dfs(neighbor, visited, recursion_stack):
                    return True
            elif neighbor in recursion_stack:
                # Back edge found → cycle
                return True

        recursion_stack.remove(course)
        return False

    def find_cycle_path(self) -> Optional[List[str]]:
        """
        Find and return one cycle path if a cycle exists.

        Returns the list of courses that form the cycle,
        ending with the course that creates the back edge.

        Returns:
            list[str]: Courses forming the cycle.
            None:      If no cycle exists.

        Example:
            CS101 → CS201 → CS301 → CS101

            find_cycle_path()
            → ["CS101", "CS201", "CS301", "CS101"]
        """
        visited: Set[str]         = set()
        recursion_stack: Set[str] = set()
        path: List[str]           = []

        for course in self.graph:
            if course not in visited:
                result = self._dfs_with_path(
                    course, visited, recursion_stack, path
                )
                if result is not None:
                    return result

        return None

    def _dfs_with_path(
        self,
        course: str,
        visited: Set[str],
        recursion_stack: Set[str],
        path: List[str]
    ) -> Optional[List[str]]:
        """
        DFS helper that tracks the current path.

        Args:
            course         : Current node.
            visited        : Fully processed nodes.
            recursion_stack: Nodes in current DFS path.
            path           : Current DFS path as ordered list.

        Returns:
            list[str]: The cycle path if found.
            None:      If no cycle found from this node.
        """
        visited.add(course)
        recursion_stack.add(course)
        path.append(course)

        for neighbor in self.graph.get(course, set()):
            if neighbor not in visited:
                result = self._dfs_with_path(
                    neighbor, visited, recursion_stack, path
                )
                if result is not None:
                    return result

            elif neighbor in recursion_stack:
                # Found the cycle — extract just the cycle portion
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                return cycle

        path.pop()
        recursion_stack.remove(course)
        return None

    def would_create_cycle(
        self,
        prerequisite: str,
        dependent: str
    ) -> bool:
        """
        Check whether adding an edge would create a cycle,
        WITHOUT actually modifying the graph.

        This is called BEFORE saving a new prerequisite relationship
        to prevent invalid graph states.

        Algorithm:
            If we add prerequisite → dependent,
            a cycle would exist if and only if
            there is already a path from dependent → prerequisite.

            (Because the new edge closes the loop.)

        Args:
            prerequisite: Course that would become the prerequisite.
            dependent:    Course that would require it.

        Returns:
            bool: True if adding this edge would create a cycle.

        Example:
            Existing: CS101 → CS201 → CS301

            would_create_cycle("CS301", "CS101")
            → True  (CS301 → CS101 closes the loop)

            would_create_cycle("CS101", "CS301")
            → False (CS101 → CS301 is just a shortcut)
        """
        # Self-loop is always a cycle
        if prerequisite == dependent:
            return True

        # If dependent can already reach prerequisite,
        # adding prerequisite → dependent creates a cycle
        return self._can_reach(dependent, prerequisite)

    def _can_reach(self, start: str, target: str) -> bool:
        """
        BFS to check if target is reachable from start.

        Args:
            start : Starting course code.
            target: Target course code to reach.

        Returns:
            bool: True if target is reachable from start.
        """
        if start not in self.graph:
            return False

        from collections import deque
        visited: Set[str] = set()
        queue = deque([start])

        while queue:
            current = queue.popleft()
            if current == target:
                return True
            if current not in visited:
                visited.add(current)
                for neighbor in self.graph.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)

        return False

    def get_all_cycles(self) -> List[List[str]]:
        """
        Find ALL distinct cycles in the graph.

        Used for diagnostic reporting when multiple cycles exist.

        Returns:
            list[list[str]]: Each inner list is one cycle path.
                             Empty list if no cycles exist.
        """
        cycles: List[List[str]] = []
        visited: Set[str]       = set()

        for course in self.graph:
            if course not in visited:
                recursion_stack: Set[str] = set()
                path: List[str]           = []
                self._find_all_cycles_dfs(
                    course, visited, recursion_stack, path, cycles
                )

        return cycles

    def _find_all_cycles_dfs(
        self,
        course: str,
        visited: Set[str],
        recursion_stack: Set[str],
        path: List[str],
        cycles: List[List[str]]
    ) -> None:
        """DFS helper for finding all cycles."""
        visited.add(course)
        recursion_stack.add(course)
        path.append(course)

        for neighbor in self.graph.get(course, set()):
            if neighbor not in visited:
                self._find_all_cycles_dfs(
                    neighbor, visited, recursion_stack, path, cycles
                )
            elif neighbor in recursion_stack:
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                if cycle not in cycles:
                    cycles.append(cycle)

        path.pop()
        recursion_stack.remove(course)