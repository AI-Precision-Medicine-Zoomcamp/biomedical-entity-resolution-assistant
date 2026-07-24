import re
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.tools.resolve_entity import resolve_entity

class AgentPlanner:
    """
    Analyzes the user's clinical query, performs pronoun reference resolution,
    and plans the sequence of tools to run.
    """
    def __init__(self, history_manager=None):
        self.history_manager = history_manager

    def resolve_pronouns(self, query: str, session_id: str) -> str:
        """
        Detects pronouns or referencing words like 'it', 'this concept', 'that gene'
        and replaces them with the name of the last resolved concept from the session history.
        """
        if not self.history_manager or not session_id:
            return query
            
        last_resolved = self.history_manager.get_last_resolved_entities(session_id)
        if not last_resolved:
            return query

        # Target concept to substitute
        target_concept = last_resolved[0].get("canonical_name", "")
        if not target_concept:
            return query

        # Case-insensitive replacement for common pronoun constructs
        pronoun_patterns = [
            r"\bit\b",
            r"\bthis concept\b",
            r"\bthat concept\b",
            r"\bthis entity\b",
            r"\bthat entity\b",
            r"\bthe disease\b",
            r"\bthe drug\b",
            r"\bthe gene\b"
        ]
        
        resolved_query = query
        for pattern in pronoun_patterns:
            resolved_query = re.sub(pattern, target_concept, resolved_query, flags=re.IGNORECASE)
            
        return resolved_query

    def create_plan(self, query: str, session_id: str = None) -> dict:
        """
        Creates an action plan specifying the intent and tools to execute.
        """
        # 1. Resolve pronouns in the query
        enriched_query = self.resolve_pronouns(query, session_id)
        
        # 2. Extract and resolve entities in the enriched query
        resolved_entities = resolve_entity(enriched_query)
        
        # 3. Determine plan based on resolved entities
        num_entities = len(resolved_entities)
        
        if num_entities == 0:
            # Fallback to literal search if no entities resolved
            return {
                "enriched_query": enriched_query,
                "intent": "EXPLAIN_TEXT",
                "resolved_entities": [],
                "steps": [
                    {"tool": "search_literature", "args": {"query": enriched_query}},
                    {"tool": "generate_report", "args": {"query_text": enriched_query, "resolved_entities": []}}
                ]
            }
        elif num_entities == 1:
            entity = resolved_entities[0]
            ent_id = entity.get("identifier", "")
            canonical = entity.get("canonical_name", "")
            return {
                "enriched_query": enriched_query,
                "intent": "EXPLAIN_ENTITY",
                "resolved_entities": resolved_entities,
                "steps": [
                    {"tool": "retrieve_concept", "args": {"concept_id": ent_id}},
                    {"tool": "search_literature", "args": {"query": canonical}},
                    {"tool": "generate_report", "args": {"query_text": enriched_query, "resolved_entities": resolved_entities}}
                ]
            }
        else:
            # 2 or more entities: comparison flow
            ent_ids = [e.get("identifier", "") for e in resolved_entities[:2]]
            canonicals = [e.get("canonical_name", "") for e in resolved_entities[:2]]
            return {
                "enriched_query": enriched_query,
                "intent": "COMPARE_ENTITIES",
                "resolved_entities": resolved_entities,
                "steps": [
                    {"tool": "retrieve_concept", "args": {"concept_id": ent_ids[0]}},
                    {"tool": "retrieve_concept", "args": {"concept_id": ent_ids[1]}},
                    {"tool": "compare_entities", "args": {}}, # Arguments injected dynamically during execution
                    {"tool": "search_literature", "args": {"query": canonicals[0]}},
                    {"tool": "search_literature", "args": {"query": canonicals[1]}},
                    {"tool": "generate_report", "args": {"query_text": enriched_query, "resolved_entities": resolved_entities}}
                ]
            }

if __name__ == "__main__":
    planner = AgentPlanner()
    print("Testing planner with 1 entity...")
    print(planner.create_plan("Explain TP53"))
    print("\nTesting planner with 2 entities...")
    print(planner.create_plan("Compare Diabetes and Prediabetes"))
