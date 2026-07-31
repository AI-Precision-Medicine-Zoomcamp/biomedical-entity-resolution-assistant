import sys
import uuid
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

import uvicorn
try:
    from fastapi import FastAPI
except ImportError:  # pragma: no cover
    from starlette.applications import Starlette as FastAPI
from pydantic import BaseModel

# Custom local imports
from src.retrieval.rag_pipeline import BiomedicalRetriever
from src.entity_resolution.pipeline import BiomedicalEntityResolverPipeline
from src.entity_resolution.multi_source_rag import MultiSourceRAG
from src.agent.pydantic_ai_agent import PydanticAIBiomedicalAgent
from src.agent.router import WorkflowRouter
from src.tools import generate_report

app = FastAPI(
    title="Biomedical Entity Resolution Assistant API",
    description="Resolves biomedical entities to standard representations",
    version="0.1.0"
)

# Instantiate the retriever
retriever = BiomedicalRetriever()

class ResolutionRequest(BaseModel):
    query: str

class ResolutionResponse(BaseModel):
    query: str
    canonical_name: str
    entity_type: str
    identifier: str
    confidence: float
    source: str

class CandidateResolution(BaseModel):
    identifier: str
    canonical_name: str
    description: str
    entity_type: str
    source: str
    score: float
    retrieval_method: str

class SearchResponse(BaseModel):
    query: str
    results: List[CandidateResolution]

resolver_pipeline = None
rag_pipeline = None
agent_instance = None
router_instance = None

def get_resolver():
    global resolver_pipeline
    if resolver_pipeline is None:
        resolver_pipeline = BiomedicalEntityResolverPipeline()
    return resolver_pipeline

def get_rag_pipeline():
    global rag_pipeline
    if rag_pipeline is None:
        rag_pipeline = MultiSourceRAG()
    return rag_pipeline

def get_agent():
    global agent_instance
    if agent_instance is None:
        agent_instance = PydanticAIBiomedicalAgent()
    return agent_instance

def get_router():
    global router_instance
    if router_instance is None:
        router_instance = WorkflowRouter()
    return router_instance

def generate_conversational_response(query_text: str, resolved_entities: list) -> str:
    if not resolved_entities:
        return (
            "I am a specialized Biomedical Entity Resolution Assistant. I couldn't identify any clinical terms, "
            "genes, variants, or drugs in your query, which appears to be outside my medical domain. "
            "Please specify a clinical term or ask a biomedical question!"
        )
    
    parts = []
    parts.append(f"I analyzed your query and identified the following biomedical concept(s):\n")
    for ent in resolved_entities:
        if isinstance(ent, dict):
            mention = ent.get("mention", "")
            canonical = ent.get("canonical_name", ent.get("canonical", ""))
            etype = ent.get("entity_type", "Concept")
            oid = ent.get("identifier", "")
            explanation = ent.get("explanation", "")
        else:
            mention = getattr(ent, "mention", "")
            canonical = getattr(ent, "canonical_name", getattr(ent, "canonical", ""))
            etype = getattr(ent, "entity_type", "Concept")
            oid = getattr(ent, "identifier", "")
            explanation = getattr(ent, "explanation", "")
            
        parts.append(f"* **Mention:** `{mention}` → **{canonical}** (`{oid}`)")
        parts.append(f"  * **Type:** {etype}")
        if explanation:
            parts.append(f"  * **Explanation:** {explanation}")
            
    parts.append("\n*If you would like a detailed, formal clinical report with PubMed references, please ask me to 'generate a report'.*")
    return "\n".join(parts)

class TextResolutionRequest(BaseModel):
    text: str

class TextResolutionItem(BaseModel):
    mention: str
    start_char: int
    end_char: int
    canonical_name: str
    canonical: str
    entity_type: str
    identifier: str
    concept_id: str
    ontology: str
    confidence: float
    status: str
    reason: List[str]
    explanation: str

class RAGRequest(BaseModel):
    text: str

