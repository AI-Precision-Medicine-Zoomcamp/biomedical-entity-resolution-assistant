import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GT_PATH = PROJECT_ROOT / "data" / "ground_truth" / "entity_resolution.csv"

def load_ground_truth(file_path: str = None) -> pd.DataFrame:
    """
    Loads the ground truth CSV file into a pandas DataFrame.
    """
    if file_path is None:
        path = DEFAULT_GT_PATH
    else:
        path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Ground truth dataset not found at {path}. "
            "Please make sure you have generated the ground truth dataset first."
        )

    df = pd.read_csv(path)
    # Ensure standard columns are present
    required_cols = ["mention", "canonical", "ontology", "identifier"]
    for col in required_cols:
        if col not in df.columns:
            # If identifier is missing, we can map/default it
            if col == "identifier":
                df["identifier"] = ""
            else:
                raise ValueError(f"Ground truth dataset is missing required column: {col}")
                
    return df

if __name__ == "__main__":
    df = load_ground_truth()
    print(f"Loaded ground truth dataset with {len(df)} records.")
    print(df.head())
