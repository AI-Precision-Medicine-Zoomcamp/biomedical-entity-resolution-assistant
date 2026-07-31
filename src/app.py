import sys
import uuid
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import streamlit as st
from src.agent.pydantic_ai_agent import PydanticAIBiomedicalAgent
from src.agent.router import WorkflowRouter
from src.entity_resolution.pipeline import BiomedicalEntityResolverPipeline
from src.tools import generate_report

def generate_conversational_response(query_text: str, resolved_entities: list) -> str:
    if not resolved_entities:
        return (
            "I am a specialized Biomedical Entity Resolution Assistant. I couldn't identify any clinical terms, "
            "genes, variants, or drugs in your query, which appears to be outside my medical domain. "
            "Please specify a clinical term or ask a biomedical question!"
        )
    
    parts = []
    parts.append(f"I analyzed your query and identified the following biomedical concept(s):\n")
    for ent in resolved_entities:
        if isinstance(ent, dict):
            mention = ent.get("mention", "")
            canonical = ent.get("canonical_name", ent.get("canonical", ""))
            etype = ent.get("entity_type", "Concept")
            oid = ent.get("identifier", "")
            explanation = ent.get("explanation", "")
        else:
            mention = getattr(ent, "mention", "")
            canonical = getattr(ent, "canonical_name", getattr(ent, "canonical", ""))
            etype = getattr(ent, "entity_type", "Concept")
            oid = getattr(ent, "identifier", "")
            explanation = getattr(ent, "explanation", "")
            
        parts.append(f"* **Mention:** `{mention}` → **{canonical}** (`{oid}`)")
        parts.append(f"  * **Type:** {etype}")
        if explanation:
            parts.append(f"  * **Explanation:** {explanation}")
            
    parts.append("\n*If you would like a detailed, formal clinical report with PubMed references, please ask me to 'generate a report'.*")
    return "\n".join(parts)

