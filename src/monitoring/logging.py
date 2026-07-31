import logging
import json

class JSONFormatter(logging.Formatter):
    """
    Format standard python logs as single-line JSON structures.
    """
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "line": record.lineno
        }
        
        # Inject trace/request context if attached to record
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "latency_ms"):
            log_record["latency_ms"] = record.latency_ms
            
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured JSON logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%SZ")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger
