import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.tools import (
    resolve_entity,
    retrieve_concept,
    search_literature,
    compare_entities,
    generate_report,
)

def test_resolve_entity_tool():
    results = resolve_entity("Patients diagnosed with MI.")
    assert len(results) > 0
    assert results[0]["canonical_name"] == "Myocardial Infarction"

def test_retrieve_concept_tool():
    concept = retrieve_concept("MESH:D009203")
    assert concept["canonical_name"] == "Myocardial Infarction"
    assert concept["entity_type"] == "Disease"

def test_search_literature_tool():
    articles = search_literature("myocardial infarction", limit=1)
    assert len(articles) > 0
    assert "title" in articles[0]
    assert "pmid" in articles[0]

def test_compare_entities_tool():
    ent1 = retrieve_concept("MESH:D009203")
    ent2 = {
        "canonical_name": "Cardiac Arrest",
        "entity_type": "Disease",
        "source": "MeSH",
        "synonyms": "Cardiac Arrest|Heart Stop",
        "description": "Sudden cessation of cardiac output."
    }
    comparison = compare_entities(ent1, ent2)
    assert comparison["concept_a"] == "Myocardial Infarction"
    assert comparison["concept_b"] == "Cardiac Arrest"
    assert comparison["same_type"] is True

def test_generate_report_tool():
    resolved = resolve_entity("MI and Tylenol")
    lit = search_literature("Myocardial Infarction", limit=1)
    report = generate_report("MI and Tylenol case study", resolved, lit)
    assert "# Biomedical Analysis & Clinical Report" in report
    assert "Executive Summary" in report
    assert "Myocardial Infarction" in report
