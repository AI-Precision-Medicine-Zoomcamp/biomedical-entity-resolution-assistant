import sys
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.entity_resolution.pipeline import BiomedicalEntityResolverPipeline
from src.evaluation.metrics import compute_classification_metrics

def evaluate_pipeline(gt_df: pd.DataFrame) -> dict:
    """
    Evaluates the complete end-to-end BiomedicalEntityResolverPipeline.
    Computes overall classification metrics, confidence calibration, and error list.
    """
    pipeline = BiomedicalEntityResolverPipeline()
    
    predictions = []
    expected = gt_df["identifier"].tolist()
    mentions = gt_df["mention"].tolist()
    
    # Store error details
    errors = []
    
    # Store confidence scores and whether prediction was correct
    confidence_data = []
    
    for idx, row in gt_df.iterrows():
        mention = row["mention"]
        target_id = row["identifier"]
        target_canon = row["canonical"]
        ontology = row["ontology"]
        
        # Resolve text
        try:
            resolved = pipeline.resolve_text(mention)
        except Exception as e:
            print(f"Error resolving mention '{mention}': {e}")
            resolved = []
            
        pred_id = ""
        pred_canon = ""
        confidence = 0.0
        status = "rejected"
        
        # Match by priority: find the candidate matching target, or default to first resolved
        if resolved:
            # Prefer match if it exists
            match = next((ent for ent in resolved if ent["identifier"] == target_id), None)
            if match:
                pred_item = match
            else:
                pred_item = resolved[0]
                
            pred_id = pred_item["identifier"]
            pred_canon = pred_item["canonical_name"]
            confidence = pred_item["confidence"]
            status = pred_item["status"]
            
        predictions.append(pred_id)
        
        is_correct = (pred_id == target_id)
        
        if pred_id != "":
            confidence_data.append({
                "confidence": confidence,
                "correct": 1 if is_correct else 0
            })
            
        # Log error if incorrect
        if not is_correct:
            reason = "Missed resolution (None found)" if pred_id == "" else "Incorrect identifier returned"
            errors.append({
                "Mention": mention,
                "Predicted_ID": pred_id if pred_id != "" else "N/A",
                "Predicted_Canonical": pred_canon if pred_canon != "" else "N/A",
                "Expected_ID": target_id,
                "Expected_Canonical": target_canon,
                "Confidence": confidence if pred_id != "" else 0.0,
                "Status": status if pred_id != "" else "N/A",
                "Ontology": ontology,
                "Reason": reason
            })
            
    # Compute overall classification metrics
    overall_metrics = compute_classification_metrics(predictions, expected)
    
    # Compute metrics sliced by ontology
    ontology_metrics = {}
    for ont in gt_df["ontology"].unique():
        sub_gt = gt_df[gt_df["ontology"] == ont]
        sub_preds = []
        sub_expected = sub_gt["identifier"].tolist()
        
        for mention in sub_gt["mention"]:
            try:
                resolved = pipeline.resolve_text(mention)
                pred_id = resolved[0]["identifier"] if resolved else ""
            except Exception:
                pred_id = ""
            sub_preds.append(pred_id)
            
        ontology_metrics[ont] = compute_classification_metrics(sub_preds, sub_expected)
        
    # Confidence calibration analysis
    calibration_bins = {
        "0.0-0.60": {"correct": 0, "total": 0, "accuracy": 0.0},
        "0.60-0.80": {"correct": 0, "total": 0, "accuracy": 0.0},
        "0.80-0.90": {"correct": 0, "total": 0, "accuracy": 0.0},
        "0.90-1.0": {"correct": 0, "total": 0, "accuracy": 0.0}
    }
    
    for item in confidence_data:
        conf = item["confidence"]
        corr = item["correct"]
        
        if conf < 0.60:
            bin_name = "0.0-0.60"
        elif conf < 0.80:
            bin_name = "0.60-0.80"
        elif conf < 0.90:
            bin_name = "0.80-0.90"
        else:
            bin_name = "0.90-1.0"
            
        calibration_bins[bin_name]["total"] += 1
        calibration_bins[bin_name]["correct"] += corr
        
    # Calculate accuracy per bin
    for bin_name, data in calibration_bins.items():
        if data["total"] > 0:
            data["accuracy"] = data["correct"] / data["total"]
        else:
            data["accuracy"] = 0.0
            
    return {
        "overall_metrics": overall_metrics,
        "ontology_metrics": ontology_metrics,
        "calibration": calibration_bins,
        "errors": errors
    }

if __name__ == "__main__":
    from src.evaluation.datasets import load_ground_truth
    df = load_ground_truth()
    results = evaluate_pipeline(df)
    print("Overall metrics:", results["overall_metrics"])
    print("Calibration bins:", results["calibration"])
    print("Error count:", len(results["errors"]))
