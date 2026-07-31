import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
from pathlib import Path
from datetime import datetime
import sys

# Insert project root into sys.path to enable 'src' resolution when run directly via Streamlit
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Local imports
from src.monitoring.metrics import DB_PATH, log_feedback, resolve_alert
from src.monitoring.analytics import run_drift_detection, get_system_health_metrics, get_biomedical_analytics

st.set_page_config(
    page_title="Biomedical Resolver Observability Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    div[data-testid="metric-container"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 15px 20px;
        border-radius: 10px;
        color: white;
    }
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

def get_conn():
    return sqlite3.connect(str(DB_PATH))

# Title
st.title("🏥 Biomedical Entity Resolution Observability Dashboard")
st.markdown("Real-time telemetry, model drift detection, cost monitoring, and clinician feedback loops.")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to Page", [
    "🏥 System Health Overview",
    "🧠 AI & LLM Performance",
    "🧬 Biomedical Analytics",
    "🚨 System Alerts",
    "🔍 Human-in-the-Loop Review"
])

st.sidebar.write("---")
st.sidebar.markdown("### Client Apps")
st.sidebar.markdown("[🧬 Main Chat Agent (Port 8501)](http://localhost:8501)")

conn = get_conn()

# Page 1: System Health Overview
if page == "🏥 System Health Overview":
    st.header("System Health & Operational Metrics")
    
    # Get metrics
    metrics = get_system_health_metrics()
    
    if not metrics or metrics.get("total_requests", 0) == 0:
        st.info("No request logs found in the database. Run the API or benchmark suite to generate telemetry data.")
    else:
        # Top-level Metric Cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total API Requests", f"{metrics['total_requests']:,}")
        with col2:
            st.metric("Avg Latency (ms)", f"{metrics['avg_latency_ms']:.1f}")
        with col3:
            st.metric("Error Rate", f"{(metrics['error_requests'] / metrics['total_requests'] * 100):.1f}%")
        with col4:
            st.metric("Total Cumulative Cost (USD)", f"${metrics['total_cost']:.4f}")
            
        st.write("---")
        
        # Drift Detection Box
        st.subheader("🤖 Active Drift Detection")
        drift = run_drift_detection()
        if drift["status"] == "SUCCESS":
            if drift["drift_detected"]:
                st.error(
                    f"⚠️ **CONFIDENCE DRIFT DETECTED!** "
                    f"Baseline average confidence: {drift['baseline_avg']:.2f}, "
                    f"Recent average confidence: {drift['target_avg']:.2f} "
                    f"(Difference: {drift['drift_value']:.2f} > threshold {drift['threshold']:.2f}). "
                    f"Please review low confidence queries and verify ontology/embedding health."
                )
            else:
                st.success(
                    f"✅ **System Stable.** Baseline average confidence: {drift['baseline_avg']:.2f}, "
                    f"Recent average confidence: {drift['target_avg']:.2f}. "
                    f"No resolution confidence drift detected."
                )
        else:
            st.info(f"Drift status: {drift.get('message', 'No drift data available.')}")
            
        st.write("---")
        
        # Latency & Throughput over time
        st.subheader("Performance Trends")
        df_reqs = pd.read_sql_query("SELECT timestamp, total_latency_ms, status FROM requests_log ORDER BY timestamp ASC", conn)
        df_reqs['timestamp'] = pd.to_datetime(df_reqs['timestamp'])
        df_reqs.set_index('timestamp', inplace=True)
        
        # Resample by minute/hour to show throughput and latency
        df_resampled = df_reqs.resample('10Min').agg({'total_latency_ms': 'mean', 'status': 'count'})
        df_resampled.columns = ['Avg Latency (ms)', 'Requests Count']
        df_resampled.fillna(0, inplace=True)
        
        col_left, col_right = st.columns(2)
        with col_left:
            st.write("#### Average Latency Over Time (10 Min Bins)")
            st.line_chart(df_resampled['Avg Latency (ms)'])
        with col_right:
            st.write("#### Throughput / Request Volume Over Time")
            st.area_chart(df_resampled['Requests Count'])

# Page 2: AI & LLM Performance
elif page == "🧠 AI & LLM Performance":
    st.header("LLM Costs & Token Usage Metrics")
    
    metrics = get_system_health_metrics()
    if not metrics or metrics.get("total_requests", 0) == 0:
        st.info("No LLM logs found. Generate some agent requests first.")
    else:
        # Token metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Input Tokens", f"{metrics['total_input_tokens']:,}")
        with col2:
            st.metric("Total Output Tokens", f"{metrics['total_output_tokens']:,}")
        with col3:
            st.metric("Estimated Cost", f"${metrics['total_cost']:.4f}")
            
        st.write("---")
        
        # Latency breakdown
        st.subheader("Pipeline Latency Breakdown")
        stages = {
            "Named Entity Recognition (NER)": metrics.get("avg_ner_ms", 0),
            "Candidate Retrieval": metrics.get("avg_retrieval_ms", 0),
            "Candidate Ranking": metrics.get("avg_ranking_ms", 0),
            "LLM Agent reasoning": metrics.get("avg_llm_ms", 0),
        }
        df_stages = pd.DataFrame(list(stages.items()), columns=["Pipeline Stage", "Average Latency (ms)"])
        st.bar_chart(df_stages.set_index("Pipeline Stage"))
        
        # Request details table
        st.subheader("Recent Requests Log")
        df_details = pd.read_sql_query("""
            SELECT timestamp, query, intent, total_latency_ms, input_tokens, output_tokens, cost, status
            FROM requests_log 
            ORDER BY timestamp DESC LIMIT 50
        """, conn)
        st.dataframe(df_details, use_container_width=True)

