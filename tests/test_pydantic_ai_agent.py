import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.agent.pydantic_ai_agent import PydanticAIBiomedicalAgent

def test_pydantic_ai_agent_workflow():
    agent = PydanticAIBiomedicalAgent()
    session_id = "pydantic_ai_test_session"
    
    # Run test
    res = agent.process_query("Explain MI", session_id=session_id)
    assert res["intent"] == "EXPLAIN_ENTITY"
    assert len(res["resolved_entities"]) == 1
    assert "myocardial infarction" in res["report"].lower()
