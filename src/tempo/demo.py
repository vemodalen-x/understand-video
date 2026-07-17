"""Credential-free, deterministic Work & Productivity judge scenario."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
from typing import Any, Callable
import uuid

from .charter import generate_charter, sign_charter
from .errors import CheckerFailure, TempoError
from .evidence import add_evidence
from .ledger import Ledger
from .providers import import_proposal
from .readiness import assess
from .state import StateStore
from .util import (
    Workspace,
    atomic_write_json,
    atomic_write_text,
    isoformat_z,
    load_json,
    sha256_file,
    utc_now,
)
from .warrant import authorize, initialize_demo_context, start, validate_warrant


DEMO_ACTOR = "agent:demo-runner"
DEMO_SIGNER = "platform:demo-fixture-signer"


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def prepare_demo_workspace(source: Workspace, *, session: str) -> Workspace:
    """Create a unique ignored workspace whose inputs are all labeled fixtures."""
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    destination = source.path(f".tempo/demo-workspaces/{stamp}-{uuid.uuid4().hex[:8]}")
    destination.mkdir(parents=True, exist_ok=False)
    _copy(source.path("MANIFEST.json"), destination / "MANIFEST.json")
    _copy(source.path("VERSION"), destination / "VERSION")
    shutil.copytree(source.path("schemas"), destination / "schemas")
    shutil.copytree(source.path("config"), destination / "config")
    sample = source.path("samples/business-mvp")
    mappings = {
        "opportunity.json": "plan/opportunity.json",
        "business-model.json": "plan/business-model.json",
        "hypotheses.json": "plan/hypotheses.json",
        "readiness-policy.json": "plan/readiness-policy.json",
        "decision-brief.initial.json": "plan/decision-brief.json",
        "charter-proposal.json": "plan/charter-proposal.json",
        "task.json": "tasks/T-DEMO-BUILD.json",
        "commercial-proposal.json": "inputs/commercial-proposal.json",
        "evidence-model.json": "inputs/evidence-model.json",
        "evidence-interview-a.json": "inputs/evidence-interview-a.json",
        "evidence-interview-b.json": "inputs/evidence-interview-b.json",
    }
    for source_name, target_name in mappings.items():
        _copy(sample / source_name, destination / target_name)
    workspace = Workspace.from_path(destination)
    initialize_demo_context(workspace, mvp_ref="M-DEMO-001", session=session)
    return workspace


def _expected_block(
    name: str,
    function: Callable[[], Any],
    expected: set[str],
) -> dict[str, Any]:
    try:
        function()
    except TempoError as exc:
        if exc.reason_code not in expected:
            raise CheckerFailure(
                "DEMO_UNEXPECTED_BLOCK",
                f"{name} blocked for {exc.reason_code}, expected one of {sorted(expected)}",
            ) from exc
        return {
            "check_id": f"CHK-{name.upper().replace('_', '-')}",
            "name": name,
            "status": "passed",
            "duration_ms": 0,
            "details": f"Expected policy block observed: {exc.reason_code}",
            "reason_code": exc.reason_code,
        }
    raise CheckerFailure("DEMO_EXPECTED_BLOCK_MISSING", f"{name} unexpectedly succeeded")


def _check(name: str, details: str, **evidence: Any) -> dict[str, Any]:
    return {
        "check_id": f"CHK-{name.upper().replace('_', '-')}",
        "name": name,
        "status": "passed",
        "duration_ms": 0,
        "details": details,
        **evidence,
    }


def _receipt_check(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "check_id": step["check_id"],
        "name": step["name"],
        "status": step["status"],
        "duration_ms": step["duration_ms"],
        "details": step["details"],
    }


def run_demo(source: Workspace, *, session: str = "local:judge-demo") -> dict[str, Any]:
    """Exercise block -> evidence -> candidate -> warrant -> drift in one command."""
    demo_session = f"demo:{uuid.uuid4().hex}"
    workspace = prepare_demo_workspace(source, session=demo_session)
    steps: list[dict[str, Any]] = []
    store = StateStore(workspace)
    store.initialize()
    store.transition("business", "DISCOVERY", "DEMO_STARTED")
    store.transition("business", "VALIDATING", "DEMO_PLANNING_INPUTS_LOADED")

    proposal = import_proposal(
        workspace,
        "json",
        workspace.path("inputs/commercial-proposal.json"),
        actor=DEMO_ACTOR,
        session=demo_session,
    )
    if proposal.get("authorization_created") is not False:
        raise CheckerFailure("DEMO_PROVIDER_AUTHORITY_LEAK", "Commercial proposal created authority")
    steps.append(
        _check(
            "provider_is_advisory",
            "Recorded GPT-5.6-shaped output was normalized as untrusted advice and created no authority.",
            proposal_id=proposal["proposal_id"],
        )
    )

    add_evidence(
        workspace,
        workspace.path("inputs/evidence-model.json"),
        actor=DEMO_ACTOR,
        session=demo_session,
    )
    generate_charter(workspace, actor=DEMO_ACTOR, session=demo_session)
    first, first_exit = assess(
        workspace,
        actor="kernel:readiness",
        session=demo_session,
        allow_fixtures=False,
    )
    if first_exit != 2 or first["primary_outcome"] != "EXPERIMENT_REQUIRED" or first["build_allowed"]:
        raise CheckerFailure("DEMO_FIRST_GATE_FAILED", "Model-only evidence did not fail closed")
    first_codes = {item["reason_code"] for item in first["hard_blockers"]}
    if not {"EXTERNAL_EVIDENCE_REQUIRED", "MODEL_ONLY_EVIDENCE"}.issubset(first_codes):
        raise CheckerFailure("DEMO_FIRST_GATE_INCOMPLETE", "Expected evidence blockers were not emitted")
    steps.append(
        _check(
            "model_only_blocks",
            "Model-only evidence returned EXPERIMENT_REQUIRED and build_allowed=false.",
            assessment_id=first["assessment_id"],
            blocker_codes=sorted(first_codes),
        )
    )

    store.new_business_cycle("DEMO_CHEAP_EXPERIMENT_COMPLETE")
    store.transition("business", "VALIDATING", "DEMO_FIXTURE_EVIDENCE_RECORDED")
    for name in ("evidence-interview-a.json", "evidence-interview-b.json"):
        add_evidence(
            workspace,
            workspace.path(f"inputs/{name}"),
            actor=DEMO_ACTOR,
            session=demo_session,
        )
    _copy(source.path("samples/business-mvp/decision-brief.ready.json"), workspace.path("plan/decision-brief.json"))
    generate_charter(workspace, actor=DEMO_ACTOR, session=demo_session)
    sign_charter(
        workspace,
        signer_ref=DEMO_SIGNER,
        session=demo_session,
        demo_fixture=True,
    )
    ready, ready_exit = assess(
        workspace,
        actor="kernel:readiness",
        session=demo_session,
        allow_fixtures=True,
    )
    if ready_exit != 0 or ready["primary_outcome"] != "MVP_AUTHORIZED":
        raise CheckerFailure(
            "DEMO_READINESS_DID_NOT_PASS",
            "The fully labeled fixture scenario did not reach authorization eligibility",
            details={"outcome": ready["primary_outcome"], "blockers": ready["hard_blockers"], "floors": ready["floor_failures"]},
        )
    if ready["authorization_valid"] or ready["build_allowed"]:
        raise CheckerFailure("DEMO_AUTHORITY_COLLAPSE", "Readiness incorrectly implied implementation authority")
    steps.append(
        _check(
            "readiness_is_not_authority",
            "Readiness passed, but authorization_valid and build_allowed remained false.",
            assessment_id=ready["assessment_id"],
            assessment_hash=ready["assessment_hash"],
            weighted_score=ready["weighted_score"],
            authorization_ceiling=ready["authorization_ceiling"],
            rank_one_threshold=ready["rank_one_threshold"],
        )
    )

    before_authorization = _expected_block(
        "start_without_warrant",
        lambda: start(
            workspace,
            task_id="T-DEMO-BUILD",
            path="src/tempo/bounded_change.py",
            lane="kernel",
            action="implementation_write",
            actor=DEMO_ACTOR,
            session=demo_session,
        ),
        {"WARRANT_MISSING"},
    )
    steps.append(before_authorization)

    warrant = authorize(
        workspace,
        assessment_hash=ready["assessment_hash"],
        signer_ref=DEMO_SIGNER,
        signer_session=demo_session,
        ttl_hours=1,
        demo_fixture=True,
    )
    if warrant["provenance_kind"] != "local_integrity_only" or not warrant["build_allowed"]:
        raise CheckerFailure("DEMO_WARRANT_INVALID", "Fixture warrant provenance was not explicit")
    steps.append(
        _check(
            "bounded_warrant_issued",
            "The isolated fixture signer issued a one-hour, local-integrity-only warrant.",
            warrant_id=warrant["warrant_id"],
            provenance_kind=warrant["provenance_kind"],
        )
    )

    started = start(
        workspace,
        task_id="T-DEMO-BUILD",
        path="src/tempo/bounded_change.py",
        lane="kernel",
        action="implementation_write",
        actor=DEMO_ACTOR,
        session=demo_session,
    )
    if not started["build_allowed"]:
        raise CheckerFailure("DEMO_IN_SCOPE_START_FAILED", "In-scope task was not allowed")
    steps.append(
        _check(
            "in_scope_start_allowed",
            "A traced task inside the declared path and lane was allowed.",
            path=started["path"],
            lane=started["lane"],
        )
    )

    steps.append(
        _expected_block(
            "out_of_scope_blocks",
            lambda: start(
                workspace,
                task_id="T-DEMO-BUILD",
                path="submission/publish.py",
                lane="kernel",
                action="implementation_write",
                actor=DEMO_ACTOR,
                session=demo_session,
            ),
            {"SCOPE_NOT_AUTHORIZED"},
        )
    )

    charter_path = workspace.path("plan/mvp-charter.json")
    original_charter = charter_path.read_text(encoding="utf-8")
    changed = load_json(charter_path)
    changed["technical_boundaries"] = [*changed["technical_boundaries"], "Unauthorized scope drift"]
    atomic_write_json(charter_path, changed)
    steps.append(
        _expected_block(
            "protected_drift_invalidates",
            lambda: validate_warrant(workspace, actor=DEMO_ACTOR, session=demo_session),
            {"PROTECTED_INPUT_DRIFT"},
        )
    )
    atomic_write_text(charter_path, original_charter)
    steps.append(
        _expected_block(
            "restoring_bytes_does_not_revive",
            lambda: validate_warrant(workspace, actor=DEMO_ACTOR, session=demo_session),
            {"WARRANT_INVALIDATED"},
        )
    )

    ledger = Ledger(workspace).verify()
    steps.append(
        _check(
            "ledger_chain_valid",
            f"Verified {ledger['events']} serialized hash-chained events and their durable head checkpoint.",
            head_hash=ledger["head_hash"],
        )
    )

    from .verdict import compile_verdict

    verdict = compile_verdict(workspace, actor=DEMO_ACTOR, session=demo_session)
    if verdict.get("human_verdict_filled"):
        raise CheckerFailure("DEMO_HUMAN_VERDICT_FILLED", "Compiler filled the human verdict section")
    steps.append(
        _check(
            "human_verdict_remains_blank",
            "The compiler assembled machine evidence while leaving the human verdict/signature section blank.",
            verdict_path=verdict.get("path"),
        )
    )

    report = {
        "ok": True,
        "outcome": "JUDGE_DEMO_PASSED",
        "generated_at": isoformat_z(),
        "workspace": str(workspace.root),
        "fixture_mode": True,
        "fixture_disclaimer": "Synthetic inputs prove workflow mechanics only; they are not external customer validation or platform attestation.",
        "assessment": {
            "initial_outcome": first["primary_outcome"],
            "eligible_outcome": ready["primary_outcome"],
            "assessment_id": ready["assessment_id"],
            "assessment_hash": ready["assessment_hash"],
            "authorization_ceiling": ready["authorization_ceiling"],
            "rank_one_threshold": ready["rank_one_threshold"],
        },
        "warrant": {
            "warrant_id": warrant["warrant_id"],
            "provenance_kind": warrant["provenance_kind"],
            "terminal_state": "invalidated",
        },
        "steps": steps,
        "ledger": ledger,
    }
    report_path = workspace.path(".tempo/demo-report.json")
    atomic_write_json(report_path, report)

    from .verify import write_receipt

    receipt = write_receipt(
        workspace,
        receipt_type="judge_demo",
        subject_ref="repository:TEMPO-demo",
        session=demo_session,
        command_argv=["python", "bin/tempo", "demo"],
        checks=[_receipt_check(step) for step in steps],
        exit_code=0,
        actor="verifier:tempo.demo",
        input_paths=[
            "plan/opportunity.json",
            "plan/business-model.json",
            "plan/hypotheses.json",
            "plan/readiness-policy.json",
            "plan/decision-brief.json",
            "plan/mvp-charter.json",
            "plan/evidence/manifest.jsonl",
            ".tempo/demo-report.json",
        ],
        artifacts=[
            {
                "path": ".tempo/demo-report.json",
                "hash": sha256_file(report_path),
                "media_type": "application/json",
                "size_bytes": report_path.stat().st_size,
            }
        ],
    )
    report["receipt_id"] = receipt["receipt_id"]
    report["receipt_hash"] = receipt["receipt_hash"]
    report["report_path"] = str(report_path)
    report["build_allowed"] = False
    report["why"] = "The demo proved the governed workflow and then permanently invalidated its fixture warrant by design."
    report["next_action"] = "Use real external evidence and a real human TTY for any non-demo authorization."
    return report
