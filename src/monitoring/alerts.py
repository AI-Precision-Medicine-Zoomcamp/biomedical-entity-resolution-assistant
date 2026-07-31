import sqlite3
from typing import Any
import sys
from pathlib import Path

# Add project root to path to enable 'src' imports when running standalone scripts
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.monitoring.metrics import log_alert, DB_PATH

def check_and_trigger_alerts(ctx: Any):
    """
    Evaluates telemetry metrics for a finished request and logs alerts to the database.
    """
    # Rule 1: Low Confidence Resolution
    for ent in ctx.resolved_entities:
        confidence = ent.get("confidence", 1.0)
        if confidence < 0.60:
            log_alert(
                alert_type="LOW_CONFIDENCE",
                severity="WARNING" if confidence >= 0.40 else "CRITICAL",
                message=f"Entity '{ent.get('mention')}' resolved with low confidence {confidence:.2f} (canonical: '{ent.get('canonical_name')}', identifier: '{ent.get('identifier')}')"
            )
            
    # Rule 2: High Latency Trigger (> 2.0 seconds is long for resolution, > 5.0 is critical)
    if ctx.total_latency_ms > 5000.0:
        log_alert(
            alert_type="HIGH_LATENCY",
            severity="CRITICAL",
            message=f"Request end-to-end latency exceeded critical limit: {ctx.total_latency_ms:.1f}ms (query: '{ctx.query}')"
        )
    elif ctx.total_latency_ms > 2000.0:
        log_alert(
            alert_type="HIGH_LATENCY",
            severity="WARNING",
            message=f"Request end-to-end latency was slow: {ctx.total_latency_ms:.1f}ms (query: '{ctx.query}')"
        )
        
    # Rule 3: Request Pipeline Error
    if ctx.status == "ERROR":
        log_alert(
            alert_type="PIPELINE_ERROR",
            severity="CRITICAL",
            message=f"Pipeline execution failed for query '{ctx.query}'. Error: {ctx.error_message}"
        )
        
    # Rule 4: High Single-Request Cost (> $0.05)
    if ctx.cost > 0.05:
        log_alert(
            alert_type="COST_LIMIT",
            severity="WARNING",
            message=f"Request LLM cost exceeded limit: ${ctx.cost:.4f} (query: '{ctx.query}')"
        )
        
    # Check cumulative daily cost limit (critical alert if > $5.00 in a day)
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        # Fetch sum of costs in last 24 hours
        cursor.execute("""
            SELECT SUM(cost) FROM requests_log 
            WHERE timestamp >= datetime('now', '-1 day')
        """)
        row = cursor.fetchone()
        daily_cost = row[0] if row and row[0] is not None else 0.0
        conn.close()
        
        if daily_cost > 5.00:
            log_alert(
                alert_type="DAILY_COST_LIMIT",
                severity="CRITICAL",
                message=f"Cumulative daily LLM spending exceeded critical limit: ${daily_cost:.2f}"
            )
    except Exception as e:
        print(f"Error checking cumulative cost: {e}")
