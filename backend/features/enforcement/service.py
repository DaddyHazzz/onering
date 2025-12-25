"""Phase 10.1 enforcement pipeline (governance-first)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import ValidationError

from backend.core.config import settings
from backend.features.enforcement import policy
from backend.features.enforcement.audit import write_agent_decisions
from backend.features.enforcement.contracts import (
    AgentContractMeta,
    DraftContent,
    EvidenceBundle,
    EnforcementReceipt,
    FormatMetadata,
    PostingDecision,
    QADecision,
    StrategyPlan,
    CONTRACT_VERSION,
    QA_AGENT_NAME,
    stable_hash,
)


@dataclass
class EnforcementRequest:
    prompt: str
    platform: str
    user_id: str
    request_id: Optional[str] = None
    ring_id: Optional[str] = None
    draft_id: Optional[str] = None
    turn_id: Optional[str] = None
    content: Optional[str] = None
    publish_intent: bool = False


@dataclass
class EnforcementDecisionSummary:
    agent_name: str
    status: str
    violation_codes: List[str]
    required_edits: List[str]
    decision_id: str


@dataclass
class EnforcementResult:
    request_id: Optional[str]
    mode: str
    decisions: List[EnforcementDecisionSummary]
    qa_summary: Dict[str, object]
    receipt: Optional[EnforcementReceipt]
    would_block: bool
    required_edits: List[str]
    audit_ok: bool
    warnings: List[str]


def get_enforcement_mode() -> str:
    mode = getattr(settings, "ONERING_ENFORCEMENT_MODE", "off") or "off"
    return mode if mode in {"off", "advisory", "enforced"} else "off"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _agent_meta(
    *,
    agent_name: str,
    agent_version: str,
    model_name: str,
    model_version: str,
    prompt: str,
    input_payload: Dict[str, object],
    output_payload: Dict[str, object],
    request: EnforcementRequest,
    started_at: datetime,
    finished_at: datetime,
    retry_count: int = 0,
) -> AgentContractMeta:
    prompt_hash = stable_hash(prompt)
    input_hash = stable_hash(input_payload)
    output_hash = stable_hash(output_payload)
    latency_ms = int((finished_at - started_at).total_seconds() * 1000)
    return AgentContractMeta(
        request_id=request.request_id,
        ring_id=request.ring_id,
        draft_id=request.draft_id,
        turn_id=request.turn_id,
        user_id=request.user_id,
        agent_name=agent_name,
        agent_version=agent_version,
        model_name=model_name,
        model_version=model_version,
        prompt_hash=prompt_hash,
        input_hash=input_hash,
        output_hash=output_hash,
        policy_version=policy.POLICY_VERSION,
        started_at=started_at,
        finished_at=finished_at,
        latency_ms=latency_ms,
        retry_count=retry_count,
    )


def _strategy_agent(request: EnforcementRequest) -> StrategyPlan:
    angle = request.prompt.strip().split("\n")[0][:120]
    constraints = ["no-numbering", f"platform:{request.platform.lower()}"]
    required_citations = False
    return StrategyPlan(
        angle=angle or "default-angle",
        constraints=constraints,
        required_citations=required_citations,
        confidence=0.7,
    )


def _research_agent(request: EnforcementRequest) -> EvidenceBundle:
    return EvidenceBundle(
        sources=[],
        summary="",
        quality_score=0.0,
    )


def _writer_agent(request: EnforcementRequest, strategy: StrategyPlan, evidence: EvidenceBundle) -> DraftContent:
    content = (request.content or request.prompt or "").strip()
    max_chars = policy.platform_max_chars(request.platform)
    metadata = FormatMetadata(format="text", max_chars=max_chars, line_breaks="double")
    policy_tags = ["no_harm", "no_misinfo", "no_numbering"]
    return DraftContent(content=content, format=metadata, policy_tags=policy_tags)


def _posting_agent(request: EnforcementRequest, draft: DraftContent) -> PostingDecision:
    preview = draft.content[:200]
    checks = []
    if not draft.content.strip():
        checks.append("EMPTY_CONTENT")
    if draft.format.max_chars != policy.platform_max_chars(request.platform):
        checks.append("FORMAT_MISMATCH")
    rate_limit_snapshot = {"remaining": None, "retry_after": None}
    return PostingDecision(
        payload_preview=preview,
        platform_checks=checks,
        rate_limit_snapshot=rate_limit_snapshot,
    )


def _decision_record(meta: AgentContractMeta, output: object, status: str) -> Dict[str, object]:
    meta_json = meta.model_dump(mode="json")
    return {
        "request_id": meta.request_id,
        "draft_id": meta.draft_id,
        "ring_id": meta.ring_id,
        "turn_id": meta.turn_id,
        "user_id": meta.user_id,
        "agent_name": meta.agent_name,
        "agent_version": meta.agent_version,
        "contract_version": CONTRACT_VERSION,
        "policy_version": meta.policy_version,
        "input_hash": meta.input_hash,
        "output_hash": meta.output_hash,
        "prompt_hash": meta.prompt_hash,
        "decision_json": {"meta": meta_json, "output": output},
        "status": status,
        "created_at": meta.finished_at,
    }


def run_enforcement_pipeline(request: EnforcementRequest) -> EnforcementResult:
    mode = get_enforcement_mode()
    if mode == "off":
        return EnforcementResult(
            request_id=request.request_id,
            mode=mode,
            decisions=[],
            qa_summary={},
            receipt=None,
            would_block=False,
            required_edits=[],
            audit_ok=True,
            warnings=[],
        )

    decisions: List[EnforcementDecisionSummary] = []
    audit_records: List[Dict[str, object]] = []
    warnings: List[str] = []
    contract_failures: List[str] = []

    # Strategy
    started = _now()
    try:
        strategy = _strategy_agent(request)
        strategy = StrategyPlan.model_validate(strategy)
        status = "PASS"
    except ValidationError as exc:
        strategy = StrategyPlan(
            angle="invalid",
            constraints=["contract_invalid"],
            required_citations=False,
            confidence=0.0,
        )
        warnings.append(f"strategy_contract_invalid:{exc}")
        contract_failures.append("STRATEGY_CONTRACT_INVALID")
        status = "FAIL"
    finished = _now()
    strategy_meta = _agent_meta(
        agent_name="Strategy",
        agent_version="v1",
        model_name="deterministic",
        model_version="10.1",
        prompt=request.prompt,
        input_payload={"prompt": request.prompt, "platform": request.platform},
        output_payload=strategy.model_dump(mode="json"),
        request=request,
        started_at=started,
        finished_at=finished,
    )
    audit_records.append(_decision_record(strategy_meta, strategy.model_dump(mode="json"), status))
    decisions.append(
        EnforcementDecisionSummary(
            agent_name="Strategy",
            status=status,
            violation_codes=[],
            required_edits=[],
            decision_id=strategy_meta.output_hash,
        )
    )

    # Research (optional)
    evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
    if policy.requires_research(strategy.required_citations):
        started = _now()
        try:
            evidence = _research_agent(request)
            evidence = EvidenceBundle.model_validate(evidence)
            status = "PASS"
        except ValidationError as exc:
            evidence = EvidenceBundle(sources=[], summary="", quality_score=0.0)
            warnings.append(f"research_contract_invalid:{exc}")
            contract_failures.append("RESEARCH_CONTRACT_INVALID")
            status = "FAIL"
        finished = _now()
        research_meta = _agent_meta(
            agent_name="Research",
            agent_version="v1",
            model_name="deterministic",
            model_version="10.1",
            prompt=request.prompt,
            input_payload={"required_citations": strategy.required_citations},
            output_payload=evidence.model_dump(mode="json"),
            request=request,
            started_at=started,
            finished_at=finished,
        )
        audit_records.append(_decision_record(research_meta, evidence.model_dump(mode="json"), status))
        decisions.append(
            EnforcementDecisionSummary(
                agent_name="Research",
                status=status,
                violation_codes=[],
                required_edits=[],
                decision_id=research_meta.output_hash,
            )
        )

    # Writer (uses existing content when provided)
    started = _now()
    try:
        draft = _writer_agent(request, strategy, evidence)
        draft = DraftContent.model_validate(draft)
        status = "PASS"
    except ValidationError as exc:
        draft = DraftContent(
            content=request.content or "",
            format=FormatMetadata(format="text", max_chars=policy.platform_max_chars(request.platform), line_breaks="double"),
            policy_tags=["contract_invalid"],
        )
        warnings.append(f"writer_contract_invalid:{exc}")
        contract_failures.append("WRITER_CONTRACT_INVALID")
        status = "FAIL"
    finished = _now()
    writer_meta = _agent_meta(
        agent_name="Writer",
        agent_version="v1",
        model_name="deterministic",
        model_version="10.1",
        prompt=request.prompt,
        input_payload={"strategy": strategy.model_dump(mode="json"), "evidence": evidence.model_dump(mode="json")},
        output_payload=draft.model_dump(mode="json"),
        request=request,
        started_at=started,
        finished_at=finished,
    )
    audit_records.append(_decision_record(writer_meta, draft.model_dump(mode="json"), status))
    decisions.append(
        EnforcementDecisionSummary(
            agent_name="Writer",
            status=status,
            violation_codes=[],
            required_edits=[],
            decision_id=writer_meta.output_hash,
        )
    )

    # QA Gatekeeper
    started = _now()
    qa = policy.build_qa_decision(
        draft=draft,
        evidence=evidence,
        required_citations=strategy.required_citations,
        platform=request.platform,
    )
    if contract_failures:
        qa = QADecision(
            status="FAIL",
            violation_codes=sorted(set(qa.violation_codes + contract_failures)),
            required_edits=qa.required_edits or ["Resolve contract validation failures."],
            risk_score=max(qa.risk_score, 0.9),
        )
    finished = _now()
    qa_decision_hash = stable_hash(qa.model_dump(mode="json"))
    ttl_seconds = int(getattr(settings, "ONERING_ENFORCEMENT_RECEIPT_TTL_SECONDS", 3600) or 3600)
    receipt = EnforcementReceipt(
        receipt_id=str(uuid4()),
        request_id=request.request_id,
        draft_id=request.draft_id,
        ring_id=request.ring_id,
        turn_id=request.turn_id,
        qa_status=qa.status,
        qa_decision_hash=qa_decision_hash,
        policy_version=policy.POLICY_VERSION,
        created_at=finished,
        expires_at=finished + timedelta(seconds=ttl_seconds),
    )

    qa_meta = _agent_meta(
        agent_name=QA_AGENT_NAME,
        agent_version="v1",
        model_name="deterministic",
        model_version="10.1",
        prompt=request.prompt,
        input_payload={"draft": draft.model_dump(mode="json"), "evidence": evidence.model_dump(mode="json")},
        output_payload={
            "qa": qa.model_dump(mode="json"),
            "receipt": receipt.model_dump(mode="json"),
            "mode": mode,
        },
        request=request,
        started_at=started,
        finished_at=finished,
    )
    audit_records.append(
        _decision_record(
            qa_meta,
            {
                "qa": qa.model_dump(mode="json"),
                "receipt": receipt.model_dump(mode="json"),
                "mode": mode,
            },
            "PASS" if qa.status == "PASS" else "FAIL",
        )
    )
    decisions.append(
        EnforcementDecisionSummary(
            agent_name=QA_AGENT_NAME,
            status=qa.status,
            violation_codes=qa.violation_codes,
            required_edits=qa.required_edits,
            decision_id=qa_meta.output_hash,
        )
    )

    # Posting (publish intent only)
    if request.publish_intent:
        started = _now()
        posting = _posting_agent(request, draft)
        finished = _now()
        posting_meta = _agent_meta(
            agent_name="Posting",
            agent_version="v1",
            model_name="deterministic",
            model_version="10.1",
            prompt=request.prompt,
            input_payload={"draft": draft.model_dump(mode="json")},
            output_payload=posting.model_dump(mode="json"),
            request=request,
            started_at=started,
            finished_at=finished,
        )
        audit_records.append(_decision_record(posting_meta, posting.model_dump(mode="json"), "PASS"))
        decisions.append(
            EnforcementDecisionSummary(
                agent_name="Posting",
                status="PASS",
                violation_codes=posting.platform_checks,
                required_edits=[],
                decision_id=posting_meta.output_hash,
            )
        )

    # Analytics shadow hook (Phase 10.2 placeholder)
    token_mode = getattr(settings, "ONERING_TOKEN_ISSUANCE", "off") or "off"
    started = _now()
    finished = _now()
    analytics_meta = _agent_meta(
        agent_name="Analytics",
        agent_version="v1",
        model_name="deterministic",
        model_version="10.1",
        prompt=request.prompt,
        input_payload={"token_mode": token_mode},
        output_payload={"token_mode": token_mode},
        request=request,
        started_at=started,
        finished_at=finished,
    )
    audit_records.append(_decision_record(analytics_meta, {"token_mode": token_mode}, "PASS"))
    decisions.append(
        EnforcementDecisionSummary(
            agent_name="Analytics",
            status="PASS",
            violation_codes=[],
            required_edits=[],
            decision_id=analytics_meta.output_hash,
        )
    )

    audit_ok = write_agent_decisions(audit_records, mode=mode)
    if not audit_ok:
        warnings.append("audit_write_failed")
    would_block = qa.status == "FAIL" or (request.publish_intent and not audit_ok)
    if mode == "advisory":
        would_block = qa.status == "FAIL"

    qa_summary = {
        "status": qa.status,
        "violation_codes": qa.violation_codes,
        "required_edits": qa.required_edits,
        "risk_score": qa.risk_score,
    }

    required_edits = qa.required_edits
    return EnforcementResult(
        request_id=request.request_id,
        mode=mode,
        decisions=decisions,
        qa_summary=qa_summary,
        receipt=receipt,
        would_block=would_block,
        required_edits=required_edits,
        audit_ok=audit_ok,
        warnings=warnings,
    )
