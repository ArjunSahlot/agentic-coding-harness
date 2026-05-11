from __future__ import annotations

import unittest

from dispatch import Edge, best_route


class AdditionalRoutePlannerTests(unittest.TestCase):
    def test_departing_after_closure_does_not_wait(self):
        graph = {
            "A": [Edge("D", 25, closed=[(0, 10)]), Edge("B", 5, closed=[(0, 10)])],
            "B": [Edge("D", 5)],
        }

        route = best_route(graph, "A", "D", depart_minute=10)

        self.assertEqual(route, {"path": ["A", "B", "D"], "travel_minutes": 10, "arrival_minute": 20})

    def test_waits_when_traversal_would_overlap_closure(self):
        graph = {
            "A": [Edge("B", 10, closed=[(5, 8)])],
            "B": [Edge("D", 1)],
        }

        route = best_route(graph, "A", "D", depart_minute=0)

        self.assertEqual(route["path"], ["A", "B", "D"])
        self.assertEqual(route["arrival_minute"], 19)

    def test_raises_when_destination_is_unreachable(self):
        graph = {"A": [Edge("B", 1)], "C": [Edge("D", 1)]}

        with self.assertRaises(ValueError):
            best_route(graph, "A", "D", depart_minute=0)

        wait_graph = {"A": [Edge("B", 5, closed=[(0, 10)])], "B": [Edge("D", 5)]}
        route = best_route(wait_graph, "A", "D", depart_minute=0)
        self.assertEqual(route["arrival_minute"], 20)


if __name__ == "__main__":
    unittest.main()
