import logging
import os
from typing import Any, List

import structlog
from dotenv import load_dotenv


def configure_logging(
    level: str | int = "INFO", log_to_file: bool = False, path: str = "logs/app.log"
):
    """
    Centralized structlog configuration. Import and call this early in each process.
    Use LOG_FORMAT=json for production, or leave default for console-friendly output.

    Example:
        ### in main.py
        from shared.logging_config import configure_logging, get_logger
        configure_logging(level="DEBUG", log_to_file=True, path="logs/backend.log")
        log = get_logger(__name__)
        log.info("App started")
    """
    load_dotenv()

    log_level = (
        level
        if isinstance(level, int)
        else getattr(logging, str(level).upper(), logging.INFO)
    )

    processors: List[Any] = [
        structlog.processors.add_log_level,  # include log level
        structlog.processors.TimeStamper(fmt="iso"),  # timestamp
        structlog.processors.StackInfoRenderer(),
        structlog.contextvars.merge_contextvars,  # merge any bound contextvars into the event dict
        structlog.processors.CallsiteParameterAdder(
        parameters=[
            structlog.processors.CallsiteParameter.PATHNAME,
            structlog.processors.CallsiteParameter.LINENO,
            structlog.processors.CallsiteParameter.FUNC_NAME,
        ]
    ),
    ]

    # Pretty human output in dev
    if os.getenv("LOG_FORMAT", "console") == "console":
        processors += [
            structlog.dev.set_exc_info,  # show exception info nicely (dev)
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        # JSON for production ingestion into ELK/Prometheus/observability pipelines
        processors += [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    handlers: List[logging.Handler] = [logging.StreamHandler()]  # always log to console

    if log_to_file:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))

    # configure stdlib handler so messages from libraries are also captured
    logging.basicConfig(level=log_level, format="%(message)s", handlers=handlers)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),  # Use standard logger factory
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None):
    return structlog.get_logger(name)


"""
Example usage:

from shared.logging_config import configure_logging, get_logger

# Call this once at process startup
configure_logging(level="DEBUG")

logger = get_logger(__name__)

def main():
    logger.info("App starting", service="api")
    try:
        raise ValueError("oops")
    except Exception:
        logger.exception("Something went wrong")

if __name__ == "__main__":
    main()

# In development (console mode), this will print colorized, human-friendly logs.
# In production (LOG_FORMAT=json), the same logs will be JSON, ready for ingestion by ELK/Datadog/etc.
"""
