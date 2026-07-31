import sys
import yaml
from pathlib import Path
from huggingface_hub import hf_hub_download

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Load config
SETTINGS_PATH = PROJECT_ROOT / "configs" / "settings.yaml"
try:
    with open(SETTINGS_PATH, "r") as f:
        config = yaml.safe_load(f)
except Exception:
    config = {}

EMBEDDING_MODEL_NAME = config.get("embedding", {}).get("model", "sapbert")
if EMBEDDING_MODEL_NAME == "sapbert":
    MODEL_HF_ID = "Xenova/SapBERT-from-PubMedBERT-fulltext"
else:
    MODEL_HF_ID = EMBEDDING_MODEL_NAME

def download_onnx_model(
    repo_id: str = MODEL_HF_ID,
    out_dir: str = "models",
):
    """
    Downloads tokenizer.json and model.onnx into:
      {out_dir}/{repo_id}/
    """
    model_dir = PROJECT_ROOT / out_dir / repo_id
    model_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading tokenizer.json and model.onnx from Hugging Face: {repo_id}...")
    tokenizer_path = hf_hub_download(
        repo_id=repo_id,
        filename="tokenizer.json",
        local_dir=str(model_dir),
        local_dir_use_symlinks=False,
    )
    
    try:
        onnx_path = hf_hub_download(
            repo_id=repo_id,
            filename="model.onnx",
            local_dir=str(model_dir),
            local_dir_use_symlinks=False,
        )
    except Exception as e:
        print("model.onnx not found at root, trying onnx/model.onnx...")
        onnx_path = hf_hub_download(
            repo_id=repo_id,
            filename="onnx/model.onnx",
            local_dir=str(model_dir),
            local_dir_use_symlinks=False,
        )
    return tokenizer_path, onnx_path

if __name__ == "__main__":
    download_onnx_model()
    print("Download completed successfully!")
