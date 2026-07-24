import sys
import yaml
from pathlib import Path
from src.embeddings.embedder import BiomedicalEmbedder
from qdrant_client import QdrantClient

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.retrieval.embed_and_index import get_qdrant_client, COLLECTION_NAME, MODEL_HF_ID

def vector_search(query: str, top_k: int = 5):
    # Initialize Qdrant Client
    client = get_qdrant_client()
    
    # Check if collection exists
    collections = client.get_collections().collections
    exists = any(c.name == COLLECTION_NAME for c in collections)
    if not exists:
        print(f"Error: Qdrant collection '{COLLECTION_NAME}' does not exist. Please run indexing first.")
        return
        
    # Load model
    print(f"[Vector Search] Loading model: '{MODEL_HF_ID}'...")
    model = BiomedicalEmbedder(MODEL_HF_ID)
    
    # Embed query
    print(f"[Vector Search] Embedding query: '{query}'...")
    query_vector = model.embed_texts([query])[0].tolist()

    
    # Search Qdrant
    print(f"[Vector Search] Querying Qdrant collection '{COLLECTION_NAME}'...")
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k
    )
    results = response.points
    
    print("\n" + "=" * 80)
    print(f"VECTOR SEARCH RESULTS FOR: '{query}'")
    print("=" * 80)
    
    for idx, hit in enumerate(results, 1):

        payload = hit.payload
        score = hit.score
        print(f"{idx}. [{payload['entity_type']}] {payload['canonical_name']} (Score: {score:.4f})")
        print(f"   Identifier : {payload['identifier']}")
        print(f"   Source     : {payload['source']}")
        print(f"   Synonyms   : {payload['synonyms']}")
        print(f"   Description: {payload['description']}")
        print("-" * 80)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        vector_search(query)
    else:
        print("Usage: uv run python src/cli_vector_search.py <query>")
        print("Example: uv run python src/cli_vector_search.py lung cancer")
