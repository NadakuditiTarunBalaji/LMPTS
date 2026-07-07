"""
test_algorithms.py
------------------
Comprehensive tests for all LMPTS algorithm classes.

Covers:
    - CourseGraph          (graph.py)
    - CycleDetector        (cycle_detection.py)
    - PathFinder           (path_finder.py)
    - TopologicalSorter    (topological_sort.py)
    - PrerequisiteValidator (prerequisite_validator.py)
    - RecommendationEngine  (recommendation.py)
    - LearnerCredits        (prerequisite_validator.py)

Runs with both:
    python -m pytest tests/test_algorithms.py -v
    python -m unittest tests/test_algorithms.py -v
"""

import unittest

from algorithms.graph import CourseGraph
from algorithms.cycle_detection import CycleDetector
from algorithms.path_finder import PathFinder
from algorithms.topological_sort import TopologicalSorter
from algorithms.prerequisite_validator import (
    PrerequisiteValidator,
    LearnerCredits,
    ValidationResult,
    CreditType,
)
from algorithms.recommendation import RecommendationEngine, CourseInfo


# ═══════════════════════════════════════════════════════════════════════════════
# Shared graph builders
# ═══════════════════════════════════════════════════════════════════════════════

def make_linear_graph() -> CourseGraph:
    """
    PY101 → PY201 → PY301 → ML101
    """
    g = CourseGraph()
    g.add_edge("PY101", "PY201")
    g.add_edge("PY201", "PY301")
    g.add_edge("PY301", "ML101")
    return g


def make_branching_graph() -> CourseGraph:
    """
    CS101 → CS201 → CS301
    CS102 → CS201
    """
    g = CourseGraph()
    g.add_edge("CS101", "CS201")
    g.add_edge("CS102", "CS201")
    g.add_edge("CS201", "CS301")
    return g


def make_cycle_graph() -> CourseGraph:
    """
    PY101 → PY201 → PY301 → ML101 → PY101  (cycle)
    """
    g = CourseGraph()
    g.add_edge("PY101", "PY201")
    g.add_edge("PY201", "PY301")
    g.add_edge("PY301", "ML101")
    g.add_edge("ML101", "PY101")
    return g


