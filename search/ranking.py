def rank_results(metadata_dict):
    """
    Given a metadata dictionary of results mapping URL -> Metadata dict,
    sorts and ranks the results prioritizing frequency and depth using the exact math formula.
    
    Returns a sorted list of tuples: (url, metadata)
    """
    ranked_list = []
    
    for url, meta in metadata_dict.items():
        freq = meta.get("term_frequency", 0)
        depth = meta.get("depth", 0)
        
        # Calculate exact formula
        score = (freq * 10) + 1000 - (depth * 5)
        meta["relevance_score"] = score
        
        ranked_list.append((url, meta))
        
    # Sort by score descending
    ranked_list.sort(key=lambda item: item[1]["relevance_score"], reverse=True)
    
    return ranked_list
