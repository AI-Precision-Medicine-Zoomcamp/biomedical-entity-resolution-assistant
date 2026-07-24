import os
import requests
import pandas as pd
from pathlib import Path

# Constants
RXNORM_API_URL = "https://rxnav.nlm.nih.gov/REST/Prescribe/allconcepts.json?tty=IN+BN"
PROJECT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DATA_DIR = PROJECT_DIR / "data" / "processed"
CACHE_DIR = PROJECT_DIR / "data" / "ontology_cache"

def download_rxnorm_from_api(force: bool = False) -> Path:
    """
    Downloads active prescribable RxNorm ingredients and brand names from the free RxNav API.
    This does not require UMLS authentication.
    
    Returns:
        Path: Path to the cached raw JSON file.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    raw_path = CACHE_DIR / "rxnorm_prescribe_concepts.json"
    
    if raw_path.exists() and not force:
        print(f"[RxNorm] Using cached API file: {raw_path}")
        return raw_path
        
    print(f"[RxNorm] Fetching active concepts (Ingredients and Brand Names) from RxNav API...")
    response = requests.get(RXNORM_API_URL)
    response.raise_for_status()
    
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(response.text)
        
    print(f"[RxNorm] Saved raw API response to {raw_path}")
    return raw_path

def validate_rxnorm_json(file_path: Path) -> bool:
    """
    Validates the downloaded RxNorm API JSON data.
    """
    print(f"[RxNorm] Validating {file_path}...")
    if not file_path.exists():
        print("[RxNorm] Validation failed: File does not exist.")
        return False
        
    try:
        df = pd.read_json(file_path)
        if "minConceptGroup" not in df.columns:
            print("[RxNorm] Validation failed: Key 'minConceptGroup' not found in JSON.")
            return False
    except Exception as e:
        print(f"[RxNorm] Validation failed: File is not a valid JSON. Error: {e}")
        return False
        
    print("[RxNorm] Validation successful!")
    return True

def process_rxnorm_api(file_path: Path) -> Path:
    """
    Processes the raw JSON API file into a standardized format and saves as Parquet.
    """
    print("[RxNorm] Processing concepts from JSON...")
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    processed_path = PROCESSED_DATA_DIR / "rxnorm.parquet"
    
    # Load JSON data
    import json
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    concepts = data.get("minConceptGroup", {}).get("minConcept", [])
    
    records = []
    for concept in concepts:
        rxcui = concept.get("rxcui")
        name = concept.get("name")
        tty = concept.get("tty")
        
        if rxcui and name:
            term_type_label = "Ingredient" if tty == "IN" else "Brand Name"
            records.append({
                "identifier": f"RXCUI:{rxcui}",
                "canonical_name": name,
                "description": f"RxNorm {term_type_label} concept ({tty})",
                "synonyms": "", # API does not contain full synonyms list in this call; can map relationships later
                "entity_type": "Medication",
                "source": "RxNorm"
            })
            
    df = pd.DataFrame(records)
    print(f"[RxNorm] Total processed medication records: {len(df)}")
    
    # Deduplicate and save
    df = df.drop_duplicates(subset=["identifier"])
    df.to_parquet(processed_path, index=False)
    
    print(f"[RxNorm] Processed data saved to {processed_path}")
    return processed_path

def run_rxnorm_ingestion(force: bool = False):
    """
    Runs the full RxNorm ingestion pipeline using the public API fallback.
    """
    # Note: UMLS monthly releases require UTS license.
    # To ensure the assistant runs out of the box, we use the public RxNav API.
    raw_file = download_rxnorm_from_api(force=force)
    if validate_rxnorm_json(raw_file):
        process_rxnorm_api(raw_file)
        print("[RxNorm] Ingestion pipeline completed successfully.")
    else:
        raise ValueError("[RxNorm] Downloaded file validation failed.")

if __name__ == "__main__":
    run_rxnorm_ingestion()
