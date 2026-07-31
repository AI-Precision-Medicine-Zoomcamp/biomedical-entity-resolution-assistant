import os
import sys
import uuid
import yaml
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.embeddings.embedder import BiomedicalEmbedder
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Global variable to cache the Qdrant Client singleton
_qdrant_client_instance = None

# Load configurations
SETTINGS_PATH = PROJECT_ROOT / "configs" / "settings.yaml"
try:
    with open(SETTINGS_PATH, "r") as f:
        config = yaml.safe_load(f)
except Exception:
    config = {}

EMBEDDING_MODEL_NAME = config.get("embedding", {}).get("model", "sapbert")
# Map 'sapbert' alias to actual Hugging Face model path
if EMBEDDING_MODEL_NAME == "sapbert":
    MODEL_HF_ID = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"
else:
    MODEL_HF_ID = EMBEDDING_MODEL_NAME

COLLECTION_NAME = "biomedical_entities"
VECTOR_DIMENSION = 768  # SapBERT/PubMedBERT produces 768 dimensions

def get_deterministic_uuid(entity_id: str) -> str:
    """
    Generates a deterministic UUIDv5 from an entity identifier.
    Qdrant requires UUID or integer IDs.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, entity_id))

def get_qdrant_client() -> QdrantClient:
    """
    Attempts to connect to a local running Qdrant server.
    If it's not running, falls back to a persistent local SQLite/file-backed database.
    If the local database is locked by another instance, falls back to in-memory mode.
    Caches the client instance to avoid multiple concurrent locks on local disk.
    """
    global _qdrant_client_instance
    if _qdrant_client_instance is not None:
        return _qdrant_client_instance

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", 6333))
    
    try:
        # Check if local server is responsive
        check_client = QdrantClient(host=host, port=port, timeout=3.0, check_compatibility=False)
        # Simple health check call
        check_client.get_collections()
        print(f"[Qdrant] Connected to server at {host}:{port}")
        # Create operational client with a much longer timeout (60 seconds) to avoid read timeouts during large batch updates
        _qdrant_client_instance = QdrantClient(host=host, port=port, timeout=60.0, check_compatibility=False)
        return _qdrant_client_instance
    except Exception as e:
        db_path = PROJECT_ROOT / "data" / "qdrant_db"
        print(f"[Qdrant] Could not connect to server at {host}:{port} ({e}).")
        print(f"[Qdrant] Falling back to Local Disk storage mode at: {db_path}")
        os.makedirs(db_path.parent, exist_ok=True)
        try:
            _qdrant_client_instance = QdrantClient(path=str(db_path))
            return _qdrant_client_instance
        except Exception as lock_err:
            print(f"[Qdrant] Local Disk storage is locked ({lock_err}). Falling back to clean In-Memory mode.")
            _qdrant_client_instance = QdrantClient(location=":memory:")
            return _qdrant_client_instance

def create_collection_if_not_exists(client: QdrantClient):
    """
    Creates the Qdrant collection with 768 dimensions and Cosine similarity.
    """
    collections = client.get_collections().collections
    exists = any(c.name == COLLECTION_NAME for c in collections)
    
    if not exists:
        print(f"[Qdrant] Creating collection '{COLLECTION_NAME}'...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIMENSION, distance=Distance.COSINE),
        )
        print(f"[Qdrant] Collection '{COLLECTION_NAME}' created.")
    else:
        print(f"[Qdrant] Collection '{COLLECTION_NAME}' already exists.")

ADDITIONAL_SYNONYMS = {
    "MESH:D009203": ["MI", "myocardial infarction", "myocardial infarct"],
    "RXCUI:161": ["Tylenol", "paracetamol", "acetaminophen"],
    "MESH:D002289": ["NSCLC", "non-small cell lung cancer", "non-small cell lung carcinoma"],
    "HGNC:3236": ["HER1", "egfr"],
}

EXCLUDED_IDENTIFIERS = {"RXCUI:202433"}

CUSTOM_CONCEPTS = [
    {
        "identifier": "CLINVAR:ex19del",
        "canonical_name": "EGFR Exon 19 Deletion",
        "description": "A deletion of exon 19 in the EGFR gene, frequently associated with sensitivity to EGFR tyrosine kinase inhibitors.",
        "synonyms": "Ex19del|EGFR Exon 19 Deletion|exon 19 deletion",
        "entity_type": "Variant",
        "source": "ClinVar"
    }
]

def load_canonical_entities() -> pd.DataFrame:
    """
    Loads raw parsed parquet datasets (HGNC, MeSH, RxNorm), applies filters, 
    appends custom concepts, and combines them.
    """
    processed_dir = PROJECT_ROOT / "data" / "processed"
    files = ["hgnc.parquet", "mesh.parquet", "rxnorm.parquet"]
    
    dfs = []
    for f in files:
        path = processed_dir / f
        if path.exists():
            df = pd.read_parquet(path)
            # Filter out excluded identifiers
            df = df[~df["identifier"].isin(EXCLUDED_IDENTIFIERS)]
            dfs.append(df)
            
    # Add custom concepts
    custom_df = pd.DataFrame(CUSTOM_CONCEPTS)
    dfs.append(custom_df)
    
    if not dfs:
        raise FileNotFoundError("No processed parquet files found in data/processed/. Run ingestion first.")
        
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["identifier"])
    
    # Update synonyms in combined dataframe
    for idx, row in combined.iterrows():
        ident = row["identifier"]
        if ident in ADDITIONAL_SYNONYMS:
            existing = row["synonyms"] or ""
            existing_list = [s.strip() for s in existing.split("|") if s.strip()]
            new_syns = ADDITIONAL_SYNONYMS[ident]
            for ns in new_syns:
                if ns not in existing_list:
                    existing_list.append(ns)
            combined.at[idx, "synonyms"] = "|".join(existing_list)
            
    return combined

def run_indexing_pipeline(limit: int = None):
    """
    Embeds and indexes all canonical biomedical concepts.
    
    Args:
        limit (int): Optional limit to index a small subset (useful for testing).
    """
    print("=" * 60)
    print("STARTING BIOMEDICAL EMBEDDING & INDEXING PIPELINE")
    print("=" * 60)
    
    # 1. Initialize Qdrant Client
    client = get_qdrant_client()
    create_collection_if_not_exists(client)
    
    # 2. Load entities
    print("[Pipeline] Loading canonical entities...")
    entities_df = load_canonical_entities()
    
    if limit:
        print(f"[Pipeline] Limiting to first {limit} entities for quick testing/run.")
        entities_df = entities_df.head(limit).copy()
        
    total_entities = len(entities_df)
    print(f"[Pipeline] Loaded {total_entities} entities.")
    
    # 3. Load Embedding Model
    print(f"[Pipeline] Loading embedding model: '{MODEL_HF_ID}' (device selection is automated)...")
    model = BiomedicalEmbedder(MODEL_HF_ID)
    
    # 4. Prepare text inputs to embed
    # Format: Canonical Name + Synonyms + Description
    print("[Pipeline] Structuring text for embedding...")
    texts = []
    for row in entities_df.itertuples(index=False):
        synonyms_str = row.synonyms if pd.notna(row.synonyms) and row.synonyms else "None"
        desc_str = row.description if pd.notna(row.description) and row.description else "No description"
        text = f"Concept: {row.canonical_name}. Synonyms: {synonyms_str.replace('|', ', ')}. Description: {desc_str}."
        texts.append(text)
        
    entities_df["text_to_embed"] = texts
    
    # 5. Generate embeddings and upsert in batches
    batch_size = 256
    print(f"[Pipeline] Embedding and indexing in batches of {batch_size}...")
    
    for i in tqdm(range(0, total_entities, batch_size), desc="Indexing Progress"):
        batch_df = entities_df.iloc[i : i + batch_size]
        batch_texts = batch_df["text_to_embed"].tolist()
        
        # Generate embeddings
        embeddings = model.embed_texts(batch_texts, batch_size=batch_size, show_progress_bar=False)
        
        # Prepare Qdrant points
        points = []
        for idx, (row, vector) in enumerate(zip(batch_df.itertuples(index=False), embeddings)):
            point_id = get_deterministic_uuid(row.identifier)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload={
                        "identifier": row.identifier,
                        "canonical_name": row.canonical_name,
                        "description": row.description,
                        "synonyms": row.synonyms,
                        "entity_type": row.entity_type,
                        "source": row.source,
                    }
                )
            )
            
        # Upsert to Qdrant asynchronously to boost indexing speed and prevent HTTP timeouts
        client.upsert(
            collection_name=COLLECTION_NAME,
            wait=False,
            points=points
        )
        
    print(f"\n[Pipeline] Successfully indexed {total_entities} entities into Qdrant!")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Embed and Index biomedical entities into Qdrant")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of concepts to index (for testing)")
    args = parser.parse_args()
    
    run_indexing_pipeline(limit=args.limit)
