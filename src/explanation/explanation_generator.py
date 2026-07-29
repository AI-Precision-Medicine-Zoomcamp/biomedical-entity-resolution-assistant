import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

class ExplanationGenerator:
    """
    Generates human-readable explanations explaining why a mention resolved
    to a specific ontology concept.
    """
    def __init__(self):
        pass

    def generate_explanation(self, mention: str, candidate: dict, confidence: float) -> str:
        """
        Generates a clear clinical explanation for the entity resolution.
        
        Args:
            mention (str): The original text mention.
            candidate (dict): The resolved canonical concept.
            confidence (float): Calculated confidence score.
            
        Returns:
            str: Human-readable explanation.
        """
        if not candidate:
            return "No matching candidate was found in the ontology database."

        canonical = candidate["canonical_name"]
        identifier = candidate["identifier"]
        source = candidate["source"]
        retrieval_method = candidate.get("retrieval_method", "unknown")
        
        mention_clean = mention.strip().lower()
        canonical_clean = canonical.strip().lower()
        
        # Scenario 1: Exact ID match
        if "id_match" in retrieval_method:
            return (
                f"Resolved mention '{mention}' directly to '{canonical}' ({identifier}) "
                f"via direct identifier lookup in the {source} ontology (Confidence: {int(confidence*100)}%)."
            )
            
        # Scenario 2: Exact canonical match
        if mention_clean == canonical_clean:
            return (
                f"Resolved mention '{mention}' to '{canonical}' ({identifier}) "
                f"based on an exact case-insensitive match of the canonical label in the {source} ontology."
            )
            
        # Scenario 3: Exact synonym match
        synonyms = candidate.get("synonyms", "")
        exact_syn_match = False
        if synonyms:
            syn_list = [s.strip().lower() for s in synonyms.split("|")]
            if mention_clean in syn_list:
                exact_syn_match = True
                
        if exact_syn_match:
            return (
                f"Resolved mention '{mention}' to '{canonical}' ({identifier}) "
                f"because '{mention}' is listed as an exact synonym or alternative alias of '{canonical}' in {source}."
            )
            
        # Scenario 4: Vector semantic match
        if "vector" in retrieval_method and not "lexical" in retrieval_method:
            desc_part = ""
            if candidate.get("description"):
                desc_part = f" which is described as: '{candidate['description']}'"
            return (
                f"Resolved mention '{mention}' to '{canonical}' ({identifier}) "
                f"using semantic vector search (SapBERT). No exact lexical matches were found, but the term is "
                f"conceptually similar to '{canonical}' in {source}{desc_part}."
            )
            
        # Scenario 5: General Hybrid Match
        return (
            f"Resolved mention '{mention}' to '{canonical}' ({identifier}) "
            f"via a hybrid lexical-semantic matching process. The term '{mention}' shares strong lexical and semantic "
            f"similarity with this concept in the {source} database."
        )

    def generate_reasons(self, mention: str, candidate: dict, confidence: float) -> list[str]:
        """
        Generates structured explanation reasons as a list of strings.
        """
        reasons = []
        if not candidate:
            return ["No matching candidate found in database"]

        mention_clean = mention.strip().lower()
        canonical_clean = candidate["canonical_name"].strip().lower()
        retrieval_method = candidate.get("retrieval_method", "unknown")

        # 1. Check direct matches
        if "id_match" in retrieval_method:
            reasons.append("Matched official identifier/code")
        
        if mention_clean == canonical_clean:
            reasons.append("Matched canonical label")
            
        synonyms = candidate.get("synonyms", "")
        if synonyms:
            syn_list = [s.strip().lower() for s in synonyms.split("|")]
            if mention_clean in syn_list:
                reasons.append("Matched ontology synonym")

        # 2. Check semantic similarity
        vector_sim = candidate.get("vector_similarity", 0.0)
        # Handle fallback / exact match cases that might not have vector_similarity explicitly computed
        if "vector_similarity" not in candidate:
            exact_match = (mention_clean == canonical_clean) or (synonyms and mention_clean in [s.strip().lower() for s in synonyms.split("|")])
            vector_sim = 1.0 if exact_match else 0.8

        if vector_sim >= 0.85:
            reasons.append("Highest semantic similarity")
        elif vector_sim >= 0.70:
            reasons.append("High semantic similarity (SapBERT)")

        # 3. Check lexical similarity
        lexical_sim = candidate.get("lexical_similarity", 0.0)
        if lexical_sim >= 0.85:
            reasons.append("High lexical similarity")

        # 4. Competing concept checks
        # If confidence is high, it typically means there is no close second competitor
        if confidence >= 0.85:
            reasons.append("No competing concepts")

        # Fallback if list is empty
        if not reasons:
            reasons.append("Matched via hybrid lexical-semantic retrieval")

        return reasons
