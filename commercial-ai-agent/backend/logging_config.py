"""
Structured logging configuration for the Commercial AI Agent.
Provides JSON logging with correlation IDs and context tracking.
"""
import logging
import json
import uuid
import sys
from typing import Any, Dict, Optional
from datetime import datetime
try:
    from pythonjsonlogger import jsonlogger
    _HAS_PJLOG = True
except Exception:
    # Fallback minimal json logger for environments where python-json-logger is not installed
    _HAS_PJLOG = False
    class jsonlogger:
        class JsonFormatter(logging.Formatter):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
            def format(self, record):
                # Basic JSON-ish formatting
                import json
                rv = {
                    "timestamp": getattr(record, 'created', None),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if hasattr(record, 'correlation_id'):
                    rv['correlation_id'] = record.correlation_id
                if record.exc_info:
                    rv['exception'] = self.formatException(record.exc_info)
                return json.dumps(rv)


class CorrelationIDFilter(logging.Filter):
    """Add correlation ID to all log records."""
    
    _correlation_id = None
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to record."""
        record.correlation_id = self.get_correlation_id()
        return True
    
    @classmethod
    def set_correlation_id(cls, correlation_id: str) -> None:
        """Set the correlation ID for this thread/request."""
        cls._correlation_id = correlation_id
    
    @classmethod
    def get_correlation_id(cls) -> str:
        """Get current correlation ID, generate if missing."""
        if not cls._correlation_id:
            cls._correlation_id = str(uuid.uuid4())
        return cls._correlation_id
    
    @classmethod
    def clear_correlation_id(cls) -> None:
        """Clear correlation ID."""
        cls._correlation_id = None


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to JSON log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["correlation_id"] = getattr(record, "correlation_id", "")
        
        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_record.update(record.extra_fields)


def setup_logging(app_env: str = "development", log_file: Optional[str] = None) -> None:
    """
    Configure structured JSON logging for the application.
    
    Args:
        app_env: Environment (development/production)
        log_file: Optional log file path
    """
    # Create correlation ID filter
    correlation_filter = CorrelationIDFilter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if app_env == "development" else logging.INFO)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # JSON formatter
    json_formatter = CustomJsonFormatter(
        fmt='%(timestamp)s %(level)s %(logger)s %(message)s %(correlation_id)s',
        rename_fields={"message": "msg"}
    )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    console_handler.addFilter(correlation_filter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(json_formatter)
        file_handler.addFilter(correlation_filter)
        root_logger.addHandler(file_handler)
    
    # Suppress verbose library logs
    for noisy_logger in ("urllib3", "requests", "openai", "httpx", "httpcore", "httpx2", "httpcore2", "asyncio"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    logging.getLogger("flask").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_with_context(
    logger_instance: logging.Logger,
    level: int,
    message: str,
    **context
) -> None:
    """
    Log message with additional context fields.
    
    Args:
        logger_instance: Logger to use
        level: Log level
        message: Log message
        **context: Additional context fields to include
    """
    # Create log record
    extra = {"extra_fields": context} if context else {}
    logger_instance.log(level, message, extra=extra)


# Convenience functions
def log_execution(execution_id: str, step_id: int, message: str, logger_instance: logging.Logger = None) -> None:
    """Log execution event with context."""
    logger = logger_instance or get_logger(__name__)
    log_with_context(
        logger,
        logging.INFO,
        message,
        execution_id=execution_id,
        step_id=step_id
    )


def log_tool_invocation(tool_name: str, arguments: Dict[str, Any], logger_instance: logging.Logger = None) -> None:
    """Log tool invocation."""
    logger = logger_instance or get_logger(__name__)
    log_with_context(
        logger,
        logging.DEBUG,
        f"Invoking tool: {tool_name}",
        tool=tool_name,
        arguments=json.dumps(arguments, default=str)
    )


def log_performance(operation: str, duration_ms: float, logger_instance: logging.Logger = None) -> None:
    """Log performance metric."""
    logger = logger_instance or get_logger(__name__)
    log_with_context(
        logger,
        logging.INFO,
        f"Performance: {operation}",
        operation=operation,
        duration_ms=duration_ms
    )
