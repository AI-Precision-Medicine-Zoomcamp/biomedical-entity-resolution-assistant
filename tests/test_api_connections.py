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
