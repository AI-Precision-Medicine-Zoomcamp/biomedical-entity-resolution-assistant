import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

class ConfidenceEstimator:
    """
    Computes a normalized confidence score (0.0 to 1.0) for a resolved candidate
    based on lexical, vector, match type, and source metadata.
    """
    def __init__(self):
        pass

    def estimate_confidence(self, mention: str, candidate: dict) -> float:
        """
        Estimates the resolution confidence.
        
        Args:
            mention (str): Extracted mention.
            candidate (dict): The resolved entity candidate.
            
        Returns:
            float: Normalized confidence score between 0.0 and 1.0.
        """
        if not candidate:
            return 0.0

        mention_clean = mention.strip().lower()
        canonical_clean = candidate["canonical_name"].strip().lower()
        
        # 1. Base score derived from matching type
        retrieval_method = candidate.get("retrieval_method", "unknown")
        
        # Start with a base score
        if "id_match" in retrieval_method:
            base_score = 0.98
        elif "lexical" in retrieval_method:
            base_score = 0.90
        elif "vector" in retrieval_method:
            # Vector-only similarity starts slightly lower since it is semantic/approximate
            base_score = 0.75
        else:
            base_score = 0.70

        # 2. Check for exact name mapping
        exact_match = (mention_clean == canonical_clean)
        if not exact_match and candidate.get("synonyms"):
            syns = [s.strip().lower() for s in candidate["synonyms"].split("|")]
            if mention_clean in syns:
                exact_match = True

        # Apply exact match bonus
        if exact_match:
            base_score += 0.10
        else:
            # Penalize slightly if there is no exact string match anywhere
            base_score -= 0.10

        # 3. Consider lexical similarity
        lex_sim = candidate.get("lexical_similarity", 0.0)
        if lex_sim > 0:
            # Adjust score based on lexical similarity
            base_score = (base_score * 0.7) + (lex_sim * 0.3)

        # 4. Final bounds check
        confidence = min(max(base_score, 0.0), 1.0)
        return round(confidence, 2)
