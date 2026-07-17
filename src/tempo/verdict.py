"""Compile machine evidence around a strictly human-owned verdict section."""
from __future__ import annotations

from typing import Any

from .evidence import read_manifest
from .errors import CheckerFailure, PolicyBlock
from .ledger import Ledger
from .schema import validate_data
from .state import StateStore
from .util import Workspace, atomic_write_text, canonical_relpath, isoformat_z, load_json, sha256_file
from .verify import verify_receipt


HUMAN_VERDICT_START = b"<!-- HUMAN_VERDICT_START -->"
HUMAN_VERDICT_END = b"<!-- HUMAN_VERDICT_END -->"
_BLANK_HUMAN_SECTION = b"""<!-- HUMAN_VERDICT_START -->
## Human verdict and signature

Decision:

Signed by:

Signed at:
<!-- HUMAN_VERDICT_END -->"""


def _extract_human_section(raw: bytes, *, allow_empty: bool) -> bytes:
    starts = raw.count(HUMAN_VERDICT_START)
    ends = raw.count(HUMAN_VERDICT_END)
    if starts == 0 and ends == 0:
        if allow_empty and not raw.strip():
            return _BLANK_HUMAN_SECTION
        raise PolicyBlock(
            "HUMAN_VERDICT_MARKERS_MISSING",
            "Existing verdict memo has no protected human verdict markers",
            next_action="Add one marked human section before recompiling, or move the unmarked memo aside.",
        )
    if starts != 1 or ends != 1:
        raise PolicyBlock(
            "HUMAN_VERDICT_MARKERS_INVALID",
            "Verdict memo must contain exactly one HUMAN verdict marker pair",
            details={"start_markers": starts, "end_markers": ends},
        )
    start = raw.find(HUMAN_VERDICT_START)
    end_start = raw.find(HUMAN_VERDICT_END)
    if end_start < start:
        raise PolicyBlock("HUMAN_VERDICT_MARKERS_INVALID", "Human verdict markers are reversed")
    return raw[start : end_start + len(HUMAN_VERDICT_END)]


def _optional_json(workspace: Workspace, relative: str) -> dict[str, Any] | None:
    path = workspace.path(relative)
    if not path.is_file():
        return None
    value = load_json(path)
    if not isinstance(value, dict):
        raise CheckerFailure("VERDICT_INPUT_INVALID", f"Verdict input is not an object: {relative}")
    return value


def _receipt_paths(workspace: Workspace) -> list[str]:
    found: set[str] = set()
    for event in Ledger(workspace).events():
        if event.get("event_type") != "verification_completed":
            continue
        relative = event.get("details", {}).get("receipt_path")
        if isinstance(relative, str):
            found.add(canonical_relpath(relative))
    default_dir = workspace.path(".tempo/receipts")
    if default_dir.is_dir():
        for path in default_dir.glob("*.json"):
            found.add(workspace.relative(path))
    return sorted(found)


def _receipt_summaries(workspace: Workspace) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for relative in _receipt_paths(workspace):
        integrity = verify_receipt(workspace, relative)
        value = load_json(workspace.path(relative))
        summaries.append(
            {
                "receipt_id": value["receipt_id"],
                "receipt_type": value["receipt_type"],
                "outcome": value["outcome"],
                "authoritative": value["provenance"]["authoritative"],
                "receipt_hash": integrity["receipt_hash"],
                "path": relative,
            }
        )
    return summaries


