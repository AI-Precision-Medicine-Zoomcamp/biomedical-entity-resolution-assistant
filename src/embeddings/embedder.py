import sys
import yaml
from pathlib import Path
from sentence_transformers import SentenceTransformer

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
    MODEL_HF_ID = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"
else:
    MODEL_HF_ID = EMBEDDING_MODEL_NAME

class BiomedicalEmbedder:
    """
    Responsible for loading the biomedical embedding model (e.g., SapBERT)
    and generating high-dimensional vectors (embeddings) for given texts.
    """
    def __init__(self, model_name: str = MODEL_HF_ID):
        self.model_name = model_name
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            # Device selection is handled automatically by sentence-transformers (GPU if available, else CPU)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: list[str], batch_size: int = 256, show_progress_bar: bool = False):
        """
        Generates embeddings for a list of text inputs.
        
        Args:
            texts (list[str]): List of sentences/terms to embed.
            batch_size (int): Batch size to process.
            show_progress_bar (bool): Show progress bar during embedding.
            
        Returns:
            np.ndarray: Matrix of embeddings of shape (len(texts), dimension)
        """
        if not texts:
            return []
        return self.model.encode(texts, batch_size=batch_size, show_progress_bar=show_progress_bar)
