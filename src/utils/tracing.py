"""分布式追踪 —— contextvars 协程安全"""

import uuid
import time
from contextvars import ContextVar
from contextlib import contextmanager
from src.utils.logging_config import logger

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_span_id: ContextVar[str] = ContextVar("span_id", default="")
_component: ContextVar[str] = ContextVar("component", default="system")


def new_trace() -> str:
    tid = str(uuid.uuid4())[:8]
    _trace_id.set(tid)
    return tid


def set_trace(trace_id: str):
    _trace_id.set(trace_id)


def get_trace_id() -> str:
    return _trace_id.get() or "--------"


@contextmanager
def span(component: str, operation: str):
    """追踪 span"""
    sid = str(uuid.uuid4())[:8]
    prev_span = _span_id.get()
    prev_comp = _component.get()
    _span_id.set(sid)
    _component.set(component)

    logger.bind(
        trace_id=_trace_id.get(),
        span_id=sid,
        component=component,
    ).debug(f"[{operation}] start")

    start = time.monotonic()
    try:
        yield
    except Exception as e:
        logger.bind(
            trace_id=_trace_id.get(),
            span_id=sid,
            component=component,
        ).error(f"[{operation}] error: {e}")
        raise
    finally:
        elapsed = time.monotonic() - start
        logger.bind(
            trace_id=_trace_id.get(),
            span_id=sid,
            component=component,
        ).debug(f"[{operation}] done ({elapsed:.2f}s)")
        _span_id.set(prev_span)
        _component.set(prev_comp)
