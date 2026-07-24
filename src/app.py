import sys
import uuid
from pathlib import Path
import streamlit as st

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.agent.pydantic_ai_agent import PydanticAIBiomedicalAgent
from src.agent.router import WorkflowRouter
from src.entity_resolution.pipeline import BiomedicalEntityResolverPipeline
from src.tools import generate_report

# 1. Page Configuration and Theming
st.set_page_config(
    page_title="Biomedical Entity Resolution Assistant",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium CSS styling (Harmonious Teal/Slate theme with subtle micro-animations)
st.markdown("""
<style>
    /* Main container styling */
    .stApp {
        background-color: #0f172a;
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid #334155;
    }
    
    /* Title typography */
    h1, h2, h3 {
        font-family: 'Outfit', 'Inter', sans-serif;
        font-weight: 700;
        color: #38bdf8;
    }
    
    /* Clinical Card style */
    .clinical-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.3s ease;
    }
    .clinical-card:hover {
        border-color: #0ea5e9;
        box-shadow: 0 10px 15px -3px rgba(14, 165, 233, 0.1), 0 4px 6px -4px rgba(14, 165, 233, 0.1);
    }
    
    /* Badge styling */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .badge-ontology {
        background-color: #0284c7;
        color: #e0f2fe;
    }
    .badge-resolved {
        background-color: #16a34a;
        color: #dcfce7;
    }
    .badge-review {
        background-color: #ea580c;
        color: #ffedd5;
    }
    .badge-rejected {
        background-color: #dc2626;
        color: #fee2e2;
    }
    .badge-confidence {
        background-color: #4f46e5;
        color: #e0e7ff;
    }
    
    /* Custom divider line */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #334155, transparent);
        margin: 24px 0;
    }
</style>
""", unsafe_allow_html=True)

# 2. Cache resources for top performance
@st.cache_resource
def get_agent_instance():
    return PydanticAIBiomedicalAgent()

@st.cache_resource
def get_router_instance():
    return WorkflowRouter()

@st.cache_resource
def get_resolver_pipeline():
    return BiomedicalEntityResolverPipeline()

agent = get_agent_instance()
router = get_router_instance()
resolver = get_resolver_pipeline()

# 3. Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "all_resolved_entities" not in st.session_state:
    st.session_state.all_resolved_entities = []

# 4. Sidebar Options and Analytics Panel
with st.sidebar:
    st.image("https://img.icons8.com/color/120/dna.png", width=70)
    st.title("Biomedical Agent")
    st.markdown("🧬 *Clinical Entity Resolution & Multi-Source RAG*")
    st.markdown("---")
    
    st.subheader("⚙️ Session Configurations")
    session_id_input = st.text_input("Active Session ID", value=st.session_state.session_id, key="active_session_id")
    if session_id_input != st.session_state.session_id:
        st.session_state.session_id = session_id_input
        st.session_state.messages = []
        st.session_state.all_resolved_entities = []
        st.success("Session reset completed!")
        st.rerun()

    st.markdown("---")
    st.subheader("📊 Session Resolution Stats")
    
    if st.session_state.all_resolved_entities:
        total_ents = len(st.session_state.all_resolved_entities)
        resolved_ents = sum(1 for e in st.session_state.all_resolved_entities if e.get("status") == "resolved")
        review_ents = sum(1 for e in st.session_state.all_resolved_entities if e.get("status") == "needs_review")
        
        st.metric("Total Mentions Captured", total_ents)
        st.metric("Automatically Resolved", f"{resolved_ents} ({(resolved_ents/total_ents)*100:.1f}%)")
        st.metric("Needs Human Review", review_ents)
        
        # Display list of recently resolved terms
        st.markdown("**Recently Resolved Concepts:**")
        unique_canonicals = list(set(e.get("canonical_name", e.get("canonical", "Unknown")) for e in st.session_state.all_resolved_entities))
        for item in unique_canonicals[-5:]:
            st.markdown(f"🔬 `{item}`")
    else:
        st.info("No biomedical entities resolved in this session yet.")
        
    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.all_resolved_entities = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# 5. Main Screen Header
st.title("🧬 Biomedical Agent System")
st.markdown("Query clinical concepts, analyze research literature, and resolve biomedical synonyms in real-time.")

# 6. Chat History Render
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            # Check if this response has structured clinical results to display
            res_meta = message.get("metadata", {})
            
            # Show routing route & intent
            intent = res_meta.get("intent", "Unknown")
            route = res_meta.get("route", "COMPLEX_AGENT")
            
            # Render custom intent banner
            if route == "SIMPLE_RESOLUTION":
                st.info(f"⚡ **Fast Route (Module 2)**: Resolved deterministically (0 LLM Tokens used)")
            else:
                st.success(f"🧠 **Complex Route (Biomedical Agent)**: Multi-turn RAG & LLM Reasoning orchestration completed.")
                if res_meta.get("enriched_query") and res_meta.get("enriched_query") != res_meta.get("original_query"):
                    st.caption(f"*Pronoun resolved query: \"{res_meta.get('enriched_query')}\"*")
            
            # 1. Main Clinical Report Content
            st.markdown(message["content"])
            
            # 2. Resolved Entities expander panel
            entities = res_meta.get("resolved_entities", [])
            if entities:
                with st.expander("🔬 View Resolved Biomedical Entities Details", expanded=True):
                    cols = st.columns(len(entities) if len(entities) <= 3 else 3)
                    for idx, ent in enumerate(entities):
                        col_idx = idx % 3
                        with cols[col_idx]:
                            status = ent.get("status", "resolved")
                            badge_cls = "badge-resolved" if status == "resolved" else ("badge-review" if status == "needs_review" else "badge-rejected")
                            
                            st.markdown(f"""
                            <div class="clinical-card">
                                <strong>Mention:</strong> <code style="color:#38bdf8;">{ent.get('mention')}</code><br>
                                <strong>Canonical:</strong> <code>{ent.get('canonical_name', ent.get('canonical', 'Unknown'))}</code><br>
                                <span class="badge badge-ontology">{ent.get('ontology')}</span>
                                <span class="badge {badge_cls}">{status.upper()}</span>
                                <br>
                                <strong>ID:</strong> <code>{ent.get('identifier', ent.get('concept_id', 'N/A'))}</code><br>
                                <strong>Confidence:</strong> <code>{ent.get('confidence', 0.0):.2f}</code><br>
                                <details style="margin-top:8px;font-size:0.8rem;">
                                    <summary>Reasoning</summary>
                                    <ul style="padding-left:15px;margin-top:4px;">
                                        {"".join(f"<li>{r}</li>" for r in ent.get('reason', []))}
                                    </ul>
                                </details>
                            </div>
                            """, unsafe_allow_html=True)

# 7. User Interaction Input Loop
if user_query := st.chat_input("Enter clinical statement (e.g., 'Compare MI with Tylenol')"):
    # Append User Message to State
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # Process and Query
    with st.chat_message("assistant"):
        with st.spinner("Analyzing queries, resolving ontology entities, and querying literature sources..."):
            try:
                # A. Route query using Workflow Router
                route = router.route(user_query)
                
                # B. Execute corresponding handler
                if route == "SIMPLE_RESOLUTION":
                    resolved_entities_raw = resolver.resolve_text(user_query)
                    
                    # Convert to list of dict
                    entities_dict = []
                    for ent in resolved_entities_raw:
                        if isinstance(ent, dict):
                            entities_dict.append({
                                "mention": ent.get("mention", ""),
                                "canonical_name": ent.get("canonical_name", ent.get("canonical", "")),
                                "canonical": ent.get("canonical", ""),
                                "entity_type": ent.get("entity_type", ""),
                                "identifier": ent.get("identifier", ""),
                                "concept_id": ent.get("concept_id", ""),
                                "ontology": ent.get("ontology", ""),
                                "confidence": ent.get("confidence", 0.0),
                                "status": ent.get("status", "resolved"),
                                "reason": ent.get("reason", []),
                                "explanation": ent.get("explanation", "")
                            })
                        else:
                            entities_dict.append({
                                "mention": getattr(ent, "mention", ""),
                                "canonical_name": getattr(ent, "canonical_name", getattr(ent, "canonical", "")),
                                "canonical": getattr(ent, "canonical", ""),
                                "entity_type": getattr(ent, "entity_type", ""),
                                "identifier": getattr(ent, "identifier", ""),
                                "concept_id": getattr(ent, "concept_id", ""),
                                "ontology": getattr(ent, "ontology", ""),
                                "confidence": getattr(ent, "confidence", 0.0),
                                "status": getattr(ent, "status", "resolved"),
                                "reason": getattr(ent, "reason", []),
                                "explanation": getattr(ent, "explanation", "")
                            })
                            
                    report = generate_report(user_query, entities_dict)
                    
                    # Log turn in history
                    agent.history_manager.add_turn(
                        session_id=st.session_state.session_id,
                        user_content=user_query,
                        assistant_content=report,
                        resolved_entities=entities_dict
                    )
                    
                    res_payload = {
                        "session_id": st.session_state.session_id,
                        "original_query": user_query,
                        "enriched_query": user_query,
                        "intent": "SIMPLE_RESOLUTION",
                        "resolved_entities": entities_dict,
                        "report": report,
                        "route": "SIMPLE_RESOLUTION"
                    }
                else:
                    # Route to Complex reasoning agent
                    res = agent.process_query(user_query, session_id=st.session_state.session_id)
                    res_payload = {
                        "session_id": res["session_id"],
                        "original_query": res["original_query"],
                        "enriched_query": res["enriched_query"],
                        "intent": res["intent"],
                        "resolved_entities": res["resolved_entities"],
                        "report": res["report"],
                        "route": "COMPLEX_AGENT"
                    }

                # Display Results
                if res_payload["route"] == "SIMPLE_RESOLUTION":
                    st.info(f"⚡ **Fast Route (Module 2)**: Resolved deterministically (0 LLM Tokens used)")
                else:
                    st.success(f"🧠 **Complex Route (Biomedical Agent)**: Multi-turn RAG & LLM Reasoning orchestration completed.")
                    if res_payload["enriched_query"] != res_payload["original_query"]:
                        st.caption(f"*Pronoun resolved query: \"{res_payload['enriched_query']}\"*")

                st.markdown(res_payload["report"])
                
                # Render entities block
                entities = res_payload["resolved_entities"]
                if entities:
                    with st.expander("🔬 View Resolved Biomedical Entities Details", expanded=True):
                        cols = st.columns(len(entities) if len(entities) <= 3 else 3)
                        for idx, ent in enumerate(entities):
                            col_idx = idx % 3
                            with cols[col_idx]:
                                status = ent.get("status", "resolved")
                                badge_cls = "badge-resolved" if status == "resolved" else ("badge-review" if status == "needs_review" else "badge-rejected")
                                
                                st.markdown(f"""
                                <div class="clinical-card">
                                    <strong>Mention:</strong> <code style="color:#38bdf8;">{ent.get('mention')}</code><br>
                                    <strong>Canonical:</strong> <code>{ent.get('canonical_name', ent.get('canonical', 'Unknown'))}</code><br>
                                    <span class="badge badge-ontology">{ent.get('ontology')}</span>
                                    <span class="badge {badge_cls}">{status.upper()}</span>
                                    <br>
                                    <strong>ID:</strong> <code>{ent.get('identifier', ent.get('concept_id', 'N/A'))}</code><br>
                                    <strong>Confidence:</strong> <code>{ent.get('confidence', 0.0):.2f}</code><br>
                                    <details style="margin-top:8px;font-size:0.8rem;">
                                        <summary>Reasoning</summary>
                                        <ul style="padding-left:15px;margin-top:4px;">
                                            {"".join(f"<li>{r}</li>" for r in ent.get('reason', []))}
                                        </ul>
                                    </details>
                                </div>
                                """, unsafe_allow_html=True)
                                
                    # Accumulate session metrics
                    st.session_state.all_resolved_entities.extend(entities)

                # Save Response Message to State
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": res_payload["report"],
                    "metadata": res_payload
                })
                
            except Exception as err:
                st.error(f"Failed to process request: {err}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Failed to process request: {err}",
                    "metadata": {}
                })