# Page 3: 🧬 Biomedical Analytics
elif page == "🧬 Biomedical Analytics":
    st.header("Biomedical Search Analytics")
    
    analytics = get_biomedical_analytics()
    if not analytics or not analytics.get("ontology_usage"):
        st.info("No biomedical entities logged. Send queries containing clinical terms to populate statistics.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("#### Ontology Usage Breakdown")
            df_ont = pd.DataFrame(analytics["ontology_usage"], columns=["Ontology", "Usage Count"])
            st.bar_chart(df_ont.set_index("Ontology"))
            
        with col2:
            st.write("#### Most Queried Medical Terms")
            df_mentions = pd.DataFrame(analytics["top_mentions"], columns=["Term Mention", "Search Frequency"])
            st.bar_chart(df_mentions.set_index("Term Mention"))
            
        st.write("---")
        
        st.subheader("Most Ambiguous / Low Confidence Terms (Average Confidence)")
        if analytics["ambiguous_mentions"]:
            df_amb = pd.DataFrame(analytics["ambiguous_mentions"], columns=["Term Mention", "Avg Confidence", "Query Volume"])
            st.dataframe(df_amb, use_container_width=True)
        else:
            st.write("No ambiguous queries with multiple hits yet.")

# Page 4: System Alerts
elif page == "🚨 System Alerts":
    st.header("Active System Alerts")
    
    df_alerts = pd.read_sql_query("""
        SELECT id, timestamp, alert_type, severity, message, resolved 
        FROM alerts_log 
        ORDER BY resolved ASC, timestamp DESC
    """, conn)
    
    if df_alerts.empty:
        st.success("🎉 No alerts registered in the system logs.")
    else:
        # Summarize alerts
        active_count = len(df_alerts[df_alerts['resolved'] == 0])
        st.metric("Active Warnings/Errors", active_count)
        
        st.write("---")
        
        # Display alerts table
        for idx, row in df_alerts.iterrows():
            resolved_text = "✅ Resolved" if row['resolved'] == 1 else "🚨 Active"
            color = "red" if row['severity'] == "CRITICAL" else "orange"
            
            with st.expander(f"[{resolved_text}] - {row['alert_type']} ({row['severity']}) - {row['timestamp'][:19]}"):
                st.write(f"**Description:** {row['message']}")
                if row['resolved'] == 0:
                    if st.button(f"Mark Alert {row['id']} as Resolved", key=f"alert_btn_{row['id']}"):
                        resolve_alert(row['id'])
                        st.rerun()

# Page 5: Human-in-the-Loop Review
elif page == "🔍 Human-in-the-Loop Review":
    st.header("Clinician & Expert Verification Panel")
    st.markdown("""
        Review resolutions that fell below the auto-accept confidence threshold ($< 0.90$) or triggered low-confidence warnings.
        Providing corrections closes the loop, saving validation data to retrain rankings and evaluate prompt adjustments.
    """)
    
    df_review = pd.read_sql_query("""
        SELECT e.id, e.request_id, e.timestamp, e.mention, e.canonical_name, e.entity_type, e.identifier, e.ontology, e.confidence, e.status
        FROM resolved_entities_log e
        WHERE e.status = 'needs_review' OR e.confidence < 0.80
        ORDER BY e.confidence ASC, e.timestamp DESC
    """, conn)
    
    if df_review.empty:
        st.success("✅ No records require human verification at this time.")
    else:
        st.write(f"There are **{len(df_review)}** resolutions awaiting review:")
        st.dataframe(df_review, use_container_width=True)
        
        st.write("---")
        st.subheader("Submit Correction Form")
        
        # Pick one concept to correct
        selected_mention_idx = st.selectbox(
            "Select entity to verify/correct",
            range(len(df_review)),
            format_func=lambda i: f"'{df_review.iloc[i]['mention']}' (currently resolved to: '{df_review.iloc[i]['canonical_name']}' - Conf: {df_review.iloc[i]['confidence']:.2f})"
        )
        
        if selected_mention_idx is not None:
            row = df_review.iloc[selected_mention_idx]
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("### Current System Output")
                st.write(f"**Mention:** `{row['mention']}`")
                st.write(f"**Canonical Name:** `{row['canonical_name']}`")
                st.write(f"**Identifier:** `{row['identifier']}`")
                st.write(f"**Ontology Source:** `{row['ontology']}`")
                st.write(f"**Confidence:** `{row['confidence']:.4f}`")
                
            with col2:
                st.write("### Expert Corection Inputs")
                correct_canonical = st.text_input("Correct Canonical Standard Name", value=row['canonical_name'])
                correct_identifier = st.text_input("Correct Ontology Identifier (URI)", value=row['identifier'])
                expert_notes = st.text_area("Clinician / Reviewer Notes", placeholder="Enter notes explaining the correction...")
                
                if st.button("Submit Expert Review & Save"):
                    log_feedback(
                        request_id=row['request_id'],
                        mention=row['mention'],
                        correct_canonical=correct_canonical,
                        correct_identifier=correct_identifier,
                        expert_notes=expert_notes
                    )
                    # Update database status to "resolved" to remove from review queue
                    cursor = conn.cursor()
                    cursor.execute("UPDATE resolved_entities_log SET status = 'resolved', confidence = 1.0 WHERE id = ?", (int(row['id']),))
                    conn.commit()
                    st.success("Correction submitted and stored in feedback log. Resolving status updated!")
                    st.rerun()

conn.close()
