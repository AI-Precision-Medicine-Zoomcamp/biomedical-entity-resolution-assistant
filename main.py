import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(
    title="Biomedical Entity Resolution Assistant API",
    description="Resolves biomedical entities to standard representations",
    version="0.1.0"
)

class ResolutionRequest(BaseModel):
    query: str

class ResolutionResponse(BaseModel):
    query: str
    canonical_name: str
    entity_type: str
    identifier: str
    confidence: float
    source: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the Biomedical Entity Resolution Assistant API. Use POST /resolve to resolve entities."}

@app.post("/resolve", response_model=ResolutionResponse)
def resolve_entity(request: ResolutionRequest):
    query = request.query
    query_upper = query.upper().strip()
    
    # Basic mock resolution for demo purposes
    if query_upper in ["HER1", "ERBB1", "EGFR"]:
        return ResolutionResponse(
            query=query,
            canonical_name="EGFR",
            entity_type="Gene",
            identifier="HGNC:3236",
            confidence=0.99,
            source="HGNC"
        )
    elif query_upper in ["NSCLC", "NON-SMALL CELL LUNG CANCER"]:
        return ResolutionResponse(
            query=query,
            canonical_name="Non-Small Cell Lung Cancer",
            entity_type="Disease",
            identifier="MONDO:0008903",
            confidence=0.95,
            source="MONDO"
        )
    elif query_upper in ["EX19DEL", "EGFR EXON 19 DELETION"]:
        return ResolutionResponse(
            query=query,
            canonical_name="EGFR Exon 19 Deletion",
            entity_type="Variant",
            identifier="ClinVar:16209",
            confidence=0.90,
            source="ClinVar"
        )
    else:
        return ResolutionResponse(
            query=query,
            canonical_name=query,
            entity_type="Unknown",
            identifier="Unknown",
            confidence=0.0,
            source="None"
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
