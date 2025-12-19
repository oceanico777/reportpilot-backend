import logging
import json
from datetime import datetime

class StructuredLogger(logging.Logger):
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        if extra is None:
            extra = {}
            
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": logging.getLevelName(level),
            "message": msg,
            "service": "reportpilot-backend",
            **extra
        }
        
        # Serialize to JSON if possible
        try:
             json_msg = json.dumps(log_data)
        except Exception:
             json_msg = str(log_data)
             
        super()._log(level, json_msg, args, exc_info, extra=None, stack_info=stack_info, stacklevel=stacklevel)

# Setup function
def setup_logging():
    logging.setLoggerClass(StructuredLogger)
    logger = logging.getLogger("app")
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
