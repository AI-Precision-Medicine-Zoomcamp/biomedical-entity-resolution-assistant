import streamlit as st
import requests

st.set_page_config(
    page_title="Biomedical Entity Resolution Assistant",
    page_icon="🧬",
    layout="centered"
)

st.title("🧬 Biomedical Entity Resolution Assistant")
st.markdown("""
A Precision Medicine AI assistant for resolving **biomedical entities** (genes, diseases, and genomic variants) into **canonical standardized representations**.
""")

# Input
query = st.text_input("Enter biomedical entity (e.g., HER1, NSCLC, Ex19del):", placeholder="HER1")

if st.button("Resolve Entity", type="primary"):
    if query:
        st.subheader("Resolution Result")
        query_upper = query.upper().strip()
        
        # Check API status or do direct resolve mock
        try:
            # Try to query the local API
            response = requests.post("http://localhost:8000/resolve", json={"query": query}, timeout=2)
            if response.status_code == 200:
                result = response.json()
            else:
                raise Exception("API returned non-200 status code")
        except Exception:
            # Fallback to direct resolution
            if query_upper in ["HER1", "ERBB1", "EGFR"]:
                result = {
                    "query": query,
                    "canonical_name": "EGFR",
                    "entity_type": "Gene",
                    "identifier": "HGNC:3236",
                    "confidence": 0.99,
                    "source": "HGNC"
                }
            elif query_upper in ["NSCLC", "NON-SMALL CELL LUNG CANCER"]:
                result = {
                    "query": query,
                    "canonical_name": "Non-Small Cell Lung Cancer",
                    "entity_type": "Disease",
                    "identifier": "MONDO:0008903",
                    "confidence": 0.95,
                    "source": "MONDO"
                }
            elif query_upper in ["EX19DEL", "EGFR EXON 19 DELETION"]:
                result = {
                    "query": query,
                    "canonical_name": "EGFR Exon 19 Deletion",
                    "entity_type": "Variant",
                    "identifier": "ClinVar:16209",
                    "confidence": 0.90,
                    "source": "ClinVar"
                }
            else:
                result = {
                    "query": query,
                    "canonical_name": query,
                    "entity_type": "Unknown",
                    "identifier": "Unknown",
                    "confidence": 0.0,
                    "source": "None"
                }
        
        # Display results nicely
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Canonical Name", value=result["canonical_name"])
            st.metric(label="Entity Type", value=result["entity_type"])
        with col2:
            st.metric(label="Identifier", value=result["identifier"])
            st.metric(label="Confidence Score", value=f"{result['confidence']:.2f}")
            
        st.json(result)
    else:
        st.warning("Please enter a query first!")
