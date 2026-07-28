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
        except Exception as e:
            st.error(f"Error connecting to local resolve API: {e}")
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
