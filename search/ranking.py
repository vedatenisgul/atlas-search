def rank_results(metadata_dict):
    """
    Given a metadata dictionary of results mapping URL -> Metadata dict,
    sorts and ranks the results prioritizing primarily term frequency, then depth.
    
    Returns a sorted list of tuples: (url, metadata)
    """
    items = list(metadata_dict.items())
    
    # Sort Key computes dynamically: 
    # Tuple ordering dictates primary sort condition, then secondary
    # Frequency is negated to sort descending. Depth sorts ascending naturally.
    def sort_key(item):
        url, meta = item
        return (-meta.get("term_frequency", 0), meta.get("depth", 999))
        
    items.sort(key=sort_key)
    return items
