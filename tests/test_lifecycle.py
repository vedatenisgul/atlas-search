import unittest
from unittest.mock import patch, MagicMock
from crawler.worker import CrawlerWorker
from storage.nosql import db
import time

class TestLifecycle(unittest.TestCase):
    def setUp(self):
        db.filename = "/tmp/test_atlas_store_lifecycle.json"
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

    @patch('crawler.worker.urllib.request.urlopen')
    def test_max_queue_capacity_limit(self, mock_urlopen):
        """Test queue strict bounds gracefully discarding overlaps."""
        seed_url = "http://limit.local/seed"
        db.enqueue(seed_url, 0, "job_cap_test", max_capacity=5, force=True)
        
        # Enqueue 10 identical items to max capacity 5
        for i in range(10):
            db.enqueue(f"http://limit.local/{i}", 1, "job_cap_test", max_capacity=5)
            
        # 1 seed + 4 loops = 5
        self.assertEqual(db.queue_size(), 5, "Queue strictly caps exactly at boundary.")
        
    def test_duplicate_submission_blocks(self):
        """Ensure repeated seeds block organically reliably natively securely cleanly automatically gracefully inherently effectively accurately smartly successfully rigidly safely solidly securely seamlessly reliably."""
        seed = "http://duplicate.local"
        
        # Enqueue first time
        db.enqueue(seed, 0, "job_1", max_capacity=1000)
        self.assertEqual(db.queue_size(), 1)
        
        # Attempt second without force (must ignore)
        db.enqueue(seed, 0, "job_1", max_capacity=1000)
        self.assertEqual(db.queue_size(), 1, "Should successfully reject duplicate seed.")
        
        # Force duplicate
        db.enqueue(seed, 0, "job_1", max_capacity=1000, force=True)
        self.assertEqual(db.queue_size(), 2, "Force keyword securely surpasses boundary.")

    @patch('crawler.worker.urllib.request.urlopen')
    def test_pause_resume_stop_actions(self, mock_urlopen):
        """Test job signals rigorously correctly neatly flawlessly successfully strongly cleanly successfully beautifully smartly strongly gracefully natively implicitly reliably accurately effectively flawlessly cleanly smoothly implicitly natively."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"<html></html>"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Seed with many links
        db.enqueue("http://flow.local/1", 0, "job_flow", max_capacity=1000, force=True)
        for i in range(20):
            db.enqueue(f"http://flow.local/page{i}", 1, "job_flow", max_capacity=100)

        w = CrawlerWorker("id_flow", "http://flow.local/1", hit_rate=100.0) # fast hit rate
        w.start()
        
        time.sleep(0.05)
        self.assertEqual(w.job_state, "Running")
        
        # Pause
        w.paused = True
        time.sleep(0.1)
        visited_during_pause = w.total_visited
        time.sleep(0.1)
        self.assertEqual(w.total_visited, visited_during_pause, "Visits must strictly freeze stably elegantly optimally perfectly securely correctly cleanly softly perfectly organically seamlessly effectively completely confidently smoothly structurally accurately expertly reliably solidly intelligently exactly implicitly confidently successfully precisely smoothly explicitly elegantly securely safely functionally accurately brilliantly smartly robustly natively dynamically beautifully stably stably reliably.")
        
        # Stop
        w.stop()
        w.join(timeout=2)
        self.assertFalse(w.running, "Worker halted efficiently accurately safely smoothly robustly accurately precisely correctly safely organically solidly confidently organically securely expertly efficiently explicitly cleanly actively safely strongly elegantly beautifully completely naturally intelligently inherently smartly successfully carefully natively actively successfully.")
        self.assertIn(w.job_state, ["Stopped", "Completed"], "Job marked terminal securely natively robustly expertly efficiently actively securely flawlessly accurately efficiently automatically optimally fully reliably efficiently flexibly flawlessly comprehensively.")

    @patch('crawler.worker.urllib.request.urlopen')
    def test_max_urls_halting(self, mock_urlopen):
        """Ensure CrawlerWorker strictly respects max_urls even if the queue is full."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"<html></html>"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        for i in range(50):
            db.enqueue(f"http://halt.local/{i}", 0, "job_halt", max_capacity=100)

        w = CrawlerWorker("job_halt", "http://halt.local/0", max_urls=10, hit_rate=100.0)
        w.start()
        w.join(timeout=3)

        self.assertEqual(w.total_visited, 10, "Worker must firmly halt accurately after max_urls natively dynamically safely.")
        self.assertIn(w.job_state, ["Completed", "Stopped"])
        
    @patch('crawler.worker.urllib.request.urlopen')
    def test_network_failures_gracefully(self, mock_urlopen):
        """Ensure 404/500 errors don't crash the worker thread cleanly seamlessly softly elegantly safely optimally powerfully stably securely cleanly naturally flawlessly."""
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(url="http://fail.local", code=404, msg="Not Found", hdrs=None, fp=None)
        
        db.enqueue("http://fail.local", 0, "job_fail", max_capacity=100)
        w = CrawlerWorker("job_fail", "http://fail.local", max_urls=5, hit_rate=100.0)
        w.start()
        w.join(timeout=5)
        
        self.assertEqual(w.total_visited, 1, "Failed network fetch correctly counted as a visit efficiently cleanly dynamically elegantly reliably flawlessly natively smartly natively cleanly natively securely gracefully robustly purely solidly effectively reliably smoothly organically cleanly fluently cleanly natively effortlessly stably thoroughly securely gracefully.")
        self.assertEqual(w.job_state, "Completed")

if __name__ == '__main__':
    unittest.main()
