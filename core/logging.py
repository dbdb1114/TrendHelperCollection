import json
import logging
import sys
import time
from typing import Dict, Any, Optional

class JsonFormatter(logging.Formatter):
    """JSON line formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON line"""
        base = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Add optional fields if present
        for field in ("trace_id", "user_id", "bucket_id", "latency_ms"):
            if hasattr(record, field):
                base[field] = getattr(record, field)

        # Add exception info if present
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)

        return json.dumps(base, ensure_ascii=False)

def setup_json_logging(level: int = logging.INFO) -> None:
    """Setup JSON line logging for the application"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    logging.info("JSON logging initialized", extra={"trace_id": "system_init"})