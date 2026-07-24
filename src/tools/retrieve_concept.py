import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.retrieval.rag_pipeline import BiomedicalRetriever

def retrieve_concept(concept_id: str) -> dict:
    """
    Tool: retrieve_concept
    Retrieves full concept metadata (canonical name, description, ontology, synonyms)
    for a specific ontology concept identifier (e.g., 'MESH:D009203', 'RXCUI:161', 'HGNC:11998').
    
    Args:
        concept_id (str): The concept identifier (with prefix, e.g. MESH:D009203).
        
    Returns:
        dict: The retrieved concept metadata, or empty dict if not found.
    """
    if not concept_id:
        return {}
    
    retriever = BiomedicalRetriever()
    df = retriever.lookup_df
    
    matches = df[df["identifier"].str.upper() == concept_id.strip().upper()]
    if not matches.empty:
        row = matches.iloc[0]
        # Gather all unique aliases for this identifier
        aliases = matches["alias"].dropna().unique()
        synonyms = "|".join(aliases)
        
        return {
            "identifier": row.identifier,
            "canonical_name": row.canonical_name,
            "description": row.description if (hasattr(row, "description") and row.description) else "",
            "entity_type": row.entity_type,
            "source": row.source,
            "synonyms": synonyms
        }
        
    return {}

if __name__ == "__main__":
    import json
    print("Testing retrieve_concept tool...")
    print(json.dumps(retrieve_concept("MESH:D009203"), indent=2))
