"""Accountability, provenance hashing, and JSONL audit logging for OONCA."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid


def _canonical_json(payload: dict[str, Any]) -> str:
    """Serialize payload deterministically for SHA-256 provenance hashing."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def build_audit_record(
    state: dict[str, Any],
    *,
    model_version: str | None = None,
) -> dict[str, Any]:
    """Build a structured accountability & audit trail record from agent state."""
    operation = state.get("operation", {}) or {}
    profile = state.get("profile", {}) or {}
    assessment = state.get("assessment", {}) or {}
    llm_status = state.get("llm_status", "unknown")

    evidence_payload = {
        "operation": operation,
        "profile": profile,
        "assessment": assessment,
    }
    canonical = _canonical_json(evidence_payload)
    evidence_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    policy_info = assessment.get("policy", {}) or {}
    policy_id = policy_info.get("policy_id") or operation.get("policy_id") or "default_triage_v2"
    operator_id = operation.get("operator_id")
    agent_id = operation.get("agent_id") or "oonca_v1"
    resolved_model = model_version or ("none (deterministic_only)" if llm_status in ("disabled", "missing_key") else "openrouter_llm")

    sender_meta = profile.get("wallet_metadata")
    recipient_meta = profile.get("recipient_metadata")

    accountability_fields = {
        "wallet_from": bool(operation.get("wallet_from")),
        "wallet_to": bool(operation.get("wallet_to")),
        "operator_id": bool(operator_id),
        "agent_id": bool(agent_id),
        "policy_id": bool(policy_id),
        "model_version": bool(resolved_model and resolved_model != "none (deterministic_only)"),
        "temporal_cutoff_as_of": bool(operation.get("as_of")),
        "sender_metadata_available": bool(sender_meta),
        "recipient_metadata_available": bool(recipient_meta),
    }
    present_count = sum(1 for v in accountability_fields.values() if v)
    total_fields = len(accountability_fields)
    completeness_score = round(present_count / total_fields, 4) if total_fields else 0.0

    rule_breakdown = assessment.get("rule_breakdown", []) or []
    triggered_rules = [r["rule_id"] for r in rule_breakdown if r.get("triggered")]

    decision = assessment.get("decision", "REVIEW")
    human_review_required = decision in ("REVIEW", "BLOCK")

    return {
        "audit_id": str(uuid.uuid4()),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_sha256": evidence_sha256,
        "decision": decision,
        "risk_score": assessment.get("risk_score", 0),
        "score_kind": assessment.get("score_kind", "heuristic_not_probability"),
        "human_review_required": human_review_required,
        "operator_id": operator_id,
        "agent_id": agent_id,
        "policy_id": policy_id,
        "model_version": resolved_model,
        "llm_status": llm_status,
        "triggered_rules": triggered_rules,
        "missing_data_flags": assessment.get("missing_data_flags", []),
        "accountability_completeness": {
            "score": completeness_score,
            "present_count": present_count,
            "total_fields": total_fields,
            "fields": accountability_fields,
        },
    }


def append_audit_log(record: dict[str, Any], log_path: str | Path) -> Path:
    """Append an audit record as a single JSON line to `log_path`."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, default=str)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return path
