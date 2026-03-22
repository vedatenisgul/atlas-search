import ipaddress
import socket
import re
import time
from urllib.parse import urlparse

def validate_url(url):
    """
    Ensures URL scheme is valid and prevents Server-Side Request Forgery (SSRF)
    by strictly blocking private, loopback, and local network IP addresses.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
        
    hostname = parsed.hostname
    if not hostname:
        return False
        
    try:
        # Resolve hostname to actual IP
        ip_str = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip_str)
        
        # Block malicious internal routing attempts natively
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast:
            return False
    except socket.gaierror:
        # Fail securely if DNS resolution drops
        return False
        
    return True

def sanitize_html_input(text):
    """
    Strips raw malicious scripting sequences and control anomalies natively.
    """
    if not text:
        return ""
    # Strip raw HTML tags defensively using standard regex rules
    clean = re.sub(r'<[^>]+>', '', text)
    # Strip dangerous non-printable ASCII/control characters
    clean = re.sub(r'[\x00-\x1F\x7F]', '', clean)
    return clean.strip()

class RateLimiter:
    """
    Enforces a strict hit_rate boundary per worker executing cycles natively without external dependencies.
    """
    def __init__(self, hit_rate_per_sec=2.0):
        # Minimum idle timeline allowed between consecutive fetches (e.g. 0.5s for 2.0 hits/sec constraint)
        self.interval = 1.0 / hit_rate_per_sec if hit_rate_per_sec > 0 else 0
        self.last_fetch = 0.0

    def wait(self):
        if self.interval <= 0:
            return
            
        elapsed = time.time() - self.last_fetch
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
            
        self.last_fetch = time.time()
