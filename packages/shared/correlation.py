import contextlib
import contextvars
import uuid

import structlog

# A ContextVar we control (more explicit than reading structlog internals)
CORRELATION_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar("correlation_id", default=None)

def get_correlation_id() -> str | None:
    return CORRELATION_ID.get()

def set_correlation_id(value: str) -> None:
    CORRELATION_ID.set(value)
    # Also bind to structlog contextvars for structured logs
    structlog.contextvars.bind_contextvars(correlation_id=value)

def clear_correlation_id() -> None:
    try:
        # Clear our ContextVar
        CORRELATION_ID.set(None)
    finally:
        # Clear structlog contextvars to avoid leakage
        structlog.contextvars.clear_contextvars()

@contextlib.contextmanager
def correlation_id_context(correlation_id: str | None = None):
    """
    Context manager to set a correlation id for non-HTTP contexts (background jobs, bot events).
    If correlation_id is not provided one is generated.
    """
    cid = correlation_id or str(uuid.uuid4())
    set_correlation_id(cid)
    try:
        yield cid
    finally:
        clear_correlation_id()
