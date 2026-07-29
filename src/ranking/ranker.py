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

    @property
    def embedding_model(self):
        if not hasattr(self, "_embedding_model") or self._embedding_model is None:
            from src.embeddings.embedder import BiomedicalEmbedder
            self._embedding_model = BiomedicalEmbedder()
        return self._embedding_model

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

        # Generate query embedding using SapBERT
        query_emb = self.embedding_model.embed_texts([mention])[0]
        import numpy as np
        query_emb_norm = query_emb / np.linalg.norm(query_emb)

        # Generate candidate embeddings (for their canonical names)
        candidate_names = [cand["canonical_name"] for cand in candidates]
        cand_embs = self.embedding_model.embed_texts(candidate_names)

        for cand, emb in zip(candidates, cand_embs):
            canonical_clean = cand["canonical_name"].strip().lower()
            
            # Compute vector similarity via cosine similarity
            emb_norm = emb / np.linalg.norm(emb)
            vector_sim = float(np.dot(query_emb_norm, emb_norm))
            vector_sim = max(min(vector_sim, 1.0), 0.0)
            
            # Compute lexical similarity to canonical name
            canonical_sim = SequenceMatcher(None, mention_clean, canonical_clean).ratio()
            
            # Compute max lexical similarity to synonyms
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
            text_sim = max(canonical_sim, max_synonym_sim)
            
            # Determine alias match (exact match on canonical or synonym)
            alias_bonus = 1.0 if (exact_canonical_match or exact_synonym_match) else 0.0
            
            # Final ranking score combining all signals
            final_score = (0.6 * vector_sim) + (0.3 * text_sim) + (0.1 * alias_bonus)
            if exact_canonical_match or exact_synonym_match:
                final_score += 1.0
            
            # Copy candidate info and attach scores
            cand_info = cand.copy()
            cand_info["vector_similarity"] = vector_sim
            cand_info["lexical_similarity"] = text_sim
            cand_info["exact_match"] = exact_canonical_match or exact_synonym_match
            cand_info["alias_bonus"] = alias_bonus
            cand_info["final_ranking_score"] = final_score
            
            ranked.append(cand_info)

        # Sort candidates by final_ranking_score descending
        ranked = sorted(ranked, key=lambda x: x["final_ranking_score"], reverse=True)
        return ranked
