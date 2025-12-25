"""Agent contract schemas and hashing utilities for Phase 10.1."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Literal

from pydantic import BaseModel, Field, ConfigDict

CONTRACT_VERSION = "10.1"
QA_AGENT_NAME = "qa_gatekeeper"


def stable_hash(value: object) -> str:
    if isinstance(value, str):
        raw = value
    else:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AgentContractMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: Optional[str] = None
    ring_id: Optional[str] = None
    draft_id: Optional[str] = None
    turn_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_name: str
    agent_version: str
    model_name: str
    model_version: str
    prompt_hash: str
    input_hash: str
    output_hash: str
    policy_version: str
    started_at: datetime
    finished_at: datetime
    latency_ms: int
    retry_count: int = 0


class StrategyPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    angle: str
    constraints: List[str]
    required_citations: bool
    confidence: float = Field(ge=0.0, le=1.0)


class EvidenceSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    title: str
    timestamp: datetime
    relevance_score: float = Field(ge=0.0, le=1.0)


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: List[EvidenceSource]
    summary: str
    quality_score: float = Field(ge=0.0, le=1.0)


class FormatMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: str
    max_chars: int
    line_breaks: str


class DraftContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    format: FormatMetadata
    policy_tags: List[str]


class QADecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["PASS", "FAIL"]
    violation_codes: List[str]
    required_edits: List[str]
    risk_score: float = Field(ge=0.0, le=1.0)


class EnforcementReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: str
    request_id: Optional[str] = None
    draft_id: Optional[str] = None
    ring_id: Optional[str] = None
    turn_id: Optional[str] = None
    qa_status: Literal["PASS", "FAIL"]
    qa_decision_hash: str
    policy_version: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class PostingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload_preview: str
    platform_checks: List[str]
    rate_limit_snapshot: Dict[str, Optional[int]]
