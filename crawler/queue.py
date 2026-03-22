from storage.nosql import db

class CrawlerQueue:
    """
    Abstracts queue operations enforcing job tracking and global back-pressure limits.
    """
    def __init__(self, job_id, max_capacity=10000):
        self.job_id = job_id
        self.max_capacity = max_capacity
        
    def push(self, url, depth):
        # Back-pressure enforcement
        if db.queue_size() >= self.max_capacity:
            db.log("WARN", f"Back-pressure triggered. Max capacity ({self.max_capacity}) reached. Dropping: {url}", self.job_id)
            return False
            
        db.enqueue(url, depth, self.job_id)
        return True
        
    def pop(self):
        return db.dequeue()
        
    def get_size(self):
        return db.queue_size()
