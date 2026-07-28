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
    /* Hide Streamlit default styling elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
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
    
    /* Chat Input Styling */
    [data-testid="stChatInput"] {
        background-color: #2f2f2f !important;
        border: 1px solid #424242 !important;
        border-radius: 24px !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #ececec !important;
        font-size: 14px !important;
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

# 5. Top Navigation Selector (Just like Model dropdown in ChatGPT)
col_left, col_right = st.columns([8, 2])
with col_left:
    st.markdown("""
    <div class="model-selector">
        <span class="active-dot"></span>
        <strong style="color: #ececec; font-size: 13px;">Biomedical Agent v1.0</strong>
    </div>
    """, unsafe_allow_html=True)
with col_right:
    st.markdown("<span style='font-size: 11px; color: #666; float: right; margin-top: 6px;'>MeSH / RxNorm / HGNC</span>", unsafe_allow_html=True)

st.markdown("<div style='height: 1px; background-color: #2f2f2f; margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

# 6. Chat History Render
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🧬"
    with st.chat_message(message["role"], avatar=avatar):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            res_meta = message.get("metadata", {})
            route = res_meta.get("route", "COMPLEX_AGENT")
            
            # Sub-info/routing details rendered minimally
            if route == "SIMPLE_RESOLUTION":
                st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>⚡ <em>Deterministic Module 2 Resolution</em></p>", unsafe_allow_html=True)
            else:
                st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>🧠 <em>Biomedical Agent RAG reasoning loop</em></p>", unsafe_allow_html=True)
                
            # Main text content
            st.markdown(message["content"])
            
            # Horizontal minimal entity pills instead of massive boxes
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
if user_query := st.chat_input("Message Biomedical Agent..."):
    # Append User Message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_query)

    # Process Query
    with st.chat_message("assistant", avatar="🧬"):
        try:
            route = router.route(user_query)
            
            if route == "SIMPLE_RESOLUTION":
                resolved_entities_raw = resolver.resolve_text(user_query)
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
                
            # Render Results
            if res_payload["route"] == "SIMPLE_RESOLUTION":
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
                
            st.session_state.messages.append({
                "role": "assistant",
                "content": res_payload["report"],
                "metadata": res_payload
            })
            
        except Exception as err:
            st.error(f"Error processing request: {err}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Error: {err}",
                "metadata": {}
            })

# Minimalist floating disclaimer
st.markdown("""
<div style='text-align: center; font-size: 11px; color: #555; margin-top: 40px; width: 100%;'>
    Biomedical Agent can make mistakes. Verify clinical details in peer-reviewed sources.
</div>
""", unsafe_allow_html=True)