# ═══════════════════════════════════════════════════════════════════════════════
# Graph Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCourseGraph(unittest.TestCase):
    """Tests for CourseGraph — core data structure."""

    def setUp(self):
        """Fresh linear graph for every test."""
        self.graph = make_linear_graph()

    # ── Course management ──────────────────────────────────────────────────────

    def test_add_course(self):
        self.graph.add_course("AI101")
        self.assertTrue(self.graph.has_course("AI101"))

    def test_add_course_idempotent(self):
        self.graph.add_course("AI101")
        self.graph.add_course("AI101")
        # Should not duplicate
        self.assertEqual(
            self.graph.get_courses().count("AI101"), 1
        )

    def test_add_course_empty_raises(self):
        with self.assertRaises(ValueError):
            self.graph.add_course("")

    def test_has_course_true(self):
        self.assertTrue(self.graph.has_course("PY101"))

    def test_has_course_false(self):
        self.assertFalse(self.graph.has_course("UNKNOWN"))

    def test_remove_course(self):
        self.graph.remove_course("PY201")
        self.assertFalse(self.graph.has_course("PY201"))

    def test_remove_course_cleans_forward_edges(self):
        self.graph.remove_course("PY201")
        self.assertNotIn("PY201", self.graph.get_neighbors("PY101"))

    def test_remove_course_cleans_reverse_edges(self):
        self.graph.remove_course("PY201")
        self.assertNotIn("PY201", self.graph.get_prerequisites("PY301"))

    def test_get_courses_returns_sorted_list(self):
        courses = self.graph.get_courses()
        self.assertEqual(courses, sorted(courses))

    def test_number_of_courses(self):
        self.assertEqual(self.graph.number_of_courses(), 4)

    def test_number_of_relationships(self):
        self.assertEqual(self.graph.number_of_relationships(), 3)

    def test_clear_graph(self):
        self.graph.clear_graph()
        self.assertEqual(self.graph.number_of_courses(), 0)
        self.assertEqual(self.graph.number_of_relationships(), 0)

    # ── Edge management ────────────────────────────────────────────────────────

    def test_add_edge(self):
        self.assertTrue(self.graph.has_edge("PY101", "PY201"))

    def test_add_edge_creates_both_nodes(self):
        g = CourseGraph()
        g.add_edge("NEW1", "NEW2")
        self.assertTrue(g.has_course("NEW1"))
        self.assertTrue(g.has_course("NEW2"))

    def test_add_edge_self_loop_raises(self):
        with self.assertRaises(ValueError):
            self.graph.add_edge("PY101", "PY101")

    def test_add_edge_empty_raises(self):
        with self.assertRaises(ValueError):
            self.graph.add_edge("", "PY201")

    def test_remove_edge(self):
        self.graph.remove_edge("PY101", "PY201")
        self.assertFalse(self.graph.has_edge("PY101", "PY201"))

    def test_remove_edge_safe_if_not_exists(self):
        # Must not raise
        self.graph.remove_edge("PY101", "ML101")

    def test_has_edge_true(self):
        self.assertTrue(self.graph.has_edge("PY101", "PY201"))

    def test_has_edge_false(self):
        self.assertFalse(self.graph.has_edge("PY101", "ML101"))

    # ── Neighbor queries ───────────────────────────────────────────────────────

    def test_get_neighbors_forward(self):
        """PY101 → PY201: neighbors of PY101 = {PY201}"""
        neighbors = self.graph.get_neighbors("PY101")
        self.assertIn("PY201", neighbors)

    def test_get_neighbors_empty_for_leaf(self):
        self.assertEqual(self.graph.get_neighbors("ML101"), set())

    def test_get_prerequisites_reverse(self):
        """PY201 requires PY101"""
        prereqs = self.graph.get_prerequisites("PY201")
        self.assertIn("PY101", prereqs)

    def test_get_prerequisites_empty_for_root(self):
        self.assertEqual(self.graph.get_prerequisites("PY101"), set())

    def test_get_all_prerequisites_full_chain(self):
        """ML101 needs PY101, PY201, PY301"""
        all_prereqs = self.graph.get_all_prerequisites("ML101")
        self.assertEqual(all_prereqs, {"PY101", "PY201", "PY301"})

    def test_get_all_prerequisites_empty_for_root(self):
        self.assertEqual(
            self.graph.get_all_prerequisites("PY101"), set()
        )

    def test_get_all_dependents(self):
        """PY101 unlocks PY201, PY301, ML101"""
        all_deps = self.graph.get_all_dependents("PY101")
        self.assertEqual(all_deps, {"PY201", "PY301", "ML101"})

    def test_get_neighbors_returns_copy(self):
        neighbors = self.graph.get_neighbors("PY101")
        neighbors.add("HACKED")
        self.assertNotIn("HACKED", self.graph.get_neighbors("PY101"))

    # ── Build from courses ─────────────────────────────────────────────────────

    def test_build_from_courses(self):
        g = CourseGraph()
        g.build_from_courses(
            ["CS101", "CS201", "CS301"],
            {"CS201": {"CS101"}, "CS301": {"CS201"}}
        )
        self.assertTrue(g.has_edge("CS101", "CS201"))
        self.assertTrue(g.has_edge("CS201", "CS301"))
        self.assertEqual(g.number_of_courses(), 3)

    def test_build_from_courses_clears_old(self):
        g = make_linear_graph()
        g.build_from_courses(["A", "B"], {"B": {"A"}})
        self.assertFalse(g.has_course("PY101"))
        self.assertTrue(g.has_course("A"))

    def test_build_from_courses_updates_both_graphs(self):
        g = CourseGraph()
        g.build_from_courses(
            ["CS101", "CS201"],
            {"CS201": {"CS101"}}
        )
        self.assertIn("CS201", g.get_neighbors("CS101"))
        self.assertIn("CS101", g.get_prerequisites("CS201"))


