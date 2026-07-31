import sys
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.retrieval.rag_pipeline import BiomedicalRetriever
from src.embeddings.embedder import BiomedicalEmbedder
from src.evaluation.metrics import hit_rate_at_k, mean_reciprocal_rank
from src.embeddings.download_model import download_onnx_model

def evaluate_retrieval_strategies(gt_df: pd.DataFrame) -> dict:
    """
    Evaluates Lexical, Vector, and Hybrid search strategies on Qdrant.
    Returns a dictionary of metrics for each strategy.
    """
    retriever = BiomedicalRetriever()
    
    results = {
        "lexical": {"top_1": [], "top_5": [], "top_10": [], "reciprocal_ranks": []},
        "vector": {"top_1": [], "top_5": [], "top_10": [], "reciprocal_ranks": []},
        "hybrid": {"top_1": [], "top_5": [], "top_10": [], "reciprocal_ranks": []}
    }
    
    # Pre-extract target ids
    targets = gt_df["identifier"].tolist()
    mentions = gt_df["mention"].tolist()
    
    for method in ["lexical", "vector", "hybrid"]:
        retrieved_ids_list = []
        for mention in mentions:
            try:
                if method == "lexical":
                    candidates = retriever.lexical_search(mention, limit=10)
                elif method == "vector":
                    candidates = retriever.vector_search(mention, limit=10)
                else:
                    candidates = retriever.hybrid_search(mention, limit=10)
                
                retrieved_ids = [c["identifier"] for c in candidates]
            except Exception as e:
                print(f"Error in {method} search for query '{mention}': {e}")
                retrieved_ids = []
            retrieved_ids_list.append(retrieved_ids)
            
        # Compute metrics
        results[method] = {
            "hit_at_1": hit_rate_at_k(retrieved_ids_list, targets, k=1),
            "hit_at_5": hit_rate_at_k(retrieved_ids_list, targets, k=5),
            "hit_at_10": hit_rate_at_k(retrieved_ids_list, targets, k=10),
            "mrr": mean_reciprocal_rank(retrieved_ids_list, targets)
        }
        
    return results


def evaluate_embedding_models(gt_df: pd.DataFrame, model_names: list[str]) -> dict:
    """
    Compares different embedding models by performing in-memory vector search
    (cosine similarity) over the ground truth and target concepts.
    This avoids vector dimension mismatches inside the main Qdrant collection.
    """
    results = {}
    
    # Load all concepts to construct a candidate pool
    lookup_path = PROJECT_ROOT / "data" / "processed" / "normalized_lookup.parquet"
    if not lookup_path.exists():
        # Fallback if preprocessing wasn't run
        candidate_pool = gt_df.drop_duplicates(subset=["identifier"]).copy()
    else:
        # Sample some additional concepts to make the search harder
        df_lookup = pd.read_parquet(lookup_path)
        candidate_pool = df_lookup.drop_duplicates(subset=["identifier"]).copy()
        
    # Ensure all targets are present in candidate pool
    targets = gt_df["identifier"].tolist()
    target_records = candidate_pool[candidate_pool["identifier"].isin(targets)]
    
    # Filter candidate pool to ~150 concepts for speed & consistency during evaluation
    non_target_pool = candidate_pool[~candidate_pool["identifier"].isin(targets)].head(150)
    eval_pool = pd.concat([target_records, non_target_pool]).drop_duplicates(subset=["identifier"])
    
    pool_texts = eval_pool["canonical_name"].tolist()
    pool_ids = eval_pool["identifier"].tolist()
    
    mentions = gt_df["mention"].tolist()
    
    for model_name in model_names:
        print(f"Evaluating embedding model: {model_name}...")
        # Automatically download model if not exists
        model_path = PROJECT_ROOT / "models" / model_name
        if not model_path.exists():
            try:
                download_onnx_model(repo_id=model_name)
            except Exception as e:
                print(f"Warning: Failed to download model {model_name}: {e}. Skipping model.")
                continue
                
        try:
            embedder = BiomedicalEmbedder(model_name=model_name)
            
            # Embed pool and mentions
            pool_embeddings = embedder.embed_texts(pool_texts)
            mention_embeddings = embedder.embed_texts(mentions)
            
            # Normalize for cosine similarity
            pool_norms = np.linalg.norm(pool_embeddings, axis=1, keepdims=True)
            pool_normed = pool_embeddings / np.clip(pool_norms, 1e-12, None)
            
            mention_norms = np.linalg.norm(mention_embeddings, axis=1, keepdims=True)
            mention_normed = mention_embeddings / np.clip(mention_norms, 1e-12, None)
            
            # Similarity matrix: [num_mentions, num_pool]
            sim_matrix = np.dot(mention_normed, pool_normed.T)
            
            retrieved_ids_list = []
            for i in range(len(mentions)):
                # Get indices sorted descending
                sorted_idx = np.argsort(sim_matrix[i])[::-1]
                # Map to identifiers
                sorted_ids = [pool_ids[idx] for idx in sorted_idx[:10]]
                retrieved_ids_list.append(sorted_ids)
                
            results[model_name] = {
                "hit_at_1": hit_rate_at_k(retrieved_ids_list, targets, k=1),
                "hit_at_5": hit_rate_at_k(retrieved_ids_list, targets, k=5),
                "hit_at_10": hit_rate_at_k(retrieved_ids_list, targets, k=10),
                "mrr": mean_reciprocal_rank(retrieved_ids_list, targets)
            }
        except Exception as e:
            print(f"Error evaluating model {model_name}: {e}")
            
    return results

if __name__ == "__main__":
    from src.evaluation.datasets import load_ground_truth
    df = load_ground_truth()
    print("--- Evaluating Search Strategies ---")
    print(evaluate_retrieval_strategies(df))
    
    print("\n--- Comparing Embedding Models ---")
    models = ["Xenova/SapBERT-from-PubMedBERT-fulltext", "Xenova/all-MiniLM-L6-v2"]
    print(evaluate_embedding_models(df, models))
