import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.agent.pydantic_ai_agent import PydanticAIBiomedicalAgent

def main():
    agent = PydanticAIBiomedicalAgent()
    session_id = "cli_demo_session"
    
    print("=" * 80)
    print("BIOMEDICAL AGENT INTERACTIVE CLI")
    print("You can test single queries, multi-turn pronoun memory, and comparisons.")
    print("Example 1: Explain MI")
    print("Example 2: Compare it with Tylenol")
    print("Type 'exit' or 'quit' to end the session.")
    print("=" * 80)

    while True:
        try:
            query = input("\nUser> ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
                
            print("\n[Orchestrator] Planning and executing tools...")
            response = agent.process_query(query, session_id=session_id)
            
            print(f"\n[Intent Classified] -> {response['intent']}")
            if response["enriched_query"] != query:
                print(f"[Pronoun Reference Resolved] -> \"{response['enriched_query']}\"")
                
            print("\n" + "=" * 40 + " CLINICAL REPORT " + "=" * 40)
            print(response["report"])
            print("=" * 97)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n[Error] {e}")

if __name__ == "__main__":
    main()