# ═══════════════════════════════════════════════════════════════════════════════
# Cycle Detection Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCycleDetector(unittest.TestCase):
    """Tests for CycleDetector — DFS cycle detection."""

    def setUp(self):
        self.graph = make_linear_graph()

    # ── detect_cycle ──────────────────────────────────────────────────────────

    def test_no_cycle(self):
        detector = CycleDetector(self.graph)
        self.assertFalse(detector.detect_cycle())

    def test_cycle_exists(self):
        self.graph.add_edge("ML101", "PY101")
        detector = CycleDetector(self.graph)
        self.assertTrue(detector.detect_cycle())

    def test_empty_graph_no_cycle(self):
        detector = CycleDetector(CourseGraph())
        self.assertFalse(detector.detect_cycle())

    def test_single_node_no_cycle(self):
        g = CourseGraph()
        g.add_course("CS101")
        detector = CycleDetector(g)
        self.assertFalse(detector.detect_cycle())

    def test_two_node_cycle(self):
        g = CourseGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "A")
        detector = CycleDetector(g)
        self.assertTrue(detector.detect_cycle())

    def test_disconnected_one_cycle(self):
        g = CourseGraph()
        g.add_edge("A", "B")           # no cycle
        g.add_edge("C", "D")
        g.add_edge("D", "C")           # cycle
        detector = CycleDetector(g)
        self.assertTrue(detector.detect_cycle())

    # ── would_create_cycle ────────────────────────────────────────────────────

    def test_would_create_cycle_true(self):
        detector = CycleDetector(self.graph)
        # PY301 → PY101 closes the loop
        self.assertTrue(detector.would_create_cycle("PY301", "PY101"))

    def test_would_create_cycle_false(self):
        detector = CycleDetector(self.graph)
        # Adding new independent edge
        self.assertFalse(detector.would_create_cycle("AI101", "AI201"))

    def test_would_create_cycle_self_loop(self):
        detector = CycleDetector(self.graph)
        self.assertTrue(detector.would_create_cycle("PY101", "PY101"))

    def test_would_not_modify_graph(self):
        original = self.graph.number_of_relationships()
        detector = CycleDetector(self.graph)
        detector.would_create_cycle("ML101", "PY101")
        self.assertEqual(
            self.graph.number_of_relationships(), original
        )

    # ── find_cycle_path ───────────────────────────────────────────────────────

    def test_find_cycle_path_none_when_no_cycle(self):
        detector = CycleDetector(self.graph)
        self.assertIsNone(detector.find_cycle_path())

    def test_find_cycle_path_returns_list(self):
        self.graph.add_edge("ML101", "PY101")
        detector = CycleDetector(self.graph)
        path = detector.find_cycle_path()
        self.assertIsNotNone(path)
        self.assertIsInstance(path, list)

    def test_find_cycle_path_first_equals_last(self):
        self.graph.add_edge("ML101", "PY101")
        detector = CycleDetector(self.graph)
        path = detector.find_cycle_path()
        self.assertIsNotNone(path)
        self.assertEqual(path[0], path[-1])

    # ── get_all_cycles ────────────────────────────────────────────────────────

    def test_get_all_cycles_empty_when_no_cycle(self):
        detector = CycleDetector(self.graph)
        self.assertEqual(detector.get_all_cycles(), [])

    def test_get_all_cycles_finds_one(self):
        self.graph.add_edge("ML101", "PY101")
        detector = CycleDetector(self.graph)
        cycles = detector.get_all_cycles()
        self.assertGreaterEqual(len(cycles), 1)


# ═══════════════════════════════════════════════════════════════════════════════
# Path Finder Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPathFinder(unittest.TestCase):
    """Tests for PathFinder — BFS learning path algorithms."""

    def setUp(self):
        self.graph = make_linear_graph()
        self.finder = PathFinder(self.graph)

    # ── find_learning_path ────────────────────────────────────────────────────

    def test_learning_path_full(self):
        path = self.finder.find_learning_path("PY101", "ML101")
        self.assertEqual(path, ["PY101", "PY201", "PY301", "ML101"])

    def test_learning_path_same_course(self):
        path = self.finder.find_learning_path("PY101", "PY101")
        self.assertEqual(path, ["PY101"])

    def test_learning_path_no_path(self):
        """No backward path"""
        path = self.finder.find_learning_path("ML101", "PY101")
        self.assertIsNone(path)

    def test_learning_path_start_not_found(self):
        path = self.finder.find_learning_path("UNKNOWN", "ML101")
        self.assertIsNone(path)

    def test_learning_path_end_not_found(self):
        path = self.finder.find_learning_path("PY101", "UNKNOWN")
        self.assertIsNone(path)

    def test_learning_path_starts_with_start(self):
        path = self.finder.find_learning_path("PY101", "ML101")
        self.assertEqual(path[0], "PY101")

    def test_learning_path_ends_with_end(self):
        path = self.finder.find_learning_path("PY101", "ML101")
        self.assertEqual(path[-1], "ML101")

    # ── find_all_prerequisites ────────────────────────────────────────────────

    def test_find_all_prerequisites_full_chain(self):
        prereqs = self.finder.find_all_prerequisites("ML101")
        self.assertIn("PY101", prereqs)
        self.assertIn("PY201", prereqs)
        self.assertIn("PY301", prereqs)

    def test_find_all_prerequisites_root(self):
        prereqs = self.finder.find_all_prerequisites("PY101")
        self.assertEqual(prereqs, [])

    def test_find_all_prerequisites_ordered(self):
        """PY101 must appear before PY201"""
        prereqs = self.finder.find_all_prerequisites("PY301")
        idx_py101 = prereqs.index("PY101")
        idx_py201 = prereqs.index("PY201")
        self.assertLess(idx_py101, idx_py201)

    # ── get_recommended_path ──────────────────────────────────────────────────

    def test_recommended_path_no_completed(self):
        path = self.finder.get_recommended_path(
            target="ML101", completed=set()
        )
        self.assertIn("PY101", path)
        self.assertIn("PY201", path)
        self.assertIn("PY301", path)
        self.assertIn("ML101", path)

    def test_recommended_path_partial_completion(self):
        path = self.finder.get_recommended_path(
            target="ML101",
            completed={"PY101", "PY201"}
        )
        self.assertNotIn("PY101", path)
        self.assertNotIn("PY201", path)
        self.assertIn("PY301", path)
        self.assertIn("ML101", path)

    def test_recommended_path_transfer_credits(self):
        path = self.finder.get_recommended_path(
            target="ML101",
            completed=set(),
            transfer_credits={"PY101", "PY201", "PY301"},
        )
        self.assertEqual(path, ["ML101"])

    def test_recommended_path_exemptions(self):
        path = self.finder.get_recommended_path(
            target="PY301",
            completed=set(),
            exemptions={"PY101", "PY201"},
        )
        self.assertEqual(path, ["PY301"])

    def test_recommended_path_target_satisfied(self):
        path = self.finder.get_recommended_path(
            target="PY101",
            completed={"PY101"}
        )
        self.assertNotIn("PY101", path)

    # ── get_study_order ───────────────────────────────────────────────────────

    def test_get_study_order_all(self):
        order = self.finder.get_study_order()
        self.assertLess(
            order.index("PY101"), order.index("PY201")
        )
        self.assertLess(
            order.index("PY201"), order.index("PY301")
        )

    def test_get_study_order_subset(self):
        order = self.finder.get_study_order({"PY301", "PY101"})
        self.assertNotIn("PY201", order)
        self.assertLess(
            order.index("PY101"), order.index("PY301")
        )

    def test_get_study_order_empty_subset(self):
        order = self.finder.get_study_order(set())
        self.assertEqual(order, [])


