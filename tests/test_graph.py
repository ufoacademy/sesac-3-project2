import unittest

from src.app import graph


class GraphTopologyTest(unittest.TestCase):
    def test_supervisor_contains_parallel_subagent_branches(self):
        node_names = set(graph.nodes)

        self.assertIn("company_subagent", node_names)
        self.assertIn("candidate_subagent", node_names)
        self.assertIn("join_subagents", node_names)
        self.assertIn("calculate_fit", node_names)


if __name__ == "__main__":
    unittest.main()
