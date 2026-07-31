import os
import sys
import uuid
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.conversation.history import ConversationHistory
from src.agent.planner import AgentPlanner
from src.agent.prompts import SYSTEM_PROMPT
from src.tools.resolve_entity import resolve_entity
from src.tools.retrieve_concept import retrieve_concept
from src.tools.search_literature import search_literature
from src.tools.compare_entities import compare_entities
from src.tools.generate_report import generate_report

# Structured output format for Pydantic AI
class AgentResponseModel(BaseModel):
    intent: str = Field(description="The detected user intent (EXPLAIN_ENTITY, COMPARE_ENTITIES, EXPLAIN_TEXT)")
    resolved_entities: list[dict] = Field(default_factory=list, description="Resolved biomedical entity concepts")
    report: str = Field(description="The final clinical or comparison report in Markdown format")

def get_pydantic_ai_model():
    """
    Initializes appropriate Pydantic AI model based on environment config.
    """
    if os.getenv("GROQ_API_KEY"):
        return "groq:llama-3.3-70b-versatile"
    # elif os.getenv("GEMINI_API_KEY"):
    #     return "gemini-1.5-flash"
    # elif os.getenv("OPENAI_API_KEY"):
    #     return "openai:gpt-4o-mini"
    # else:
    #     # Default to Groq model string (will raise missing key error at runtime)
    #     return "groq:llama-3.3-70b-versatile"

model = get_pydantic_ai_model()

class AgentDeps:
    def __init__(self, query: str, session_id: Optional[str] = None):
        self.query = query
        self.session_id = session_id

# Create Pydantic AI Agent
pydantic_agent = Agent(
    model,
    deps_type=AgentDeps,
    output_type=AgentResponseModel,
    system_prompt=SYSTEM_PROMPT
)

# Input schemas for agent tools to prevent LLM validation errors
class ResolveEntityArgs(BaseModel):
    text: str = Field(description="The clinical query text to extract and resolve entities from.")

class RetrieveConceptArgs(BaseModel):
    concept_id: str = Field(description="The concept identifier (e.g. MESH:D009203 or RXCUI:161) to retrieve.")

class SearchLiteratureArgs(BaseModel):
    query: str = Field(description="The query string to search for literature citations.")
    limit: int = Field(default=3, description="The maximum number of citation results to return.")

class CompareEntitiesArgs(BaseModel):
    entity_a: dict = Field(description="The first resolved entity concept dictionary.")
    entity_b: dict = Field(description="The second resolved entity concept dictionary.")

class GenerateReportArgs(BaseModel):
    query_text: str = Field(description="The original user query text.")
    resolved_entities: list[dict] = Field(description="List of resolved entity dictionaries.")
    literature_results: Optional[list[dict]] = Field(default=None, description="Optional retrieved literature citations.")
    comparison_results: Optional[dict] = Field(default=None, description="Optional comparison analysis results.")

# Register Tools with Pydantic AI Agent
@pydantic_agent.tool
def tool_resolve_entity(ctx: RunContext[AgentDeps], args: ResolveEntityArgs) -> list[dict]:
    """
    Resolves biomedical entities in the input text using the entity resolution pipeline.
    """
    return resolve_entity(args.text)

@pydantic_agent.tool
def tool_retrieve_concept(ctx: RunContext[AgentDeps], args: RetrieveConceptArgs) -> dict:
    """
    Retrieves full concept metadata (canonical name, description, ontology, synonyms)
    for a specific ontology concept identifier.
    """
    return retrieve_concept(args.concept_id)

@pydantic_agent.tool
def tool_search_literature(ctx: RunContext[AgentDeps], args: SearchLiteratureArgs) -> list[dict]:
    """
    Queries scientific literature (NCBI PubMed database) for publications.
    """
    return search_literature(args.query, args.limit)

@pydantic_agent.tool
def tool_compare_entities(ctx: RunContext[AgentDeps], args: CompareEntitiesArgs) -> dict:
    """
    Compares two resolved entity definitions by comparing their types, ontology sources, etc.
    """
    return compare_entities(args.entity_a, args.entity_b)

