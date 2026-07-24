import os
import sys
import pandas as pd
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.preprocessing.text_normalizer import generate_normalized_variants

PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

def preprocess_ontology_file(file_path: Path) -> pd.DataFrame:
    """
    Loads a processed ontology parquet file, normalizes names and synonyms,
    explodes them into alias-to-concept rows, and returns a DataFrame.
    """
    print(f"[Preprocessor] Preprocessing {file_path.name}...")
    df = pd.read_parquet(file_path)
    
    records = []
    
    # We iterate over rows to generate exploded lookup entries
    # Using itertuples is much faster than iterrows
    for row in df.itertuples(index=False):
        identifier = row.identifier
        canonical_name = row.canonical_name
        description = getattr(row, "description", "")
        entity_type = row.entity_type
        source = row.source
        synonyms_str = getattr(row, "synonyms", "")
        
        # Parse synonyms list
        synonyms = set()
        if pd.notna(synonyms_str) and isinstance(synonyms_str, str) and synonyms_str:
            synonyms.update([s.strip() for s in synonyms_str.split("|") if s.strip()])
            
        # 1. Process Canonical Name variants (highest priority)
        canonical_variants = generate_normalized_variants(canonical_name)
        for variant in canonical_variants:
            records.append({
                "alias": variant,
                "identifier": identifier,
                "canonical_name": canonical_name,
                "description": description,
                "entity_type": entity_type,
                "source": source,
                "match_type": "canonical"
            })
            
        # 2. Process Description as a potential match if it is short (e.g. for short descriptions)
        # Usually we only match on symbols/synonyms, so we skip description matching to avoid noise,
        # but we preserve it in the canonical metadata.
        
        # 3. Process Synonyms variants (secondary priority)
        for synonym in synonyms:
            synonym_variants = generate_normalized_variants(synonym)
            for variant in synonym_variants:
                records.append({
                    "alias": variant,
                    "identifier": identifier,
                    "canonical_name": canonical_name,
                    "description": description,
                    "entity_type": entity_type,
                    "source": source,
                    "match_type": "synonym"
                })
                
    # Convert to DataFrame
    exploded_df = pd.DataFrame(records)
    
    # Deduplicate: if the same alias maps to the same identifier, keep the one with the higher priority (canonical)
    # We sort by match_type ('canonical' < 'synonym' alphabetically, so 'canonical' comes first)
    exploded_df = exploded_df.sort_values(by=["alias", "identifier", "match_type"])
    exploded_df = exploded_df.drop_duplicates(subset=["alias", "identifier"], keep="first")
    
    print(f"[Preprocessor] {file_path.name} exploded from {len(df)} to {len(exploded_df)} lookup aliases.")
    return exploded_df

def run_preprocessing_pipeline():
    """
    Runs the preprocessing pipeline for all available processed ontologies,
    merging them into a single, unified, high-performance lookup index.
    """
    print("=" * 60)
    print("STARTING BIOMEDICAL ONTOLOGY PREPROCESSING PIPELINE")
    print("=" * 60)
    
    files = {
        "HGNC": PROCESSED_DATA_DIR / "hgnc.parquet",
        "MeSH": PROCESSED_DATA_DIR / "mesh.parquet",
        "RxNorm": PROCESSED_DATA_DIR / "rxnorm.parquet"
    }
    
    dfs = []
    for name, path in files.items():
        if path.exists():
            try:
                df = preprocess_ontology_file(path)
                dfs.append(df)
            except Exception as e:
                print(f"[Preprocessor] Error preprocessing {name}: {e}")
        else:
            print(f"[Preprocessor] Warning: Processed file not found for {name} ({path})")
            
    if not dfs:
        print("[Preprocessor] Error: No processed files found to preprocess!")
        return
        
    # Merge all datasets into one unified lookup index
    print("\n[Preprocessor] Merging all ontologies into a unified lookup index...")
    unified_df = pd.concat(dfs, ignore_index=True)
    
    # Final deduplication and clean up
    unified_df = unified_df.drop_duplicates(subset=["alias", "identifier"])
    
    # Save unified index
    output_path = PROCESSED_DATA_DIR / "normalized_lookup.parquet"
    unified_df.to_parquet(output_path, index=False)
    
    print(f"\n[Preprocessor] Unified lookup index saved to: {output_path}")
    print(f"[Preprocessor] Total indexing keys: {len(unified_df)}")
    
    # Print some stats
    print("\nEntity Type Distribution:")
    print(unified_df["entity_type"].value_counts().to_string())
    print("=" * 60)

if __name__ == "__main__":
    run_preprocessing_pipeline()
