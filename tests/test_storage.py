import unittest
import os
import shutil
from storage.nosql import NoSQLStore
from storage.trie import trie_db, TrieNode
from storage.exporter import export_all_to_legacy_format, import_legacy_data_to_trie

class TestNoSQLStoreSave(unittest.TestCase):
    def setUp(self):
        self.db = NoSQLStore(filename="/tmp/test_nosql_save.json")

    def tearDown(self):
        self.db.running = False
        if os.path.exists("/tmp/test_nosql_save.json"):
            os.remove("/tmp/test_nosql_save.json")

    def test_public_save_method_exists(self):
        """db.save() must exist and not raise AttributeError."""
        self.assertTrue(hasattr(self.db, 'save'), "NoSQLStore must have a public save() method.")
        self.db.save()  # Should not raise

    def test_save_persists_to_disk(self):
        """Data saved via save() must be retrievable after reload."""
        self.db.data["jobs"]["test-123"] = {"state": "Completed"}
        self.db.save()
        
        db2 = NoSQLStore(filename="/tmp/test_nosql_save.json")
        db2.running = False
        self.assertIn("test-123", db2.data.get("jobs", {}))
        self.assertEqual(db2.data["jobs"]["test-123"]["state"], "Completed")


class TestNoSQLStoreClearAll(unittest.TestCase):
    def setUp(self):
        self.db = NoSQLStore(filename="/tmp/test_nosql_clear.json")

    def tearDown(self):
        self.db.running = False
        if os.path.exists("/tmp/test_nosql_clear.json"):
            os.remove("/tmp/test_nosql_clear.json")

    def test_clear_all_preserves_full_schema(self):
        """clear_all() must reset all 7 keys, not just 3."""
        self.db.data["jobs"]["j1"] = {"state": "Running"}
        self.db.data["metadata"]["url1"] = {"title": "t"}
        self.db.clear_all()
        
        expected_keys = {"seen_urls", "visited_urls", "crawler_queue", "crawler_logs", "job_history", "jobs", "metadata"}
        self.assertEqual(set(self.db.data.keys()), expected_keys)
        self.assertEqual(self.db.data["jobs"], {})
        self.assertEqual(self.db.data["metadata"], {})


class TestETLExporter(unittest.TestCase):
    def setUp(self):
        with trie_db.lock:
            trie_db.root = TrieNode()
            trie_db.word_list = []
        self.storage_dir = "data/storage"
        if os.path.exists(self.storage_dir):
            shutil.rmtree(self.storage_dir)

    def tearDown(self):
        if os.path.exists(self.storage_dir):
            shutil.rmtree(self.storage_dir)

    def test_export_creates_alphabetical_files(self):
        """Exporter must create a.data for words starting with 'a', etc."""
        trie_db.insert("atlas", "http://test.com", "http://seed.com", 0)
        trie_db.insert("beta", "http://test.com", "http://seed.com", 1)
        
        result = export_all_to_legacy_format()
        self.assertEqual(result["status"], "success")
        self.assertTrue(os.path.exists(os.path.join(self.storage_dir, "a.data")))
        self.assertTrue(os.path.exists(os.path.join(self.storage_dir, "b.data")))

    def test_export_line_format(self):
        """Each line must be: word url origin_url depth term_frequency."""
        trie_db.insert("hello", "http://page.com", "http://origin.com", 2)
        export_all_to_legacy_format()
        
        with open(os.path.join(self.storage_dir, "h.data"), "r") as f:
            line = f.readline().strip()
        
        parts = line.split()
        self.assertEqual(len(parts), 5)
        self.assertEqual(parts[0], "hello")
        self.assertEqual(parts[1], "http://page.com")
        self.assertEqual(parts[2], "http://origin.com")
        self.assertEqual(parts[3], "2")
        self.assertEqual(parts[4], "1")

    def test_import_restores_trie(self):
        """import_legacy_data_to_trie must restore data from exported files."""
        trie_db.insert("restore", "http://r.com", "http://s.com", 1)
        export_all_to_legacy_format()
        
        # Clear Trie
        with trie_db.lock:
            trie_db.root = TrieNode()
            trie_db.word_list = []
        
        # Reimport
        import_legacy_data_to_trie()
        
        results = trie_db.search("restore", exact=True)
        self.assertIn("http://r.com", results)
        self.assertEqual(results["http://r.com"]["term_frequency"], 1)

    def test_non_alpha_words_go_to_other_data(self):
        """Words starting with numbers or symbols should go to other.data."""
        trie_db.insert("123test", "http://num.com", "http://s.com", 0)
        export_all_to_legacy_format()
        self.assertTrue(os.path.exists(os.path.join(self.storage_dir, "other.data")))

if __name__ == '__main__':
    unittest.main()
