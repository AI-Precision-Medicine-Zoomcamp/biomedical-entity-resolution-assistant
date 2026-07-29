import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.tools.resolve_entity import resolve_entity
from src.tools.search_literature import search_literature
from src.tools.generate_report import generate_report

class MultiSourceRAG:
    """
    Implements Multi-Source RAG:
    User Query -> Ontology Retrieval (Entity Resolution) -> Literature Retrieval -> Merge Context -> Report/Generation
    """
    def __init__(self):
        pass

    def run_pipeline(self, text: str) -> dict:
        """
        Runs the multi-stage RAG pipeline.
        
        Args:
            text (str): The clinical text or case study query.
            
        Returns:
            dict: The final report and merged context metadata.
        """
        if not text:
            return {
                "query": "",
                "resolved_entities": [],
                "literature": {},
                "merged_context": "",
                "report": ""
            }

        # Stage 1: Ontology Retrieval (Entity Resolution)
        resolved_entities = resolve_entity(text)
        
        # Stage 2: Literature Retrieval for each resolved entity
        literature_results = {}
        all_lit_list = []
        seen_pmids = set()
        
        for ent in resolved_entities:
            canonical = ent.get("canonical_name")
            if canonical:
                # Search literature for this entity
                articles = search_literature(canonical, limit=2)
                literature_results[canonical] = articles
                for art in articles:
                    if art["pmid"] not in seen_pmids:
                        seen_pmids.add(art["pmid"])
                        all_lit_list.append(art)
                        
        # Stage 3: Merge Context
        context_parts = []
        context_parts.append("=== ONTOLOGY RESOLUTION CONTEXT ===")
        for ent in resolved_entities:
            context_parts.append(
                f"- Entity: {ent['canonical_name']} ({ent['identifier']})\n"
                f"  Type: {ent['entity_type']} | Source: {ent['ontology']}\n"
                f"  Description: {ent.get('explanation', '')}"
            )
            
        context_parts.append("\n=== LITERATURE CONTEXT ===")
        for canonical, articles in literature_results.items():
            context_parts.append(f"Publications for {canonical}:")
            for art in articles:
                context_parts.append(
                    f"  - Title: {art['title']}\n"
                    f"    Authors: {art['authors']} | Source: {art['source']} ({art['pubdate']})\n"
                    f"    Link: {art['url']}"
                )
        merged_context = "\n".join(context_parts)
        
        # Stage 4: Compiler / Report Generation
        report = generate_report(text, resolved_entities, all_lit_list)
        
        return {
            "query": text,
            "resolved_entities": resolved_entities,
            "literature": literature_results,
            "merged_context": merged_context,
            "report": report
        }

if __name__ == "__main__":
    import json
    rag = MultiSourceRAG()
    test_text = "Patients with MI were prescribed Tylenol."
    res = rag.run_pipeline(test_text)
    print("Testing MultiSourceRAG pipeline...")
    print(res["merged_context"][:500])
