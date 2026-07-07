"""
test_graph.py
-------------
Tests for CourseGraph — the core data structure.
"""

import pytest
from algorithms.graph import CourseGraph


@pytest.fixture
def empty_graph():
    return CourseGraph()


@pytest.fixture
def linear_graph():
    """CS101 → CS201 → CS301 → CS401"""
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS201", "CS301")
    g.add_edge("CS301", "CS401")
    return g


@pytest.fixture
def branching_graph():
    """
    CS101 → CS201 → CS301
    CS102 → CS201
    CS101 → CS301 (direct)
    """
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS102", "CS201")
    g.add_edge("CS201", "CS301")
    g.add_edge("CS101", "CS301")
    return g


class TestCourseManagement:

    def test_add_course(self, empty_graph):
        empty_graph.add_course("CS101")
        assert empty_graph.has_course("CS101")

    def test_add_course_idempotent(self, empty_graph):
        empty_graph.add_course("CS101")
        empty_graph.add_course("CS101")
        assert empty_graph.number_of_courses() == 1

    def test_add_course_empty_raises(self, empty_graph):
        with pytest.raises(ValueError, match="cannot be empty"):
            empty_graph.add_course("")

    def test_add_course_whitespace_raises(self, empty_graph):
        with pytest.raises(ValueError):
            empty_graph.add_course("   ")

    def test_remove_course(self, linear_graph):
        linear_graph.remove_course("CS201")
        assert not linear_graph.has_course("CS201")

    def test_remove_course_cleans_edges(self, linear_graph):
        linear_graph.remove_course("CS201")
        # CS101 should no longer point to CS201
        assert "CS201" not in linear_graph.get_neighbors("CS101")
        # CS301 should no longer list CS201 as prerequisite
        assert "CS201" not in linear_graph.get_prerequisites("CS301")

    def test_has_course_true(self, linear_graph):
        assert linear_graph.has_course("CS101") is True

    def test_has_course_false(self, linear_graph):
        assert linear_graph.has_course("UNKNOWN") is False

    def test_get_courses_sorted(self, branching_graph):
        courses = branching_graph.get_courses()
        assert courses == sorted(courses)

    def test_number_of_courses(self, linear_graph):
        assert linear_graph.number_of_courses() == 4

    def test_number_of_relationships(self, linear_graph):
        assert linear_graph.number_of_relationships() == 3

    def test_clear_graph(self, linear_graph):
        linear_graph.clear_graph()
        assert linear_graph.number_of_courses() == 0
        assert linear_graph.number_of_relationships() == 0


class TestEdgeManagement:

    def test_add_edge(self, empty_graph):
        empty_graph.add_edge("CS101", "CS201")
        assert empty_graph.has_edge("CS101", "CS201")

    def test_add_edge_creates_both_nodes(self, empty_graph):
        empty_graph.add_edge("CS101", "CS201")
        assert empty_graph.has_course("CS101")
        assert empty_graph.has_course("CS201")

    def test_add_edge_self_loop_raises(self, empty_graph):
        with pytest.raises(ValueError):
            empty_graph.add_edge("CS101", "CS101")

    def test_add_edge_empty_prereq_raises(self, empty_graph):
        with pytest.raises(ValueError):
            empty_graph.add_edge("", "CS201")

    def test_add_edge_empty_dependent_raises(self, empty_graph):
        with pytest.raises(ValueError):
            empty_graph.add_edge("CS101", "")

    def test_remove_edge(self, linear_graph):
        linear_graph.remove_edge("CS101", "CS201")
        assert not linear_graph.has_edge("CS101", "CS201")

    def test_remove_edge_safe_if_not_exists(self, empty_graph):
        empty_graph.remove_edge("CS101", "CS201")  # no error

    def test_has_edge_true(self, linear_graph):
        assert linear_graph.has_edge("CS101", "CS201") is True

    def test_has_edge_false(self, linear_graph):
        assert linear_graph.has_edge("CS101", "CS401") is False


