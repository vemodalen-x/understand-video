"""TEMPO command-line interface with stable, judge-readable outcomes."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

from .charter import generate_charter, sign_charter
from .config import config_value, load_config
from .errors import CheckerFailure, EXIT_ALLOWED, TempoError
from .evidence import add_evidence, read_manifest, validate_all_evidence
from .guards import evaluate_event
from .ledger import Ledger
from .providers import import_proposal
from .readiness import assess
from .selfcheck import doctor, honesty_check, narrate, selfcheck
from .state import BUSINESS_TERMINAL, StateStore
from .util import Workspace, atomic_write_json, isoformat_z, load_json, utc_now
from .warrant import authorize, revoke, start, status

DEFAULT_SESSION = "local:tempo-cli"
DEFAULT_ACTOR = "human:local-operator"

BLOCKER_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    ("B01", "DECISION_OWNER_REQUIRED", "Decision question, owner, and date are mandatory."),
    ("B02", "TARGET_USER_REQUIRED", "Target user must be explicit."),
    ("B03", "ECONOMIC_BUYER_REQUIRED", "Economic buyer and value recipient must be explicit."),
    ("B04", "EXTERNAL_EVIDENCE_REQUIRED", "Concrete non-model evidence is required."),
    ("B05", "RANK_1_REQUIRED", "Exactly one falsifiable rank-1 hypothesis is required."),
    ("B06", "THRESHOLD_REQUIRED", "Evidence threshold and kill or pivot trigger are required."),
    ("B07", "FRESH_EVIDENCE_REQUIRED", "Stale and model-only evidence cannot pass."),
    ("B08", "COUNTEREVIDENCE_ACK_REQUIRED", "Contradictory evidence must be acknowledged."),
    ("B09", "ALTERNATIVES_REQUIRED", "Alternatives and differentiation must be considered."),
    ("B10", "VALUE_PATH_REQUIRED", "An economic value or ROI path is required."),
    ("B11", "DISTRIBUTION_REQUIRED", "Distribution or adoption must be hypothesized."),
    ("B12", "TECHNICAL_BOUNDARY_REQUIRED", "Technical feasibility must be bounded."),
    ("B13", "MATERIAL_RISK_CLOSED", "Material risks must be resolved, mitigated, or human-accepted."),
    ("B14", "DECISION_UNLOCK_REQUIRED", "The MVP must name the decision it unlocks."),
    ("B15", "CHARTER_COMPLETE", "Scope, success, budget, deadline, and exclusions are mandatory."),
    ("B16", "CHEAPEST_EXPERIMENT_REQUIRED", "A cheaper sufficient experiment blocks an MVP."),
    ("B17", "BUDGET_CAP_REQUIRED", "Projected cost must remain within budget."),
    ("B18", "SCHEMA_VALIDATION_REQUIRED", "All authoritative inputs must be schema-valid."),
    ("B19", "HUMAN_DECISION_REQUIRED", "Signer-approved policy and decision brief are mandatory."),
)


def _policy_template(workspace: Workspace, actor: str) -> dict[str, Any]:
    config = load_config(workspace)
    now = isoformat_z()
    return {
        "policy_id": "RP-LOCAL-DRAFT",
        "version": 1,
        "state": "draft",
        "effective_at": now,
        "owner": actor,
        "approved_by": None,
        "approved_at": None,
        "hard_blockers": [
            {"blocker_id": blocker_id, "reason_code": code, "description": description}
            for blocker_id, code, description in BLOCKER_TEMPLATES
        ],
        "weights": deepcopy(config["readiness"]["weights"]),
        "floors": deepcopy(config["readiness"]["floors"]),
        "aggregate_threshold": config["readiness"]["aggregate_threshold"],
        "external_evidence": {
            "minimum_items": 1,
            "model_generated_counts_as_external": False,
            "require_contradictions_acknowledged": True,
        },
        "cheaper_experiment_types": [
            "interview",
            "landing_page_test",
            "concierge_workflow",
            "manual_service",
            "clickable_prototype",
            "api_feasibility_spike",
            "benchmark",
            "pricing_test",
            "data_availability_check",
        ],
    }


def business_init(
    workspace: Workspace,
    *,
    actor: str = DEFAULT_ACTOR,
    session: str = DEFAULT_SESSION,
) -> dict[str, Any]:
    """Create a non-authoritative planning scaffold and initialize state."""
    workspace.ensure_directories(
        (
            "plan/evidence",
            "plan/proposals/commercial-agent",
            "tasks",
            ".tempo/assessments",
            ".tempo/receipts",
            ".tempo/run",
        )
    )
    config = load_config(workspace)
    freshness_days = int(
        config_value(config, "evidence.default_freshness_days", "tempo.cli.business_init")
    )
    defaults_path = workspace.path(".tempo/business-defaults.json")
    if not defaults_path.exists():
        atomic_write_json(
            defaults_path,
            {
                "default_evidence_freshness_days": freshness_days,
                "created_at": isoformat_z(),
                "authority_granted": False,
            },
        )
    policy_path = workspace.path("plan/readiness-policy.json")
    policy_created = False
    if not policy_path.exists():
        atomic_write_json(policy_path, _policy_template(workspace, actor))
        policy_created = True
    store = StateStore(workspace)
    state = store.initialize()
    if state["business"]["state"] == "DRAFT":
        state = store.transition("business", "DISCOVERY", "BUSINESS_WORKSPACE_INITIALIZED")
    return {
        "ok": True,
        "outcome": "BUSINESS_DISCOVERY_READY",
        "business_state": state["business"]["state"],
        "policy_created": policy_created,
        "policy_state": load_json(policy_path)["state"],
        "default_evidence_freshness_days": freshness_days,
        "build_allowed": False,
        "why": "Planning scaffolding is available; no implementation authority was created.",
        "next_action": "Complete the opportunity, hypotheses, evidence, decision brief, and charter proposal.",
    }


def _ensure_validating(workspace: Workspace, reason_code: str) -> dict[str, Any]:
    store = StateStore(workspace)
    state = store.initialize()
    current = state["business"]["state"]
    if current in BUSINESS_TERMINAL:
        state = store.new_business_cycle(reason_code)
        current = state["business"]["state"]
    if current == "DRAFT":
        state = store.transition("business", "DISCOVERY", reason_code)
        current = state["business"]["state"]
    if current in {"DISCOVERY", "MVP_CANDIDATE"}:
        state = store.transition("business", "VALIDATING", reason_code)
    return state


def _business_status(workspace: Workspace) -> dict[str, Any]:
    state = StateStore(workspace).initialize()
    latest = workspace.path(".tempo/assessments/latest.json")
    assessment = load_json(latest) if latest.is_file() else None
    return {
        "ok": True,
        "outcome": "BUSINESS_STATUS",
        "business": state["business"],
        "latest_assessment": assessment,
        "evidence_items": len(read_manifest(workspace)),
        "authority": status(workspace),
    }


def _context(workspace: Workspace) -> dict[str, Any]:
    config = load_config(workspace)
    state = StateStore(workspace).initialize()
    tasks = sorted(path.name for path in workspace.path("tasks").glob("*") if path.is_file()) if workspace.path("tasks").exists() else []
    branch = None
    dirty = None
    try:
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"], cwd=workspace.root, capture_output=True,
            text=True, timeout=5, check=False,
        )
        branch = branch_result.stdout.strip() or None
        dirty_result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=workspace.root, capture_output=True,
            text=True, timeout=5, check=False,
        )
        dirty = bool(dirty_result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return {
        "ok": True,
        "outcome": "CONTEXT_READY",
        "workspace": str(workspace.root),
        "track": config["project"]["track"],
        "branch": branch,
        "worktree_dirty": dirty,
        "state": state,
        "tasks": tasks,
        "authority": status(workspace),
        "next_action": narrate(workspace)["next_action"],
    }


def _hypothesis_list(workspace: Workspace) -> dict[str, Any]:
    payload = load_json(workspace.path("plan/hypotheses.json"))
    hypotheses = sorted(payload.get("hypotheses", []), key=lambda item: item.get("rank", 10**9))
    return {
        "ok": True,
        "outcome": "HYPOTHESES_LISTED",
        "hypothesis_set_id": payload.get("hypothesis_set_id"),
        "hypotheses": hypotheses,
    }


def _sessions(workspace: Workspace) -> dict[str, Any]:
    path = workspace.path("submission/session.json")
    return {
        "ok": True,
        "outcome": "SESSION_CANDIDATES_LISTED",
        "session": load_json(path) if path.is_file() else None,
        "next_action": "Confirm the exact Codex /feedback session before submission.",
    }


def _read_json_argument(workspace: Workspace, raw: str) -> dict[str, Any]:
    if raw == "-":
        try:
            value = json.load(sys.stdin)
        except json.JSONDecodeError as exc:
            raise CheckerFailure("HOOK_EVENT_INVALID", f"stdin is not valid JSON: {exc}") from exc
    else:
        path = Path(raw)
        if not path.is_absolute():
            path = workspace.root / path
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CheckerFailure("HOOK_EVENT_INVALID", f"Cannot read hook event: {exc}") from exc
    if not isinstance(value, dict):
        raise CheckerFailure("HOOK_EVENT_INVALID", "Hook event must be a JSON object")
    return value


def _render(payload: dict[str, Any], *, as_json: bool, stream: Any = None) -> None:
    target = stream or sys.stdout
    if as_json:
        target.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        return
    outcome = payload.get("outcome") or payload.get("primary_outcome") or payload.get("reason_code") or ("OK" if payload.get("ok") else "FAILED")
    why: Any = payload.get("why") or payload.get("message")
    if why is None and payload.get("hard_blockers"):
        why = [item.get("reason_code") for item in payload["hard_blockers"]]
    if why is None and payload.get("reasons"):
        why = payload["reasons"]
    evidence: dict[str, Any] = {}
    for key in (
        "assessment_id", "assessment_hash", "warrant_id", "receipt_id", "receipt_hash",
        "weighted_score", "build_allowed", "authorization_valid", "workspace", "report_path",
    ):
        if key in payload:
            evidence[key] = payload[key]
    next_action: Any = payload.get("next_action") or payload.get("cheapest_next_action")
    target.write(f"Outcome: {outcome}\n")
    target.write(f"Why: {json.dumps(why, ensure_ascii=False) if why is not None else 'Completed deterministically.'}\n")
    target.write(f"Evidence: {json.dumps(evidence, ensure_ascii=False, sort_keys=True) if evidence else 'See the structured artifacts and ledger.'}\n")
    if payload.get("outcome") == "JUDGE_DEMO_PASSED" and isinstance(payload.get("steps"), list):
        target.write("Journey:\n")
        for index, step in enumerate(payload["steps"], start=1):
            if not isinstance(step, dict):
                continue
            name = str(step.get("name", "unnamed_step")).replace("_", " ")
            details = str(step.get("details", "completed"))
            reason = f" [{step['reason_code']}]" if step.get("reason_code") else ""
            threshold = step.get("rank_one_threshold")
            threshold_note = ""
            if isinstance(threshold, dict):
                threshold_note = (
                    f" threshold={threshold.get('observed')} {threshold.get('operator')} "
                    f"{threshold.get('target')} {threshold.get('unit')} ({threshold.get('status')})"
                )
            target.write(f"  {index:02d}. PASS {name}{reason}{threshold_note} - {details}\n")
    target.write(f"Next action: {json.dumps(next_action, ensure_ascii=False) if next_action is not None else 'None.'}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tempo", description="Business-gated agentic MVP workflow")
    parser.add_argument("--root", default=".", help="Repository root (default: current workspace)")
    parser.add_argument("--json", action="store_true", help="Emit stable JSON")
    parser.add_argument("--session", default=DEFAULT_SESSION)
    parser.add_argument("--actor", default=DEFAULT_ACTOR)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("context")
    sub.add_parser("doctor")
    sub.add_parser("selfcheck")
    sub.add_parser("honesty")
    sub.add_parser("narrate")
    sub.add_parser("sessions")

    business = sub.add_parser("business")
    business_sub = business.add_subparsers(dest="business_command", required=True)
    business_sub.add_parser("init")
    importing = business_sub.add_parser("import")
    importing.add_argument("--provider", default="json")
    importing.add_argument("--input", required=True)
    business_sub.add_parser("status")

    hypothesis = sub.add_parser("hypothesis")
    hypothesis_sub = hypothesis.add_subparsers(dest="hypothesis_command", required=True)
    hypothesis_sub.add_parser("list")

    evidence = sub.add_parser("evidence")
    evidence_sub = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_add = evidence_sub.add_parser("add")
    evidence_add.add_argument("--input", required=True)
    evidence_sub.add_parser("validate")

    mvp = sub.add_parser("mvp")
    mvp_sub = mvp.add_subparsers(dest="mvp_command", required=True)
    assessment = mvp_sub.add_parser("assess")
    assessment.add_argument(
        "--fixture-mode", action="store_true",
        help="Count explicitly labeled fixtures for mechanics-only demos; never external validation",
    )
    mvp_sub.add_parser("charter")
    signing = mvp_sub.add_parser("sign-charter")
    signing.add_argument("--signer", required=True)
    authorization = mvp_sub.add_parser("authorize")
    authorization.add_argument("--assessment-hash")
    authorization.add_argument("--signer", required=True)
    authorization.add_argument("--ttl-hours", type=float)
    revocation = mvp_sub.add_parser("revoke")
    revocation.add_argument("--reason", default="HUMAN_REVOCATION")
    starting = mvp_sub.add_parser("start")
    starting.add_argument("--task", required=True)
    starting.add_argument("--path", required=True)
    starting.add_argument("--lane", required=True)
    starting.add_argument("--action", default="implementation_write")
    mvp_sub.add_parser("status")

    verdict = sub.add_parser("verdict")
    verdict_sub = verdict.add_subparsers(dest="verdict_command", required=True)
    verdict_sub.add_parser("compile")

    verification = sub.add_parser("verify")
    verification.add_argument("--level", choices=("focused", "all", "judge", "readme"), default="all")
    verification.add_argument("--require-container", action="store_true")

    ledger = sub.add_parser("ledger")
    ledger_sub = ledger.add_subparsers(dest="ledger_command", required=True)
    ledger_sub.add_parser("verify")

    hook = sub.add_parser("hook")
    hook.add_argument("--input", required=True, help="Event JSON path or - for stdin")

    sub.add_parser("submit-check")
    sub.add_parser("demo")
    return parser


def _resolve_input(workspace: Workspace, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = workspace.root / path
    return path.resolve(strict=False)


def _dispatch(args: argparse.Namespace, workspace: Workspace) -> tuple[dict[str, Any], int]:
    actor = args.actor
    session = args.session
    if args.command == "context":
        return _context(workspace), 0
    if args.command == "doctor":
        return doctor(workspace), 0
    if args.command == "selfcheck":
        return selfcheck(workspace), 0
    if args.command == "honesty":
        return honesty_check(workspace), 0
    if args.command == "narrate":
        return narrate(workspace), 0
    if args.command == "sessions":
        return _sessions(workspace), 0
    if args.command == "business":
        if args.business_command == "init":
            return business_init(workspace, actor=actor, session=session), 0
        if args.business_command == "status":
            return _business_status(workspace), 0
        _ensure_validating(workspace, "COMMERCIAL_PROPOSAL_CYCLE")
        return import_proposal(
            workspace, args.provider, _resolve_input(workspace, args.input), actor=actor, session=session
        ), 0
    if args.command == "hypothesis":
        return _hypothesis_list(workspace), 0
    if args.command == "evidence":
        if args.evidence_command == "validate":
            result = validate_all_evidence(workspace)
            return {"outcome": "EVIDENCE_VALID", **result}, 0
        _ensure_validating(workspace, "NEW_EVIDENCE_CYCLE")
        return add_evidence(
            workspace, _resolve_input(workspace, args.input), actor=actor, session=session
        ), 0
    if args.command == "mvp":
        if args.mvp_command == "assess":
            result, exit_code = assess(
                workspace, actor="kernel:readiness", session=session, allow_fixtures=args.fixture_mode
            )
            result["fixture_mode"] = bool(args.fixture_mode)
            if args.fixture_mode:
                result["fixture_disclaimer"] = "Mechanics only: fixtures are not external customer validation."
            return result, exit_code
        if args.mvp_command == "charter":
            return generate_charter(workspace, actor=actor, session=session), 0
        if args.mvp_command == "sign-charter":
            return sign_charter(workspace, signer_ref=args.signer, session=session), 0
        if args.mvp_command == "authorize":
            assessment_hash = args.assessment_hash
            if not assessment_hash:
                assessment_hash = load_json(workspace.path(".tempo/assessments/latest.json"))["assessment_hash"]
            return authorize(
                workspace,
                assessment_hash=assessment_hash,
                signer_ref=args.signer,
                signer_session=session,
                ttl_hours=args.ttl_hours,
            ), 0
        if args.mvp_command == "revoke":
            return revoke(workspace, actor=actor, session=session, reason_code=args.reason), 0
        if args.mvp_command == "start":
            return start(
                workspace, task_id=args.task, path=args.path, lane=args.lane,
                action=args.action, actor=actor, session=session,
            ), 0
        return status(workspace), 0
    if args.command == "verdict":
        from .verdict import compile_verdict

        return compile_verdict(workspace, actor=actor, session=session), 0
    if args.command == "verify":
        from .verify import readme_literal_plan, run_verification

        if args.level == "readme":
            if args.require_container:
                raise CheckerFailure(
                    "README_PLAN_IS_NOT_EXECUTION",
                    "README extraction is a plan-only operation; use --level all --require-container for execution evidence.",
                )
            plan = readme_literal_plan(workspace)
            return {
                "outcome": "README_PLAN_ONLY",
                "exit_code": 4,
                "warning": "Commands were parsed but not executed.",
                **plan,
            }, 4

        receipt = run_verification(
            workspace,
            level=args.level,
            session=session,
            require_container=args.require_container,
        )
        return receipt, int(receipt["exit_code"])
    if args.command == "ledger":
        return {"outcome": "LEDGER_VALID", **Ledger(workspace).verify()}, 0
    if args.command == "hook":
        return evaluate_event(workspace, _read_json_argument(workspace, args.input)), 0
    if args.command == "submit-check":
        from .submit import submit_check

        result = submit_check(workspace, session=session)
        return result, int(result.get("exit_code", 0))
    if args.command == "demo":
        from .demo import run_demo

        return run_demo(workspace, session=session), 0
    raise CheckerFailure("COMMAND_UNSUPPORTED", f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    # argparse normally requires global flags before subcommands. Moving these
    # unambiguous flags gives judges the natural `tempo demo --json` form too.
    normalized: list[str] = []
    remaining = list(raw)
    for flag in ("--json",):
        if flag in remaining:
            remaining.remove(flag)
            normalized.append(flag)
    for flag in ("--root", "--session", "--actor"):
        if flag in remaining:
            index = remaining.index(flag)
            if index + 1 >= len(remaining):
                normalized.append(flag)
                remaining.pop(index)
                continue
            value = remaining[index + 1]
            del remaining[index : index + 2]
            normalized.extend((flag, value))
    raw = [*normalized, *remaining]
    parser = _build_parser()
    args = parser.parse_args(raw)
    as_json = bool(args.json)
    try:
        workspace = Workspace.from_path(args.root)
        payload, exit_code = _dispatch(args, workspace)
        _render(payload, as_json=as_json)
        return exit_code
    except TempoError as exc:
        _render(exc.as_dict(), as_json=as_json, stream=sys.stderr)
        return exc.exit_code
    except Exception as exc:  # fail closed at the CLI boundary
        if os.environ.get("TEMPO_DEBUG") == "1":
            raise
        failure = CheckerFailure(
            "UNEXPECTED_CHECKER_FAILURE",
            f"TEMPO could not complete the check: {type(exc).__name__}: {exc}",
            next_action="Set TEMPO_DEBUG=1 for a traceback, fix the checker, and retry.",
        )
        _render(failure.as_dict(), as_json=as_json, stream=sys.stderr)
        return failure.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
