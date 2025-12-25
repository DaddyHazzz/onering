"""Optional OpenTelemetry tracing (Phase 7)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Dict, Optional

from backend.core.config import settings

try:  # Optional dependency
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter,
        InMemorySpanExporter,
        SimpleSpanProcessor,
    )
except Exception:  # pragma: no cover - if otel not installed, tracing is disabled
    trace = None
    TracerProvider = None
    ConsoleSpanExporter = None
    InMemorySpanExporter = None
    SimpleSpanProcessor = None


_tracer = None
_enabled = False
_exporter = None


def setup_tracing(enabled: Optional[bool] = None, exporter_name: Optional[str] = None) -> None:
    global _tracer, _enabled, _exporter
    if trace is None:
        _enabled = False
        return

    flag = settings.OTEL_ENABLED if enabled is None else bool(enabled)
    _enabled = flag
    if not flag:
        return

    provider = TracerProvider(resource=Resource.create({"service.name": "onering"}))
    exporter_choice = exporter_name or os.getenv("OTEL_EXPORTER", settings.OTEL_EXPORTER)
    if exporter_choice == "memory" and InMemorySpanExporter:
        _exporter = InMemorySpanExporter()
    else:
        _exporter = ConsoleSpanExporter()

    processor = SimpleSpanProcessor(_exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("onering")


@contextmanager
def start_span(name: str, attributes: Optional[Dict[str, object]] = None):
    if not _enabled or _tracer is None:
        yield None
        return
    span = _tracer.start_span(name)
    if attributes:
        for k, v in attributes.items():
            span.set_attribute(k, v)
    with trace.use_span(span, end_on_exit=True):
        yield span


def get_exported_spans():
    if _exporter and hasattr(_exporter, "get_finished_spans"):
        return _exporter.get_finished_spans()
    return []


def reset_exported_spans():
    if _exporter and hasattr(_exporter, "clear"):
        _exporter.clear()
