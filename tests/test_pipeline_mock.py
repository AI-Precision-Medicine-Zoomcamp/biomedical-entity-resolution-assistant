import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.retrieval.base_retriever import BaseRetrievalService
from src.entity_resolution.pipeline import BiomedicalEntityResolverPipeline

class MockRetrievalService(BaseRetrievalService):
    def lexical_search(self, query: str, limit: int = 10) -> list[dict]:
        return []

    def vector_search(self, query: str, limit: int = 10, min_score: float = 0.70) -> list[dict]:
        return []

    def hybrid_search(self, query: str, limit: int = None) -> list[dict]:
        # Return a custom mock candidate for testing dependency injection
        return [{
            "identifier": "MOCK:123",
            "canonical_name": "Mocked Cancer Disease",
            "description": "A mocked concept for unit testing",
            "entity_type": "Disease",
            "source": "MockOntology",
            "synonyms": "mocked cancer|mock disease",
            "score": 1.0,
            "retrieval_method": "hybrid_rrf"
        }]

def test_pipeline_with_mock_retriever():
    mock_service = MockRetrievalService()
    pipeline = BiomedicalEntityResolverPipeline(retrieval_service=mock_service)
    
    # We resolve a test string
    results = pipeline.resolve_text("Patients diagnosed with mock disease.")
    
    # Verify the mock candidate is resolved
    assert len(results) > 0
    assert results[0]["canonical_name"] == "Mocked Cancer Disease"
    assert results[0]["ontology"] == "MockOntology"
    assert results[0]["identifier"] == "MOCK:123"
