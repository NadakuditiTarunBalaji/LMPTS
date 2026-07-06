"""
graph.py

Course Graph implementation for LMPTS.
"""

from collections import defaultdict


class CourseGraph:
    """
    Directed Graph implementation.
    """

    def __init__(self):
        self.graph = defaultdict(set)

    def add_course(self, course_code):
        """Add a course to the graph."""
        if not course_code:
            raise ValueError("Course code cannot be empty.")

        if course_code not in self.graph:
            self.graph[course_code] = set()

    def add_edge(self, prerequisite, dependent):
        """
        Add prerequisite relationship.

        prerequisite ---> dependent
        """

        if not prerequisite or not dependent:
            raise ValueError("Course codes cannot be empty.")                                                                                                                                                                                                                                       

        if prerequisite == dependent:
            raise ValueError("Course cannot be prerequisite of itself.")

        self.add_course(prerequisite)
        self.add_course(dependent)

        self.graph[prerequisite].add(dependent)

    def remove_edge(self, prerequisite, dependent):
        """Remove prerequisite relationship."""

        if prerequisite in self.graph:
            self.graph[prerequisite].discard(dependent)

    def remove_course(self, course_code):
        """Remove course and all relationships."""

        if course_code in self.graph:
            del self.graph[course_code]

        for neighbours in self.graph.values():
            neighbours.discard(course_code)

    def has_course(self, course_code):
        """Check whether course exists."""

        return course_code in self.graph

    def has_edge(self, prerequisite, dependent):
        """Check whether edge exists."""

        return (
            prerequisite in self.graph
            and dependent in self.graph[prerequisite]
        )

    def get_neighbors(self, course_code):
        """Return dependent courses."""

        return self.graph.get(course_code, set())

    def get_courses(self):
        """Return all courses."""

        return list(self.graph.keys())

    def number_of_courses(self):
        """Return total courses."""

        return len(self.graph)

    def number_of_relationships(self):
        """Return total prerequisite relationships."""

        return sum(len(neighbours) for neighbours in self.graph.values())

    def clear_graph(self):
        """Remove all courses."""

        self.graph.clear()

    def get_graph(self):
        """Return graph."""

        return self.graph

    def display(self):
        """Display graph."""

        print("\n========== COURSE GRAPH ==========")

        if not self.graph:
            print("Graph is Empty")
            return

        for course, neighbours in self.graph.items():
            print(f"{course} --> {sorted(neighbours)}")

        print("==================================")