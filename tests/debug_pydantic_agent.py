import os
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Load dotenv
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Seed Qdrant
from qdrant_client.models import Distance, VectorParams, PointStruct
from src.embeddings.embedder import BiomedicalEmbedder
from src.retrieval.embed_and_index import get_qdrant_client, COLLECTION_NAME, get_deterministic_uuid, MODEL_HF_ID
from src.retrieval.rag_pipeline import BiomedicalRetriever

# Patch lookup table
orig_path = BiomedicalRetriever().lookup_path
df = pd.read_parquet(orig_path)
df = df[~df["alias"].isin(["mi", "tylenol", "nsclc", "ex19del", "tp53", "egfr", "her1"])]
test_rows = pd.DataFrame([
    {"alias": "mi", "identifier": "MESH:D009203", "canonical_name": "Myocardial Infarction", "entity_type": "Disease", "source": "MESH", "match_type": "synonym", "description": "Necrosis of the myocardium caused by an obstruction of the blood supply to the heart."},
    {"alias": "tylenol", "identifier": "RXCUI:161", "canonical_name": "Acetaminophen", "entity_type": "Medication", "source": "RXCUI", "match_type": "synonym", "description": "A non-salicylate analgesic and antipyretic agent."},
])
patched_df = pd.concat([df, test_rows], ignore_index=True)
@property
def patched_lookup_df_prop(self):
    return patched_df
BiomedicalRetriever.lookup_df = patched_lookup_df_prop

client = get_qdrant_client()
collections = client.get_collections().collections
exists = any(c.name == COLLECTION_NAME for c in collections)
if not exists:
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )

points_res, _ = client.scroll(collection_name=COLLECTION_NAME, limit=1)
if len(points_res) == 0:
    test_entities = [
        {"identifier": "MESH:D009203", "canonical_name": "Myocardial Infarction", "description": "Necrosis of the myocardium caused by an obstruction of the blood supply to the heart.", "synonyms": "Myocardial Infarction|MI|heart attack", "entity_type": "Disease", "source": "MESH"},
        {"identifier": "RXCUI:161", "canonical_name": "Acetaminophen", "description": "A non-salicylate analgesic and antipyretic agent.", "synonyms": "Acetaminophen|Tylenol|paracetamol", "entity_type": "Medication", "source": "RXCUI"}
    ]
    embedder = BiomedicalEmbedder(MODEL_HF_ID)
    texts = [f"Concept: {e['canonical_name']}. Synonyms: {e['synonyms'].replace('|', ', ')}. Description: {e['description']}." for e in test_entities]
    embeddings = embedder.embed_texts(texts, batch_size=len(texts))
    points = [PointStruct(id=get_deterministic_uuid(e["identifier"]), vector=v.tolist(), payload=e) for e, v in zip(test_entities, embeddings)]
    client.upsert(collection_name=COLLECTION_NAME, wait=True, points=points)

# Run Agent
from src.agent.pydantic_ai_agent import PydanticAIBiomedicalAgent, pydantic_agent
agent = PydanticAIBiomedicalAgent()
res = pydantic_agent.run_sync("Explain MI")
print("\n" + "="*50)
print("AGENT OUTPUT:")
print("="*50)
print(res.output)
print("\n" + "="*50)
print("AGENT MESSAGES:")
print("="*50)
for msg in res.new_messages():
    print(msg)
