import unittest

from algorithms.graph import CourseGraph
from algorithms.cycle_detection import CycleDetector
from algorithms.path_finder import PathFinder


class TestAlgorithms(unittest.TestCase):

    def setUp(self):
        self.graph = CourseGraph()

        self.graph.add_edge("PY101", "PY201")
        self.graph.add_edge("PY201", "PY301")
        self.graph.add_edge("PY301", "ML101")

    # ------------------------------
    # Graph Tests
    # ------------------------------

    def test_add_course(self):
        self.graph.add_course("AI101")
        self.assertTrue(self.graph.has_course("AI101"))

    def test_add_edge(self):
        self.assertTrue(
            self.graph.has_edge("PY101", "PY201")
        )

    def test_remove_edge(self):
        self.graph.remove_edge("PY101", "PY201")

        self.assertFalse(
            self.graph.has_edge("PY101", "PY201")
        )

    # ------------------------------
    # Cycle Detection Tests
    # ------------------------------

    def test_no_cycle(self):

        detector = CycleDetector(self.graph)

        self.assertFalse(
            detector.detect_cycle()
        )

    def test_cycle_exists(self):

        self.graph.add_edge("ML101", "PY101")

        detector = CycleDetector(self.graph)

        self.assertTrue(
            detector.detect_cycle()
        )

    # ------------------------------
    # Path Finder Tests
    # ------------------------------

    def test_learning_path(self):

        finder = PathFinder(self.graph)

        path = finder.find_learning_path(
            "PY101",
            "ML101"
        )

        self.assertEqual(
            path,
            [
                "PY101",
                "PY201",
                "PY301",
                "ML101"
            ]
        )


if __name__ == "__main__":
    unittest.main()