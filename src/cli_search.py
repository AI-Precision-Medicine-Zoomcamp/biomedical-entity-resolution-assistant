import sys
import pandas as pd
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.preprocessing.text_normalizer import generate_normalized_variants

def search(query: str):
    lookup_path = PROJECT_ROOT / "data" / "processed" / "normalized_lookup.parquet"
    if not lookup_path.exists():
        print(f"Error: Unified index not found at {lookup_path}. Please run ingestion and preprocessing first.")
        return
        
    print("[Search] Loading unified index (this takes a fraction of a second)...")
    df = pd.read_parquet(lookup_path)
    
    # Normalize query using the same preprocessing rules
    norm_variants = generate_normalized_variants(query)
    print(f"[Search] Query: '{query}' | Normalized Variants: {norm_variants}")
    
    # Perform exact match lookup across all variants
    results = df[df["alias"].isin(norm_variants)]
    
    print("-" * 70)

    if results.empty:
        print("❌ No exact match found.")
        # Try a substring lookup as a basic fallback
        fallback_query = norm_variants[0] if norm_variants else ""
        fallback = df[df["alias"].str.contains(fallback_query, case=False, na=False)] if fallback_query else pd.DataFrame()
        if not fallback.empty:

            print(f"\n💡 Found {len(fallback)} partial matches:")
            # Display unique matches by identifier to make output clean
            display_df = fallback.drop_duplicates(subset=["identifier"]).head(5)
            print(display_df[["alias", "identifier", "canonical_name", "entity_type", "source"]].to_string(index=False))
            if len(fallback) > 5:
                print(f"... and {len(fallback) - 5} more.")
    else:
        print(f"✅ Found {len(results)} exact matches:")
        print(results[["alias", "identifier", "canonical_name", "entity_type", "source", "match_type"]].to_string(index=False))
    print("-" * 70)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        search(query)
    else:
        print("Biomedical Entity Resolution CLI Search Utility")
        print("=" * 50)
        print("Usage: uv run python src/cli_search.py <query>")
        print("Examples:")
        print("  uv run python src/cli_search.py erbb1")
        print("  uv run python src/cli_search.py Lipitor")
        print("  uv run python src/cli_search.py non-small cell lung cancer")
