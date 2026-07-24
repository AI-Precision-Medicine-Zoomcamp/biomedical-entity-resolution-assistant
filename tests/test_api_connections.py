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
    assert data["canonical_name"] == "Non-Small Cell Lung Cancer"
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
    assert mi_item["entity_type"] == "Disease"
    assert mi_item["identifier"] == "MESH:D009203"
    
    # Verify Tylenol resolved correctly
    tylenol_item = [item for item in data if item["mention"] == "Tylenol"][0]
    assert tylenol_item["canonical_name"] == "Acetaminophen"
    assert tylenol_item["entity_type"] == "Medication"
    assert tylenol_item["identifier"] == "RXCUI:161"
    
    # Verify TP53 resolved correctly
    tp53_item = [item for item in data if item["mention"] == "TP53"][0]
    assert tp53_item["canonical_name"] == "Tumor Protein P53"
    assert tp53_item["entity_type"] == "Gene"
    assert tp53_item["identifier"] == "HGNC:11998"
