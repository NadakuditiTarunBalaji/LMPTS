"""
path_finder.py

Finds the shortest learning path between two courses
using Breadth First Search (BFS).
"""

from collections import deque


class PathFinder:
    """
    Finds shortest learning path in the course graph.
    """

    def __init__(self, graph):
        """
        graph -> CourseGraph object
        """
        self.graph = graph.get_graph()

    def find_learning_path(self, start_course, end_course):
        """
        Returns the shortest path between two courses.

        Example:
        PY101 -> PY201 -> PY301 -> ML101

        Output:
        ['PY101', 'PY201', 'PY301', 'ML101']
        """

        if start_course not in self.graph:
            return None

        if end_course not in self.graph:
            return None

        queue = deque()
        visited = set()

        queue.append((start_course, [start_course]))
        visited.add(start_course)

        while queue:

            current_course, path = queue.popleft()

            if current_course == end_course:
                return path

            for neighbor in self.graph[current_course]:

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(
                        (
                            neighbor,
                            path + [neighbor]
                        )
                    )

        return None