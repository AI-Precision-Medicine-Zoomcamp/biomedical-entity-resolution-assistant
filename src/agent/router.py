import re
from typing import Literal

class WorkflowRouter:
    """
    Routes user requests either to the fast deterministic Module 2 pipeline
    or the full reasoning Biomedical Agent loop.
    """
    def __init__(self):
        # Match common definition patterns
        self.simple_patterns = [
            re.compile(r"^\s*what\s+(?:is|does)\s+([a-zA-Z0-9\s]+?)(?:\s+stand\s+for)?\??\s*$", re.IGNORECASE),
            re.compile(r"^\s*define\s+([a-zA-Z0-9\s]+?)\??\s*$", re.IGNORECASE),
            re.compile(r"^\s*resolve\s+([a-zA-Z0-9\s]+?)\??\s*$", re.IGNORECASE),
        ]

    def route(self, query: str) -> Literal["SIMPLE_RESOLUTION", "COMPLEX_AGENT"]:
        """
        Analyzes the query and routes it.
        Returns:
            "SIMPLE_RESOLUTION": Route to fast, deterministic pipeline (Module 2).
            "COMPLEX_AGENT": Route to the reasoning Biomedical Agent (Module 3).
        """
        normalized = query.strip().lower()
        
        # Check for complex agent query indicators first
        indicators = ["compare", "relation", "interact", "analysis", "paper", "study", "report", "difference", "versus", "vs", "between"]
        if any(ind in normalized for ind in indicators):
            return "COMPLEX_AGENT"
            
        # 1. Match definition patterns
        for pattern in self.simple_patterns:
            if pattern.match(query.strip()):
                return "SIMPLE_RESOLUTION"
                
        # 2. Check word count
        words = query.strip().split()
        if len(words) <= 5:
            return "SIMPLE_RESOLUTION"

        return "COMPLEX_AGENT"
