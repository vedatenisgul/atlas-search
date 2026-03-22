import threading
import time
import urllib.request
import urllib.error
import urllib.parse
import ssl
import hashlib
from storage.nosql import db
from core.parser import AtlasHTMLParser
from storage.trie import trie_db
import string

def normalize_url(url):
    try:
        # Strip trailing slashes and fragments
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
        normalized = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ''))
        return normalized
    except:
        return url

def index_text(url, origin_url, depth, text):
    if not text:
        return
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    words = text.split()
    for word in words:
        if word:
            trie_db.insert(word, url, origin_url, depth)

class CrawlerWorker(threading.Thread):
    def __init__(self, worker_id, seed_url, max_depth=3, queue_capacity=10000, max_urls=1000, hit_rate=2.0, timeout=10):
        super().__init__()
        self.worker_id = worker_id
        self.seed_url = seed_url
        self.current_url = None
        self.max_depth = max_depth
        self.queue_capacity = queue_capacity
        self.max_urls = max_urls
        self.hit_rate = hit_rate
        self.timeout = timeout
        self.daemon = True
        self.running = True
        self.paused = False
        self.job_state = "Running"
        self.total_visited = 0
        
        # Bypass SSL verification errors gracefully for broad crawling
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def hash_url(self, url):
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    def fetch_url(self, url):
        # Apply encoding for international URLs
        try:
            parsed = urllib.parse.urlsplit(url)
            # Safe quote for path/query, keeping safe chars
            new_path = urllib.parse.quote(parsed.path, safe="/%")
            new_query = urllib.parse.quote(parsed.query, safe="=&%")
            safe_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, new_path, new_query, parsed.fragment))
        except:
            safe_url = url
            
        req = urllib.request.Request(
            safe_url, 
            headers={'User-Agent': 'AtlasBot/1.0 (+http://atlas.local)'}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ctx) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type:
                        return response.read().decode('utf-8', errors='ignore')
        except urllib.error.URLError as e:
            db.log("ERROR", f"Failed to fetch {url}: {e}", self.worker_id, self.worker_id)
        except Exception as e:
            db.log("ERROR", f"Unexpected error on {url}: {e}", self.worker_id, self.worker_id)
        return None

    def run(self):
        self.created_at = getattr(self, "created_at", time.time())
        db.log("INFO", f"Worker initialized", self.worker_id, self.worker_id)
        try:
            while self.running:
                if getattr(self, "paused", False):
                    time.sleep(1)
                    continue
                    
                if self.total_visited >= self.max_urls:
                    self.job_state = "Completed"
                    db.log("INFO", f"Max URLs ({self.max_urls}) reached. Halting gracefully.", self.worker_id, self.worker_id)
                    break
                    
                item = db.dequeue(job_id=self.worker_id)
                if not item:
                    time.sleep(2) # Back-pressure / wait if queue empty
                    if db.queue_size(job_id=self.worker_id) == 0:
                        self.job_state = "Completed"
                        db.log("INFO", f"Queue fully exhausted. Halting gracefully.", self.worker_id, self.worker_id)
                        break
                    continue
                    
                url = item['url']
                depth = item['depth']
                job_id = item['origin_job_id']
                
                self.current_url = url
                
                if depth > self.max_depth:
                    self.current_url = None
                    continue
                    
                url_hash = self.hash_url(url)
                if db.is_visited_and_fresh(url_hash) and depth > 0:
                    self.current_url = None
                    continue
                    
                # Fetch step
                db.log("INFO", f"Crawling {url} at depth {depth}", job_id, self.worker_id)
                html = self.fetch_url(url)
                self.total_visited += 1
                
                # Enforce Hit Rate explicitly natively
                delay = 1.0 / self.hit_rate if self.hit_rate > 0 else 0
                if delay > 0:
                    time.sleep(delay)
                
                # Record visitation and apply TTL (polite delay)
                db.mark_visited(url_hash, url, ttl_seconds=3600)
                
                if html:
                    parser = AtlasHTMLParser(base_url=url)
                    try:
                        parser.feed(html)
                        
                        links = parser.get_links()
                        text = parser.get_text()
                        
                        title = parser.get_title()
                        snippet = parser.get_snippet()
                        
                        with db.lock:
                            db.data.setdefault("metadata", {})[url] = {
                                "title": title,
                                "snippet": snippet
                            }
                        
                        # Push content to Trie natively resolving seed_url origin traces exactly.
                        index_text(url, self.seed_url, depth, text)
                        
                        # Enqueue discovered links natively using queue capacities structurally
                        if depth < self.max_depth:
                            for link in links:
                                norm_link = normalize_url(link)
                                link_hash = self.hash_url(norm_link)
                                if not db.is_visited_and_fresh(link_hash):
                                    db.enqueue(norm_link, depth + 1, job_id, max_capacity=self.queue_capacity)
                                    
                    except Exception as e:
                        db.log("ERROR", f"HTML parsing error on {url}: {e}", job_id, self.worker_id)
                        
                self.current_url = None
        except Exception as e:
            self.job_state = "Error"
            db.log("ERROR", f"Fatal worker exception: {e}", self.worker_id, self.worker_id)
        finally:
            self.running = False
            self.ended_at = time.time()
            self.current_url = None
            if self.job_state == "Running":
                self.job_state = "Stopped"

    def stop(self):
        self.running = False
