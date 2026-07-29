import uuid

class ConversationHistory:
    """
    Manages session-based conversation memory threads to maintain multi-turn history
    and help resolve pronoun/context references.
    """
    def __init__(self):
        # Maps session_id -> list of message dicts: [{"role": "user"/"assistant", "content": str, "resolved_entities": list}]
        self.sessions = {}

    def get_history(self, session_id: str) -> list[dict]:
        if not session_id:
            return []
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def add_turn(self, session_id: str, user_content: str, assistant_content: str, resolved_entities: list[dict]):
        if not session_id:
            return
        history = self.get_history(session_id)
        
        # Store message history along with metadata about entities resolved during this turn
        history.append({
            "role": "user",
            "content": user_content
        })
        history.append({
            "role": "assistant",
            "content": assistant_content,
            "resolved_entities": resolved_entities
        })
        
        # Keep only the last 10 turns (20 messages) to avoid memory bloating
        if len(history) > 20:
            self.sessions[session_id] = history[-20:]

    def get_last_resolved_entities(self, session_id: str) -> list[dict]:
        """
        Returns the resolved entities from the last assistant turn in this session.
        Useful for pronoun resolution (e.g. 'Compare it with BRCA1').
        """
        history = self.get_history(session_id)
        # Search backwards for the last assistant response containing resolved entities
        for turn in reversed(history):
            if turn.get("role") == "assistant" and turn.get("resolved_entities"):
                return turn["resolved_entities"]
        return []
