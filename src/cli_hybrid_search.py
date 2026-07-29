import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Mock torchvision before other imports
import src.utils.mock_torchvision

from src.retrieval.rag_pipeline import BiomedicalRetriever

def run_hybrid_search_cli(query: str):
    print("Initializing Biomedical Retriever...")
    retriever = BiomedicalRetriever()
    
    print("-" * 80)
    print(f"QUERY: '{query}'")
    print("-" * 80)
    
    # 1. Lexical Search
    print("\n🔍 [1/3] LEXICAL SEARCH RESULTS:")
    try:
        lexical_results = retriever.lexical_search(query, limit=5)
        if lexical_results:
            for idx, r in enumerate(lexical_results, 1):
                print(f"  {idx}. [{r['entity_type']}] {r['canonical_name']} ({r['identifier']}) - Score: {r['score']:.3f} [{r['match_type']}]")
        else:
            print("  No lexical matches found.")
    except Exception as e:
        print(f"  Error: {e}")
        
    # 2. Vector Search
    print("\n🧠 [2/3] VECTOR SEARCH RESULTS:")
    try:
        vector_results = retriever.vector_search(query, limit=5)
        if vector_results:
            for idx, r in enumerate(vector_results, 1):
                print(f"  {idx}. [{r['entity_type']}] {r['canonical_name']} ({r['identifier']}) - Score: {r['score']:.4f}")
        else:
            print("  No vector matches found (or collection is empty).")
    except Exception as e:
        print(f"  Error: {e}")
        
    # 3. Hybrid (RRF) Search
    print("\n🔀 [3/3] HYBRID SEARCH (RRF) MERGED RANKING:")
    try:
        hybrid_results = retriever.hybrid_search(query, limit=5)
        if hybrid_results:
            for idx, r in enumerate(hybrid_results, 1):
                print(f"  {idx}. [{r['entity_type']}] {r['canonical_name']} ({r['identifier']}) - RRF Score: {r['score']:.4f} ({r['retrieval_method']})")
                print(f"     Description: {r['description']}")
        else:
            print("  No hybrid matches found.")
    except Exception as e:
        print(f"  Error: {e}")
    print("-" * 80)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        run_hybrid_search_cli(query)
    else:
        print("Usage: uv run python src/cli_hybrid_search.py <query>")
        print("Example: uv run python src/cli_hybrid_search.py EGFR")
        print("Example: uv run python src/cli_hybrid_search.py \"non-small cell lung cancer\"")
