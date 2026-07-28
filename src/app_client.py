import os
import sys
import uuid
import requests
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import streamlit as st

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
    footer {visibility: hidden;}
    div[data-testid="stToolbar"] {visibility: hidden !important;}
    div[data-testid="stDecoration"] {visibility: hidden !important;}
    
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        box-shadow: none !important;
        border: none !important;
        display: flex !important;
        visibility: visible !important;
        z-index: 99999 !important;
    }
    
    button[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        background-color: #212121 !important;
        color: #ececec !important;
        border: 1px solid #424242 !important;
        border-radius: 8px !important;
        transition: background-color 0.2s ease !important;
        z-index: 100000 !important;
    }
    button[data-testid="stSidebarCollapsedControl"]:hover, [data-testid="collapsedControl"]:hover {
        background-color: #2f2f2f !important;
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

# 2. Config & Initialization
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Check backend health
backend_online = False
try:
    health_check = requests.get(f"{API_URL}/", timeout=2.0)
    if health_check.status_code == 200:
        backend_online = True
except Exception:
    pass

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
    <div style='background-color: #2f2f2f; padding: 8px 12px; border-radius: 6px; font-size: 12px; color: #ececec; border-left: 3px solid {("#10a37f" if backend_online else "#ef4444")};'>
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
    status_dot = "active-dot" if backend_online else "inactive-dot"
    status_text = "Biomedical Entity Resolution Assistant v1.0" if backend_online else "Agent Offline"
    st.markdown(f"""
    <div class="model-selector">
        <span class="{status_dot}"></span>
        <strong style="color: #ececec; font-size: 13px;">{status_text}</strong>
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
            intent = res_meta.get("intent", "COMPLEX_AGENT")
            
            # Sub-info/routing details rendered minimally
            if intent == "SIMPLE_RESOLUTION":
                st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>⚡ <em>Deterministic Module 2 Resolution</em></p>", unsafe_allow_html=True)
            else:
                st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>🧠 <em>Biomedical Agent RAG reasoning loop</em></p>", unsafe_allow_html=True)
                
            # Main text content
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
if user_query := st.chat_input("Message Biomedical Agent..."):
    # Append User Message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_query)

    # Process Query via API
    with st.chat_message("assistant", avatar="🧬"):
        if not backend_online:
            error_msg = f"Cannot process query. Backend API at {API_URL} is offline. Please start it using `uv run python main.py`."
            st.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg,
                "metadata": {}
            })
        else:
            try:
                # Query the FastAPI backend over HTTP
                with st.spinner(" "):
                    response = requests.post(
                        f"{API_URL}/agent/query",
                        json={
                            "query": user_query,
                            "session_id": st.session_state.session_id
                        },
                        timeout=90.0
                    )
                
                if response.status_code == 200:
                    res_payload = response.json()
                    
                    intent = res_payload.get("intent", "COMPLEX_AGENT")
                    if intent == "SIMPLE_RESOLUTION":
                        st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>⚡ <em>Deterministic Module 2 Resolution</em></p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='font-size:11px; color:#b4b4b4; margin-bottom: 12px;'>🧠 <em>Biomedical Agent RAG reasoning loop</em></p>", unsafe_allow_html=True)
                        
                    st.markdown(res_payload["report"])
                    
                    # Render entity pills
                    entities = res_payload.get("resolved_entities", [])
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
                else:
                    error_msg = f"Backend returned an error ({response.status_code}): {response.text}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "metadata": {}
                    })
                    
            except Exception as err:
                error_msg = f"Failed to connect to backend: {err}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "metadata": {}
                })

# Minimalist floating disclaimer
st.markdown("""
<div style='text-align: center; font-size: 11px; color: #555; margin-top: 40px; width: 100%;'>
    Biomedical Agent can make mistakes. Verify clinical details in peer-reviewed sources.
</div>
""", unsafe_allow_html=True)
