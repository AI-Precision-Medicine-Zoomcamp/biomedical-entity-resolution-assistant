import os
import sys
from pathlib import Path
import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import src.utils.mock_torchvision
from src.embeddings.embedder import BiomedicalEmbedder
from src.retrieval.embed_and_index import get_qdrant_client, COLLECTION_NAME, get_deterministic_uuid
from qdrant_client.models import PointStruct

def index_remaining():
    client = get_qdrant_client()
    processed_dir = PROJECT_ROOT / "data" / "processed"
    files = ["hgnc.parquet", "mesh.parquet", "rxnorm.parquet"]
    
    dfs = []
    for f in files:
        path = processed_dir / f
        if path.exists():
            dfs.append(pd.read_parquet(path))
            
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["identifier"])
    
    print(f"Total entities: {len(combined)}")
    
    # Get current collection count
    count_res = client.count(collection_name=COLLECTION_NAME)
    print(f"Current Qdrant count: {count_res.count}")
    
    # Let's index from index 45000 to the end
    remaining_df = combined.iloc[45000:].copy()
    total_remaining = len(remaining_df)
    print(f"Remaining entities to index: {total_remaining}")
    
    model = BiomedicalEmbedder()
    
    texts = []
    for row in remaining_df.itertuples(index=False):
        synonyms_str = row.synonyms if pd.notna(row.synonyms) and row.synonyms else "None"
        desc_str = row.description if pd.notna(row.description) and row.description else "No description"
        text = f"Concept: {row.canonical_name}. Synonyms: {synonyms_str.replace('|', ', ')}. Description: {desc_str}."
        texts.append(text)
        
    remaining_df["text_to_embed"] = texts
    
    batch_size = 256
    for i in tqdm(range(0, total_remaining, batch_size), desc="Indexing Remaining"):
        batch_df = remaining_df.iloc[i : i + batch_size]
        batch_texts = batch_df["text_to_embed"].tolist()
        
        embeddings = model.embed_texts(batch_texts, batch_size=batch_size, show_progress_bar=False)
        
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
            
        client.upsert(
            collection_name=COLLECTION_NAME,
            wait=True,  # wait=True to be sure they are indexed
            points=points
        )
        
    print("Done indexing remaining entities!")

if __name__ == "__main__":
    index_remaining()
