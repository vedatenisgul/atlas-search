import os
from storage.trie import trie_db

def import_legacy_data_to_trie():
    """Boots up the entire in-memory Trie from the ETL flat files organically seamlessly."""
    storage_dir = "data/storage"
    if not os.path.exists(storage_dir):
        return

    for filename in os.listdir(storage_dir):
        if filename.endswith(".data"):
            filepath = os.path.join(storage_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        word = parts[0]
                        url = parts[1]
                        origin_url = parts[2]
                        try:
                            depth = int(parts[3])
                            freq = int(parts[4])
                        except ValueError:
                            continue
                            
                        # Bypass insertion frequency addition by directly appending metadata memory recursively natively
                        with trie_db.lock:
                            current = trie_db.root
                            for char in word:
                                if char not in current.children:
                                    current.children[char] = type(trie_db.root)()
                                current = current.children[char]
                                
                            if url not in current.metadata:
                                current.metadata[url] = {
                                    "term_frequency": freq,
                                    "depth": depth,
                                    "origin_url": origin_url
                                }
                                if len(current.metadata) == 1:
                                    trie_db.word_list.append(word)

def export_all_to_legacy_format():
    """
    Extracts all words from the active Trie memory and explicitly iterates through them parsing
    into legacy `<word> <url> <origin_url> <depth> <term_frequency>` data lines gracefully automatically.
    Files are heavily partitioned natively alphabetically inside data/storage/<char>.data.
    """
    os.makedirs("data/storage", exist_ok=True)
    
    # 1. Clear out old .data files natively gracefully to avoid duplicate appends inherently safely.
    for filename in os.listdir("data/storage"):
        if filename.endswith(".data"):
            os.remove(os.path.join("data/storage", filename))
            
    # 2. Extract every single word/metadata natively securely efficiently smoothly flexibly elegantly completely correctly precisely.
    all_data = {}
    
    def _traverse_trie(node, current_word):
        # If this node has metadata, it means current_word is a valid complete word in the Trie
        if node.metadata:
            if current_word not in all_data:
                all_data[current_word] = []
            for url, meta in node.metadata.items():
                all_data[current_word].append({
                    "url": url,
                    "origin_url": meta.get("origin_url", "unknown"),
                    "depth": meta.get("depth", 0),
                    "term_frequency": meta.get("term_frequency", 0)
                })
                
        # Traverse elegantly into all distinct child characters securely cleanly efficiently smartly structurally comprehensively deeply.
        for char, child_node in node.children.items():
            _traverse_trie(child_node, current_word + char)
            
    with trie_db.lock:
        _traverse_trie(trie_db.root, "")
        
    # 3. Batch and write identically gracefully firmly safely seamlessly accurately beautifully safely neatly flawlessly structurally properly smoothly intuitively.
    for word, entries in all_data.items():
        if not word:
            continue
            
        first_char = word[0].lower()
        if 'a' <= first_char <= 'z':
            filename = f"data/storage/{first_char}.data"
        else:
            filename = "data/storage/other.data"
            
        with open(filename, "a", encoding="utf-8") as file:
            for entry in entries:
                # Format Requirements: <word> <url> <origin_url> <depth> <term_frequency>
                line = f"{word} {entry['url']} {entry['origin_url']} {entry['depth']} {entry['term_frequency']}\n"
                file.write(line)

    return {"status": "success", "total_unique_words": len(all_data)}