# ═══════════════════════════════════════════════════════════════════════════════
# Topological Sort Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTopologicalSorter(unittest.TestCase):
    """Tests for TopologicalSorter — Kahn's algorithm."""

    def setUp(self):
        self.graph  = make_linear_graph()
        self.sorter = TopologicalSorter(self.graph)

    # ── sort ──────────────────────────────────────────────────────────────────

    def test_sort_linear_order(self):
        order = self.sorter.sort()
        self.assertLess(order.index("PY101"), order.index("PY201"))
        self.assertLess(order.index("PY201"), order.index("PY301"))
        self.assertLess(order.index("PY301"), order.index("ML101"))

    def test_sort_all_nodes_included(self):
        order = self.sorter.sort()
        self.assertEqual(
            set(order), {"PY101", "PY201", "PY301", "ML101"}
        )

    def test_sort_empty_graph(self):
        sorter = TopologicalSorter(CourseGraph())
        self.assertEqual(sorter.sort(), [])

    def test_sort_single_node(self):
        g = CourseGraph()
        g.add_course("CS101")
        sorter = TopologicalSorter(g)
        self.assertEqual(sorter.sort(), ["CS101"])

    def test_sort_branching_prerequisites_before_dependent(self):
        g      = make_branching_graph()
        sorter = TopologicalSorter(g)
        order  = sorter.sort()
        self.assertLess(order.index("CS101"), order.index("CS201"))
        self.assertLess(order.index("CS102"), order.index("CS201"))

    def test_sort_alphabetical_at_same_level(self):
        """CS101 and CS102 have no prereqs — alphabetical order."""
        g      = make_branching_graph()
        sorter = TopologicalSorter(g)
        order  = sorter.sort()
        self.assertLess(order.index("CS101"), order.index("CS102"))

    def test_sort_cycle_raises_value_error(self):
        g = make_cycle_graph()
        with self.assertRaises(ValueError):
            TopologicalSorter(g).sort()

    def test_sort_cycle_error_message(self):
        g = make_cycle_graph()
        try:
            TopologicalSorter(g).sort()
            self.fail("Expected ValueError")
        except ValueError as e:
            self.assertIn("cycle", str(e).lower())

    # ── sort_subset ───────────────────────────────────────────────────────────

    def test_sort_subset(self):
        order = self.sorter.sort_subset({"ML101", "PY101"})
        self.assertNotIn("PY201", order)
        self.assertLess(order.index("PY101"), order.index("ML101"))

    def test_sort_subset_empty(self):
        self.assertEqual(self.sorter.sort_subset(set()), [])

    # ── get_levels ────────────────────────────────────────────────────────────

    def test_get_levels_linear(self):
        levels = self.sorter.get_levels()
        self.assertEqual(levels[0], ["PY101"])
        self.assertEqual(levels[1], ["PY201"])
        self.assertEqual(levels[2], ["PY301"])
        self.assertEqual(levels[3], ["ML101"])

    def test_get_levels_branching(self):
        g      = make_branching_graph()
        sorter = TopologicalSorter(g)
        levels = sorter.get_levels()
        # CS101 and CS102 are both at level 0
        self.assertIn("CS101", levels[0])
        self.assertIn("CS102", levels[0])

    def test_get_levels_empty(self):
        sorter = TopologicalSorter(CourseGraph())
        self.assertEqual(sorter.get_levels(), [])

    # ── get_course_level ──────────────────────────────────────────────────────

    def test_get_course_level_root(self):
        self.assertEqual(self.sorter.get_course_level("PY101"), 0)

    def test_get_course_level_middle(self):
        self.assertEqual(self.sorter.get_course_level("PY201"), 1)

    def test_get_course_level_leaf(self):
        self.assertEqual(self.sorter.get_course_level("ML101"), 3)

    def test_get_course_level_unknown(self):
        self.assertEqual(self.sorter.get_course_level("UNKNOWN"), -1)


