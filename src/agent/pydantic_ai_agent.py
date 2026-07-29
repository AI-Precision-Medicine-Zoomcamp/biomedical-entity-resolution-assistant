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

# Create Pydantic AI Agent
pydantic_agent = Agent(
    model,
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
def tool_resolve_entity(ctx: RunContext, args: ResolveEntityArgs) -> list[dict]:
    """
    Resolves biomedical entities in the input text using the entity resolution pipeline.
    """
    return resolve_entity(args.text)

@pydantic_agent.tool
def tool_retrieve_concept(ctx: RunContext, args: RetrieveConceptArgs) -> dict:
    """
    Retrieves full concept metadata (canonical name, description, ontology, synonyms)
    for a specific ontology concept identifier.
    """
    return retrieve_concept(args.concept_id)

@pydantic_agent.tool
def tool_search_literature(ctx: RunContext, args: SearchLiteratureArgs) -> list[dict]:
    """
    Queries scientific literature (NCBI PubMed database) for publications.
    """
    return search_literature(args.query, args.limit)

@pydantic_agent.tool
def tool_compare_entities(ctx: RunContext, args: CompareEntitiesArgs) -> dict:
    """
    Compares two resolved entity definitions by comparing their types, ontology sources, etc.
    """
    return compare_entities(args.entity_a, args.entity_b)

@pydantic_agent.tool
def tool_generate_report(ctx: RunContext, args: GenerateReportArgs) -> str:
    """
    Generates a structured clinical Markdown report summarizing resolved entities and literature.
    """
    return generate_report(args.query_text, args.resolved_entities, args.literature_results, args.comparison_results)



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

        # Run the live agent
        result = pydantic_agent.run_sync(enriched_query)
        data = result.output
        intent = data.intent
        resolved_entities = data.resolved_entities
        report = data.report

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
