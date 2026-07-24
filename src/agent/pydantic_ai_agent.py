import os
import sys
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

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
    Falls back to Pydantic AI TestModel if offline/unauthenticated.
    """
    if os.getenv("OPENAI_API_KEY"):
        return "openai:gpt-4o"
    elif os.getenv("GEMINI_API_KEY"):
        return "gemini:gemini-1.5-flash"
    else:
        # Return Pydantic AI's built-in TestModel for offline testing/validation
        from pydantic_ai.models.test import TestModel
        return TestModel()

model = get_pydantic_ai_model()

# Create Pydantic AI Agent
pydantic_agent = Agent(
    model,
    output_type=AgentResponseModel,
    system_prompt=SYSTEM_PROMPT
)

# Register Tools with Pydantic AI Agent
@pydantic_agent.tool
def tool_resolve_entity(ctx: RunContext, text: str) -> list[dict]:
    """
    Resolves biomedical entities in the input text using the entity resolution pipeline.
    """
    return resolve_entity(text)

@pydantic_agent.tool
def tool_retrieve_concept(ctx: RunContext, concept_id: str) -> dict:
    """
    Retrieves full concept metadata (canonical name, description, ontology, synonyms)
    for a specific ontology concept identifier.
    """
    return retrieve_concept(concept_id)

@pydantic_agent.tool
def tool_search_literature(ctx: RunContext, query: str, limit: int = 3) -> list[dict]:
    """
    Queries scientific literature (NCBI PubMed database) for publications.
    """
    return search_literature(query, limit)

@pydantic_agent.tool
def tool_compare_entities(ctx: RunContext, entity_a: dict, entity_b: dict) -> dict:
    """
    Compares two resolved entity definitions by comparing their types, ontology sources, etc.
    """
    return compare_entities(entity_a, entity_b)

@pydantic_agent.tool
def tool_generate_report(ctx: RunContext, query_text: str, resolved_entities: list[dict], literature_results: list[dict] = None, comparison_results: dict = None) -> str:
    """
    Generates a structured clinical Markdown report summarizing resolved entities and literature.
    """
    return generate_report(query_text, resolved_entities, literature_results, comparison_results)


class PydanticAIBiomedicalAgent:
    """
    Orchestration wrapper around pydantic_agent, supporting pronoun resolution,
    conversational memory, and executing the Agent tool sequence.
    """
    def __init__(self, history_manager=None):
        self.history_manager = history_manager or ConversationHistory()
        self.planner = AgentPlanner(history_manager=self.history_manager)

    def process_query(self, query: str, session_id: str = None) -> dict:
        """
        Executes the agent loop. If running offline/TestModel, uses the deterministic
        planner to execute the planned tools and mock-construct the structured response.
        If a live model is available, delegates to Pydantic AI agent run.
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        # 1. Pronoun reference resolution
        enriched_query = self.planner.resolve_pronouns(query, session_id)

        # 2. Run Agent
        # If we are using a real model, we run it through pydantic_agent.run_sync
        # If we are using TestModel, we execute the deterministic tool flow to simulate the run
        is_mock = isinstance(pydantic_agent.model, TestModel) if hasattr(pydantic_agent, 'model') else True
        if not is_mock:
            try:
                result = pydantic_agent.run_sync(enriched_query)
                data = result.data
                intent = data.intent
                resolved_entities = data.resolved_entities
                report = data.report
            except Exception as e:
                # Fallback to deterministic run if real run fails
                print(f"Pydantic AI real run failed: {e}. Falling back to deterministic plan.", file=sys.stderr)
                is_mock = True

        if is_mock:
            # Deterministic/Offline local simulation
            plan = self.planner.create_plan(query, session_id)
            context = {"concepts": [], "literature": [], "comparison": None}
            
            # Execute steps
            for step in plan["steps"]:
                tname = step["tool"]
                args = step.get("args", {}).copy()
                
                if tname == "retrieve_concept":
                    res = retrieve_concept(**args)
                    if res:
                        context["concepts"].append(res)
                elif tname == "search_literature":
                    res = search_literature(**args)
                    if res:
                        context["literature"].extend(res)
                elif tname == "compare_entities":
                    if len(context["concepts"]) >= 2:
                        res = compare_entities(context["concepts"][0], context["concepts"][1])
                        context["comparison"] = res
                elif tname == "generate_report":
                    args["literature_results"] = context["literature"]
                    if context["comparison"]:
                        args["comparison_results"] = context["comparison"]
                    res = generate_report(**args)
                    context["report"] = res

            intent = plan["intent"]
            resolved_entities = plan["resolved_entities"]
            report = context.get("report", "No report generated.")

        # 3. Store in history
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

# Import TestModel at top-level if needed
try:
    from pydantic_ai.models.test import TestModel
except ImportError:
    class TestModel:
        pass