# ═══════════════════════════════════════════════════════════════════════════════
# Prerequisite Validator Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPrerequisiteValidator(unittest.TestCase):
    """Tests for PrerequisiteValidator — enrollment eligibility."""

    def setUp(self):
        """
        CS101 → CS201 → CS301
        CS102 → CS201
        """
        self.graph     = make_branching_graph()
        self.validator = PrerequisiteValidator(self.graph)

    # ── can_enroll ────────────────────────────────────────────────────────────

    def test_no_prerequisites_always_allowed(self):
        credits = LearnerCredits()
        result  = self.validator.can_enroll(credits, "CS101")
        self.assertTrue(result.can_enroll)

    def test_all_direct_prerequisites_satisfied(self):
        credits = LearnerCredits(completed={"CS101", "CS102"})
        result  = self.validator.can_enroll(credits, "CS201")
        self.assertTrue(result.can_enroll)

    def test_missing_one_prerequisite(self):
        credits = LearnerCredits(completed={"CS101"})
        result  = self.validator.can_enroll(credits, "CS201")
        self.assertFalse(result.can_enroll)
        self.assertIn("CS102", result.missing_prerequisites)

    def test_missing_all_prerequisites(self):
        credits = LearnerCredits()
        result  = self.validator.can_enroll(credits, "CS201")
        self.assertFalse(result.can_enroll)
        self.assertEqual(len(result.missing_prerequisites), 2)

    def test_transfer_credit_satisfies(self):
        credits = LearnerCredits(
            transfer_credits={"CS101", "CS102"}
        )
        result = self.validator.can_enroll(credits, "CS201")
        self.assertTrue(result.can_enroll)

    def test_exemption_satisfies(self):
        credits = LearnerCredits(
            exemptions={"CS101", "CS102"}
        )
        result = self.validator.can_enroll(credits, "CS201")
        self.assertTrue(result.can_enroll)

    def test_placement_test_satisfies(self):
        credits = LearnerCredits(
            placement_tests={"CS101", "CS102"}
        )
        result = self.validator.can_enroll(credits, "CS201")
        self.assertTrue(result.can_enroll)

    def test_mixed_credit_types(self):
        credits = LearnerCredits(
            completed={"CS101"},
            transfer_credits={"CS102"},
        )
        result = self.validator.can_enroll(credits, "CS201")
        self.assertTrue(result.can_enroll)

    def test_course_not_found(self):
        credits = LearnerCredits()
        result  = self.validator.can_enroll(credits, "UNKNOWN")
        self.assertFalse(result.can_enroll)
        self.assertIn("not found", result.message.lower())

    def test_result_bool_true(self):
        credits = LearnerCredits(completed={"CS101", "CS102"})
        result  = self.validator.can_enroll(credits, "CS201")
        self.assertTrue(bool(result))

    def test_result_bool_false(self):
        credits = LearnerCredits()
        result  = self.validator.can_enroll(credits, "CS201")
        self.assertFalse(bool(result))

    def test_success_message_contains_allowed(self):
        credits = LearnerCredits(completed={"CS101", "CS102"})
        result  = self.validator.can_enroll(credits, "CS201")
        self.assertIn("allowed", result.message.lower())

    def test_failure_message_contains_missing(self):
        credits = LearnerCredits()
        result  = self.validator.can_enroll(credits, "CS201")
        self.assertTrue(
            "missing" in result.message.lower() or
            "cannot" in result.message.lower()
        )

    # ── satisfied_by mapping ──────────────────────────────────────────────────

    def test_satisfied_by_normal(self):
        credits = LearnerCredits(completed={"CS101", "CS102"})
        result  = self.validator.can_enroll(credits, "CS201")
        self.assertEqual(result.satisfied_by.get("CS101"), CreditType.NORMAL)

    def test_satisfied_by_transfer(self):
        credits = LearnerCredits(transfer_credits={"CS101", "CS102"})
        result  = self.validator.can_enroll(credits, "CS201")
        self.assertEqual(
            result.satisfied_by.get("CS101"), CreditType.TRANSFER
        )

    def test_satisfied_by_exemption(self):
        credits = LearnerCredits(exemptions={"CS101", "CS102"})
        result  = self.validator.can_enroll(credits, "CS201")
        self.assertEqual(
            result.satisfied_by.get("CS101"), CreditType.EXEMPTION
        )

    # ── can_enroll_full_chain ─────────────────────────────────────────────────

    def test_full_chain_all_satisfied(self):
        credits = LearnerCredits(
            completed={"CS101", "CS102", "CS201"}
        )
        result = self.validator.can_enroll_full_chain(credits, "CS301")
        self.assertTrue(result.can_enroll)

    def test_full_chain_missing_transitive(self):
        """CS201 done but CS101/CS102 not — full chain fails."""
        credits = LearnerCredits(completed={"CS201"})
        result  = self.validator.can_enroll_full_chain(credits, "CS301")
        self.assertFalse(result.can_enroll)

    def test_direct_passes_full_chain_fails(self):
        """Direct check passes but full chain fails."""
        credits       = LearnerCredits(completed={"CS201"})
        direct_result = self.validator.can_enroll(credits, "CS301")
        full_result   = self.validator.can_enroll_full_chain(
            credits, "CS301"
        )
        self.assertTrue(direct_result.can_enroll)
        self.assertFalse(full_result.can_enroll)

    # ── what_can_enroll ───────────────────────────────────────────────────────

    def test_what_can_enroll_no_credits(self):
        credits    = LearnerCredits()
        enrollable = self.validator.what_can_enroll(credits)
        self.assertIn("CS101", enrollable)
        self.assertIn("CS102", enrollable)
        self.assertNotIn("CS201", enrollable)

    def test_what_can_enroll_after_prerequisites(self):
        credits    = LearnerCredits(completed={"CS101", "CS102"})
        enrollable = self.validator.what_can_enroll(credits)
        self.assertIn("CS201", enrollable)

    def test_what_can_enroll_satisfied_excluded(self):
        credits    = LearnerCredits(completed={"CS101"})
        enrollable = self.validator.what_can_enroll(credits)
        self.assertNotIn("CS101", enrollable)

    # ── can_add_prerequisite ──────────────────────────────────────────────────

    def test_can_add_prerequisite_safe(self):
        self.assertTrue(
            self.validator.can_add_prerequisite("CS201", "CS102")
        )

    def test_can_add_prerequisite_would_cycle(self):
        self.assertFalse(
            self.validator.can_add_prerequisite("CS101", "CS301")
        )

    def test_can_add_prerequisite_self(self):
        self.assertFalse(
            self.validator.can_add_prerequisite("CS101", "CS101")
        )

    # ── LearnerCredits ────────────────────────────────────────────────────────

    def test_learner_credits_all_satisfied_union(self):
        credits = LearnerCredits(
            completed={"A"},
            transfer_credits={"B"},
            exemptions={"C"},
            placement_tests={"D"},
        )
        self.assertEqual(
            credits.all_satisfied, {"A", "B", "C", "D"}
        )

    def test_learner_credits_empty(self):
        credits = LearnerCredits()
        self.assertEqual(credits.all_satisfied, set())


