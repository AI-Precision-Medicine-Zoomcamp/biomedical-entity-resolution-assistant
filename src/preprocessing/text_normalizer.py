import re
import unicodedata

def normalize_unicode(text: str) -> str:
    """
    Normalizes Unicode characters to NFKD form and converts to ASCII by stripping accents.
    """
    if not isinstance(text, str):
        return ""
    # Normalize to decomposition form to separate accents, then encode to ascii and decode
    normalized = unicodedata.normalize('NFKD', text)
    return normalized.encode('ascii', 'ignore').decode('utf-8')

def clean_text(text: str) -> str:
    """
    Standard normalization: lowercase, strip, and normalize whitespaces.
    """
    if not isinstance(text, str):
        return ""
    text = normalize_unicode(text)
    text = text.lower().strip()
    # Replace multiple whitespaces/tabs/newlines with a single space
    text = re.sub(r'\s+', ' ', text)
    return text

def remove_punctuation(text: str, replace_with_space: bool = True) -> str:
    """
    Removes punctuation. 
    If replace_with_space is True, replaces characters like hyphens/underscores/slashes with a space.
    Otherwise, removes them entirely.
    """
    text = clean_text(text)
    if replace_with_space:
        # Replace hyphens, underscores, slashes, and other connector punctuation with space
        text = re.sub(r'[-_/\\]', ' ', text)
    # Remove all other non-alphanumeric characters except space
    text = re.sub(r'[^\w\s]', '', text)
    # Re-normalize spaces in case we introduced duplicates
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def generate_normalized_variants(text: str) -> list[str]:
    """
    Generates multiple normalized variants for a term to maximize matching recall.
    For example: "HER-1" -> ["her 1", "her1", "her-1"]
    """
    cleaned = clean_text(text)
    if not cleaned:
        return []
        
    variants = {cleaned}
    
    # Variant 1: Replace hyphens/underscores/slashes with spaces
    v1 = re.sub(r'[-_/\\]', ' ', cleaned)
    v1 = re.sub(r'\s+', ' ', v1).strip()
    variants.add(v1)
    
    # Variant 2: Remove hyphens/underscores/slashes entirely
    v2 = re.sub(r'[-_/\\]', '', cleaned)
    variants.add(v2)
    
    # Clean all variants of non-alphanumeric punctuation
    final_variants = set()
    for v in variants:
        # Standard clean
        v_clean_space = re.sub(r'[^\w\s]', '', v)
        v_clean_space = re.sub(r'\s+', ' ', v_clean_space).strip()
        if v_clean_space:
            final_variants.add(v_clean_space)
            
        v_clean_no_space = re.sub(r'[^\w]', '', v).strip()
        if v_clean_no_space:
            final_variants.add(v_clean_no_space)
            
    return sorted(list(final_variants))
