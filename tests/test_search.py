import unittest
from storage.trie import trie_db, TrieNode
from search.engine import SearchEngine

class TestTurkishCaseFolding(unittest.TestCase):
    def setUp(self):
        with trie_db.lock:
            trie_db.root = TrieNode()
            trie_db.word_list = []
        # Index with lowercase Turkish "ilber"
        trie_db.insert("ilber", "http://wiki.tr/ilber", "http://wiki.tr", 1)

    def test_lowercase_query_matches(self):
        """Searching 'ilber' should match the indexed 'ilber'."""
        result = SearchEngine.query("ilber")
        self.assertEqual(result["total"], 1)

    def test_uppercase_turkish_I_matches(self):
        """Searching 'İlber' (Turkish İ) should fold to 'ilber' and match."""
        result = SearchEngine.query("İlber")
        self.assertEqual(result["total"], 1)

    def test_english_uppercase_I_does_not_match(self):
        """Searching 'Ilber' (English I) should fold to 'ılber' (dotless ı), not 'ilber'."""
        result = SearchEngine.query("Ilber")
        # English I maps to ı, so 'Ilber' -> 'ılber', which differs from 'ilber'
        self.assertEqual(result["total"], 0)


class TestSearchDeduplication(unittest.TestCase):
    def setUp(self):
        with trie_db.lock:
            trie_db.root = TrieNode()
            trie_db.word_list = []

    def test_same_url_not_duplicated_in_results(self):
        """Same URL indexed under different words should appear once in results."""
        trie_db.insert("hello", "http://example.com/page1", "http://example.com", 0)
        trie_db.insert("world", "http://example.com/page1", "http://example.com", 0)
        result = SearchEngine.query("hello world")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0][0], "http://example.com/page1")


class TestSearchRelevanceScoreInResults(unittest.TestCase):
    def setUp(self):
        with trie_db.lock:
            trie_db.root = TrieNode()
            trie_db.word_list = []
        trie_db.insert("atlas", "http://atlas.local/home", "http://atlas.local", 0)

    def test_relevance_score_present_in_items(self):
        """Search results should include a non-zero relevance_score."""
        result = SearchEngine.query("atlas")
        self.assertEqual(result["total"], 1)
        # items tuple: (url, origin_url, depth, frequency, relevance_score)
        relevance_score = result["items"][0][4]
        self.assertGreater(relevance_score, 0)

if __name__ == '__main__':
    unittest.main()
