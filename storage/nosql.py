import json
import os
import threading
import time

class NoSQLStore:
    def __init__(self, filename="atlas_store.json", sync_interval=5.0):
        self.filename = filename
        self.lock = threading.Lock()
        self.sync_interval = sync_interval
        self.data = {
            "seen_urls": {},
            "visited_urls": {},
            "crawler_queue": [],
            "crawler_logs": [],
            "job_history": [],
            "jobs": {},
            "metadata": {}
        }
        self._load()
        
        # Start a background thread to periodically persist data to disk safely
        self.running = True
        self.sync_thread = threading.Thread(target=self._periodic_sync, daemon=True)
        self.sync_thread.start()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    loaded = json.load(f)
                    self.data["seen_urls"] = loaded.get("seen_urls", {})
                    self.data["visited_urls"] = loaded.get("visited_urls", {})
                    self.data["crawler_queue"] = loaded.get("crawler_queue", [])
                    self.data["crawler_logs"] = loaded.get("crawler_logs", [])
                    self.data["job_history"] = loaded.get("job_history", [])
                    self.data["jobs"] = loaded.get("jobs", {})
                    self.data["metadata"] = loaded.get("metadata", {})
            except Exception:
                pass

    def _save(self):
        # Obtain lock only to make a snapshot copy in memory
        with self.lock:
            snapshot = {
                "seen_urls": self.data.get("seen_urls", {}).copy(),
                "visited_urls": self.data["visited_urls"].copy(),
                "crawler_queue": self.data["crawler_queue"].copy(),
                "crawler_logs": self.data["crawler_logs"].copy(),
                "job_history": self.data.get("job_history", []).copy(),
                "jobs": self.data.get("jobs", {}).copy(),
                "metadata": self.data.get("metadata", {}).copy()
            }
        
        # Write to disk outside the lock to prevent blocking active crawler threads
        temp_file = self.filename + ".tmp"
        try:
            with open(temp_file, 'w') as f:
                json.dump(snapshot, f)
            os.replace(temp_file, self.filename)
        except Exception:
            pass

    def _periodic_sync(self):
        while self.running:
            time.sleep(self.sync_interval)
            self._save()

    def stop(self):
        self.running = False
        self._save()

    def save(self):
        """Public save method for external callers."""
        self._save()

    def clear_all(self):
        with self.lock:
            self.data = {
                "seen_urls": {},
                "visited_urls": {},
                "crawler_queue": [],
                "crawler_logs": [],
                "job_history": [],
                "jobs": {},
                "metadata": {}
            }
        self._save()

    def is_visited_and_fresh(self, url_hash):
        with self.lock:
            if url_hash in self.data["visited_urls"]:
                entry = self.data["visited_urls"][url_hash]
                if time.time() < entry.get("ttl_expires_at", 0):
                    return True
            return False
            
    def mark_visited(self, url_hash, url, ttl_seconds=3600):
        with self.lock:
            self.data["visited_urls"][url_hash] = {
                "url": url,
                "last_crawled_at": time.time(),
                "ttl_expires_at": time.time() + ttl_seconds
            }

    def enqueue(self, url, depth, origin_job_id, max_capacity=10000, force=False):
        with self.lock:
            job_counts = self.data.setdefault("job_queue_counts", {})
            current_sz = job_counts.get(origin_job_id, 0)
            if current_sz >= max_capacity:
                return False
                
            seen = self.data.setdefault("seen_urls", {})
            job_seen = seen.setdefault(origin_job_id, {})
            
            if url in job_seen and not force:
                return False
                
            job_seen[url] = True
            job_counts[origin_job_id] = current_sz + 1
            
            self.data.setdefault("crawler_queue", []).append({
                "url": url,
                "depth": depth,
                "origin_job_id": origin_job_id
            })
            return True
    def dequeue(self, job_id=None):
        with self.lock:
            if not self.data.get("crawler_queue"):
                return None
            queue = self.data["crawler_queue"]
            job_counts = self.data.setdefault("job_queue_counts", {})
            if job_id:
                for i, item in enumerate(queue):
                    if item.get("origin_job_id") == job_id:
                        popped = queue.pop(i)
                        if job_id in job_counts and job_counts[job_id] > 0:
                            job_counts[job_id] -= 1
                        return popped
                return None
                
            popped = queue.pop(0)
            orig = popped.get("origin_job_id")
            if orig in job_counts and job_counts[orig] > 0:
                job_counts[orig] -= 1
            return popped

    def queue_size(self, job_id=None):
        with self.lock:
            if job_id:
                return self.data.get("job_queue_counts", {}).get(job_id, 0)
            return len(self.data.get("crawler_queue", []))
    def log(self, level, message, job_id, worker_node="local"):
        with self.lock:
            self.data["crawler_logs"].append({
                "level": level,
                "message": message,
                "job_id": job_id,
                "worker_node": worker_node,
                "timestamp": time.time()
            })

# Singleton instance to be used across the application
db = NoSQLStore()