@pydantic_agent.tool
def tool_generate_report(ctx: RunContext[AgentDeps], args: GenerateReportArgs) -> str:
    """
    Generates a structured clinical Markdown report summarizing resolved entities and literature.
    """
    query_text = args.query_text
    
    # 1. Fallback/sanitize query text if LLM passed dummy values
    if not query_text or query_text.strip().lower() in ["user query", "original query", "query"]:
        if ctx.deps and ctx.deps.query:
            query_text = ctx.deps.query
            
    # 2. Fallback/sanitize resolved entities if LLM passed dummy/empty values
    resolved_entities = args.resolved_entities
    
    # Check if resolved_entities is empty or contains dummy/placeholder items
    has_dummy = False
    if resolved_entities:
        for ent in resolved_entities:
            canon = ent.get("canonical_name", "")
            mention = ent.get("mention", "")
            if not canon or canon == "****" or not mention or mention == "****":
                has_dummy = True
                break
                
    if not resolved_entities or has_dummy:
        # Resolve entities directly using the real query text
        resolved_entities = resolve_entity(query_text)
        
        # If still empty, check history as a final fallback
        if not resolved_entities and ctx.deps and ctx.deps.session_id:
            history = ConversationHistory()
            last_resolved = history.get_last_resolved_entities(ctx.deps.session_id)
            if last_resolved:
                resolved_entities = last_resolved

    # 3. Fallback/sanitize literature results if missing
    lit_results = args.literature_results
    if not lit_results and resolved_entities:
        # Retrieve literature for the first resolved entity
        canonical_query = resolved_entities[0].get("canonical_name", "")
        if canonical_query:
            lit_results = search_literature(canonical_query, limit=3)
            
    return generate_report(query_text, resolved_entities, lit_results, args.comparison_results)



# Simple explanation agent that doesn't use tools
explanation_agent = Agent(
    model,
    system_prompt=(
        "You are a specialized Biomedical Assistant. "
        "Your task is to write a natural, friendly, and conversational explanation of the user's query "
        "using the provided resolved biomedical entity details as ground truth context. "
        "Do NOT output markdown tables. Do NOT output a formal clinical report. "
        "Write 1-2 natural paragraphs explaining the clinical terms, their clinical significance, and any key highlights. "
        "Keep it friendly and conversational, like ChatGPT/Gemini."
    )
)


