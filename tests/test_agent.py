import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.agent.agent import BiomedicalAgent

def test_agent_single_entity():
    agent = BiomedicalAgent()
    res = agent.process_query("Tell me about MI", session_id="test_session_1")
    assert res["intent"] == "EXPLAIN_ENTITY"
    assert len(res["resolved_entities"]) == 1
    assert res["resolved_entities"][0]["canonical_name"] == "Myocardial Infarction"
    assert "Myocardial Infarction" in res["report"]
    assert "PubMed" in res["report"]

def test_agent_pronoun_memory():
    agent = BiomedicalAgent()
    session_id = "test_session_2"
    
    # 1. Resolve MI first
    res1 = agent.process_query("Explain MI", session_id=session_id)
    assert len(res1["resolved_entities"]) == 1
    
    # 2. Reference it in next query
    res2 = agent.process_query("Compare it with Tylenol", session_id=session_id)
    assert res2["enriched_query"] == "Compare Myocardial Infarction with Tylenol"
    assert res2["intent"] == "COMPARE_ENTITIES"
    assert len(res2["resolved_entities"]) == 2
    assert "Myocardial Infarction" in res2["report"]
    assert "acetaminophen" in res2["report"].lower()

def test_agent_fallback():
    agent = BiomedicalAgent()
    res = agent.process_query("Some unknown query about space travel", session_id="test_session_3")
    assert res["intent"] == "EXPLAIN_TEXT"
    assert len(res["resolved_entities"]) == 0
    assert "space travel" in res["report"]

def test_agent_standalone_report_resolution():
    agent = BiomedicalAgent()
    session_id = "test_session_4"
    
    # 1. Ask about MI
    res1 = agent.process_query("Explain MI", session_id=session_id)
    assert len(res1["resolved_entities"]) == 1
    
    # 2. Command 'generate a report'
    res2 = agent.process_query("generate a report", session_id=session_id)
    assert res2["enriched_query"] == "generate a report for Myocardial Infarction"
