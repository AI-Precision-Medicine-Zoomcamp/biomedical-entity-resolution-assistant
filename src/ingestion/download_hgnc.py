import os
import requests
import pandas as pd
from tqdm import tqdm
from pathlib import Path

# Constants
HGNC_URL = "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt"
PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_DIR / "data" / "processed"
CACHE_DIR = PROJECT_DIR / "data" / "ontology_cache"

def download_hgnc(force: bool = False) -> Path:
    """
    Downloads the HGNC complete gene dataset.
    
    Args:
        force (bool): If True, downloads even if cached.
        
    Returns:
        Path: Path to the downloaded raw file.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    raw_path = CACHE_DIR / "hgnc_complete_set.txt"
    
    if raw_path.exists() and not force:
        print(f"[HGNC] Using cached file: {raw_path}")
        return raw_path
        
    print(f"[HGNC] Downloading complete gene set from {HGNC_URL}...")
    response = requests.get(HGNC_URL, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024 * 1024  # 1MB
    
    with open(raw_path, "wb") as f, tqdm(
        total=total_size, unit="iB", unit_scale=True, desc="HGNC"
    ) as progress_bar:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            f.write(data)
            
    print(f"[HGNC] Saved raw download to {raw_path}")
    return raw_path

def validate_hgnc(file_path: Path) -> bool:
    """
    Validates that the downloaded file is a valid HGNC TSV file.
    """
    print(f"[HGNC] Validating {file_path}...")
    if not file_path.exists():
        print(f"[HGNC] Validation failed: File does not exist.")
        return False
        
    if file_path.stat().st_size < 1_000_000:  # Expect > 1MB
        print(f"[HGNC] Validation failed: File size too small ({file_path.stat().st_size} bytes).")
        return False
        
    # Check headers
    try:
        df_head = pd.read_csv(file_path, sep="\t", nrows=5, low_memory=False)
        required_cols = {"hgnc_id", "symbol", "status", "name"}
        missing_cols = required_cols - set(df_head.columns)
        if missing_cols:
            print(f"[HGNC] Validation failed: Missing required columns {missing_cols}.")
            return False
    except Exception as e:
        print(f"[HGNC] Validation failed: Could not read file as TSV. Error: {e}")
        return False
        
    print("[HGNC] Validation successful!")
    return True

def process_hgnc(file_path: Path) -> Path:
    """
    Processes the raw HGNC TSV file into a standardized format and saves as Parquet.
    """
    print(f"[HGNC] Processing raw file...")
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    processed_path = PROCESSED_DATA_DIR / "hgnc.parquet"
    
    # Load required columns only to conserve memory
    cols = ["hgnc_id", "symbol", "name", "status", "alias_symbol", "prev_symbol"]
    df = pd.read_csv(file_path, sep="\t", usecols=cols, low_memory=False)
    
    # Keep only approved symbols
    df = df[df["status"] == "Approved"].copy()
    
    print("[HGNC] Extracting aliases and synonyms...")
    # Fast vectorized/zipped extraction of synonyms
    alias_col = df["alias_symbol"].fillna("").astype(str).values
    prev_col = df["prev_symbol"].fillna("").astype(str).values
    
    synonyms_list = []
    for alias_val, prev_val in zip(alias_col, prev_col):
        row_aliases = set()
        if alias_val:
            parts = [p.strip().upper() for p in alias_val.replace("|", ",").split(",") if p.strip()]
            row_aliases.update(parts)
        if prev_val:
            parts = [p.strip().upper() for p in prev_val.replace("|", ",").split(",") if p.strip()]
            row_aliases.update(parts)
        synonyms_list.append("|".join(sorted(row_aliases)))
        
    df["synonyms"] = synonyms_list

    
    # Format to standardized ingestion schema
    processed_df = pd.DataFrame({
        "identifier": df["hgnc_id"],
        "canonical_name": df["symbol"],
        "description": df["name"].fillna(""),
        "synonyms": df["synonyms"],
        "entity_type": "Gene",
        "source": "HGNC"
    })
    
    # Deduplicate and clean
    processed_df = processed_df.drop_duplicates(subset=["identifier"])
    processed_df.to_parquet(processed_path, index=False)
    
    print(f"[HGNC] Processed data saved to {processed_path} (Total records: {len(processed_df)})")
    return processed_path

def run_hgnc_ingestion(force: bool = False):
    """
    Runs the full HGNC ingestion pipeline.
    """
    raw_file = download_hgnc(force=force)
    if validate_hgnc(raw_file):
        process_hgnc(raw_file)
        print("[HGNC] Ingestion pipeline completed successfully.")
    else:
        raise ValueError("[HGNC] Downloaded file validation failed.")

if __name__ == "__main__":
    run_hgnc_ingestion()
