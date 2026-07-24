import re
import sys
import yaml
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.preprocessing.text_normalizer import generate_normalized_variants
from src.retrieval.embed_and_index import get_qdrant_client, COLLECTION_NAME, MODEL_HF_ID

class BiomedicalRetriever:
    """
    Hybrid Retriever combining Lexical Search (from normalized lookup table)
    and Vector Search (from Qdrant) using Reciprocal Rank Fusion (RRF).
    """
    def __init__(self):
        # Load configurations
        self.settings_path = PROJECT_ROOT / "configs" / "settings.yaml"
        try:
            with open(self.settings_path, "r") as f:
                config = yaml.safe_load(f)
        except Exception:
            config = {}
            
        self.top_k = config.get("retrieval", {}).get("top_k", 10)
        
        # Paths
        self.lookup_path = PROJECT_ROOT / "data" / "processed" / "normalized_lookup.parquet"
        
        # Lazy loaded components to prevent heavy startup if not used
        self._lookup_df = None
        self._qdrant_client = None
        self._embedding_model = None

    @property
    def lookup_df(self) -> pd.DataFrame:
        if self._lookup_df is None:
            if not self.lookup_path.exists():
                raise FileNotFoundError(
                    f"Unified lookup table not found at {self.lookup_path}. Please run preprocessing first."
                )
            # Load the lookup parquet into memory
            self._lookup_df = pd.read_parquet(self.lookup_path)
        return self._lookup_df

    @property
    def qdrant_client(self) -> QdrantClient:
        if self._qdrant_client is None:
            self._qdrant_client = get_qdrant_client()
        return self._qdrant_client

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(MODEL_HF_ID)
        return self._embedding_model

    def lexical_search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Performs lexical match based on query formatting or normalized lookup aliases.
        """
        # 1. Check if the query is an exact ID code pattern
        # MESH:D002289, HGNC:3236, RXCUI:83367, etc.
        id_pattern = r'^([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)$'
        match = re.match(id_pattern, query.strip())
        if match:
            # Look up by ID directly
            results = self.lookup_df[self.lookup_df["identifier"].str.upper() == query.strip().upper()]
            if not results.empty:
                # Deduplicate matching canonical records
                unique_records = results.drop_duplicates(subset=["identifier"]).head(limit)
                return [
                    {
                        "identifier": row.identifier,
                        "canonical_name": row.canonical_name,
                        "description": row.description,
                        "entity_type": row.entity_type,
                        "source": row.source,
                        "score": 1.0,
                        "match_type": "id_match"
                    }
                    for row in unique_records.itertuples(index=False)
                ]

        # 2. Regular lexical search using normalized variants
        variants = generate_normalized_variants(query)
        if not variants:
            return []
            
        matches = self.lookup_df[self.lookup_df["alias"].isin(variants)]
        if matches.empty:
            return []
            
        # Rank by match_type ('canonical' gets priority over 'synonym')
        matches = matches.sort_values(by=["match_type", "alias"])
        
        # Deduplicate to ensure same entity isn't returned twice
        unique_matches = matches.drop_duplicates(subset=["identifier"]).head(limit)
        
        results_list = []
        for idx, row in enumerate(unique_matches.itertuples(index=False)):
            # Score decreases slightly based on rank and match_type
            score = 1.0 if row.match_type == "canonical" else 0.8
            # Adjust score by position
            score = score / (1 + idx * 0.05)
            results_list.append({
                "identifier": row.identifier,
                "canonical_name": row.canonical_name,
                "description": row.description,
                "entity_type": row.entity_type,
                "source": row.source,
                "score": score,
                "match_type": row.match_type
            })
            
        return results_list

    def vector_search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Performs semantic vector search on Qdrant using SapBERT embeddings.
        """
        # Validate collection exists
        collections = self.qdrant_client.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)
        if not exists:
            return []
            
        # Embed query
        query_vector = self.embedding_model.encode(query).tolist()
        
        # Query Qdrant
        response = self.qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=limit
        )
        
        results_list = []
        for hit in response.points:
            payload = hit.payload
            results_list.append({
                "identifier": payload["identifier"],
                "canonical_name": payload["canonical_name"],
                "description": payload["description"],
                "entity_type": payload["entity_type"],
                "source": payload["source"],
                "score": hit.score,
                "match_type": "semantic"
            })
            
        return results_list

    def hybrid_search(self, query: str, limit: int = None, rrf_k: int = 60) -> list[dict]:
        """
        Combines Lexical Search and Vector Search using Reciprocal Rank Fusion (RRF).
        RRF Score(d) = SUM( 1 / (rrf_k + rank(d)) )
        """
        if limit is None:
            limit = self.top_k
            
        # 1. Retrieve candidates from both sources (pull more candidates than limit to allow fusion)
        fetch_limit = max(limit * 2, 20)
        
        try:
            lexical_results = self.lexical_search(query, limit=fetch_limit)
        except Exception as e:
            print(f"[Hybrid Retriever] Lexical search warning: {e}")
            lexical_results = []
            
        try:
            vector_results = self.vector_search(query, limit=fetch_limit)
        except Exception as e:
            print(f"[Hybrid Retriever] Vector search warning: {e}")
            vector_results = []
            
        # If both empty, return empty
        if not lexical_results and not vector_results:
            return []
            
        # 2. Compute RRF ranks
        # Combine items by unique identifier
        all_candidates = {}
        
        # Process Lexical results
        for rank, item in enumerate(lexical_results, 1):
            identifier = item["identifier"]
            all_candidates[identifier] = {
                "item": item,
                "lexical_rank": rank,
                "vector_rank": None
            }
            
        # Process Vector results
        for rank, item in enumerate(vector_results, 1):
            identifier = item["identifier"]
            if identifier in all_candidates:
                all_candidates[identifier]["vector_rank"] = rank
                # Preserve item detail (prefer lexical fields or merge description)
            else:
                all_candidates[identifier] = {
                    "item": item,
                    "lexical_rank": None,
                    "vector_rank": rank
                }
                
        # 3. Calculate RRF scores
        fused_results = []
        for identifier, ranks in all_candidates.items():
            item = ranks["item"]
            
            # RRF formula: 1 / (k + rank)
            rrf_score = 0.0
            methods_found = []
            
            if ranks["lexical_rank"] is not None:
                rrf_score += 1.0 / (rrf_k + ranks["lexical_rank"])
                methods_found.append("lexical")
            if ranks["vector_rank"] is not None:
                rrf_score += 1.0 / (rrf_k + ranks["vector_rank"])
                methods_found.append("vector")
                
            # Store calculated fusion metadata
            fused_item = {
                "identifier": item["identifier"],
                "canonical_name": item["canonical_name"],
                "description": item["description"],
                "entity_type": item["entity_type"],
                "source": item["source"],
                "score": rrf_score,
                "retrieval_method": "hybrid (" + "+".join(methods_found) + ")"
            }
            fused_results.append(fused_item)
            
        # 4. Sort by RRF score descending and limit results
        fused_results = sorted(fused_results, key=lambda x: x["score"], reverse=True)
        return fused_results[:limit]
