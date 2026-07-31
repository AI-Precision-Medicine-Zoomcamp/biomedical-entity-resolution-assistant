import sqlite3
import os
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "monitoring.db"

def get_db_connection():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the SQLite database schema if not present.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. requests_log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests_log (
            request_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            query TEXT NOT NULL,
            intent TEXT NOT NULL,
            status TEXT NOT NULL,
            total_latency_ms REAL NOT NULL,
            ner_latency_ms REAL DEFAULT 0.0,
            retrieval_latency_ms REAL DEFAULT 0.0,
            ranking_latency_ms REAL DEFAULT 0.0,
            llm_latency_ms REAL DEFAULT 0.0,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost REAL DEFAULT 0.0,
            error_message TEXT
        )
    """)
    
    # 2. resolved_entities_log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resolved_entities_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            mention TEXT NOT NULL,
            canonical_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            identifier TEXT NOT NULL,
            ontology TEXT NOT NULL,
            confidence REAL NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (request_id) REFERENCES requests_log (request_id)
        )
    """)
    
    # 3. feedback_log (Human-in-the-loop expert corrections)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            mention TEXT NOT NULL,
            correct_canonical TEXT NOT NULL,
            correct_identifier TEXT NOT NULL,
            expert_notes TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    
    # 4. alerts_log (Proactive monitoring alerts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            resolved INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

def log_request(
    request_id: str,
    query: str,
    intent: str,
    status: str,
    total_latency_ms: float,
    ner_latency_ms: float = 0.0,
    retrieval_latency_ms: float = 0.0,
    ranking_latency_ms: float = 0.0,
    llm_latency_ms: float = 0.0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost: float = 0.0,
    error_message: str = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO requests_log (
            request_id, timestamp, query, intent, status,
            total_latency_ms, ner_latency_ms, retrieval_latency_ms,
            ranking_latency_ms, llm_latency_ms, input_tokens,
            output_tokens, cost, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        request_id, timestamp, query, intent, status,
        total_latency_ms, ner_latency_ms, retrieval_latency_ms,
        ranking_latency_ms, llm_latency_ms, input_tokens,
        output_tokens, cost, error_message
    ))
    conn.commit()
    conn.close()

def log_resolved_entity(
    request_id: str,
    mention: str,
    canonical_name: str,
    entity_type: str,
    identifier: str,
    ontology: str,
    confidence: float,
    status: str
):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO resolved_entities_log (
            request_id, timestamp, mention, canonical_name,
            entity_type, identifier, ontology, confidence, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        request_id, timestamp, mention, canonical_name,
        entity_type, identifier, ontology, confidence, status
    ))
    conn.commit()
    conn.close()

def log_feedback(
    request_id: str,
    mention: str,
    correct_canonical: str,
    correct_identifier: str,
    expert_notes: str = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO feedback_log (
            request_id, mention, correct_canonical, correct_identifier,
            expert_notes, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        request_id, mention, correct_canonical, correct_identifier,
        expert_notes, timestamp
    ))
    conn.commit()
    conn.close()

def log_alert(alert_type: str, severity: str, message: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO alerts_log (timestamp, alert_type, severity, message, resolved)
        VALUES (?, ?, ?, ?, 0)
    """, (timestamp, alert_type, severity, message))
    conn.commit()
    conn.close()

def resolve_alert(alert_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts_log SET resolved = 1 WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()

# Auto-initialize database on import
init_db()
