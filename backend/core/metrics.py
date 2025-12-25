"""Lightweight in-memory metrics (Prometheus text format)."""

from __future__ import annotations

import re
import threading
from typing import Dict, Iterable, List, Optional, Tuple


def _sanitize_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\"", "\\\"")


def _format_labels(label_names: List[str], values: Tuple[str, ...]) -> str:
    if not label_names:
        return ""
    parts = [f'{name}="{_sanitize_label_value(val)}"' for name, val in zip(label_names, values)]
    return "{" + ",".join(parts) + "}"


class Counter:
    def __init__(self, name: str, label_names: Optional[Iterable[str]] = None):
        self.name = name
        self.label_names = list(label_names or [])
        self._values: Dict[Tuple[str, ...], float] = {}
        self._lock = threading.Lock()

    def inc(self, labels: Optional[Dict[str, str]] = None, amount: float = 1.0):
        key = self._label_tuple(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + float(amount)

    def _label_tuple(self, labels: Optional[Dict[str, str]]) -> Tuple[str, ...]:
        labels = labels or {}
        return tuple(str(labels.get(name, "")) for name in self.label_names)

    def export(self) -> List[str]:
        lines = [f"# TYPE {self.name} counter"]
        with self._lock:
            for label_values, value in self._values.items():
                labels = _format_labels(self.label_names, label_values)
                lines.append(f"{self.name}{labels} {value}")
        return lines

    def reset(self):
        with self._lock:
            self._values.clear()


class Gauge:
    def __init__(self, name: str, label_names: Optional[Iterable[str]] = None):
        self.name = name
        self.label_names = list(label_names or [])
        self._values: Dict[Tuple[str, ...], float] = {}
        self._lock = threading.Lock()

    def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        key = self._label_tuple(labels)
        with self._lock:
            self._values[key] = float(value)

    def inc(self, labels: Optional[Dict[str, str]] = None, amount: float = 1.0):
        key = self._label_tuple(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + float(amount)

    def dec(self, labels: Optional[Dict[str, str]] = None, amount: float = 1.0):
        key = self._label_tuple(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) - float(amount)

    def _label_tuple(self, labels: Optional[Dict[str, str]]) -> Tuple[str, ...]:
        labels = labels or {}
        return tuple(str(labels.get(name, "")) for name in self.label_names)

    def export(self) -> List[str]:
        lines = [f"# TYPE {self.name} gauge"]
        with self._lock:
            for label_values, value in self._values.items():
                labels = _format_labels(self.label_names, label_values)
                lines.append(f"{self.name}{labels} {value}")
        return lines

    def reset(self):
        with self._lock:
            self._values.clear()


class MetricsRegistry:
    def __init__(self):
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, label_names: Optional[Iterable[str]] = None) -> Counter:
        with self._lock:
            if name not in self.counters:
                self.counters[name] = Counter(name, label_names)
            return self.counters[name]

    def gauge(self, name: str, label_names: Optional[Iterable[str]] = None) -> Gauge:
        with self._lock:
            if name not in self.gauges:
                self.gauges[name] = Gauge(name, label_names)
            return self.gauges[name]

    def export_prometheus(self) -> str:
        lines: List[str] = []
        for metric in list(self.counters.values()) + list(self.gauges.values()):
            lines.extend(metric.export())
        return "\n".join(lines) + "\n"

    def reset(self):
        for metric in self.counters.values():
            metric.reset()
        for metric in self.gauges.values():
            metric.reset()


METRICS = MetricsRegistry()

http_requests_total = METRICS.counter("http_requests_total", ["method", "path", "status"])
ws_connections_total = METRICS.counter("ws_connections_total")
ws_messages_sent_total = METRICS.counter("ws_messages_sent_total", ["event_type"])
collab_mutations_total = METRICS.counter("collab_mutations_total", ["type"])
ratelimit_block_total = METRICS.counter("ratelimit_block_total", ["scope"])

ws_active_connections = METRICS.gauge("ws_active_connections")
drafts_active_rooms = METRICS.gauge("drafts_active_rooms")


_UUID_RE = re.compile(r"^[0-9a-fA-F-]{8,}$")


def normalize_path(path: str) -> str:
    """Reduce cardinality by replacing UUID/number segments with :id."""
    parts = []
    for segment in path.split("/"):
        if not segment:
            continue
        if segment.isdigit() or _UUID_RE.match(segment):
            parts.append(":id")
        else:
            parts.append(segment)
    return "/" + "/".join(parts)
