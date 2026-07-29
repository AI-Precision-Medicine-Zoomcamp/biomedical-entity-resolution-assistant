from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_resolve_gene():
    response = client.post("/resolve", json={"query": "HER1"})
    assert response.status_code == 200
    data = response.json()
    assert data["canonical_name"] == "EGFR"
    assert data["entity_type"] == "Gene"
    assert data["identifier"] == "HGNC:3236"

def test_resolve_disease():
    response = client.post("/resolve", json={"query": "NSCLC"})
    assert response.status_code == 200
    data = response.json()
    assert data["canonical_name"] == "Carcinoma, Non-Small-Cell Lung"
    assert data["entity_type"] == "Disease"

def test_resolve_variant():
    response = client.post("/resolve", json={"query": "Ex19del"})
    assert response.status_code == 200
    data = response.json()
    assert data["canonical_name"] == "EGFR Exon 19 Deletion"
    assert data["entity_type"] == "Variant"

def test_resolve_text_endpoint():
    response = client.post("/resolve-text", json={
        "text": "Patients diagnosed with MI were given Tylenol. The TP53 mutation was also observed."
    })
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    
    # Verify MI resolved correctly
    mi_item = [item for item in data if item["mention"] == "MI"][0]
    assert mi_item["canonical_name"] == "Myocardial Infarction"
    assert mi_item["canonical"] == "Myocardial Infarction"
    assert mi_item["entity_type"] == "Disease"
    assert mi_item["identifier"] == "MESH:D009203"
    assert mi_item["concept_id"] == "D009203"
    assert mi_item["status"] in ["resolved", "needs_review", "rejected"]
    assert isinstance(mi_item["reason"], list)
    
    # Verify Tylenol resolved correctly
    tylenol_item = [item for item in data if item["mention"] == "Tylenol"][0]
    assert tylenol_item["canonical_name"].lower() == "acetaminophen"
    assert tylenol_item["canonical"].lower() == "acetaminophen"
    assert tylenol_item["entity_type"] == "Medication"
    assert tylenol_item["identifier"] == "RXCUI:161"
    assert tylenol_item["concept_id"] == "161"
    assert tylenol_item["status"] in ["resolved", "needs_review", "rejected"]
    assert isinstance(tylenol_item["reason"], list)
    
    # Verify TP53 resolved correctly
    tp53_item = [item for item in data if item["mention"] == "TP53"][0]
    assert tp53_item["canonical_name"].upper() in ["TP53", "TUMOR PROTEIN P53"]
    assert tp53_item["canonical"].upper() in ["TP53", "TUMOR PROTEIN P53"]
    assert tp53_item["entity_type"] == "Gene"
    assert tp53_item["identifier"] == "HGNC:11998"
    assert tp53_item["concept_id"] == "11998"
    assert tp53_item["status"] in ["resolved", "needs_review", "rejected"]
    assert isinstance(tp53_item["reason"], list)

def test_resolve_rag_endpoint():
    response = client.post("/resolve-rag", json={
        "text": "Patients diagnosed with MI were given Tylenol."
    })
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Patients diagnosed with MI were given Tylenol."
    assert len(data["resolved_entities"]) == 2
    assert "Myocardial Infarction" in data["literature"]
    assert any(k.lower() == "acetaminophen" for k in data["literature"])
    assert len(data["merged_context"]) > 0
    assert len(data["report"]) > 0
    assert "Biomedical Analysis & Clinical Report" in data["report"]

def test_agent_endpoint():
    response1 = client.post("/agent/query", json={
        "query": "Tell me about MI",
        "session_id": "test_api_session"
    })
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["session_id"] == "test_api_session"
    assert data1["intent"] == "SIMPLE_RESOLUTION"
    assert len(data1["resolved_entities"]) == 1
    assert "Myocardial Infarction" in data1["report"]

    response2 = client.post("/agent/query", json={
        "query": "Compare it with Tylenol",
        "session_id": "test_api_session"
    })
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["enriched_query"] == "Compare Myocardial Infarction with Tylenol"
    assert data2["intent"] == "COMPARE_ENTITIES"
    assert len(data2["resolved_entities"]) == 2
