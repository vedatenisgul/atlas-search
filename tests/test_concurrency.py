import unittest
from unittest.mock import patch, MagicMock
from crawler.worker import CrawlerWorker, normalize_url
from storage.nosql import db
from storage.trie import trie_db, TrieNode
import threading
import time

class TestConcurrency(unittest.TestCase):
    def setUp(self):
        db.filename = "/tmp/test_atlas_store_concurrency.json"
        # Reset database state before each test
        with db.lock:
            db.data = {
                "seen_urls": {},
                "visited_urls": {},
                "crawler_queue": [],
                "crawler_logs": [],
                "job_history": [],
                "jobs": {},
                "metadata": {}
            }
        with trie_db.lock:
            trie_db.root = TrieNode()
            trie_db.word_list = []

    @patch('crawler.worker.urllib.request.urlopen')
    def test_multi_threaded_crawling(self, mock_urlopen):
        """Test multiple crawlers resolving simultaneously without corrupting file writes."""
        # Create a mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers.get.return_value = 'text/html; charset=utf-8'
        html_content = '''
        <html><head><title>Atlas Test Page</title></head>
        <body>
            <p>Atlas is incredibly fast.</p>
            <p>Apple devices enjoy Apple software.</p>
            <a href="http://atlas.local/page2">Link</a>
        </body></html>
        '''.encode('utf-8')
        mock_response.read.return_value = html_content
        
        # mock_urlopen acts as a context manager
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Prepare 3 crawlers pointing to the same seed (but bypass initial seen_urls dynamically for the test)
        seed_url = "http://atlas.local/seed"
        db.enqueue(seed_url, 0, "job_test_sync", max_capacity=1000, force=True)
        # Push extra items to keep them strictly overlapping
        db.enqueue("http://atlas.local/pageA", 0, "job_test_sync", max_capacity=1000, force=True)
        db.enqueue("http://atlas.local/pageB", 0, "job_test_sync", max_capacity=1000, force=True)
        
        workers = []
        for i in range(3):
            w = CrawlerWorker("job_test_sync", seed_url, max_depth=1, max_urls=2, hit_rate=100.0)
            workers.append(w)
        
        for w in workers:
            w.start()
            
        for w in workers:
            w.join(timeout=5)
            # Ensure they all stopped correctly!
            self.assertFalse(w.running, f"Worker {w.worker_id} did not stop gracefully.")

        # Assert data structures aren't corrupted
        with db.lock:
            visited_count = len(db.data.get("visited_urls", {}))
            self.assertGreaterEqual(visited_count, 3, "Expected at least 3 distinct fetch steps.")

            # Validate shared state indexing properly
            apples = trie_db.search("apple", exact=True)
            self.assertTrue(len(apples) > 0, "Trie must securely track the word Apple cleanly.")
            
            # Since multiple threads might parse identical or mock pages,
            # frequencies should incrementally sum correctly in Trie nodes without race conditions!
            
            # Check Metadata integrity
            meta = db.data.get("metadata", {})
            self.assertIn(seed_url, meta, "Metadata for seed must be safely registered.")

    @patch('crawler.worker.urllib.request.urlopen')
    def test_queue_depletion_race_condition(self, mock_urlopen):
        """Test multiple workers contending for the final few queue items safely without deadlocking."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"<html></html>"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Enqueue exactly 5 items
        for i in range(5):
            db.enqueue(f"http://deplete.local/{i}", 0, "job_test_sync", max_capacity=100)
            
        # Start 10 crawlers simultaneously to fight for those 5 items
        workers = []
        for i in range(10):
            w = CrawlerWorker("job_test_sync", "http://deplete.local/0", max_urls=5, hit_rate=100.0)
            workers.append(w)
            
        for w in workers:
            w.start()
            
        for w in workers:
            w.join(timeout=3)
            self.assertFalse(w.running, "Worker must stop intelligently once queue is empty without hanging.")
            
        # The sum of total visits across all workers should be exactly 5.
        total_visits_sum = sum(w.total_visited for w in workers)
        self.assertEqual(total_visits_sum, 5, "Exactly 5 queue items should have been processed safely across all threads natively organically.")
            
if __name__ == '__main__':
    unittest.main()
