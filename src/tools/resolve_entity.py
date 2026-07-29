import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.entity_resolution.pipeline import BiomedicalEntityResolverPipeline

def resolve_entity(text: str) -> list[dict]:
    """
    Tool: resolve_entity
    Resolves biomedical entities in the input text using the entity resolution pipeline.
    Identifies diseases, drugs, genes, and mutations, normalizes them, and maps to standard ontologies.
    
    Args:
        text (str): The input text containing clinical/biomedical mentions.
        
    Returns:
        list[dict]: List of resolved entity concepts.
    """
    if not text:
        return []
    
    pipeline = BiomedicalEntityResolverPipeline()
    return pipeline.resolve_text(text)

if __name__ == "__main__":
    import json
    test_text = "Patients diagnosed with MI were given Tylenol."
    print("Testing resolve_entity tool...")
    print(json.dumps(resolve_entity(test_text), indent=2))
