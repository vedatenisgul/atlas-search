import unittest
from search.ranking import rank_results

class TestRelevancyScoring(unittest.TestCase):
    def test_exact_formula(self):
        """Verify score = (frequency * 10) + 1000 - (depth * 5)."""
        aggregated = {
            "http://a.com": {"term_frequency": 5, "depth": 2, "origin_url": "http://seed.com"},
            "http://b.com": {"term_frequency": 10, "depth": 0, "origin_url": "http://seed.com"},
            "http://c.com": {"term_frequency": 1, "depth": 5, "origin_url": "http://seed.com"},
        }
        ranked = rank_results(aggregated)
        
        # b.com: (10*10) + 1000 - (0*5) = 1100
        # a.com: (5*10) + 1000 - (2*5) = 1040
        # c.com: (1*10) + 1000 - (5*5) = 985
        self.assertEqual(ranked[0][0], "http://b.com")
        self.assertEqual(ranked[0][1]["relevance_score"], 1100)
        self.assertEqual(ranked[1][0], "http://a.com")
        self.assertEqual(ranked[1][1]["relevance_score"], 1040)
        self.assertEqual(ranked[2][0], "http://c.com")
        self.assertEqual(ranked[2][1]["relevance_score"], 985)

    def test_descending_sort_order(self):
        """Results must be sorted descending by relevance_score."""
        aggregated = {
            "http://low.com": {"term_frequency": 1, "depth": 10, "origin_url": "http://s.com"},
            "http://high.com": {"term_frequency": 50, "depth": 0, "origin_url": "http://s.com"},
        }
        ranked = rank_results(aggregated)
        scores = [meta["relevance_score"] for _, meta in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_empty_input(self):
        """Rank results on empty input should return empty list."""
        self.assertEqual(rank_results({}), [])

if __name__ == '__main__':
    unittest.main()
