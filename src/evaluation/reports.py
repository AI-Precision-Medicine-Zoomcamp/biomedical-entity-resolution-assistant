import sys
import json
import yaml
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def save_experiment_report(
    metrics: dict,
    errors: list[dict],
    config: dict,
    run_dir: Path
) -> None:
    """
    Saves metrics.json, config.yaml, and errors.csv into the specified run directory.
    Also creates a global file in reports/errors.csv.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Save metrics.json
    metrics_path = run_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)
        
    # 2. Save config.yaml
    config_path = run_dir / "config.yaml"
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)
        
    # 3. Save errors.csv to run directory
    errors_df = pd.DataFrame(errors)
    if not errors_df.empty:
        errors_df.to_csv(run_dir / "errors.csv", index=False)
    else:
        # Create empty CSV with columns
        cols = ["Mention", "Predicted_ID", "Predicted_Canonical", "Expected_ID", "Expected_Canonical", "Confidence", "Status", "Ontology", "Reason"]
        pd.DataFrame(columns=cols).to_csv(run_dir / "errors.csv", index=False)
        
    # 4. Save global reports/errors.csv
    global_reports_dir = PROJECT_ROOT / "reports"
    global_reports_dir.mkdir(parents=True, exist_ok=True)
    
    if not errors_df.empty:
        errors_df.to_csv(global_reports_dir / "errors.csv", index=False)
    else:
        pd.DataFrame(columns=cols).to_csv(global_reports_dir / "errors.csv", index=False)
        
    print(f"Successfully saved experiment results to {run_dir}")
    print(f"Saved global error logs to {global_reports_dir / 'errors.csv'}")