# 1. Page Configuration and Theming
st.set_page_config(
    page_title="Biomedical Agent",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom ChatGPT-like Dark & Minimalist Theme
st.markdown("""
<style>
    /* Hide Streamlit default styling elements but keep toolbar visible for the expand button */
    footer {visibility: hidden;}
    div[data-testid="stDecoration"] {visibility: hidden !important;}
    
    /* Hide specific deployment/settings actions from toolbar */
    div[data-testid="stAppDeployButton"], 
    button[data-testid="stBaseButton-header"],
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
    }
    
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        box-shadow: none !important;
        border: none !important;
        z-index: 99999 !important;
        display: block !important;
        visibility: visible !important;
    }
    
    /* Custom Styling for Streamlit's Expand Sidebar Button when collapsed */
    button[data-testid="stExpandSidebarButton"] {
        background-color: #2f2f2f !important; /* Lighter background for better contrast against #212121 */
        color: #ececec !important;
        border: 1px solid #4f4f4f !important;
        border-radius: 8px !important;
        transition: background-color 0.2s ease !important;
        z-index: 9999999 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: fixed !important;
        top: 12px !important;
        left: 12px !important;
        width: 40px !important;
        height: 40px !important;
    }
    button[data-testid="stExpandSidebarButton"]:hover {
        background-color: #383838 !important;
    }
    button[data-testid="stExpandSidebarButton"] svg, button[data-testid="stExpandSidebarButton"] span {
        color: #ececec !important;
        fill: #ececec !important;
        visibility: visible !important;
    }
    
    /* Force collapse button inside the sidebar to be visible */
    div[data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        display: block !important;
        opacity: 1 !important;
    }
    div[data-testid="stSidebarCollapseButton"] button {
        visibility: visible !important;
        display: inline-flex !important;
        opacity: 1 !important;
        background-color: transparent !important;
        border: none !important;
    }
    div[data-testid="stSidebarCollapseButton"] button:hover {
        background-color: #2f2f2f !important;
    }
    div[data-testid="stSidebarCollapseButton"] button svg {
        color: #ececec !important;
        fill: #ececec !important;
    }
    
    /* Main body background to match ChatGPT Dark Mode */
    .stApp {
        background-color: #212121 !important;
        color: #ececec !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    /* Center and limit width of the chat area */
    .block-container {
        max-width: 800px !important;
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #171717 !important;
        border-right: 1px solid #2f2f2f !important;
        width: 260px !important;
    }
    
    /* Sidebar navigation elements */
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: transparent !important;
        color: #ececec !important;
        border: 1px solid #4d4d4d !important;
        border-radius: 8px !important;
        width: 100% !important;
        text-align: left !important;
        padding: 10px 14px !important;
        font-size: 13px !important;
        transition: background-color 0.2s ease !important;
        font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #2f2f2f !important;
        border-color: #4d4d4d !important;
    }
    
    /* Main Chat bubble text size controls */
    div[data-testid="stChatMessage"] {
        background-color: transparent !important;
        border: none !important;
        padding: 1.2rem 0 !important;
    }
    div[data-testid="stChatMessageContent"] {
        font-size: 14px !important;
        line-height: 1.6 !important;
    }
    
    /* Minimal micro-pill badge styling */
    .micro-pill {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 500;
        margin-right: 6px;
        margin-bottom: 6px;
        border: 1px solid transparent;
        font-family: monospace;
    }
    .pill-resolved {
        background-color: rgba(22, 163, 74, 0.1);
        color: #4ade80;
        border-color: rgba(22, 163, 74, 0.3);
    }
    .pill-review {
        background-color: rgba(234, 88, 12, 0.1);
        color: #fb923c;
        border-color: rgba(234, 88, 12, 0.3);
    }
    .pill-rejected {
        background-color: rgba(220, 38, 38, 0.1);
        color: #f87171;
        border-color: rgba(220, 38, 38, 0.3);
    }
    
    /* Model selector container */
    .model-selector {
        font-size: 14px;
        color: #b4b4b4;
        display: inline-flex;
        align-items: center;
        padding: 6px 12px;
        border-radius: 8px;
        cursor: default;
    }
    .active-dot {
        height: 6px;
        width: 6px;
        background-color: #10a37f;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    .inactive-dot {
        height: 6px;
        width: 6px;
        background-color: #ef4444;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    
    /* ChatGPT-style custom chat input styling */
    div[data-testid="stChatInput"] {
        background-color: #262730 !important;
        border: 1px solid #4f4f4f !important;
        border-radius: 28px !important;
        padding: 6px 12px !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }
    div[data-testid="stChatInput"]:focus-within {
        box-shadow: 0 0 0 2px rgba(16, 163, 127, 0.2) !important;
    }
    div[data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        border: none !important;
        color: #ececec !important;
        font-size: 15px !important;
        border-radius: 28px !important;
        padding-left: 10px !important;
    }
    div[data-testid="stChatInput"] button {
        border-radius: 50% !important;
        background-color: #4f4f4f !important;
        color: white !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: background-color 0.2s, color 0.2s !important;
    }
    div[data-testid="stChatInput"]:focus-within button {
        background-color: #ececec !important;
        color: #212121 !important;
    }
    div[data-testid="stChatInput"]:focus-within button svg {
        color: #212121 !important;
        fill: #212121 !important;
    }

    /* Custom styling for Streamlit's bottom container wrapper */
    div[data-testid="stBottomBlockContainer"] {
        background-color: #212121 !important; 
        background-image: none !important;
        border: none !important;                  
        padding-bottom: 20px !important;         
        box-shadow: none !important;
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

# 4. Minimalist ChatGPT Sidebar
with st.sidebar:
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.all_resolved_entities = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
        
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 11px; font-weight: 600; color: #666; margin-left: 5px; text-transform: uppercase;'>Recent</p>", unsafe_allow_html=True)
    
    # Active Session display
    st.markdown(f"""
    <div style='background-color: #2f2f2f; padding: 8px 12px; border-radius: 6px; font-size: 12px; color: #ececec; border-left: 3px solid #10a37f;'>
        💬 Active Session<br>
        <span style='font-size: 10px; color: #888;'>{st.session_state.session_id[:13]}...</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 11px; font-weight: 600; color: #666; margin-left: 5px; text-transform: uppercase;'>Resolution Metrics</p>", unsafe_allow_html=True)
    
    # Minimal metrics counter
    if st.session_state.all_resolved_entities:
        total_ents = len(st.session_state.all_resolved_entities)
        resolved_ents = sum(1 for e in st.session_state.all_resolved_entities if e.get("status") == "resolved")
        review_ents = sum(1 for e in st.session_state.all_resolved_entities if e.get("status") == "needs_review")
        st.markdown(f"""
        <div style='font-size: 12px; color: #b4b4b4; padding-left: 5px; line-height: 1.8;'>
            Captured: <strong>{total_ents}</strong><br>
            Resolved: <strong style="color: #4ade80;">{resolved_ents}</strong><br>
            Review Queue: <strong style="color: #fb923c;">{review_ents}</strong>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("<p style='font-size: 12px; color: #555; padding-left: 5px;'>No data logged.</p>", unsafe_allow_html=True)

# 5. Top Navigation Selector
col_left, col_right = st.columns([8, 2])
with col_left:
    st.markdown("""
    <div class="model-selector">
        <span class="active-dot"></span>
        <strong style="color: #ececec; font-size: 13px;">Biomedical Agent v1.0 (Direct Mode)</strong>
    </div>
    """, unsafe_allow_html=True)
with col_right:
    st.markdown("<span style='font-size: 11px; color: #666; float: right; margin-top: 6px;'>MeSH / RxNorm / HGNC</span>", unsafe_allow_html=True)

st.markdown("<div style='height: 1px; background-color: #2f2f2f; margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

# 6. Chat History Render or Empty State
if not st.session_state.messages:
    # Override chat input position to be vertically centered on the page when empty
    st.markdown("""
    <style>
        div[data-testid="stChatInput"] {
            position: fixed !important;
            bottom: 30% !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: calc(100% - 40px) !important;
            max-width: 680px !important;
            z-index: 1000 !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
            transition: left 0.3s ease-in-out !important;
        }
        /* Shift input right when sidebar is expanded */
        [data-testid="stSidebar"][aria-expanded="true"] ~ * div[data-testid="stChatInput"] {
            left: 58% !important;
        }
        .block-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 80vh;
        }
    </style>
    """, unsafe_allow_html=True)

    # Large emoji and heading
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1rem; margin-top: -50px;">
        <h1 style="font-size: 32px; font-weight: 700; margin-top: 1rem; color: #ececec; letter-spacing: -0.5px;">How can I help you today?</h1>
        <p style="color: #b4b4b4; font-size: 15px; max-width: 500px; margin: 0.5rem auto 0 auto; line-height: 1.5;">
            Resolve clinical mentions, map gene symbols, fetch PubMed literature, or run comparative analyses.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Custom styling for card buttons to make them look premium
    st.markdown("""
    <style>
        div[data-testid="column"] div.stButton > button {
            background-color: #2f2f2f !important;
            color: #ececec !important;
            border: 1px solid #3c3c3c !important;
            border-radius: 12px !important;
            padding: 16px 20px !important;
            text-align: left !important;
            min-height: 85px !important;
            width: 100% !important;
            transition: background-color 0.2s, border-color 0.2s, transform 0.1s !important;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: flex-start;
        }
        div[data-testid="column"] div.stButton > button:hover {
            background-color: #383838 !important;
            border-color: #555555 !important;
            transform: translateY(-1px);
        }
        div[data-testid="column"] div.stButton > button:active {
            transform: translateY(0);
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<p style='font-size: 11px; font-weight: 600; color: #777; text-align: center; text-transform: uppercase; margin-bottom: 1.5rem; letter-spacing: 0.5px;'>Suggested Actions</p>", unsafe_allow_html=True)
    
    cols = st.columns(2)
    prompts = [
        {"title": "🧬 Resolve Gene symbol", "desc": "Normalize 'TP53' to HGNC canonical", "query": "Resolve gene symbol TP53"},
        {"title": "📚 Search PubMed Literature", "desc": "Fetch articles on Acetaminophen safety", "query": "Search PubMed for Acetaminophen safety"}
    ]
    for idx, p in enumerate(prompts):
        with cols[idx % 2]:
            button_label = f"**{p['title']}**\n{p['desc']}"
            if st.button(button_label, key=f"suggest_{idx}", use_container_width=True):
                st.session_state.suggested_query = p["query"]
                st.rerun()

    # Extra spacing so the input is placed nicely below suggestions
    st.markdown("<div style='height: 180px; background-color: #212121 !important;'></div>", unsafe_allow_html=True)

else:
    # Standard ChatGPT bottom-aligned layout
    st.markdown("""
    <style>
        div[data-testid="stChatInput"] {
            position: fixed !important;
            bottom: 25px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: calc(100% - 40px) !important;
            max-width: 760px !important;
            z-index: 1000 !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2) !important;
            transition: left 0.3s ease-in-out !important;
        }
        /* Shift input right when sidebar is expanded */
        [data-testid="stSidebar"][aria-expanded="true"] ~ * div[data-testid="stChatInput"] {
            left: 58% !important;
        }
        .block-container {
            padding-bottom: 120px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🧬"
        with st.chat_message(message["role"], avatar=avatar):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                res_meta = message.get("metadata", {})
                intent = res_meta.get("intent", "COMPLEX_AGENT")
                
                # Sub-info/routing details rendered minimally
                if intent == "OUT_OF_DOMAIN":
                    st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>🌐 <em>Out of Domain Guardrail</em></p>", unsafe_allow_html=True)
                elif intent == "SIMPLE_RESOLUTION":
                    st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>⚡ <em>Deterministic Module 2 Resolution</em></p>", unsafe_allow_html=True)
                else:
                    st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>🧠 <em>Biomedical Agent RAG reasoning loop</em></p>", unsafe_allow_html=True)
                    
                st.markdown(message["content"])
                
                # Horizontal minimal entity pills
                entities = res_meta.get("resolved_entities", [])
                if entities:
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    pills_html = ""
                    for ent in entities:
                        status = ent.get("status", "resolved")
                        pill_class = "pill-resolved" if status == "resolved" else ("pill-review" if status == "needs_review" else "pill-rejected")
                        
                        pill_text = f"{ent.get('ontology')}: {ent.get('mention')} ➜ {ent.get('canonical_name', ent.get('canonical'))} ({ent.get('identifier', ent.get('concept_id'))})"
                        pills_html += f"<span class='micro-pill {pill_class}'>{pill_text}</span>"
                        
                    st.markdown(pills_html, unsafe_allow_html=True)

# 7. Bottom Input Bar & Disclaimer
user_query = None
if "suggested_query" in st.session_state and st.session_state.suggested_query:
    user_query = st.session_state.suggested_query
    del st.session_state.suggested_query
else:
    user_query = st.chat_input("Message Biomedical Agent...")

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.session_state.pending_query = user_query
    st.rerun()

# If there is a pending query, process it in the new layout phase
if "pending_query" in st.session_state and st.session_state.pending_query:
    query_to_process = st.session_state.pending_query
    del st.session_state.pending_query
    
    with st.chat_message("assistant", avatar="🧬"):
        try:
            with st.spinner(" "):
                route = router.route(query_to_process)
                
                if route == "SIMPLE_RESOLUTION":
                    resolved_entities_raw = resolver.resolve_text(query_to_process)
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
                            
                    normalized = query_to_process.lower().strip()
                    needs_report = any(keyword in normalized for keyword in ["report", "table", "markdown", "generate report", "make a report", "clinical report"])
                    
                    if not resolved_entities_raw:
                        report = (
                            "I am a specialized Biomedical Entity Resolution Assistant. I couldn't identify any clinical terms, "
                            "genes, variants, or drugs in your query, which appears to be outside my medical domain. "
                            "Please specify a clinical term or ask a biomedical question!"
                        )
                        intent = "OUT_OF_DOMAIN"
                    else:
                        if needs_report:
                            report = generate_report(query_to_process, entities_dict)
                        else:
                            report = agent.generate_conversational_explanation(query_to_process, entities_dict)
                        intent = "SIMPLE_RESOLUTION"
                        
                    agent.history_manager.add_turn(
                        session_id=st.session_state.session_id,
                        user_content=query_to_process,
                        assistant_content=report,
                        resolved_entities=entities_dict
                    )
                    res_payload = {
                        "session_id": st.session_state.session_id,
                        "original_query": query_to_process,
                        "enriched_query": query_to_process,
                        "intent": intent,
                        "resolved_entities": entities_dict,
                        "report": report,
                        "route": "SIMPLE_RESOLUTION"
                    }
                else:
                    res = agent.process_query(query_to_process, session_id=st.session_state.session_id)
                    res_payload = {
                        "session_id": res["session_id"],
                        "original_query": res["original_query"],
                        "enriched_query": res["enriched_query"],
                        "intent": res["intent"],
                        "resolved_entities": res["resolved_entities"],
                        "report": res["report"],
                        "route": "COMPLEX_AGENT"
                    }
            
            # Render Results
            if res_payload.get("intent") == "OUT_OF_DOMAIN":
                st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>🌐 <em>Out of Domain Guardrail</em></p>", unsafe_allow_html=True)
            elif res_payload["route"] == "SIMPLE_RESOLUTION":
                st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>⚡ <em>Deterministic Module 2 Resolution</em></p>", unsafe_allow_html=True)
            else:
                st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>🧠 <em>Biomedical Agent RAG reasoning loop</em></p>", unsafe_allow_html=True)
                
            st.markdown(res_payload["report"])
            
            # Render entity pills
            entities = res_payload["resolved_entities"]
            if entities:
                st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                pills_html = ""
                for ent in entities:
                    status = ent.get("status", "resolved")
                    pill_class = "pill-resolved" if status == "resolved" else ("pill-review" if status == "needs_review" else "pill-rejected")
                    
                    pill_text = f"{ent.get('ontology')}: {ent.get('mention')} ➜ {ent.get('canonical_name', ent.get('canonical'))} ({ent.get('identifier', ent.get('concept_id'))})"
                    pills_html += f"<span class='micro-pill {pill_class}'>{pill_text}</span>"
                    
                st.markdown(pills_html, unsafe_allow_html=True)
                st.session_state.all_resolved_entities.extend(entities)
                
            # Save response to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": res_payload["report"],
                "metadata": res_payload
            })
            
        except Exception as err:
            error_msg = f"Error processing request: {err}"
            st.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg,
                "metadata": {}
            })
    st.rerun()

# Minimalist floating disclaimer
st.markdown("""
<div style='text-align: center; font-size: 11px; color: #555; margin-top: 40px; width: 100%;'>
    Biomedical Agent can make mistakes. Verify clinical details in peer-reviewed sources.
    <br>
    Built with ❤️ by <a href='https://www.linkedin.com/in/unekwuojo-james-b2511225b/' target='_blank' style='color: #888; text-decoration: underline;'>Jamesunekwuojo</a>
</div>
""", unsafe_allow_html=True)
