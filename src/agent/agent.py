import sys
import uuid
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.conversation.history import ConversationHistory
from src.agent.planner import AgentPlanner
from src.agent.prompts import SYSTEM_PROMPT
from src.tools import (
    resolve_entity,
    retrieve_concept,
    search_literature,
    compare_entities,
    generate_report,
)

class BiomedicalAgent:
    """
    Biomedical Agent reasoning system. Orchestrates tool calls based on intent plans
    created by AgentPlanner and manages conversation memory.
    """
    def __init__(self, history_manager=None):
        self.history_manager = history_manager or ConversationHistory()
        self.planner = AgentPlanner(history_manager=self.history_manager)
        
        # Tool directory mapping
        self.tools = {
            "resolve_entity": resolve_entity,
            "retrieve_concept": retrieve_concept,
            "search_literature": search_literature,
            "compare_entities": compare_entities,
            "generate_report": generate_report,
        }

    def process_query(self, query: str, session_id: str = None) -> dict:
        """
        Processes a user query: creates a plan, executes tools in sequence,
        saves the turn to memory, and generates the final output report.
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        # 1. Generate plan using the planner (including pronoun resolution)
        plan = self.planner.create_plan(query, session_id)
        
        # 2. Execute plan steps while maintaining execution context
        context = {
            "concepts": [],
            "literature": [],
            "comparison": None
        }
        
        for step in plan["steps"]:
            tool_name = step["tool"]
            tool_fn = self.tools.get(tool_name)
            if not tool_fn:
                continue
                
            # Set up arguments for tool execution
            args = step.get("args", {}).copy()
            
            if tool_name == "compare_entities":
                # Inject retrieved concepts dynamically
                if len(context["concepts"]) >= 2:
                    args["entity_a"] = context["concepts"][0]
                    args["entity_b"] = context["concepts"][1]
                else:
                    # Fallback to empty if not loaded
                    args["entity_a"] = {}
                    args["entity_b"] = {}
                    
            elif tool_name == "generate_report":
                # Inject all retrieved literature list & comparison results
                args["literature_results"] = context["literature"]
                if context["comparison"]:
                    args["comparison_results"] = context["comparison"]

            # Run the tool
            try:
                res = tool_fn(**args)
                
                # Capture results into execution context
                if tool_name == "retrieve_concept":
                    if res:
                        context["concepts"].append(res)
                elif tool_name == "search_literature":
                    if isinstance(res, list):
                        context["literature"].extend(res)
                elif tool_name == "compare_entities":
                    context["comparison"] = res
                elif tool_name == "generate_report":
                    context["report"] = res
            except Exception as e:
                # Robust error handling for individual step failures
                print(f"Error executing tool '{tool_name}': {e}", file=sys.stderr)
                if tool_name == "generate_report":
                    context["report"] = f"Error generating clinical report: {e}"

        # 3. Handle default report if none was created
        final_report = context.get("report", "No report was generated.")

        # 4. Save turn to conversation history
        self.history_manager.add_turn(
            session_id=session_id,
            user_content=query,
            assistant_content=final_report,
            resolved_entities=plan["resolved_entities"]
        )

        return {
            "session_id": session_id,
            "original_query": query,
            "enriched_query": plan["enriched_query"],
            "intent": plan["intent"],
            "resolved_entities": plan["resolved_entities"],
            "report": final_report,
            "system_prompt": SYSTEM_PROMPT
        }

if __name__ == "__main__":
    import json
    agent = BiomedicalAgent()
    print("Executing query 1: Explain TP53")
    res1 = agent.process_query("Explain TP53", session_id="test_session")
    print(res1["report"][:400])
    
    print("\nExecuting query 2: Compare it with BRCA1")
    res2 = agent.process_query("Compare it with BRCA1", session_id="test_session")
    print(res2["report"][:400])
