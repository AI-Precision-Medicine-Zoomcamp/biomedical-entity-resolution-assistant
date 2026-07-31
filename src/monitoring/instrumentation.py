import time
import uuid
import contextvars
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add project root to path to enable 'src' imports when running standalone scripts
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.monitoring.tracing import get_tracer
from src.monitoring.metrics import log_request, log_resolved_entity
from src.monitoring.alerts import check_and_trigger_alerts

# Thread-safe / Coroutine-safe Context Variable for holding the active TelemetryContext
_active_context = contextvars.ContextVar("active_context", default=None)

def get_active_context() -> Optional['TelemetryContext']:
    return _active_context.get()

class TelemetryContext:
    def __init__(self, query: str, intent: str):
        self.request_id = str(uuid.uuid4())
        self.query = query
        self.intent = intent
        self.start_time = None
        self.total_latency_ms = 0.0
        
        # Latency breakdown
        self.ner_latency_ms = 0.0
        self.retrieval_latency_ms = 0.0
        self.ranking_latency_ms = 0.0
        self.llm_latency_ms = 0.0
        
        # LLM metrics
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost = 0.0
        
        # Extracted & Resolved entities
        self.resolved_entities: List[Dict[str, Any]] = []
        self.status = "SUCCESS"
        self.error_message: Optional[str] = None
        
        self.tracer = get_tracer()
        self.root_span = None

    def start(self):
        self.start_time = time.perf_counter()
        self.root_span = self.tracer.start_span("resolve_request")
        self.root_span.set_attribute("request_id", self.request_id)
        self.root_span.set_attribute("query", self.query)
        self.root_span.set_attribute("intent", self.intent)

    @contextmanager
    def span(self, name: str):
        sub_start = time.perf_counter()
        with self.tracer.start_as_current_span(name) as sub_span:
            yield sub_span
            latency = (time.perf_counter() - sub_start) * 1000.0
            
            # Map sub-span timings
            if name == "detect_entities":
                self.ner_latency_ms = latency
            elif name == "retrieve_candidates":
                self.retrieval_latency_ms = latency
            elif name == "rank_candidates":
                self.ranking_latency_ms = latency
            elif name == "generate_explanation":
                self.llm_latency_ms = latency

    def add_resolved_entities(self, entities: List[Dict[str, Any]]):
        """
        Record resolved entities generated during this request pipeline.
        """
        for ent in entities:
            # Map standard pipeline keys to ensure telemetry receives proper formats
            self.resolved_entities.append({
                "mention": ent.get("mention", ""),
                "canonical_name": ent.get("canonical_name", ent.get("canonical", "")),
                "entity_type": ent.get("entity_type", ""),
                "identifier": ent.get("identifier", ""),
                "ontology": ent.get("ontology", ent.get("source", "")),
                "confidence": ent.get("confidence", 0.0),
                "status": ent.get("status", "resolved")
            })

    def track_llm_usage(self, input_tokens: int, output_tokens: int, cost: float):
        """
        Record LLM usage metrics.
        """
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cost += cost

    def finish(self):
        self.total_latency_ms = (time.perf_counter() - self.start_time) * 1000.0
        
        # End root span
        if self.root_span:
            self.root_span.set_attribute("status", self.status)
            self.root_span.set_attribute("total_latency_ms", self.total_latency_ms)
            self.root_span.set_attribute("input_tokens", self.input_tokens)
            self.root_span.set_attribute("output_tokens", self.output_tokens)
            self.root_span.set_attribute("cost", self.cost)
            self.root_span.set_attribute("resolved_entities_count", len(self.resolved_entities))
            if self.error_message:
                self.root_span.set_attribute("error_message", self.error_message)
            self.root_span.end()
            
        # SQLite persistence
        log_request(
            request_id=self.request_id,
            query=self.query,
            intent=self.intent,
            status=self.status,
            total_latency_ms=self.total_latency_ms,
            ner_latency_ms=self.ner_latency_ms,
            retrieval_latency_ms=self.retrieval_latency_ms,
            ranking_latency_ms=self.ranking_latency_ms,
            llm_latency_ms=self.llm_latency_ms,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cost=self.cost,
            error_message=self.error_message
        )
        
        for ent in self.resolved_entities:
            log_resolved_entity(
                request_id=self.request_id,
                mention=ent["mention"],
                canonical_name=ent["canonical_name"],
                entity_type=ent["entity_type"],
                identifier=ent["identifier"],
                ontology=ent["ontology"],
                confidence=ent["confidence"],
                status=ent["status"]
            )
            
        # Evaluate alerting rules
        check_and_trigger_alerts(self)

@contextmanager
def record_telemetry(query: str, intent: str):
    ctx = TelemetryContext(query, intent)
    ctx.start()
    token = _active_context.set(ctx)
    try:
        yield ctx
    except Exception as e:
        ctx.status = "ERROR"
        ctx.error_message = str(e)
        raise e
    finally:
        ctx.finish()
        _active_context.reset(token)