class RAGResponse(BaseModel):
    query: str
    resolved_entities: List[TextResolutionItem]
    literature: dict
    merged_context: str
    report: str

class AgentRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class AgentResponse(BaseModel):
    session_id: str
    original_query: str
    enriched_query: str
    intent: str
    resolved_entities: List[TextResolutionItem]
    report: str
    system_prompt: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the Biomedical Entity Resolution Assistant API. Use POST /resolve or GET /search."}

@app.post("/resolve", response_model=ResolutionResponse)
def resolve_entity(request: ResolutionRequest):
    from src.monitoring.instrumentation import record_telemetry
    with record_telemetry(request.query, "FAST_RESOLVE") as ctx:
        query = request.query
        with ctx.span("retrieve_candidates") as span:
            results = retriever.hybrid_search(query, limit=1)
            span.set_attribute("candidates_count", len(results))
        
        if results:
            best_match = results[0]
            # Map/Scale RRF score for representation in the confidence field
            if "lexical" in best_match["retrieval_method"] and "vector" in best_match["retrieval_method"]:
                confidence = 0.99
            elif "id_match" in best_match["retrieval_method"]:
                confidence = 1.0
            else:
                confidence = 0.85
                
            ctx.add_resolved_entities([{
                "mention": query,
                "canonical_name": best_match["canonical_name"],
                "entity_type": best_match["entity_type"],
                "identifier": best_match["identifier"],
                "source": best_match["source"],
                "confidence": confidence,
                "status": "resolved"
            }])
                
            return ResolutionResponse(
                query=query,
                canonical_name=best_match["canonical_name"],
                entity_type=best_match["entity_type"],
                identifier=best_match["identifier"],
                confidence=confidence,
                source=best_match["source"]
            )
            
        # No candidates found, return a default unknown response
        return ResolutionResponse(
            query=query,
            canonical_name=query,
            entity_type="Unknown",
            identifier="Unknown",
            confidence=0.0,
            source="None"
        )

@app.get("/search", response_model=SearchResponse)
def search_entities(query: str, limit: int = 5):
    results = retriever.hybrid_search(query, limit=limit)
    candidates = [
        CandidateResolution(
            identifier=r["identifier"],
            canonical_name=r["canonical_name"],
            description=r["description"] or "",
            entity_type=r["entity_type"],
            source=r["source"],
            score=r["score"],
            retrieval_method=r["retrieval_method"]
        )
        for r in results
    ]
    return SearchResponse(query=query, results=candidates)

@app.post("/resolve-text", response_model=List[TextResolutionItem])
def resolve_text_endpoint(request: TextResolutionRequest):
    from src.monitoring.instrumentation import record_telemetry
    with record_telemetry(request.text, "SIMPLE_RESOLUTION"):
        resolver = get_resolver()
        return resolver.resolve_text(request.text)

@app.post("/resolve-rag", response_model=RAGResponse)
def resolve_rag_endpoint(request: RAGRequest):
    from src.monitoring.instrumentation import record_telemetry
    with record_telemetry(request.text, "MULTI_SOURCE_RAG") as ctx:
        rag = get_rag_pipeline()
        res = rag.run_pipeline(request.text)
        if "resolved_entities" in res:
            ctx.add_resolved_entities(res["resolved_entities"])
        return res

