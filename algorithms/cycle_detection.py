"""
cycle_detection.py

Detects circular dependencies in the course graph
using Depth First Search (DFS).
"""


class CycleDetector:
    """
    Detects cycles in a directed graph.
    """

    def __init__(self, graph):
        """
        graph -> CourseGraph object
        """
        self.graph = graph.get_graph()

    def detect_cycle(self):
        """
        Returns True if a cycle exists.
        Otherwise returns False.
        """

        visited = set()
        recursion_stack = set()

        for course in self.graph:
            if course not in visited:
                if self._dfs(course, visited, recursion_stack):
                    return True

        return False

    def _dfs(self, course, visited, recursion_stack):
        """
        Recursive DFS function.
        """

        visited.add(course)
        recursion_stack.add(course)

        for neighbor in self.graph[course]:

            if neighbor not in visited:

                if self._dfs(neighbor, visited, recursion_stack):
                    return True

            elif neighbor in recursion_stack:
                return True

        recursion_stack.remove(course)

        return False