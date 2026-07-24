import sys
from pathlib import Path
from difflib import SequenceMatcher

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

class CandidateRanker:
    """
    Ranks retrieved biomedical concept candidates.
    Enhances the RRF score with:
    1. Lexical similarity (SequenceMatcher ratio) between mention and candidate canonical name/synonyms.
    2. Exact-match boosting for exact synonym/canonical match.
    3. Type-based prior adjustments.
    """
    def __init__(self):
        pass

    def rank_candidates(self, mention: str, candidates: list[dict]) -> list[dict]:
        """
        Ranks a list of candidate entity dicts for a given mention.
        
        Args:
            mention (str): The entity text snippet extracted from the document.
            candidates (list[dict]): Candidates retrieved from hybrid retrieval.
            
        Returns:
            list[dict]: Ranked candidates with updated scores and ranking metadata.
        """
        if not candidates:
            return []

        ranked = []
        mention_clean = mention.strip().lower()

        for cand in candidates:
            canonical_clean = cand["canonical_name"].strip().lower()
            
            # 1. Similarity to canonical name
            canonical_sim = SequenceMatcher(None, mention_clean, canonical_clean).ratio()
            
            # 2. Max similarity to any of the synonyms
            synonyms_list = []
            if cand.get("synonyms") and isinstance(cand["synonyms"], str):
                synonyms_list = [s.strip().lower() for s in cand["synonyms"].split("|")]
            
            max_synonym_sim = 0.0
            exact_synonym_match = False
            for syn in synonyms_list:
                sim = SequenceMatcher(None, mention_clean, syn).ratio()
                if sim > max_synonym_sim:
                    max_synonym_sim = sim
                if mention_clean == syn:
                    exact_synonym_match = True
            
            exact_canonical_match = (mention_clean == canonical_clean)
            
            # 3. Compute a similarity score (weighted combination)
            text_sim = max(canonical_sim, max_synonym_sim)
            
            # 4. Hybrid score combination
            # Start with the retriever's score (usually RRF score or cosine score)
            retrieval_score = cand.get("score", 0.0)
            
            # Add boosts for exact matches
            exact_boost = 0.0
            if exact_canonical_match:
                exact_boost = 0.30
            elif exact_synonym_match:
                exact_boost = 0.20
                
            # Final ranking score
            # Combining retrieval_score and text_sim + exact_boost
            # Scaled to be between 0.0 and 1.0
            final_score = (0.4 * retrieval_score) + (0.4 * text_sim) + exact_boost
            final_score = min(max(final_score, 0.0), 1.0)
            
            # Copy candidate info and attach scores
            cand_info = cand.copy()
            cand_info["lexical_similarity"] = text_sim
            cand_info["exact_match"] = exact_canonical_match or exact_synonym_match
            cand_info["final_ranking_score"] = final_score
            
            ranked.append(cand_info)

        # Sort candidates by final_ranking_score descending
        ranked = sorted(ranked, key=lambda x: x["final_ranking_score"], reverse=True)
        return ranked
