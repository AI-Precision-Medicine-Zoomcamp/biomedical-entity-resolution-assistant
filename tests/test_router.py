import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.agent.router import WorkflowRouter

def test_workflow_router():
    router = WorkflowRouter()
    
    # Simple queries
    assert router.route("What does MI stand for?") == "SIMPLE_RESOLUTION"
    assert router.route("Define TP53") == "SIMPLE_RESOLUTION"
    assert router.route("Resolve EGFR") == "SIMPLE_RESOLUTION"
    assert router.route("MI") == "SIMPLE_RESOLUTION"
    assert router.route("TP53 and BRCA1") == "SIMPLE_RESOLUTION"
    
    # Complex queries
    assert router.route("Compare EGFR with BRCA1") == "COMPLEX_AGENT"
    assert router.route("Analyze this oncology paper and summarize all gene-disease interactions.") == "COMPLEX_AGENT"
    assert router.route("What is the relation between TP53 and cancer?") == "COMPLEX_AGENT"
    assert router.route("Explain the difference between Tylenol and Aspirin") == "COMPLEX_AGENT"