@app.post("/agent/query", response_model=AgentResponse)
def query_agent_endpoint(request: AgentRequest):
    from src.monitoring.instrumentation import record_telemetry
    with record_telemetry(request.query, "COMPLEX_AGENT") as ctx:
        router = get_router()
        route = router.route(request.query)
        
        if route == "SIMPLE_RESOLUTION":
            # Route to fast deterministic resolver pipeline (Module 2, no LLM)
            resolver = get_resolver()
            resolved_entities = resolver.resolve_text(request.query)
            
            # Convert entities to dict representation
            entities_dict = []
            for ent in resolved_entities:
                if isinstance(ent, dict):
                    entities_dict.append({
                        "mention": ent.get("mention", ""),
                        "canonical_name": ent.get("canonical_name", ent.get("canonical", "")),
                        "canonical": ent.get("canonical", ""),
                        "entity_type": ent.get("entity_type", ""),
                        "identifier": ent.get("identifier", ""),
                        "concept_id": ent.get("concept_id", ""),
                        "ontology": ent.get("ontology", ""),
                        "confidence": ent.get("confidence", 0.0),
                        "status": ent.get("status", "resolved"),
                        "reason": ent.get("reason", []),
                        "explanation": ent.get("explanation", "")
                    })
                else:
                    entities_dict.append({
                        "mention": getattr(ent, "mention", ""),
                        "canonical_name": getattr(ent, "canonical_name", getattr(ent, "canonical", "")),
                        "canonical": getattr(ent, "canonical", ""),
                        "entity_type": getattr(ent, "entity_type", ""),
                        "identifier": getattr(ent, "identifier", ""),
                        "concept_id": getattr(ent, "concept_id", ""),
                        "ontology": getattr(ent, "ontology", ""),
                        "confidence": getattr(ent, "confidence", 0.0),
                        "status": getattr(ent, "status", "resolved"),
                        "reason": getattr(ent, "reason", []),
                        "explanation": getattr(ent, "explanation", "")
                    })
                
            normalized = request.query.lower().strip()
            needs_report = any(keyword in normalized for keyword in ["report", "table", "markdown", "generate report", "make a report", "clinical report"])
            
            # If no entities were extracted, let's treat it as out-of-domain / unresolvable
            if not resolved_entities:
                report = (
                    "I am a specialized Biomedical Entity Resolution Assistant. I couldn't identify any clinical terms, "
                    "genes, variants, or drugs in your query, which appears to be outside my medical domain. "
                    "Please specify a clinical term or ask a biomedical question!"
                )
                intent = "OUT_OF_DOMAIN"
            else:
                if needs_report:
                    report = generate_report(request.query, entities_dict)
                else:
                    report = generate_conversational_response(request.query, resolved_entities)
                intent = "SIMPLE_RESOLUTION"
                
            ctx.intent = intent
            session_id = request.session_id or str(uuid.uuid4())
            
            # Log to agent memory
            agent = get_agent()
            agent.history_manager.add_turn(
                session_id=session_id,
                user_content=request.query,
                assistant_content=report,
                resolved_entities=entities_dict
            )
            
            return AgentResponse(
                session_id=session_id,
                original_query=request.query,
                enriched_query=request.query,
                intent=intent,
                resolved_entities=resolved_entities,
                report=report,
                system_prompt="Deterministic Module 2 Resolver Pipeline (No LLM)"
            )
        else:
            # Route to complex agent loop
            agent = get_agent()
            res = agent.process_query(query=request.query, session_id=request.session_id)
            
            resolved_items = []
            for ent in res["resolved_entities"]:
                resolved_items.append(TextResolutionItem(
                    mention=ent.get("mention", ""),
                    start_char=ent.get("start_char", 0),
                    end_char=ent.get("end_char", 0),
                    canonical_name=ent.get("canonical_name", ent.get("canonical", "")),
                    canonical=ent.get("canonical", ""),
                    entity_type=ent.get("entity_type", ""),
                    identifier=ent.get("identifier", ""),
                    concept_id=ent.get("concept_id", ""),
                    ontology=ent.get("ontology", ""),
                    confidence=ent.get("confidence", 0.0),
                    status=ent.get("status", "resolved"),
                    reason=ent.get("reason", []),
                    explanation=ent.get("explanation", "")
                ))
                
            return AgentResponse(
                session_id=res["session_id"],
                original_query=res["original_query"],
                enriched_query=res["enriched_query"],
                intent=res["intent"],
                resolved_entities=resolved_items,
                report=res["report"],
                system_prompt=res["system_prompt"]
            )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


