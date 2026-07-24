def generate_report(query_text: str, resolved_entities: list[dict], literature_results: list[dict] = None, comparison_results: dict = None) -> str:
    """
    Tool: generate_report
    Generates a structured clinical Markdown report summarizing resolved entities,
    scientific literature citations, and comparative analysis results.
    
    Args:
        query_text (str): The original clinical query or text block.
        resolved_entities (list[dict]): Entities resolved via the pipeline.
        literature_results (list[dict]): Publications retrieved via search_literature.
        comparison_results (dict, optional): Structured comparisons between entities.
        
    Returns:
        str: Clinical report in Markdown format.
    """
    report = []
    report.append("# Biomedical Analysis & Clinical Report")
    report.append(f"**Original Query / Case Input:** *\"{query_text}\"*\n")
    
    # 1. Executive Summary
    report.append("## 1. Executive Summary")
    entity_names = [e.get("canonical_name", e.get("mention")) for e in resolved_entities]
    if entity_names:
        summary_str = f"The clinical extraction pipeline successfully identified and resolved {len(resolved_entities)} biomedical concepts: **{', '.join(entity_names)}**."
    else:
        summary_str = "No biomedical entities were successfully resolved from the input query."
    report.append(summary_str + "\n")
    
    # 2. Entity Resolution Details
    report.append("## 2. Resolved Biomedical Entities")
    if resolved_entities:
        report.append("| Mention | Canonical Name | Entity Type | Ontology ID | Confidence | Status |")
        report.append("| --- | --- | --- | --- | --- | --- |")
        for ent in resolved_entities:
            mention = ent.get("mention", "")
            canonical = ent.get("canonical_name", ent.get("canonical", ""))
            etype = ent.get("entity_type", "")
            oid = ent.get("identifier", "")
            conf = f"{int(ent.get('confidence', 0.0) * 100)}%"
            status = ent.get("status", "unknown").upper()
            report.append(f"| `{mention}` | **{canonical}** | {etype} | `{oid}` | {conf} | **{status}** |")
        report.append("\n### Detailed Explanations")
        for ent in resolved_entities:
            canonical = ent.get("canonical_name", "")
            explanation = ent.get("explanation", "No justification provided.")
            reasons = ", ".join(ent.get("reason", []))
            report.append(f"- **{canonical}**: {explanation}")
            if reasons:
                report.append(f"  *Justifications:* {reasons}")
    else:
        report.append("No clinical entities detected.")
    report.append("")

    # 3. Comparative Analysis (if present)
    if comparison_results:
        report.append("## 3. Comparative Clinical Analysis")
        comp_summary = comparison_results.get("summary", "No summary available.")
        report.append(f"**Comparison Status:** {comparison_results.get('relationship_type', 'N/A')}")
        report.append(f"**Overlapping Synonyms:** {', '.join(comparison_results.get('shared_synonyms', [])) or 'None'}")
        report.append(f"**Analysis Details:** {comp_summary}\n")

    # 4. Scientific Literature citations
    report.append("## 4. Relevant Scientific Literature (PubMed)")
    if literature_results:
        for idx, art in enumerate(literature_results, 1):
            title = art.get("title", "No Title")
            authors = art.get("authors", "Unknown Authors")
            source = art.get("source", "PubMed")
            date = art.get("pubdate", "")
            url = art.get("url", "#")
            report.append(f"{idx}. **[{title}]({url})**")
            report.append(f"   *Authors:* {authors} | *Journal:* {source} ({date}) | *PMID:* {art.get('pmid', 'N/A')}\n")
    else:
        report.append("No clinical literature citations were retrieved.")
    report.append("")
    
    # 5. Disclaimer
    report.append("## 5. Clinical Disclaimer")
    report.append("> [!WARNING]")
    report.append("> This report is generated automatically by an AI-assisted biomedical pipeline for research and educational support. It does not constitute formal clinical advice. Diagnoses and treatment decisions should always be made by a licensed healthcare professional.")

    return "\n".join(report)

if __name__ == "__main__":
    test_resolved = [
        {
            "mention": "MI",
            "canonical_name": "Myocardial Infarction",
            "entity_type": "Disease",
            "identifier": "MESH:D009203",
            "confidence": 0.98,
            "status": "resolved",
            "reason": ["Matched official synonym", "Highest semantic similarity"],
            "explanation": "Resolved mention 'MI' to 'Myocardial Infarction' (MESH:D009203)."
        }
    ]
    test_lit = [
        {
            "pmid": "30153434",
            "title": "Fourth universal definition of myocardial infarction (2018).",
            "authors": "Thygesen K, et al.",
            "source": "J Am Coll Cardiol",
            "pubdate": "2018",
            "url": "https://pubmed.ncbi.nlm.nih.gov/30153434/"
        }
    ]
    print("Testing generate_report tool...")
    print(generate_report("MI patients", test_resolved, test_lit))
