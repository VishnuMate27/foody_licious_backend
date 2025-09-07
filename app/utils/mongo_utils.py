def flatten(d, parent_key="", sep="."):
    """
    Convert nested dicts into MongoDB dot-notation dict.
    Arrays/lists are kept as-is (not broken into dotted paths).
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict) and v is not None:
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
