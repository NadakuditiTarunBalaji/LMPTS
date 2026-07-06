from collections import defaultdict

class CourseGraph:

    def __init__(self):
        self.graph = defaultdict(set)

     def add_course(self, course_code):

        if not course_code:
            raise ValueError("Course code cannot be empty.")
        if course_code not in self.graph:
            self.graph[course_code] = set()
    def add_edge(self, prerequisite, dependent):

        if not prerequisite or not dependent:
            raise ValueError("Course codes cannot be empty.")
        if prerequisite == dependent:
            raise ValueError("Course cannot be prerequisite of itself.")
        self.add_course(prerequisite)
        self.add_course(dependent)

        self.graph[prerequisite].add(dependent)

        def remove_edge(self, prerequisite, dependent):

            if prerequisite in self.graph:
            self.graph[prerequisite].discard(dependent)
        
        def remove_course(self, course_code):

            if course_code in self.graph:
            del self.graph[course_code]

            for neighbours in self.graph.values():
            neighbours.discard(course_code)

        def has_course(self, course_code):
            return course_code in self.graph
        
        def has_edge(self, prerequisite, dependent):

            if course_code in self.graph:
            del self.graph[course_code]

            for neighbours in self.graph.values():
            neighbours.discard(course_code)
        def has_course(self, course_code):

             return course_code in self.graph
        def has_edge(self, prerequisite, dependent):

            return (
            prerequisite in self.graph
            and dependent in self.graph[prerequisite]
        )

         def get_neighbors(self, course_code):

            return self.graph.get(course_code, set())
        
        def get_courses(self):

             return list(self.graph.keys())
         def number_of_courses(self):

             return len(self.graph)
        def number_of_relationships(self):