# ═══════════════════════════════════════════════════════════════════════════════
# Recommendation Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecommendationEngine(unittest.TestCase):
    """Tests for RecommendationEngine."""

    def setUp(self):
        """
        CS101 → CS201 → CS301
        CS102 → CS201
        PY101 → PY201
        """
        self.graph = CourseGraph()
        self.graph.add_edge("CS101", "CS201")
        self.graph.add_edge("CS102", "CS201")
        self.graph.add_edge("CS201", "CS301")
        self.graph.add_edge("PY101", "PY201")

        self.course_info = {
            "CS101": CourseInfo("CS101", "Intro to CS",
                                "BEGINNER", 20),
            "CS102": CourseInfo("CS102", "Math for CS",
                                "BEGINNER", 25),
            "CS201": CourseInfo("CS201", "Data Structures",
                                "INTERMEDIATE", 40),
            "CS301": CourseInfo("CS301", "Algorithms",
                                "ADVANCED", 60),
            "PY101": CourseInfo("PY101", "Python Basics",
                                "BEGINNER", 15),
            "PY201": CourseInfo("PY201", "Python Advanced",
                                "INTERMEDIATE", 35),
        }

        self.engine = RecommendationEngine(self.graph)

    # ── recommend ─────────────────────────────────────────────────────────────

    def test_returns_list(self):
        recs = self.engine.recommend(
            LearnerCredits(), self.course_info
        )
        self.assertIsInstance(recs, list)

    def test_no_credits_recommends_entry_courses(self):
        recs  = self.engine.recommend(LearnerCredits(), self.course_info)
        codes = [r.course_code for r in recs]
        # Only courses with no prerequisites should appear
        for code in codes:
            self.assertNotIn(code, ["CS201", "CS301", "PY201"])

    def test_respects_limit(self):
        recs = self.engine.recommend(
            LearnerCredits(), self.course_info, limit=2
        )
        self.assertLessEqual(len(recs), 2)

    def test_sorted_by_score_descending(self):
        recs   = self.engine.recommend(LearnerCredits(), self.course_info)
        scores = [r.score for r in recs]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_completed_courses_excluded(self):
        credits = LearnerCredits(completed={"CS101", "CS102"})
        recs    = self.engine.recommend(credits, self.course_info)
        codes   = [r.course_code for r in recs]
        self.assertNotIn("CS101", codes)
        self.assertNotIn("CS102", codes)

    def test_transfer_unlocks_courses(self):
        credits = LearnerCredits(transfer_credits={"CS101", "CS102"})
        recs    = self.engine.recommend(credits, self.course_info)
        codes   = [r.course_code for r in recs]
        self.assertIn("CS201", codes)

    def test_exclude_parameter(self):
        recs  = self.engine.recommend(
            LearnerCredits(), self.course_info, exclude={"CS101"}
        )
        codes = [r.course_code for r in recs]
        self.assertNotIn("CS101", codes)

    def test_score_in_valid_range(self):
        recs = self.engine.recommend(LearnerCredits(), self.course_info)
        for rec in recs:
            self.assertGreaterEqual(rec.score, 0)
            self.assertLessEqual(rec.score, 100)

    def test_recommendation_has_reasons(self):
        recs = self.engine.recommend(LearnerCredits(), self.course_info)
        if recs:
            self.assertGreater(len(recs[0].reasons), 0)

    def test_all_completed_no_recommendations(self):
        all_courses = set(self.graph.get_courses())
        credits     = LearnerCredits(completed=all_courses)
        recs        = self.engine.recommend(credits, self.course_info)
        self.assertEqual(recs, [])

    def test_empty_graph_no_recommendations(self):
        engine = RecommendationEngine(CourseGraph())
        recs   = engine.recommend(LearnerCredits(), self.course_info)
        self.assertEqual(recs, [])

    # ── get_learning_roadmap ──────────────────────────────────────────────────

    def test_roadmap_single_goal(self):
        credits = LearnerCredits(completed={"CS101", "CS102"})
        roadmap = self.engine.get_learning_roadmap(
            learner_credits=credits,
            goal_courses=["CS301"],
            course_info=self.course_info,
        )
        self.assertIn("CS301", roadmap)
        self.assertIn("CS201", roadmap["CS301"])
        self.assertNotIn("CS101", roadmap["CS301"])

    def test_roadmap_transfer_shortens_path(self):
        credits = LearnerCredits(
            transfer_credits={"CS101", "CS102", "CS201"}
        )
        roadmap = self.engine.get_learning_roadmap(
            learner_credits=credits,
            goal_courses=["CS301"],
            course_info=self.course_info,
        )
        self.assertEqual(roadmap["CS301"], ["CS301"])

    def test_roadmap_empty_when_goal_satisfied(self):
        credits = LearnerCredits(
            completed={"CS101", "CS102", "CS201", "CS301"}
        )
        roadmap = self.engine.get_learning_roadmap(
            learner_credits=credits,
            goal_courses=["CS301"],
            course_info=self.course_info,
        )
        self.assertEqual(roadmap["CS301"], [])


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlgorithmIntegration(unittest.TestCase):
    """
    End-to-end tests combining multiple algorithm classes.
    Simulates real learner scenarios.
    """

    def setUp(self):
        """
        Full CS curriculum:
        CS101 → CS201 → CS301 → CS401
        CS102 → CS201
        MATH101 → CS301
        """
        self.graph = CourseGraph()
        self.graph.add_edge("CS101",   "CS201")
        self.graph.add_edge("CS102",   "CS201")
        self.graph.add_edge("CS201",   "CS301")
        self.graph.add_edge("MATH101", "CS301")
        self.graph.add_edge("CS301",   "CS401")

        self.course_info = {
            "CS101":   CourseInfo("CS101",   "Intro CS",
                                  "BEGINNER", 20),
            "CS102":   CourseInfo("CS102",   "Math CS",
                                  "BEGINNER", 25),
            "CS201":   CourseInfo("CS201",   "Data Structures",
                                  "INTERMEDIATE", 40),
            "MATH101": CourseInfo("MATH101", "Discrete Math",
                                  "BEGINNER", 30),
            "CS301":   CourseInfo("CS301",   "Algorithms",
                                  "ADVANCED", 60),
            "CS401":   CourseInfo("CS401",   "Advanced Topics",
                                  "ADVANCED", 50),
        }

    def test_fresh_learner_workflow(self):
        """New learner with no credits."""
        credits   = LearnerCredits()
        validator = PrerequisiteValidator(self.graph)
        finder    = PathFinder(self.graph)
        engine    = RecommendationEngine(self.graph)

        # Cannot enroll in CS201 yet
        result = validator.can_enroll(credits, "CS201")
        self.assertFalse(result.can_enroll)

        # Can enroll in entry courses
        enrollable = validator.what_can_enroll(credits)
        self.assertIn("CS101", enrollable)
        self.assertIn("CS102", enrollable)
        self.assertIn("MATH101", enrollable)

        # Recommendations show entry courses
        recs  = engine.recommend(credits, self.course_info)
        codes = [r.course_code for r in recs]
        self.assertNotIn("CS201", codes)
        self.assertNotIn("CS301", codes)

    def test_transfer_learner_workflow(self):
        """Learner with transfer credits skips early courses."""
        credits = LearnerCredits(
            transfer_credits={"CS101", "CS102", "MATH101"}
        )
        validator = PrerequisiteValidator(self.graph)

        # Can now enroll in CS201
        result = validator.can_enroll(credits, "CS201")
        self.assertTrue(result.can_enroll)

        # Satisfied_by shows TRANSFER
        self.assertEqual(
            result.satisfied_by.get("CS101"), CreditType.TRANSFER
        )

    def test_safe_prerequisite_addition(self):
        """Admin adds new prerequisite safely."""
        validator = PrerequisiteValidator(self.graph)
        detector  = CycleDetector(self.graph)

        # Safe: CS102 as prereq for CS301
        self.assertTrue(
            validator.can_add_prerequisite("CS301", "CS102")
        )
        self.assertFalse(
            detector.would_create_cycle("CS102", "CS301")
        )

    def test_cycle_prevention(self):
        """System prevents creating a cycle."""
        detector  = CycleDetector(self.graph)
        validator = PrerequisiteValidator(self.graph)

        # CS401 → CS101 would close the loop
        self.assertTrue(
            detector.would_create_cycle("CS401", "CS101")
        )
        self.assertFalse(
            validator.can_add_prerequisite("CS101", "CS401")
        )

    def test_study_order_is_valid(self):
        """Every course appears after all its prerequisites."""
        sorter = TopologicalSorter(self.graph)
        order  = sorter.sort()

        # Check all edges are respected
        for course in self.graph.get_courses():
            course_idx = order.index(course)
            for prereq in self.graph.get_prerequisites(course):
                prereq_idx = order.index(prereq)
                self.assertLess(
                    prereq_idx, course_idx,
                    f"{prereq} must come before {course}"
                )

    def test_roadmap_for_senior_goal(self):
        """Learner who wants CS401 with partial completion."""
        credits = LearnerCredits(
            completed={"CS101", "CS102"},
            transfer_credits={"MATH101"},
        )
        engine  = RecommendationEngine(self.graph)
        roadmap = engine.get_learning_roadmap(
            learner_credits=credits,
            goal_courses=["CS401"],
            course_info=self.course_info,
        )

        self.assertIn("CS401", roadmap)
        path = roadmap["CS401"]

        # CS201 and CS301 must be in path, not CS101/CS102/MATH101
        self.assertIn("CS201", path)
        self.assertIn("CS301", path)
        self.assertIn("CS401", path)
        self.assertNotIn("CS101",   path)
        self.assertNotIn("CS102",   path)
        self.assertNotIn("MATH101", path)


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)