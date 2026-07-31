import numpy as np

def hit_rate_at_k(retrieved_list: list[list[str]], target_list: list[str], k: int) -> float:
    """
    Computes Hit Rate@K.
    For each query, hit = 1 if target is in the top-K retrieved items, else 0.
    Returns the average hit rate across all queries.
    """
    hits = 0
    total = len(target_list)
    if total == 0:
        return 0.0

    for retrieved, target in zip(retrieved_list, target_list):
        # Slice to top K
        top_k = retrieved[:k]
        if target in top_k:
            hits += 1

    return hits / total

def mean_reciprocal_rank(retrieved_list: list[list[str]], target_list: list[str]) -> float:
    """
    Computes Mean Reciprocal Rank (MRR).
    For each query, RR = 1 / rank (1-indexed) of the target in the retrieved items.
    If target is not found in retrieved list, RR = 0.
    Returns the average reciprocal rank across all queries.
    """
    rr_sum = 0.0
    total = len(target_list)
    if total == 0:
        return 0.0

    for retrieved, target in zip(retrieved_list, target_list):
        if target in retrieved:
            rank = retrieved.index(target) + 1
            rr_sum += 1.0 / rank

    return rr_sum / total

def compute_classification_metrics(predictions: list[str], expected: list[str]) -> dict:
    """
    Computes Precision, Recall, F1 Score, and Top-1 Accuracy for entity resolution.
    predictions: List of predicted identifiers (or empty string/None if no resolution occurred)
    expected: List of target identifiers
    """
    total = len(expected)
    if total == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "accuracy": 0.0}

    # Clean predicted/expected
    preds = [p if p is not None else "" for p in predictions]
    exps = [e if e is not None else "" for e in expected]

    # Calculate True Positives, False Positives, False Negatives
    tp = 0
    fp = 0
    fn = 0
    tn = 0  # not really applicable to multi-class NER without negative class, but we can treat empty/non-empty cases

    for p, e in zip(preds, exps):
        if p == e:
            if e != "":
                tp += 1
            else:
                tn += 1
        else:
            if p != "" and e != "":
                # Wrong prediction
                fp += 1
                fn += 1
            elif p != "" and e == "":
                # Hallucination / false positive
                fp += 1
            elif p == "" and e != "":
                # Missed entity / false negative
                fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # Accuracy is simply fraction of exact matches
    correct = sum(1 for p, e in zip(preds, exps) if p == e)
    accuracy = correct / total

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "tp": tp,
        "fp": fp,
        "fn": fn
    }