def _machine_markdown(
    *,
    generated_at: str,
    assessment: dict[str, Any] | None,
    warrant: dict[str, Any] | None,
    state: dict[str, Any],
    ledger_status: dict[str, Any],
    evidence_refs: list[str],
    receipts: list[dict[str, Any]],
) -> str:
    assessment_id = assessment.get("assessment_id", "none") if assessment else "none"
    recommendation = assessment.get("primary_outcome", "not assessed") if assessment else "not assessed"
    weighted_score = assessment.get("weighted_score", "n/a") if assessment else "n/a"
    warrant_id = warrant.get("warrant_id", "none") if warrant else "none"
    warrant_state = warrant.get("state", "none") if warrant else "none"
    lines = [
        "# TEMPO verdict memo",
        "",
        "> Machine-compiled evidence only. This compiler does not make, sign, or infer the human verdict.",
        "",
        "## Decision context",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Assessment: `{assessment_id}`",
        f"- Machine readiness recommendation: `{recommendation}`",
        f"- Weighted readiness score: `{weighted_score}`",
        f"- Business state: `{state['business']['state']}`",
        f"- MVP state: `{state['mvp']['state']}`",
        f"- Recorded warrant: `{warrant_id}` (`{warrant_state}`)",
        "- Warrant note: recorded fields are summarized here; this compiler does not re-authorize work.",
        "",
        "## Evidence and integrity",
        "",
        f"- Evidence records: `{len(evidence_refs)}`",
        f"- Evidence refs: `{', '.join(evidence_refs) if evidence_refs else 'none'}`",
        f"- Ledger events: `{ledger_status['events']}`",
        f"- Ledger head: `{ledger_status['head_hash']}`",
        "",
        "## Verification receipts",
        "",
    ]
    if receipts:
        lines.extend(
            [
                "| Receipt | Type | Outcome | Authoritative |",
                "| --- | --- | --- | --- |",
            ]
        )
        for receipt in receipts:
            lines.append(
                f"| `{receipt['receipt_id']}` | `{receipt['receipt_type']}` | "
                f"`{receipt['outcome']}` | `{str(receipt['authoritative']).lower()}` |"
            )
    else:
        lines.append("No machine verification receipts were found.")
    lines.extend(
        [
            "",
            "Machine compilation is complete. The marked section below remains exclusively human-owned.",
        ]
    )
    return "\n".join(lines)


def compile_verdict(
    workspace: Workspace,
    *,
    session: str = "local:verdict",
    actor: str = "kernel:verdict-compiler",
    output_path: str = "plan/verdict-memo.md",
) -> dict[str, Any]:
    """Refresh machine sections while preserving marked human bytes exactly.

    If a non-empty existing memo lacks the marker pair, compilation fails closed
    rather than risking an overwrite of a human decision.
    """
    relative = canonical_relpath(output_path)
    destination = workspace.path(relative)
    existing = destination.read_bytes() if destination.is_file() else b""
    protected = _extract_human_section(existing, allow_empty=True)
    try:
        protected_text = protected.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CheckerFailure(
            "HUMAN_VERDICT_ENCODING_INVALID",
            "Protected human verdict section must be UTF-8",
        ) from exc

    assessment = _optional_json(workspace, ".tempo/assessments/latest.json")
    if assessment is not None:
        validate_data(workspace, "assessment", assessment)
    warrant = _optional_json(workspace, "plan/authorization-warrant.json")
    if warrant is not None:
        validate_data(workspace, "authorization-warrant", warrant)
    evidence_refs = [entry["evidence_id"] for entry in read_manifest(workspace)]
    receipts = _receipt_summaries(workspace)
    ledger_status = Ledger(workspace).verify()
    state = StateStore(workspace).read()
    generated_at = isoformat_z()
    machine = _machine_markdown(
        generated_at=generated_at,
        assessment=assessment,
        warrant=warrant,
        state=state,
        ledger_status=ledger_status,
        evidence_refs=evidence_refs,
        receipts=receipts,
    )
    content = f"{machine}\n\n{protected_text}\n"
    atomic_write_text(destination, content)

    after = destination.read_bytes()
    preserved_after = _extract_human_section(after, allow_empty=False)
    if preserved_after != protected:
        raise CheckerFailure(
            "HUMAN_VERDICT_PRESERVATION_FAILED",
            "Compiler failed its byte-for-byte human section invariant",
        )

    memo_hash = sha256_file(destination)
    relevant_ids: dict[str, str] = {}
    if assessment:
        relevant_ids["assessment_id"] = assessment["assessment_id"]
    if warrant:
        relevant_ids["warrant_id"] = warrant["warrant_id"]
    Ledger(workspace).append(
        "verdict_compiled",
        actor=actor,
        session=session,
        relevant_ids=relevant_ids,
        artifact_hashes={relative: memo_hash},
        evidence_refs=evidence_refs,
        reason_code="MACHINE_EVIDENCE_COMPILED",
        resulting_state="UNCHANGED",
        details={
            "memo_path": relative,
            "receipt_count": len(receipts),
            "human_section_preserved": True,
            "human_verdict_filled": False,
        },
    )
    return {
        "ok": True,
        "path": relative,
        "memo_hash": memo_hash,
        "assessment_ref": assessment.get("assessment_id") if assessment else None,
        "receipt_count": len(receipts),
        "human_section_preserved": True,
        "human_verdict_filled": False,
    }
