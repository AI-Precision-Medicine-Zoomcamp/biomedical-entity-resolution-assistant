import sys
import yaml
from pathlib import Path
from typing import List
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Load configuration settings
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

class ONNXEmbedder:
    def __init__(self, model_path: Path):
        tokenizer_file = model_path / "tokenizer.json"
        onnx_file = model_path / "model.onnx"
        if not onnx_file.exists():
            onnx_file = model_path / "onnx" / "model.onnx"

        if not tokenizer_file.exists() or not onnx_file.exists():
            print(f"[ONNXEmbedder] Model files not found in {model_path}. Attempting to download automatically...")
            try:
                from src.embeddings.download_model import download_onnx_model
                try:
                    repo_id = str(model_path.relative_to(PROJECT_ROOT / "models"))
                except ValueError:
                    repo_id = MODEL_HF_ID
                download_onnx_model(repo_id=repo_id, out_dir="models")
            except Exception as download_error:
                raise FileNotFoundError(
                    f"Model files not found in {model_path} and auto-download failed: {download_error}. "
                    f"Please run model downloading step: 'make download-models' or 'python src/embeddings/download_model.py'."
                ) from download_error

            # Recheck after download
            tokenizer_file = model_path / "tokenizer.json"
            onnx_file = model_path / "model.onnx"
            if not onnx_file.exists():
                onnx_file = model_path / "onnx" / "model.onnx"

        self.tokenizer = Tokenizer.from_file(str(tokenizer_file))
        self.session = ort.InferenceSession(
            str(onnx_file),
            providers=["CPUExecutionProvider"],
        )
        self.input_names = [x.name for x in self.session.get_inputs()]

    @staticmethod
    def _mean_pool(last_hidden_state: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        # last_hidden_state: [batch, seq_len, hidden]
        # attention_mask:   [batch, seq_len]
        mask = attention_mask[..., None].astype(np.float32)  # [batch, seq_len, 1]
        summed = (last_hidden_state * mask).sum(axis=1)      # [batch, hidden]
        counts = np.clip(mask.sum(axis=1), 1e-9, None)       # [batch, 1]
        return summed / counts

    @staticmethod
    def _l2_normalize(x: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(x, axis=1, keepdims=True)
        norms = np.clip(norms, 1e-12, None)
        return x / norms

    def encode_batch(self, texts: List[str], max_length: int = 512) -> np.ndarray:
        encodings = self.tokenizer.encode_batch(texts)

        input_ids = []
        attention_mask = []

        for enc in encodings:
            ids = enc.ids[:max_length]
            mask = enc.attention_mask[:max_length]

            input_ids.append(ids)
            attention_mask.append(mask)

        # pad to max seq length in batch
        max_len = max(len(ids) for ids in input_ids)

        padded_ids = []
        padded_mask = []
        for ids, mask in zip(input_ids, attention_mask):
            pad_len = max_len - len(ids)
            padded_ids.append(ids + [0] * pad_len)
            padded_mask.append(mask + [0] * pad_len)

        input_ids_np = np.array(padded_ids, dtype=np.int64)
        attention_mask_np = np.array(padded_mask, dtype=np.int64)

        # Build dynamic input dict
        inputs = {
            "input_ids": input_ids_np,
            "attention_mask": attention_mask_np,
        }
        if "token_type_ids" in self.input_names:
            inputs["token_type_ids"] = np.zeros_like(input_ids_np, dtype=np.int64)

        outputs = self.session.run(None, inputs)

        # For sentence-transformer ONNX exports, first output is usually token embeddings
        last_hidden_state = outputs[0]  # [batch, seq_len, hidden]
        pooled = self._mean_pool(last_hidden_state, attention_mask_np)
        normalized = self._l2_normalize(pooled)
        return normalized.astype(np.float32)

class BiomedicalEmbedder:
    """
    Drop-in replacement using ONNX Runtime instead of SentenceTransformers/PyTorch.
    """
    def __init__(self, model_name: str = MODEL_HF_ID):
        model_path = PROJECT_ROOT / "models" / model_name
        self.embedder = ONNXEmbedder(model_path)

    def embed_texts(self, texts: List[str], batch_size: int = 256, max_length: int = 128, show_progress_bar: bool = False) -> np.ndarray:
        if not texts:
            return np.array([], dtype=np.float32)
        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.embedder.encode_batch(batch, max_length=max_length)
            all_embeddings.append(embeddings)
        return np.vstack(all_embeddings)
