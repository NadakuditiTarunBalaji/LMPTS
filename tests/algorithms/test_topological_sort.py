"""
test_topological_sort.py
------------------------
Tests for TopologicalSorter — Kahn's algorithm.
"""

import pytest
from algorithms.graph import CourseGraph
from algorithms.topological_sort import TopologicalSorter


@pytest.fixture
def linear_graph():
    """CS101 → CS201 → CS301"""
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS201", "CS301")
    return g


@pytest.fixture
def branching_graph():
    """
    CS101 → CS201
    CS102 → CS201
    CS201 → CS301
    """
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS102", "CS201")
    g.add_edge("CS201", "CS301")
    return g


@pytest.fixture
def cycle_graph():
    """CS101 → CS201 → CS101"""
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS201", "CS101")
    return g


@pytest.fixture
def empty_graph():
    return CourseGraph()


class TestSort:

    def test_linear_order(self, linear_graph):
        sorter = TopologicalSorter(linear_graph)
        order  = sorter.sort()
        assert order.index("CS101") < order.index("CS201")
        assert order.index("CS201") < order.index("CS301")

    def test_all_nodes_included(self, linear_graph):
        sorter = TopologicalSorter(linear_graph)
        order  = sorter.sort()
        assert set(order) == {"CS101", "CS201", "CS301"}

    def test_empty_graph(self, empty_graph):
        sorter = TopologicalSorter(empty_graph)
        assert sorter.sort() == []

    def test_single_node(self):
        g = CourseGraph()
        g.add_course("CS101")
        sorter = TopologicalSorter(g)
        assert sorter.sort() == ["CS101"]

    def test_branching_prerequisites_before_dependent(
        self, branching_graph
    ):
        sorter = TopologicalSorter(branching_graph)
        order  = sorter.sort()
        cs201_idx = order.index("CS201")
        cs101_idx = order.index("CS101")
        cs102_idx = order.index("CS102")
        assert cs101_idx < cs201_idx
        assert cs102_idx < cs201_idx

    def test_alphabetical_for_same_level(self, branching_graph):
        """CS101 and CS102 both have no prereqs — alphabetical order"""
        sorter = TopologicalSorter(branching_graph)
        order  = sorter.sort()
        assert order.index("CS101") < order.index("CS102")

    def test_cycle_raises_value_error(self, cycle_graph):
        sorter = TopologicalSorter(cycle_graph)
        with pytest.raises(ValueError, match="cycle"):
            sorter.sort()

    def test_disconnected_graph(self):
        g = CourseGraph()
        g.add_edge("CS101", "CS201")
        g.add_edge("PY101", "PY201")
        sorter = TopologicalSorter(g)
        order  = sorter.sort()
        assert order.index("CS101") < order.index("CS201")
        assert order.index("PY101") < order.index("PY201")
        assert set(order) == {"CS101", "CS201", "PY101", "PY201"}


class TestSortSubset:

    def test_subset_ordering(self, linear_graph):
        sorter = TopologicalSorter(linear_graph)
        order  = sorter.sort_subset({"CS301", "CS101"})
        assert "CS201" not in order
        assert order.index("CS101") < order.index("CS301")

    def test_empty_subset(self, linear_graph):
        sorter = TopologicalSorter(linear_graph)
        assert sorter.sort_subset(set()) == []


class TestGetLevels:

    def test_linear_levels(self, linear_graph):
        sorter = TopologicalSorter(linear_graph)
        levels = sorter.get_levels()
        assert levels[0] == ["CS101"]
        assert levels[1] == ["CS201"]
        assert levels[2] == ["CS301"]

    def test_branching_level_zero(self, branching_graph):
        sorter = TopologicalSorter(branching_graph)
        levels = sorter.get_levels()
        # CS101 and CS102 both have no prerequisites
        assert "CS101" in levels[0]
        assert "CS102" in levels[0]

    def test_empty_graph(self, empty_graph):
        sorter = TopologicalSorter(empty_graph)
        assert sorter.get_levels() == []


class TestGetCourseLevel:

    def test_root_is_level_0(self, linear_graph):
        sorter = TopologicalSorter(linear_graph)
        assert sorter.get_course_level("CS101") == 0

    def test_second_level(self, linear_graph):
        sorter = TopologicalSorter(linear_graph)
        assert sorter.get_course_level("CS201") == 1

    def test_third_level(self, linear_graph):
        sorter = TopologicalSorter(linear_graph)
        assert sorter.get_course_level("CS301") == 2

    def test_unknown_course(self, linear_graph):
        sorter = TopologicalSorter(linear_graph)
        assert sorter.get_course_level("UNKNOWN") == -1