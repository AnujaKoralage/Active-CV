import logging
import json
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logger(name: str, log_file: str, level: int = logging.INFO):
    """Setup a rotating logger with a custom formatter."""
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

class AuditTrail:
    """Handles JSON-based trade audit trails."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                json.dump([], f)

    def log_event(self, event_type: str, data: dict):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            **data
        }
        try:
            with open(self.filepath, 'r+') as f:
                logs = json.load(f)
                logs.append(event)
                f.seek(0)
                json.dump(logs, f, indent=2)
                f.truncate()
        except Exception as e:
            # Fallback for concurrent access or large file
            print(f"Error logging to audit trail: {e}")

def get_trading_logger():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return setup_logger("trading", os.path.join(log_dir, "trading.log"))

def get_audit_trail():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return AuditTrail(os.path.join(log_dir, "audit_trail.json"))
