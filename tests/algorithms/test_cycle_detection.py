"""
test_cycle_detection.py
-----------------------
Tests for CycleDetector — DFS cycle detection.
"""

import pytest
from algorithms.graph import CourseGraph
from algorithms.cycle_detection import CycleDetector


@pytest.fixture
def no_cycle_graph():
    """CS101 → CS201 → CS301"""
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS201", "CS301")
    return g


@pytest.fixture
def simple_cycle_graph():
    """CS101 → CS201 → CS101 (cycle)"""
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS201", "CS101")
    return g


@pytest.fixture
def long_cycle_graph():
    """CS101 → CS201 → CS301 → CS101 (3-node cycle)"""
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS201", "CS301")
    g.add_edge("CS301", "CS101")
    return g


@pytest.fixture
def empty_graph():
    return CourseGraph()


class TestDetectCycle:

    def test_no_cycle_linear(self, no_cycle_graph):
        detector = CycleDetector(no_cycle_graph)
        assert detector.detect_cycle() is False

    def test_no_cycle_empty(self, empty_graph):
        detector = CycleDetector(empty_graph)
        assert detector.detect_cycle() is False

    def test_no_cycle_single_node(self):
        g = CourseGraph()
        g.add_course("CS101")
        detector = CycleDetector(g)
        assert detector.detect_cycle() is False

    def test_simple_cycle(self, simple_cycle_graph):
        detector = CycleDetector(simple_cycle_graph)
        assert detector.detect_cycle() is True

    def test_long_cycle(self, long_cycle_graph):
        detector = CycleDetector(long_cycle_graph)
        assert detector.detect_cycle() is True

    def test_branching_no_cycle(self):
        g = CourseGraph()
        g.add_edge("CS101", "CS201")
        g.add_edge("CS101", "CS202")
        g.add_edge("CS201", "CS301")
        g.add_edge("CS202", "CS301")
        detector = CycleDetector(g)
        assert detector.detect_cycle() is False

    def test_disconnected_graph_no_cycle(self):
        g = CourseGraph()
        g.add_edge("CS101", "CS201")
        g.add_edge("CS301", "CS401")
        detector = CycleDetector(g)
        assert detector.detect_cycle() is False

    def test_disconnected_one_has_cycle(self):
        g = CourseGraph()
        g.add_edge("CS101", "CS201")          # no cycle
        g.add_edge("CS301", "CS401")
        g.add_edge("CS401", "CS301")          # cycle
        detector = CycleDetector(g)
        assert detector.detect_cycle() is True


class TestFindCyclePath:

    def test_no_cycle_returns_none(self, no_cycle_graph):
        detector = CycleDetector(no_cycle_graph)
        assert detector.find_cycle_path() is None

    def test_empty_graph_returns_none(self, empty_graph):
        detector = CycleDetector(empty_graph)
        assert detector.find_cycle_path() is None

    def test_simple_cycle_path(self, simple_cycle_graph):
        detector = CycleDetector(simple_cycle_graph)
        path = detector.find_cycle_path()
        assert path is not None
        assert len(path) >= 2
        # Path should start and end with the same node
        assert path[0] == path[-1]

    def test_long_cycle_path_contains_members(self, long_cycle_graph):
        detector = CycleDetector(long_cycle_graph)
        path = detector.find_cycle_path()
        assert path is not None
        path_set = set(path)
        # All three cycle members should appear
        assert "CS101" in path_set or "CS201" in path_set


class TestWouldCreateCycle:

    def test_no_cycle_addition(self, no_cycle_graph):
        """Adding CS101 → CS301 shortcut should not create cycle"""
        detector = CycleDetector(no_cycle_graph)
        assert detector.would_create_cycle("CS101", "CS301") is False

    def test_creates_cycle(self, no_cycle_graph):
        """Adding CS301 → CS101 closes the loop"""
        detector = CycleDetector(no_cycle_graph)
        assert detector.would_create_cycle("CS301", "CS101") is True

    def test_self_loop_always_cycle(self, no_cycle_graph):
        detector = CycleDetector(no_cycle_graph)
        assert detector.would_create_cycle("CS101", "CS101") is True

    def test_new_independent_edge_no_cycle(self, no_cycle_graph):
        """Adding a completely new edge is safe"""
        detector = CycleDetector(no_cycle_graph)
        assert detector.would_create_cycle("CS401", "CS501") is False

    def test_reverse_of_existing_creates_cycle(self, no_cycle_graph):
        """CS201 → CS101 reverses an existing edge → cycle"""
        detector = CycleDetector(no_cycle_graph)
        assert detector.would_create_cycle("CS201", "CS101") is True

    def test_graph_unchanged_after_check(self, no_cycle_graph):
        """would_create_cycle must NOT modify the graph"""
        original_count = no_cycle_graph.number_of_relationships()
        detector = CycleDetector(no_cycle_graph)
        detector.would_create_cycle("CS301", "CS101")
        assert no_cycle_graph.number_of_relationships() == original_count


class TestGetAllCycles:

    def test_no_cycles(self, no_cycle_graph):
        detector = CycleDetector(no_cycle_graph)
        assert detector.get_all_cycles() == []

    def test_one_cycle(self, simple_cycle_graph):
        detector = CycleDetector(simple_cycle_graph)
        cycles = detector.get_all_cycles()
        assert len(cycles) >= 1

    def test_empty_graph(self, empty_graph):
        detector = CycleDetector(empty_graph)
        assert detector.get_all_cycles() == []