import sqlite3
from typing import Dict, Any, List, Tuple
import sys
from pathlib import Path

# Add project root to path to enable 'src' imports when running standalone scripts
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.monitoring.metrics import DB_PATH, log_alert

def run_drift_detection(threshold: float = 0.15) -> Dict[str, Any]:
    """
    Compares the average confidence scores of the last 50 resolutions (target)
    against the baseline (all resolutions older than those 50) to detect drift.
    Returns drift metrics and logs alerts if drift is detected.
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Get count of total resolutions
        cursor.execute("SELECT COUNT(*) FROM resolved_entities_log")
        total_count = cursor.fetchone()[0]
        
        if total_count < 20:
            conn.close()
            return {"status": "INSUFFICIENT_DATA", "message": "At least 20 resolutions needed to detect drift."}
            
        # Target: Last 20 resolutions
        cursor.execute("""
            SELECT confidence FROM resolved_entities_log 
            ORDER BY timestamp DESC LIMIT 20
        """)
        target_scores = [r[0] for r in cursor.fetchall()]
        avg_target = sum(target_scores) / len(target_scores)
        
        # Baseline: Resolutions before the last 20 (up to 500)
        cursor.execute("""
            SELECT confidence FROM resolved_entities_log 
            WHERE id NOT IN (
                SELECT id FROM resolved_entities_log 
                ORDER BY timestamp DESC LIMIT 20
            )
            ORDER BY timestamp DESC LIMIT 500
        """)
        baseline_scores = [r[0] for r in cursor.fetchall()]
        
        if not baseline_scores:
            # Fallback if there are exactly total_count >= 20 but no older baseline
            avg_baseline = 0.90  # Default expected high confidence
        else:
            avg_baseline = sum(baseline_scores) / len(baseline_scores)
            
        drift_val = avg_baseline - avg_target
        drift_detected = drift_val > threshold
        
        if drift_detected:
            log_alert(
                alert_type="DRIFT_DETECTED",
                severity="WARNING",
                message=f"Confidence drift detected! Baseline avg confidence: {avg_baseline:.2f}, Recent avg: {avg_target:.2f} (Drop: {drift_val:.2f})"
            )
            
        conn.close()
        return {
            "status": "SUCCESS",
            "drift_detected": drift_detected,
            "baseline_avg": avg_baseline,
            "target_avg": avg_target,
            "drift_value": drift_val,
            "threshold": threshold
        }
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

def get_system_health_metrics() -> Dict[str, Any]:
    """
    Aggregates throughput, average latency breakdown, and total costs.
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Throughput & Errors
        cursor.execute("""
            SELECT 
                COUNT(*) as total_requests,
                SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) as error_requests,
                SUM(cost) as total_cost,
                AVG(total_latency_ms) as avg_latency,
                AVG(ner_latency_ms) as avg_ner,
                AVG(retrieval_latency_ms) as avg_retrieval,
                AVG(ranking_latency_ms) as avg_ranking,
                AVG(llm_latency_ms) as avg_llm,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens
            FROM requests_log
        """)
        row = cursor.fetchone()
        
        metrics = {
            "total_requests": row["total_requests"] or 0,
            "error_requests": row["error_requests"] or 0,
            "total_cost": row["total_cost"] or 0.0,
            "avg_latency_ms": row["avg_latency"] or 0.0,
            "avg_ner_ms": row["avg_ner"] or 0.0,
            "avg_retrieval_ms": row["avg_retrieval"] or 0.0,
            "avg_ranking_ms": row["avg_ranking"] or 0.0,
            "avg_llm_ms": row["avg_llm"] or 0.0,
            "total_input_tokens": row["total_input_tokens"] or 0,
            "total_output_tokens": row["total_output_tokens"] or 0,
        }
        
        # 2. Avg confidence
        cursor.execute("SELECT AVG(confidence) FROM resolved_entities_log")
        avg_conf_row = cursor.fetchone()
        metrics["avg_confidence"] = avg_conf_row[0] if avg_conf_row and avg_conf_row[0] is not None else 0.0
        
        conn.close()
        return metrics
    except Exception as e:
        print(f"Error getting system health metrics: {e}")
        return {}

def get_biomedical_analytics() -> Dict[str, Any]:
    """
    Returns statistics on ontologies, top entities, and ambiguity.
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Top searched terms (mentions)
        cursor.execute("""
            SELECT mention, COUNT(*) as count 
            FROM resolved_entities_log 
            GROUP BY mention 
            ORDER BY count DESC LIMIT 10
        """)
        top_mentions = cursor.fetchall()
        
        # Ontology usage breakdown
        cursor.execute("""
            SELECT ontology, COUNT(*) as count 
            FROM resolved_entities_log 
            GROUP BY ontology 
            ORDER BY count DESC
        """)
        ontology_usage = cursor.fetchall()
        
        # Most ambiguous terms (average confidence lowest)
        cursor.execute("""
            SELECT mention, AVG(confidence) as avg_conf, COUNT(*) as count 
            FROM resolved_entities_log 
            GROUP BY mention 
            HAVING count >= 2
            ORDER BY avg_conf ASC LIMIT 10
        """)
        ambiguous_mentions = cursor.fetchall()
        
        conn.close()
        return {
            "top_mentions": top_mentions,
            "ontology_usage": ontology_usage,
            "ambiguous_mentions": ambiguous_mentions
        }
    except Exception as e:
        print(f"Error getting biomedical analytics: {e}")
        return {}
