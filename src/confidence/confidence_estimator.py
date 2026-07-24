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
        Estimates the resolution confidence based on the formula:
        confidence = 0.6 * vector_similarity + 0.3 * lexical_similarity + 0.1 * alias_bonus
        
        Args:
            mention (str): Extracted mention.
            candidate (dict): The resolved entity candidate.
            
        Returns:
            float: Normalized confidence score between 0.0 and 1.0.
        """
        if not candidate:
            return 0.0

        vector_sim = candidate.get("vector_similarity", 0.0)
        lexical_sim = candidate.get("lexical_similarity", 0.0)
        alias_bonus = candidate.get("alias_bonus", 0.0)
        
        # If these properties are not in the candidate (e.g. from fallbacks), compute them on the fly
        if "vector_similarity" not in candidate:
            mention_clean = mention.strip().lower()
            canonical_clean = candidate["canonical_name"].strip().lower()
            exact_match = (mention_clean == canonical_clean)
            if not exact_match and candidate.get("synonyms"):
                syns = [s.strip().lower() for s in candidate["synonyms"].split("|")]
                if mention_clean in syns:
                    exact_match = True
            
            alias_bonus = 1.0 if exact_match else 0.0
            vector_sim = 1.0 if exact_match else 0.8
            lexical_sim = 1.0 if exact_match else 0.8

        confidence = (0.6 * vector_sim) + (0.3 * lexical_sim) + (0.1 * alias_bonus)
        return round(min(max(confidence, 0.0), 1.0), 2)
