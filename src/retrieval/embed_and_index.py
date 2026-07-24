import os
import sys
import uuid
import yaml
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

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
    """
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", 6333))
    
    try:
        # Check if local server is responsive
        client = QdrantClient(host=host, port=port, timeout=3.0)
        # Simple health check call
        client.get_collections()
        print(f"[Qdrant] Connected to server at {host}:{port}")
        return client
    except Exception as e:
        db_path = PROJECT_ROOT / "data" / "qdrant_db"
        print(f"[Qdrant] Could not connect to server at {host}:{port} ({e}).")
        print(f"[Qdrant] Falling back to Local Disk storage mode at: {db_path}")
        os.makedirs(db_path.parent, exist_ok=True)
        return QdrantClient(path=str(db_path))

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

def load_canonical_entities() -> pd.DataFrame:
    """
    Loads raw parsed parquet datasets (HGNC, MeSH, RxNorm) and combines them.
    """
    processed_dir = PROJECT_ROOT / "data" / "processed"
    files = ["hgnc.parquet", "mesh.parquet", "rxnorm.parquet"]
    
    dfs = []
    for f in files:
        path = processed_dir / f
        if path.exists():
            dfs.append(pd.read_parquet(path))
            
    if not dfs:
        raise FileNotFoundError("No processed parquet files found in data/processed/. Run ingestion first.")
        
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["identifier"])
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
    model = SentenceTransformer(MODEL_HF_ID)
    
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
        embeddings = model.encode(batch_texts, batch_size=batch_size, show_progress_bar=False)
        
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
            
        # Upsert to Qdrant
        client.upsert(
            collection_name=COLLECTION_NAME,
            wait=True,
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