class TestNeighborQueries:

    def test_get_neighbors_forward(self, linear_graph):
        """CS101 → CS201: neighbors of CS101 = {CS201}"""
        neighbors = linear_graph.get_neighbors("CS101")
        assert "CS201" in neighbors

    def test_get_neighbors_empty_for_leaf(self, linear_graph):
        """CS401 has no dependents"""
        assert linear_graph.get_neighbors("CS401") == set()

    def test_get_prerequisites_reverse(self, linear_graph):
        """CS201 requires CS101"""
        prereqs = linear_graph.get_prerequisites("CS201")
        assert "CS101" in prereqs

    def test_get_prerequisites_empty_for_root(self, linear_graph):
        """CS101 has no prerequisites"""
        assert linear_graph.get_prerequisites("CS101") == set()

    def test_get_all_prerequisites_chain(self, linear_graph):
        """CS401 needs CS101, CS201, CS301"""
        all_prereqs = linear_graph.get_all_prerequisites("CS401")
        assert all_prereqs == {"CS101", "CS201", "CS301"}

    def test_get_all_prerequisites_empty_for_root(self, linear_graph):
        assert linear_graph.get_all_prerequisites("CS101") == set()

    def test_get_all_prerequisites_branching(self, branching_graph):
        """CS301 needs CS101, CS102, CS201"""
        all_prereqs = branching_graph.get_all_prerequisites("CS301")
        assert "CS101" in all_prereqs
        assert "CS102" in all_prereqs
        assert "CS201" in all_prereqs

    def test_get_all_dependents(self, linear_graph):
        """CS101 unlocks CS201, CS301, CS401"""
        all_deps = linear_graph.get_all_dependents("CS101")
        assert all_deps == {"CS201", "CS301", "CS401"}

    def test_get_all_dependents_empty_for_leaf(self, linear_graph):
        assert linear_graph.get_all_dependents("CS401") == set()

    def test_get_neighbors_returns_copy(self, linear_graph):
        """Mutating returned set must not affect graph."""
        neighbors = linear_graph.get_neighbors("CS101")
        neighbors.add("HACKED")
        assert "HACKED" not in linear_graph.get_neighbors("CS101")

    def test_get_prerequisites_returns_copy(self, linear_graph):
        prereqs = linear_graph.get_prerequisites("CS201")
        prereqs.add("HACKED")
        assert "HACKED" not in linear_graph.get_prerequisites("CS201")


class TestBuildFromCourses:

    def test_build_from_courses(self, empty_graph):
        courses = ["CS101", "CS201", "CS301"]
        prereqs = {
            "CS201": {"CS101"},
            "CS301": {"CS201"},
        }
        empty_graph.build_from_courses(courses, prereqs)

        assert empty_graph.has_edge("CS101", "CS201")
        assert empty_graph.has_edge("CS201", "CS301")
        assert empty_graph.number_of_courses() == 3

    def test_build_from_courses_clears_existing(self, linear_graph):
        linear_graph.build_from_courses(["A", "B"], {"B": {"A"}})
        assert not linear_graph.has_course("CS101")
        assert linear_graph.has_course("A")

    def test_build_from_courses_no_prereqs(self, empty_graph):
        empty_graph.build_from_courses(["CS101", "CS201"], {})
        assert empty_graph.has_course("CS101")
        assert empty_graph.has_course("CS201")
        assert empty_graph.number_of_relationships() == 0

    def test_both_graphs_updated_on_build(self, empty_graph):
        empty_graph.build_from_courses(
            ["CS101", "CS201"],
            {"CS201": {"CS101"}}
        )
        assert "CS201" in empty_graph.get_neighbors("CS101")
        assert "CS101" in empty_graph.get_prerequisites("CS201")

    def test_repr(self, linear_graph):
        r = repr(linear_graph)
        assert "CourseGraph" in r
        assert "4" in r