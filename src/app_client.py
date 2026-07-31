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
        <!-- <span style="font-size: 64px;">🧬</span> -->
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
        # {"title": "🔍 Explain Entity", "desc": "Explain clinical entity 'MI'", "query": "Explain MI"},
        # {"title": "⚖️ Compare Entities", "desc": "Compare Tylenol with Advil", "query": "Compare Tylenol with Advil"},
        {"title": "🧬 Resolve Gene symbol", "desc": "Normalize 'TP53' to HGNC canonical", "query": "Resolve gene symbol TP53"},
        {"title": "📚 Search PubMed Literature", "desc": "Fetch articles on Acetaminophen safety", "query": "Search PubMed for Acetaminophen safety"}
    ]
    for idx, p in enumerate(prompts):
        with cols[idx % 2]:
            # Styled card button layout
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
                            "query": query_to_process,
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
    st.rerun()

# Minimalist floating disclaimer
st.markdown("""
<div style='text-align: center; font-size: 11px; color: #555; margin-top: 40px; width: 100%;'>
    Biomedical Agent can make mistakes. Verify clinical details in peer-reviewed sources.
    <br>
    Built with ❤️ by <a href='https://www.linkedin.com/in/unekwuojo-james-b2511225b/' target='_blank' style='color: #888; text-decoration: underline;'>Jamesunekwuojo</a>
</div>
""", unsafe_allow_html=True)
