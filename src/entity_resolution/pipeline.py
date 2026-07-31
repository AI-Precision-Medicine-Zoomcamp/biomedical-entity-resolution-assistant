import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.ner.ner_extractor import BiomedicalNER
from src.retrieval.rag_pipeline import BiomedicalRetriever
from src.ranking.ranker import CandidateRanker
from src.confidence.confidence_estimator import ConfidenceEstimator
from src.explanation.explanation_generator import ExplanationGenerator

class BiomedicalEntityResolverPipeline:
    """
    Main orchestrator for the Biomedical Entity Resolution Pipeline.
    Steps:
      Text -> NER -> Retrieval -> Ranking -> Confidence -> Explanation -> JSON Response
    """
    def __init__(self, retrieval_service=None):
        self.ner = BiomedicalNER()
        if retrieval_service is None:
            self.retriever = BiomedicalRetriever()
        else:
            self.retriever = retrieval_service
        self.ranker = CandidateRanker()
        self.confidence_estimator = ConfidenceEstimator()
        self.explanation_generator = ExplanationGenerator()
        
        # Removed static clinical fallbacks
        pass

    def normalize_mention(self, text: str) -> str:
        """
        Normalizes a mention before retrieval by converting to lowercase, stripping,
        removing punctuation, resolving multiple spaces, and unicode differences.
        """
        from src.preprocessing.text_normalizer import remove_punctuation
        return remove_punctuation(text)

    def resolve_text(self, text: str) -> list[dict]:
        """
        Runs the full text-to-entities resolution pipeline.
        """
        if not text:
            return []

        # Step 1: Named Entity Recognition (NER)
        mentions = self.ner.extract_mentions(text)
        
        is_fallback = False
        if not mentions:
            # Fallback for short queries (potentially misspelled single entities)
            words = text.strip().split()
            if len(words) <= 5 and len(text) <= 40:
                mentions = [{"mention": text.strip(), "start_char": 0, "end_char": len(text.strip())}]
                is_fallback = True
        
        resolved_entities = []
        
        for item in mentions:
            mention = item["mention"]
            start_char = item["start_char"]
            end_char = item["end_char"]
            
            normalized_mention = self.normalize_mention(mention)
            best_candidate = None
            
            # Step 2: Retrieve candidate concepts from index
            candidates = self.retriever.hybrid_search(normalized_mention, limit=10)
            if candidates:
                # Step 3: Rank candidates
                ranked_candidates = self.ranker.rank_candidates(normalized_mention, candidates)
                if ranked_candidates:
                    best_candidate = ranked_candidates[0]

            # Step 4: Compute confidence and explanation
            if best_candidate:
                confidence = self.confidence_estimator.estimate_confidence(mention, best_candidate)
                
                # If we fell back and confidence is low (< 0.60), skip this concept to prevent false positives (like chitchat)
                if is_fallback and confidence < 0.60:
                    continue
                    
                explanation = self.explanation_generator.generate_explanation(mention, best_candidate, confidence)
                reasons = self.explanation_generator.generate_reasons(mention, best_candidate, confidence)
                
                # Human review thresholds
                if confidence > 0.90:
                    status = "resolved"
                elif confidence >= 0.60:
                    status = "needs_review"
                else:
                    status = "rejected"
                    
                ident = best_candidate["identifier"]
                concept_id = ident.split(":")[-1] if ":" in ident else ident

                resolved_entities.append({
                    "mention": mention,
                    "start_char": start_char,
                    "end_char": end_char,
                    "canonical_name": best_candidate["canonical_name"],
                    "canonical": best_candidate["canonical_name"],
                    "entity_type": best_candidate["entity_type"],
                    "identifier": ident,
                    "concept_id": concept_id,
                    "ontology": best_candidate["source"],
                    "confidence": confidence,
                    "status": status,
                    "reason": reasons,
                    "explanation": explanation
                })
                
        return resolved_entities
