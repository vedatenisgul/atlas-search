from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

class AtlasHTMLParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = set()
        self.text_chunks = []
        self._in_script_or_style = False
        self._in_title = False
        self.page_title = ""
        self._in_p = False
        self._skip_tags = 0
        self.snippet_chunks = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._in_script_or_style = True
        if tag == 'title':
            self._in_title = True
        if tag == 'p':
            self._in_p = True
        if tag in ('nav', 'header', 'footer', 'a'):
            self._skip_tags += 1
            
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and value:
                    # Resolve relative URLs
                    full_url = urljoin(self.base_url, value)
                    
                    # Filter out non-http protocols (e.g., javascript:, mailto:) and fragments
                    parsed = urlparse(full_url)
                    if parsed.scheme in ('http', 'https'):
                        clean_url = full_url.split('#')[0]
                        self.links.add(clean_url)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._in_script_or_style = False
        if tag == 'title':
            self._in_title = False
        if tag == 'p':
            self._in_p = False
        if tag in ('nav', 'header', 'footer', 'a'):
            if self._skip_tags > 0:
                self._skip_tags -= 1

    def handle_data(self, data):
        if self._in_title:
            self.page_title += data.strip() + " "
        elif not self._in_script_or_style:
            stripped = data.strip()
            if stripped:
                self.text_chunks.append(stripped)
                if self._in_p and self._skip_tags == 0:
                    self.snippet_chunks.append(stripped)

    def get_links(self):
        """Returns a list of all normalized and valid outgoing links found."""
        return list(self.links)

    def get_text(self):
        """Returns a single string composed of all visible text node extracts."""
        return " ".join(self.text_chunks)
        
    def get_title(self):
        """Returns the extracted native page title securely."""
        return self.page_title.strip()
        
    def get_snippet(self):
        """Returns the intelligent paragraph-level DOM snippet cleanly securely natively."""
        snip = " ".join(self.snippet_chunks).strip()
        if not snip:
            snip = " ".join(self.text_chunks).strip()
        snip = " ".join(snip.split())
        return snip[:200]
