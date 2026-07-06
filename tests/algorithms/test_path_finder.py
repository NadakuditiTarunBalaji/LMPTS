"""
test_path_finder.py
-------------------
Tests for PathFinder — BFS learning path algorithms.
"""

import pytest
from algorithms.graph import CourseGraph
from algorithms.path_finder import PathFinder


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
    CS101 → CS301 (shortcut)
    """
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS102", "CS201")
    g.add_edge("CS201", "CS301")
    g.add_edge("CS101", "CS301")
    return g


class TestFindLearningPath:

    def test_direct_path(self, linear_graph):
        finder = PathFinder(linear_graph)
        path   = finder.find_learning_path("CS101", "CS401")
        assert path is not None
        assert path[0]  == "CS101"
        assert path[-1] == "CS401"

    def test_path_includes_all_steps(self, linear_graph):
        finder = PathFinder(linear_graph)
        path   = finder.find_learning_path("CS101", "CS401")
        assert "CS201" in path
        assert "CS301" in path

    def test_same_course(self, linear_graph):
        finder = PathFinder(linear_graph)
        path   = finder.find_learning_path("CS101", "CS101")
        assert path == ["CS101"]

    def test_no_path_reverse(self, linear_graph):
        """No backward path in a DAG"""
        finder = PathFinder(linear_graph)
        assert finder.find_learning_path("CS401", "CS101") is None

    def test_start_not_in_graph(self, linear_graph):
        finder = PathFinder(linear_graph)
        assert finder.find_learning_path("UNKNOWN", "CS201") is None

    def test_end_not_in_graph(self, linear_graph):
        finder = PathFinder(linear_graph)
        assert finder.find_learning_path("CS101", "UNKNOWN") is None

    def test_shortest_path_with_shortcut(self, branching_graph):
        """Should find shorter path CS101 → CS301 not through CS201"""
        finder = PathFinder(branching_graph)
        path   = finder.find_learning_path("CS101", "CS301")
        assert path is not None
        assert path[0]  == "CS101"
        assert path[-1] == "CS301"
        # Shortest should have length 2 (direct shortcut)
        assert len(path) == 2


class TestFindAllPrerequisites:

    def test_chain_prerequisites(self, linear_graph):
        finder = PathFinder(linear_graph)
        prereqs = finder.find_all_prerequisites("CS401")
        assert set(prereqs) == {"CS101", "CS201", "CS301"}

    def test_root_has_no_prerequisites(self, linear_graph):
        finder = PathFinder(linear_graph)
        assert finder.find_all_prerequisites("CS101") == []

    def test_direct_only(self, linear_graph):
        finder = PathFinder(linear_graph)
        prereqs = finder.find_all_prerequisites("CS201")
        assert set(prereqs) == {"CS101"}

    def test_prerequisites_in_valid_order(self, linear_graph):
        """CS101 must appear before CS201 in the order"""
        finder  = PathFinder(linear_graph)
        prereqs = finder.find_all_prerequisites("CS301")
        assert prereqs.index("CS101") < prereqs.index("CS201")


class TestGetRecommendedPath:

    def test_no_completed(self, linear_graph):
        finder = PathFinder(linear_graph)
        path   = finder.get_recommended_path(
            target="CS401", completed=set()
        )
        assert "CS101" in path
        assert "CS201" in path
        assert "CS301" in path
        assert "CS401" in path

    def test_partial_completion(self, linear_graph):
        finder = PathFinder(linear_graph)
        path   = finder.get_recommended_path(
            target="CS401", completed={"CS101", "CS201"}
        )
        assert "CS101" not in path
        assert "CS201" not in path
        assert "CS301" in path
        assert "CS401" in path

    def test_transfer_credits_excluded(self, linear_graph):
        finder = PathFinder(linear_graph)
        path   = finder.get_recommended_path(
            target="CS401",
            completed=set(),
            transfer_credits={"CS101", "CS201", "CS301"},
        )
        assert "CS101" not in path
        assert "CS201" not in path
        assert "CS301" not in path
        assert path == ["CS401"]

    def test_exemptions_excluded(self, linear_graph):
        finder = PathFinder(linear_graph)
        path   = finder.get_recommended_path(
            target="CS301",
            completed=set(),
            exemptions={"CS101", "CS201"},
        )
        assert path == ["CS301"]

    def test_target_already_satisfied(self, linear_graph):
        finder = PathFinder(linear_graph)
        path   = finder.get_recommended_path(
            target="CS101", completed={"CS101"}
        )
        assert "CS101" not in path
        assert path == []


class TestGetStudyOrder:

    def test_all_courses_ordered(self, linear_graph):
        finder = PathFinder(linear_graph)
        order  = finder.get_study_order()
        assert order.index("CS101") < order.index("CS201")
        assert order.index("CS201") < order.index("CS301")

    def test_subset_ordered(self, linear_graph):
        finder = PathFinder(linear_graph)
        order  = finder.get_study_order({"CS301", "CS101"})
        assert "CS201" not in order
        assert order.index("CS101") < order.index("CS301")

    def test_empty_subset(self, linear_graph):
        finder = PathFinder(linear_graph)
        assert finder.get_study_order(set()) == []