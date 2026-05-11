from __future__ import annotations

import unittest

from dispatch import Edge, best_route


class RoutePlannerTests(unittest.TestCase):
    def test_chooses_fastest_route_not_fewest_hops(self):
        graph = {
            "A": [Edge("D", 25), Edge("B", 10), Edge("C", 3)],
            "B": [Edge("D", 10)],
            "C": [Edge("D", 30)],
        }

        route = best_route(graph, "A", "D", depart_minute=0)

        self.assertEqual(route, {"path": ["A", "B", "D"], "travel_minutes": 20, "arrival_minute": 20})

    def test_waits_for_closed_edge_when_it_is_still_best(self):
        graph = {
            "A": [Edge("B", 5, closed=[(0, 10)]), Edge("C", 50)],
            "B": [Edge("D", 5)],
            "C": [Edge("D", 5)],
        }

        route = best_route(graph, "A", "D", depart_minute=0)

        self.assertEqual(route["path"], ["A", "B", "D"])
        self.assertEqual(route["travel_minutes"], 20)
        self.assertEqual(route["arrival_minute"], 20)

    def test_chooses_alternate_when_closure_makes_direct_path_slower(self):
        graph = {
            "A": [Edge("B", 10, closed=[(5, 40)]), Edge("C", 15)],
            "B": [Edge("D", 5)],
            "C": [Edge("D", 10)],
        }

        route = best_route(graph, "A", "D", depart_minute=0)

        self.assertEqual(route["path"], ["A", "C", "D"])
        self.assertEqual(route["arrival_minute"], 25)

        weighted = {"A": [Edge("D", 30), Edge("B", 5)], "B": [Edge("D", 5)]}
        route = best_route(weighted, "A", "D", depart_minute=0)
        self.assertEqual(route["path"], ["A", "B", "D"])
        self.assertEqual(route["arrival_minute"], 10)


if __name__ == "__main__":
    unittest.main()
