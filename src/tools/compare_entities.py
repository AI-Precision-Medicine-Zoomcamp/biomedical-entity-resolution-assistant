def compare_entities(entity_a: dict, entity_b: dict) -> dict:
    """
    Tool: compare_entities
    Compares two resolved entity definitions by comparing their types, ontology sources,
    canonical names, descriptions, and synonym lists.
    
    Args:
        entity_a (dict): The first resolved entity concept dictionary.
        entity_b (dict): The second resolved entity concept dictionary.
        
    Returns:
        dict: A structured comparison dictionary.
    """
    if not entity_a or not entity_b:
        return {"error": "Invalid input entities for comparison"}

    name_a = entity_a.get("canonical_name", "Unknown Concept A")
    name_b = entity_b.get("canonical_name", "Unknown Concept B")
    
    type_a = entity_a.get("entity_type", "Unknown")
    type_b = entity_b.get("entity_type", "Unknown")
    
    src_a = entity_a.get("source", entity_a.get("ontology", "Unknown"))
    src_b = entity_b.get("source", entity_b.get("ontology", "Unknown"))

    syns_a = set([s.strip().lower() for s in entity_a.get("synonyms", "").split("|") if s.strip()])
    syns_b = set([s.strip().lower() for s in entity_b.get("synonyms", "").split("|") if s.strip()])
    
    common_synonyms = list(syns_a.intersection(syns_b))
    
    # Analyze descriptions for shared terms
    desc_a = entity_a.get("description", "") or ""
    desc_b = entity_b.get("description", "") or ""
    words_a = set([w.lower().strip(",.") for w in desc_a.split() if len(w) > 4])
    words_b = set([w.lower().strip(",.") for w in desc_b.split() if len(w) > 4])
    common_description_words = list(words_a.intersection(words_b))
    
    relationship = "Related (Same Type & Source)" if (type_a == type_b and src_a == src_b) else "Different Types/Sources"
    if name_a == name_b:
        relationship = "Identical Concept"

    summary_text = (
        f"Comparing '{name_a}' ({type_a} from {src_a}) with '{name_b}' ({type_b} from {src_b}). "
        f"Relationship classified as '{relationship}'. "
    )
    if common_synonyms:
        summary_text += f"They share common synonyms: {', '.join(common_synonyms)}. "
    else:
        summary_text += "They do not share any common synonyms. "
        
    if common_description_words:
        summary_text += f"Both concepts describe overlap in terms like: {', '.join(common_description_words[:5])}."

    return {
        "concept_a": name_a,
        "concept_b": name_b,
        "type_a": type_a,
        "type_b": type_b,
        "ontology_a": src_a,
        "ontology_b": src_b,
        "same_type": type_a == type_b,
        "same_ontology": src_a == src_b,
        "shared_synonyms": common_synonyms,
        "shared_description_keywords": common_description_words[:10],
        "relationship_type": relationship,
        "summary": summary_text
    }

if __name__ == "__main__":
    import json
    ent1 = {
        "canonical_name": "Diabetes Mellitus",
        "entity_type": "Disease",
        "source": "MeSH",
        "synonyms": "Diabetes|Diabetes Mellitus|Diabetic",
        "description": "A chronic metabolic disease characterized by elevated levels of blood glucose."
    }
    ent2 = {
        "canonical_name": "Prediabetic State",
        "entity_type": "Disease",
        "source": "MeSH",
        "synonyms": "Prediabetes|Prediabetic|Borderline Diabetes",
        "description": "A metabolic state characterized by elevated blood glucose levels below the threshold for diabetes."
    }
    print("Testing compare_entities tool...")
    print(json.dumps(compare_entities(ent1, ent2), indent=2))
