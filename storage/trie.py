import threading
import random

class TrieNode:
    __slots__ = ['children', 'metadata']
    def __init__(self):
        self.children = {}
        # Mapping: url -> {"term_frequency": int, "depth": int, "origin_url": str}
        self.metadata = {}

class AtlasTrie:
    def __init__(self):
        self.root = TrieNode()
        # RLock allows the same thread to acquire the lock multiple times, and protects concurrent edits
        self.lock = threading.RLock()
        self.word_list = [] 

    def reset(self):
        with self.lock:
            self.root = TrieNode()
            self.word_list = []

    def insert(self, word, url, origin_url, depth):
        if not word:
            return
            
        with self.lock:
            current = self.root
            for char in word:
                if char not in current.children:
                    current.children[char] = TrieNode()
                current = current.children[char]
            
            if url not in current.metadata:
                current.metadata[url] = {
                    "term_frequency": 0,
                    "depth": depth,
                    "origin_url": origin_url
                }
                
                # If this is the absolute first time the word is added to the system, track it
                if current.metadata[url]["term_frequency"] == 0 and len(current.metadata) == 1:
                    self.word_list.append(word)
                    
            current.metadata[url]["term_frequency"] += 1
            
            # If the same word is found at a shallower depth on the same page update the depth natively
            if depth < current.metadata[url]["depth"]:
                current.metadata[url]["depth"] = depth

    def search(self, word_or_prefix, exact=True):
        """
        Retrieves matching nodes synchronously. Returns a dictionary mapping URLs to metadata.
        """
        with self.lock:
            current = self.root
            for char in word_or_prefix:
                if char not in current.children:
                    return {}
                current = current.children[char]
            
            if exact:
                return current.metadata.copy()
            else:
                return self._collect_subtree(current)

    def _collect_subtree(self, node):
        results = {}
        for url, meta in node.metadata.items():
            if url not in results:
                results[url] = meta.copy()
            else:
                results[url]["term_frequency"] += meta["term_frequency"]
                
        for child_node in node.children.values():
            child_results = self._collect_subtree(child_node)
            for url, meta in child_results.items():
                if url not in results:
                    results[url] = meta.copy()
                else:
                    results[url]["term_frequency"] += meta["term_frequency"]
        return results

    def get_random_word(self):
        with self.lock:
            if not self.word_list:
                return "atlas" # Default fallback
            return random.choice(self.word_list)

# Global singleton for search and workers
trie_db = AtlasTrie()
