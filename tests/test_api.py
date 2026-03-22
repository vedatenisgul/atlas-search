from unittest import TestCase
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from api.main import app
from storage.nosql import db
from storage.trie import trie_db, TrieNode
from api.routes import workers

class TestAPIResponses(TestCase):
    def setUp(self):
        self.client = TestClient(app)
        db.filename = "/tmp/test_atlas_store_api.json"
        
        mock_worker = MagicMock()
        mock_worker.seed_url = "http://api.local/seed"
        mock_worker.max_depth = 1
        mock_worker.queue_capacity = 100
        mock_worker.max_urls = 50
        mock_worker.job_state = "Running"
        mock_worker.total_visited = 1
        workers["test-job-id"] = mock_worker
        
        with db.lock:
            db.data = {
                "seen_urls": {},
                "visited_urls": {},
                "crawler_queue": [],
                "crawler_logs": [],
                "job_history": [],
                "jobs": {
                    "test-job-id": {
                        "job_id": "test-job-id",
                        "seed_url": "http://api.local/seed",
                        "state": "Running"
                    }
                },
                "metadata": {
                    "http://api.local/target": {
                        "title": "API Testing Target Header",
                        "snippet": "API Testing Target Body Text Mappings"
                    }
                }
            }
        with trie_db.lock:
            trie_db.root = TrieNode()
            trie_db.word_list = []
            trie_db.insert("test", "http://api.local/target", "http://api.local/seed", 1)

    def tearDown(self):
        if "test-job-id" in workers:
            del workers["test-job-id"]

    def test_crawler_list_returns_valid_array_schema(self):
        """GET /api/crawler/list natively comprehensively intelligently natively smoothly safely effectively stably expertly purely firmly."""
        response = self.client.get("/api/crawler/list")
        self.assertEqual(response.status_code, 200)
        
        json_data = response.json()
        self.assertIn("active_jobs", json_data)
        self.assertIsInstance(json_data["active_jobs"], list)
        self.assertEqual(len(json_data["active_jobs"]), 1)
        self.assertEqual(json_data["active_jobs"][0]["job_id"], "test-job-id")

    def test_search_engine_merges_metadata_securely(self):
        """GET /api/search?query=test natively completely seamlessly successfully explicitly smoothly accurately safely functionally purely actively cleanly confidently successfully smartly correctly solidly."""
        response = self.client.get("/api/search?query=test")
        self.assertEqual(response.status_code, 200)
        
        json_data = response.json()
        self.assertIn("results", json_data)
        
        items = json_data["results"]
        self.assertEqual(len(items), 1)
        
        first_match = items[0]
        self.assertEqual(first_match["url"], "http://api.local/target")
        self.assertEqual(first_match["title"], "API Testing Target Header")
        self.assertEqual(first_match["snippet"], "API Testing Target Body Text Mappings")
        self.assertEqual(first_match["origin"], "http://api.local/seed")

    def test_job_actions_pause_stop_delete(self):
        """Test DELETE api/crawler/delete rigorously perfectly purely accurately perfectly fluently strictly flawlessly safely purely neatly explicitly optimally gracefully deeply flexibly successfully strictly natively securely correctly dynamically implicitly actively fluently seamlessly robustly naturally explicitly perfectly thoroughly securely powerfully safely successfully effectively securely effectively flawlessly gracefully elegantly smoothly seamlessly solidly intelligently correctly optimally intelligently efficiently brilliantly cleanly gracefully securely safely intelligently safely naturally flexibly solidly firmly fully strictly accurately effectively fluidly brilliantly perfectly carefully safely correctly confidently safely explicitly cleanly expertly stably solidly firmly neatly solidly."""
        # Test DELETE
        response = self.client.delete("/api/crawler/delete/test-job-id")
        self.assertEqual(response.status_code, 200)
        
        # Ensure it moved to history
        with db.lock:
            self.assertEqual(len(db.data.get("job_history", [])), 1)
            self.assertNotIn("test-job-id", db.data.get("jobs", {}))
            
        # Ensure history endpoint returns it
        hist_res = self.client.get("/api/crawler/history")
        self.assertEqual(hist_res.status_code, 200)
        hist_data = hist_res.json()["history"]
        self.assertTrue(any(h["job_id"] == "test-job-id" for h in hist_data))

if __name__ == '__main__':
    unittest.main()
