import string
from storage.trie import trie_db
from search.ranking import rank_results

class SearchEngine:
    @staticmethod
    def query(search_term, limit=10, offset=0):
        # 1. Clean query input stripping casing and punctuation efficiently natively.
        tr_map = { ord('I'): 'ı', ord('İ'): 'i', ord('Ü'): 'ü', ord('Ş'): 'ş', ord('Ö'): 'ö', ord('Ç'): 'ç', ord('Ğ'): 'ğ' }
        search_term = search_term.translate(tr_map).lower().strip()
        search_term = search_term.translate(str.maketrans('', '', string.punctuation))
        words = search_term.split()
        
        if not words:
            return []
            
        # 2. Extract mappings across the Trie
        aggregated = {}
        for word in words:
            word_matches = trie_db.search(word, exact=True)
            for url, meta in word_matches.items():
                if url not in aggregated:
                    aggregated[url] = meta.copy()
                else:
                    aggregated[url]["term_frequency"] += meta["term_frequency"]
                    aggregated[url]["depth"] = min(aggregated[url]["depth"], meta["depth"])
                    
        # 3. Apply Relevancy/Ranking Algorithm
        ranked = rank_results(aggregated)
        
        # 4. Filter with pagination constraint mappings
        total = len(ranked)
        paginated = ranked[offset : offset + limit]
        
        # 5. Format to tuple sequence: (relevant_url, origin_url, depth, frequency, relevance_score)
        results = []
        for url, meta in paginated:
            results.append((url, meta["origin_url"], meta["depth"], meta["term_frequency"], meta.get("relevance_score", 0)))
            
        return {"total": total, "items": results}

    @staticmethod
    def get_random_word():
        return trie_db.get_random_word()