class PydanticAIBiomedicalAgent:
    """
    Orchestration wrapper around pydantic_agent, supporting pronoun resolution,
    conversational memory, and executing the Agent tool sequence.
    """
    def __init__(self, history_manager=None):
        self.history_manager = history_manager or ConversationHistory()
        self.planner = AgentPlanner(history_manager=self.history_manager)

    def generate_conversational_explanation(self, query: str, resolved_entities: list) -> str:
        """
        Uses a lightweight model call to generate a friendly, natural language
        conversational explanation of the resolved biomedical entities.
        """
        if not resolved_entities:
            return (
                "I am a specialized Biomedical Entity Resolution Assistant. I couldn't identify any clinical terms, "
                "genes, variants, or drugs in your query, which appears to be outside my medical domain. "
                "Please specify a clinical term or ask a biomedical question!"
            )
            
        context_lines = []
        for ent in resolved_entities:
            if isinstance(ent, dict):
                mention = ent.get("mention", "")
                canonical = ent.get("canonical_name", ent.get("canonical", ""))
                etype = ent.get("entity_type", "")
                oid = ent.get("identifier", ent.get("concept_id", ""))
                explanation = ent.get("explanation", "")
            else:
                mention = getattr(ent, "mention", "")
                canonical = getattr(ent, "canonical_name", getattr(ent, "canonical", ""))
                etype = getattr(ent, "entity_type", "")
                oid = getattr(ent, "identifier", getattr(ent, "concept_id", ""))
                explanation = getattr(ent, "explanation", "")

            context_lines.append(
                f"Mention in user query: {mention}\n"
                f"Canonical Name: {canonical}\n"
                f"Entity Type: {etype}\n"
                f"Ontology ID: {oid}\n"
                f"Ontology Explanation: {explanation}"
            )
            
        entity_context = "\n\n".join(context_lines)
        prompt = f"User query: {query}\n\nResolved Entities Context:\n{entity_context}"
        
        try:
            from src.monitoring.instrumentation import get_active_context
            ctx = get_active_context()
            if ctx:
                with ctx.span("llm_reasoning") as span:
                    result = explanation_agent.run_sync(prompt)
                    usage = result.usage()
                    in_tokens = usage.input_tokens or 0
                    out_tokens = usage.output_tokens or 0
                    cost = (in_tokens * 0.59 + out_tokens * 0.79) / 1_000_000
                    ctx.track_llm_usage(in_tokens, out_tokens, cost)
                    span.set_attribute("input_tokens", in_tokens)
                    span.set_attribute("output_tokens", out_tokens)
                    span.set_attribute("cost", cost)
            else:
                result = explanation_agent.run_sync(prompt)
            return result.data
        except Exception as e:
            # Fallback to a structured string if LLM fails
            parts = []
            parts.append(f"I analyzed your query and identified the following biomedical concept(s):\n")
            for ent in resolved_entities:
                if isinstance(ent, dict):
                    mention = ent.get("mention", "")
                    canonical = ent.get("canonical_name", ent.get("canonical", ""))
                    etype = ent.get("entity_type", "Concept")
                    oid = ent.get("identifier", ent.get("concept_id", ""))
                    explanation = ent.get("explanation", "")
                else:
                    mention = getattr(ent, "mention", "")
                    canonical = getattr(ent, "canonical_name", getattr(ent, "canonical", ""))
                    etype = getattr(ent, "entity_type", "Concept")
                    oid = getattr(ent, "identifier", getattr(ent, "concept_id", ""))
                    explanation = getattr(ent, "explanation", "")
                    
                parts.append(f"* **Mention:** `{mention}` → **{canonical}** (`{oid}`)")
                parts.append(f"  * **Type:** {etype}")
                if explanation:
                    parts.append(f"  * **Explanation:** {explanation}")
                    
            parts.append("\n*If you would like a detailed, formal clinical report with PubMed references, please ask me to 'generate a report'.*")
            return "\n".join(parts)

    def process_query(self, query: str, session_id: str = None) -> dict:
        """
        Executes the agent loop using the live LLM.
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        # 1. Pronoun reference resolution
        enriched_query = self.planner.resolve_pronouns(query, session_id)

        # 2. Run Agent
        # Validate that we have API keys configured
        if not os.getenv("GROQ_API_KEY") and not os.getenv("GEMINI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            raise ValueError(
                "No API Key configured. Please set GROQ_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY in your environment."
            )

        # Run the live agent with deps context
        deps = AgentDeps(query=enriched_query, session_id=session_id)
        
        from src.monitoring.instrumentation import get_active_context
        ctx = get_active_context()
        
        if ctx:
            with ctx.span("llm_reasoning") as span:
                result = pydantic_agent.run_sync(enriched_query, deps=deps)
                usage = result.usage()
                in_tokens = usage.input_tokens or 0
                out_tokens = usage.output_tokens or 0
                cost = (in_tokens * 0.59 + out_tokens * 0.79) / 1_000_000
                ctx.track_llm_usage(in_tokens, out_tokens, cost)
                span.set_attribute("input_tokens", in_tokens)
                span.set_attribute("output_tokens", out_tokens)
                span.set_attribute("cost", cost)
        else:
            result = pydantic_agent.run_sync(enriched_query, deps=deps)
            
        data = result.output
        intent = data.intent
        resolved_entities = data.resolved_entities
        report = data.report

        # 3. Sanitize resolved_entities in response to avoid exposing placeholders
        has_dummy = False
        if resolved_entities:
            for ent in resolved_entities:
                canon = ent.get("canonical_name", "")
                mention = ent.get("mention", "")
                if not canon or canon == "****" or not mention or mention == "****":
                    has_dummy = True
                    break
        if not resolved_entities or has_dummy:
            # Re-resolve using the enriched query
            resolved_entities = resolve_entity(enriched_query)
            # If still empty, try session history fallback
            if not resolved_entities:
                resolved_entities = self.history_manager.get_last_resolved_entities(session_id)

        # 4. Sanitize report content to avoid dummy reports
        normalized_report = report.lower()
        if "no biomedical entities" in normalized_report or "****" in normalized_report or "no clinical entities detected" in normalized_report:
            if resolved_entities:
                # Retrieve literature for the first resolved entity
                lit = None
                canonical_query = resolved_entities[0].get("canonical_name", "")
                if canonical_query:
                    lit = search_literature(canonical_query, limit=3)
                report = generate_report(enriched_query, resolved_entities, lit)

        # 5. Store in history
        self.history_manager.add_turn(
            session_id=session_id,
            user_content=query,
            assistant_content=report,
            resolved_entities=resolved_entities
        )

        return {
            "session_id": session_id,
            "original_query": query,
            "enriched_query": enriched_query,
            "intent": intent,
            "resolved_entities": resolved_entities,
            "report": report,
            "system_prompt": SYSTEM_PROMPT
        }
