"""Human-controlled, hash-bound, fail-closed MVP implementation authority."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import fnmatch
import json
from pathlib import Path
import sys
from typing import Any, TextIO
import uuid

from .config import config_value, load_config
from .errors import CheckerFailure, PolicyBlock, TempoError
from .ledger import Ledger, _FileLock
from .schema import validate_data
from .state import StateStore
from .util import (
    Workspace,
    atomic_write_json,
    artifact_hashes,
    canonical_json_bytes,
    canonical_relpath,
    isoformat_z,
    load_json,
    parse_datetime,
    sha256_bytes,
    sha256_file,
    sha256_json,
    utc_now,
)


DEMO_SIGNER = "platform:demo-fixture-signer"
DEMO_CONTEXT_PATH = ".tempo/demo-fixture.json"
DEMO_CONTEXT_KIND = "tempo.isolated-demo-workspace"
DEMO_CONTEXT_VERSION = 1


def initialize_demo_context(
    workspace: Workspace,
    *,
    mvp_ref: str,
    session: str,
) -> dict[str, Any]:
    """Bind the local fixture-only signer to one exact disposable workspace."""
    marker = {
        "kind": DEMO_CONTEXT_KIND,
        "version": DEMO_CONTEXT_VERSION,
        "fixture_only": True,
        "signer_ref": DEMO_SIGNER,
        "mvp_ref": mvp_ref,
        "session": session,
        "created_at": isoformat_z(),
        "workspace_binding": sha256_json({"workspace_root": str(workspace.root.resolve())}),
        "nonce": uuid.uuid4().hex,
    }
    path = workspace.path(DEMO_CONTEXT_PATH)
    atomic_write_json(path, marker)
    return {**marker, "context_hash": sha256_file(path)}


def _demo_context_marker(workspace: Workspace, *, mvp_ref: str) -> tuple[dict[str, Any], str]:
    path = workspace.path(DEMO_CONTEXT_PATH)
    if not path.is_file():
        raise PolicyBlock(
            "DEMO_CONTEXT_MISSING",
            "The fixture signer is valid only inside a TEMPO-created isolated demo workspace",
        )
    marker = load_json(path)
    expected_keys = {
        "kind",
        "version",
        "fixture_only",
        "signer_ref",
        "mvp_ref",
        "session",
        "created_at",
        "workspace_binding",
        "nonce",
    }
    expected_binding = sha256_json({"workspace_root": str(workspace.root.resolve())})
    valid = (
        isinstance(marker, dict)
        and set(marker) == expected_keys
        and marker.get("kind") == DEMO_CONTEXT_KIND
        and marker.get("version") == DEMO_CONTEXT_VERSION
        and marker.get("fixture_only") is True
        and marker.get("signer_ref") == DEMO_SIGNER
        and marker.get("mvp_ref") == mvp_ref
        and isinstance(marker.get("session"), str)
        and len(marker["session"]) >= 3
        and isinstance(marker.get("nonce"), str)
        and len(marker["nonce"]) == 32
        and all(character in "0123456789abcdef" for character in marker["nonce"])
        and marker.get("workspace_binding") == expected_binding
    )
    try:
        if valid:
            parse_datetime(marker["created_at"])
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise PolicyBlock(
            "DEMO_CONTEXT_INVALID",
            "The isolated demo marker is malformed, copied, or bound to another workspace/MVP",
        )
    return marker, sha256_file(path)


def _latest_assessment(workspace: Workspace) -> dict[str, Any]:
    assessment = load_json(workspace.path(".tempo/assessments/latest.json"))
    validate_data(workspace, "assessment", assessment, policy_block=False)
    body = {key: value for key, value in assessment.items() if key != "assessment_hash"}
    if assessment["assessment_hash"] != sha256_bytes(canonical_json_bytes(body)):
        raise PolicyBlock("ASSESSMENT_INTEGRITY_FAILED", "Latest assessment hash is invalid")
    return assessment


def _assessment_current(workspace: Workspace, assessment: dict[str, Any]) -> None:
    drift: dict[str, dict[str, str]] = {}
    for binding in assessment["input_hashes"]:
        relative = binding["artifact_ref"]
        path = workspace.path(relative)
        current = sha256_file(path) if path.is_file() else sha256_json({"missing": relative})
        if current != binding["hash"]:
            drift[relative] = {"expected": binding["hash"], "actual": current}
    if drift:
        raise PolicyBlock(
            "ASSESSMENT_STALE",
            "Protected inputs changed after the readiness assessment",
            details={"drift": drift},
            next_action="Run tempo mvp assess again and review the new result.",
        )


def protected_hash_set(workspace: Workspace) -> dict[str, str]:
    config = load_config(workspace)
    protected = config_value(
        config,
        "warrant.protected_artifacts",
        "tempo.warrant.protected_hash_set",
    )
    hashes = artifact_hashes(workspace, protected)
    charter = load_json(workspace.path("plan/mvp-charter.json"))
    return {
        "signed_decision_brief": hashes["plan/decision-brief.json"],
        "hypothesis_set": hashes["plan/hypotheses.json"],
        "evidence_manifest": hashes["plan/evidence/manifest.jsonl"],
        "readiness_policy": hashes["plan/readiness-policy.json"],
        "mvp_charter": hashes["plan/mvp-charter.json"],
        "runtime_config": hashes["config/tempo.config.json"],
        "budget": sha256_json(charter["budget_cap"]),
        "deadline": sha256_json(charter["deadline"]),
        "allowed_scope": sha256_json(charter["in_scope"]),
    }


def _final_authorization_snapshot(
    workspace: Workspace,
    *,
    requested_assessment_hash: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Reload all signer inputs after confirmation and reject any interleaving drift."""
    assessment = _latest_assessment(workspace)
    if assessment["assessment_hash"] != requested_assessment_hash:
        raise PolicyBlock(
            "ASSESSMENT_HASH_MISMATCH",
            "Requested assessment hash is no longer the latest assessment",
        )
    _assessment_current(workspace, assessment)
    charter_path = workspace.path("plan/mvp-charter.json")
    charter_digest = sha256_file(charter_path)
    charter = load_json(charter_path)
    validate_data(workspace, "mvp-charter", charter)
    if charter["state"] != "signed" or not charter.get("signed_by"):
        raise PolicyBlock("SIGNED_CHARTER_REQUIRED", "The complete MVP charter must be human-signed")
    if charter["signed_by"].startswith("agent:"):
        raise PolicyBlock("SELF_AUTHORIZATION_FORBIDDEN", "Agent-signed charter is invalid")

    hashes = protected_hash_set(workspace)
    _assessment_current(workspace, assessment)
    if sha256_file(charter_path) != charter_digest or protected_hash_set(workspace) != hashes:
        raise PolicyBlock(
            "AUTHORIZATION_INPUTS_CHANGED",
            "Authorization inputs changed while the final signer snapshot was being created",
            next_action="Run tempo mvp assess again and repeat the authorization review.",
        )
    return assessment, charter, hashes


def _validate_demo_authorization_context(
    workspace: Workspace,
    *,
    assessment: dict[str, Any],
    charter: dict[str, Any],
    signer_session: str,
) -> str:
    if assessment.get("evaluation_mode") != "fixture_demo" or assessment.get(
        "authorization_ceiling"
    ) != "demo_only":
        raise PolicyBlock(
            "DEMO_ASSESSMENT_REQUIRED",
            "The isolated fixture signer requires a fixture_demo assessment with a demo_only ceiling",
        )
    if charter.get("signed_by") != DEMO_SIGNER:
        raise PolicyBlock(
            "DEMO_CHARTER_SIGNER_REQUIRED",
            "A fixture warrant requires the isolated demo signer on the charter",
        )
    policy = load_json(workspace.path("plan/readiness-policy.json"))
    validate_data(workspace, "readiness-policy", policy)
    if policy.get("state") != "signed" or policy.get("approved_by") != DEMO_SIGNER:
        raise PolicyBlock(
            "DEMO_POLICY_SIGNER_REQUIRED",
            "A fixture warrant requires a demo-signer-approved readiness policy",
        )
    brief = load_json(workspace.path("plan/decision-brief.json"))
    validate_data(workspace, "decision-brief", brief)
    if (
        brief.get("state") != "signed"
        or brief.get("approved_by") != DEMO_SIGNER
        or brief.get("signing_provenance") != "demo_fixture"
    ):
        raise PolicyBlock(
            "DEMO_BRIEF_SIGNER_REQUIRED",
            "A fixture warrant requires a demo-signed, fixture-labeled decision brief",
        )
    marker, marker_hash = _demo_context_marker(workspace, mvp_ref=charter["mvp_id"])
    if marker["session"] != signer_session:
        raise PolicyBlock(
            "DEMO_SESSION_MISMATCH",
            "The fixture signer session is not the one bound to this isolated demo workspace",
        )
    return marker_hash


def _authorize_locked(
    workspace: Workspace,
    *,
    assessment_hash: str,
    signer_ref: str,
    signer_session: str,
    ttl_hours: float | None = None,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    demo_fixture: bool = False,
) -> dict[str, Any]:
    """Issue a warrant only after fresh readiness and human/signer control."""
    if signer_ref.startswith(("agent:", "kernel:", "verifier:")):
        raise PolicyBlock("SELF_AUTHORIZATION_FORBIDDEN", "An agent, kernel, or verifier cannot issue a warrant")
    if not signer_ref.startswith(("human:", "platform:")):
        raise PolicyBlock("SIGNER_INVALID", "Signer must be a human or isolated platform identity")
    stdin = input_stream or sys.stdin
    stdout = output_stream or sys.stdout
    if not demo_fixture and not stdin.isatty():
        raise PolicyBlock(
            "TTY_OR_ISOLATED_SIGNER_REQUIRED",
            "MVP authorization requires a real human TTY or isolated signer",
        )
    if demo_fixture and signer_ref != DEMO_SIGNER:
        raise PolicyBlock("DEMO_SIGNER_INVALID", "Demo authority is limited to the built-in fixture signer")

    assessment = _latest_assessment(workspace)
    if assessment["assessment_hash"] != assessment_hash:
        raise PolicyBlock("ASSESSMENT_HASH_MISMATCH", "Requested assessment hash is not the latest assessment")
    _assessment_current(workspace, assessment)
    if not assessment["eligible_for_authorization"] or assessment["primary_outcome"] != "MVP_AUTHORIZED":
        raise PolicyBlock(
            "READINESS_NOT_PASSED",
            "Business readiness has not passed",
            details={"outcome": assessment["primary_outcome"]},
        )
    if assessment.get("authorization_ceiling") == "demo_only" and not demo_fixture:
        raise PolicyBlock(
            "FIXTURE_ASSESSMENT_DEMO_ONLY",
            "An assessment that counted fixture evidence can only issue the isolated demo warrant",
            details={"assessment_id": assessment["assessment_id"]},
        )

    charter_path = workspace.path("plan/mvp-charter.json")
    charter = load_json(charter_path)
    validate_data(workspace, "mvp-charter", charter)
    if charter["state"] != "signed" or not charter.get("signed_by"):
        raise PolicyBlock("SIGNED_CHARTER_REQUIRED", "The complete MVP charter must be human-signed")
    if charter["signed_by"].startswith("agent:"):
        raise PolicyBlock("SELF_AUTHORIZATION_FORBIDDEN", "Agent-signed charter is invalid")

    config = load_config(workspace)
    maximum_ttl = float(config_value(config, "warrant.max_ttl_hours", "tempo.warrant.authorize"))
    requested_ttl = float(ttl_hours if ttl_hours is not None else maximum_ttl)
    if requested_ttl <= 0 or requested_ttl > maximum_ttl:
        raise PolicyBlock(
            "WARRANT_TTL_INVALID",
            f"Warrant TTL must be within (0, {maximum_ttl}] hours",
        )
    now = utc_now()
    expires = min(now + timedelta(hours=requested_ttl), parse_datetime(charter["deadline"]))
    if expires <= now:
        raise PolicyBlock("DEADLINE_EXCEEDED", "Charter deadline has already passed")
    phrase = f"AUTHORIZE {charter['mvp_id']} {assessment_hash}"
    if not demo_fixture:
        stdout.write(
            "This grants bounded implementation authority. "
            f"Type {phrase!r} to continue: "
        )
        stdout.flush()
        if stdin.readline().strip() != phrase:
            raise PolicyBlock("HUMAN_CONFIRMATION_MISMATCH", "Authorization confirmation did not match")

    # The user-controlled confirmation can take arbitrarily long. Reload every
    # decision input after it and derive the warrant only from that final,
    # internally consistent snapshot.
    assessment, charter, final_hashes = _final_authorization_snapshot(
        workspace,
        requested_assessment_hash=assessment_hash,
    )
    if not assessment["eligible_for_authorization"] or assessment["primary_outcome"] != "MVP_AUTHORIZED":
        raise PolicyBlock(
            "READINESS_NOT_PASSED",
            "Business readiness no longer passes after confirmation",
            details={"outcome": assessment["primary_outcome"]},
        )
    if assessment.get("authorization_ceiling") == "demo_only" and not demo_fixture:
        raise PolicyBlock(
            "FIXTURE_ASSESSMENT_DEMO_ONLY",
            "An assessment that counted fixture evidence can only issue the isolated demo warrant",
            details={"assessment_id": assessment["assessment_id"]},
        )
    config = load_config(workspace)
    maximum_ttl = float(config_value(config, "warrant.max_ttl_hours", "tempo.warrant.authorize"))
    requested_ttl = float(ttl_hours if ttl_hours is not None else maximum_ttl)
    if requested_ttl <= 0 or requested_ttl > maximum_ttl:
        raise PolicyBlock("WARRANT_TTL_INVALID", f"Warrant TTL must be within (0, {maximum_ttl}] hours")
    now = utc_now()
    expires = min(now + timedelta(hours=requested_ttl), parse_datetime(charter["deadline"]))
    if expires <= now:
        raise PolicyBlock("DEADLINE_EXCEEDED", "Charter deadline has already passed")
    demo_context_hash = (
        _validate_demo_authorization_context(
            workspace,
            assessment=assessment,
            charter=charter,
            signer_session=signer_session,
        )
        if demo_fixture
        else None
    )

    warrant = {
        "warrant_id": f"W-{uuid.uuid4().hex[:16].upper()}",
        "mvp_ref": charter["mvp_id"],
        "assessment_ref": assessment["assessment_id"],
        "repository_ref": workspace.root.name,
        "state": "active",
        "signer_ref": signer_ref,
        "signer_session": signer_session,
        "issued_at": isoformat_z(now),
        "expires_at": isoformat_z(expires),
        "authorization_type": "demo_build" if demo_fixture else "mvp_build",
        "allowed_actions": ["implementation_write", "test", "build", "local_demo"],
        "allowed_scope": charter["in_scope"],
        "allowed_lanes": charter["allowed_lanes"],
        "budget_cap": charter["budget_cap"],
        "deadline": charter["deadline"],
        "hash_set": final_hashes,
        "demo_context_hash": demo_context_hash,
        "revocation": {
            "revoked": False,
            "revoked_at": None,
            "revoked_by": None,
            "reason_code": None,
        },
        "provenance_kind": "local_integrity_only" if demo_fixture else "tty_human",
        "previous_warrant_ref": None,
    }
    validate_data(workspace, "authorization-warrant", warrant, policy_block=False)
    path = workspace.path("plan/authorization-warrant.json")
    if path.exists():
        existing = load_json(path)
        if existing.get("state") == "active" and not _terminal_event_exists(workspace, existing["warrant_id"]):
            raise PolicyBlock("ACTIVE_WARRANT_EXISTS", "Revoke or expire the current warrant first")
        warrant["previous_warrant_ref"] = existing.get("warrant_id")
    atomic_write_json(path, warrant)
    digest = sha256_file(path)
    Ledger(workspace).append(
        "mvp_authorized",
        actor=signer_ref,
        session=signer_session,
        relevant_ids={
            "warrant_id": warrant["warrant_id"],
            "mvp_id": warrant["mvp_ref"],
            "assessment_id": warrant["assessment_ref"],
        },
        artifact_hashes={"plan/authorization-warrant.json": digest, **warrant["hash_set"]},
        evidence_refs=charter["evidence_baseline"]["evidence_refs"],
        reason_code="DEMO_FIXTURE_LOCAL_INTEGRITY" if demo_fixture else "HUMAN_TTY_AUTHORIZATION",
        resulting_state="AUTHORIZED",
        details={
            "provenance_kind": warrant["provenance_kind"],
            "assessment_authorization_ceiling": assessment["authorization_ceiling"],
        },
    )
    store = StateStore(workspace)
    state = store.initialize()
    if state["mvp"]["state"] == "NOT_AUTHORIZED":
        store.transition("mvp", "AUTHORIZED", "VALID_WARRANT_ISSUED")
    return {
        "ok": True,
        "warrant_id": warrant["warrant_id"],
        "mvp_id": warrant["mvp_ref"],
        "expires_at": warrant["expires_at"],
        "scope": warrant["allowed_scope"],
        "provenance_kind": warrant["provenance_kind"],
        "warrant_hash": digest,
        "build_allowed": True,
    }


def authorize(
    workspace: Workspace,
    *,
    assessment_hash: str,
    signer_ref: str,
    signer_session: str,
    ttl_hours: float | None = None,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    demo_fixture: bool = False,
) -> dict[str, Any]:
    """Serialize authorization reviews so two issuers cannot race the active warrant."""
    with _FileLock(workspace.path(".tempo/authorization.lock")):
        return _authorize_locked(
            workspace,
            assessment_hash=assessment_hash,
            signer_ref=signer_ref,
            signer_session=signer_session,
            ttl_hours=ttl_hours,
            input_stream=input_stream,
            output_stream=output_stream,
            demo_fixture=demo_fixture,
        )


def _terminal_event_exists(workspace: Workspace, warrant_id: str) -> str | None:
    terminal = {
        "mvp_authorization_revoked": "revoked",
        "mvp_authorization_expired": "expired",
        "mvp_authorization_invalidated": "invalidated",
    }
    ledger = Ledger(workspace)
    ledger.verify()
    for event in ledger.events():
        if event.get("relevant_ids", {}).get("warrant_id") == warrant_id and event.get("event_type") in terminal:
            return terminal[event["event_type"]]
    return None


def _assert_warrant_ledger_binding(
    workspace: Workspace,
    warrant: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    expected_event = {
        "active": "mvp_authorized",
        "revoked": "mvp_authorization_revoked",
        "expired": "mvp_authorization_expired",
        "invalidated": "mvp_authorization_invalidated",
    }[warrant["state"]]
    binding = next(
        (
            event
            for event in reversed(events)
            if event.get("event_type") == expected_event
            and event.get("relevant_ids", {}).get("warrant_id") == warrant["warrant_id"]
        ),
        None,
    )
    expected_hash = (
        binding.get("artifact_hashes", {}).get("plan/authorization-warrant.json")
        if binding
        else None
    )
    actual_hash = sha256_file(workspace.path("plan/authorization-warrant.json"))
    if expected_hash != actual_hash:
        raise PolicyBlock(
            "WARRANT_INTEGRITY_FAILED",
            "The warrant bytes are not bound to the corresponding verified ledger event",
            details={"expected": expected_hash, "actual": actual_hash, "event_type": expected_event},
        )


def _record_terminal(
    workspace: Workspace,
    warrant: dict[str, Any],
    event_type: str,
    *,
    actor: str,
    session: str,
    reason_code: str,
    state: str,
    details: dict[str, Any] | None = None,
) -> None:
    existing_terminal = _terminal_event_exists(workspace, warrant["warrant_id"])
    if existing_terminal:
        return
    terminal_state = {
        "mvp_authorization_revoked": "revoked",
        "mvp_authorization_expired": "expired",
        "mvp_authorization_invalidated": "invalidated",
    }.get(event_type)
    if terminal_state is None:
        raise CheckerFailure("WARRANT_TERMINAL_EVENT_INVALID", f"Unsupported terminal event: {event_type}")
    terminal_warrant = deepcopy(warrant)
    terminal_warrant["state"] = terminal_state
    terminal_warrant["revocation"] = {
        "revoked": True,
        "revoked_at": isoformat_z(),
        "revoked_by": actor,
        "reason_code": reason_code,
    }
    validate_data(workspace, "authorization-warrant", terminal_warrant, policy_block=False)
    warrant_path = workspace.path("plan/authorization-warrant.json")
    atomic_write_json(warrant_path, terminal_warrant)
    digest = sha256_file(warrant_path)
    Ledger(workspace).append(
        event_type,
        actor=actor,
        session=session,
        relevant_ids={"warrant_id": warrant["warrant_id"], "mvp_id": warrant["mvp_ref"]},
        artifact_hashes={"plan/authorization-warrant.json": digest},
        evidence_refs=[],
        reason_code=reason_code,
        resulting_state=state,
        details=details or {},
    )
    warrant.clear()
    warrant.update(terminal_warrant)


def validate_warrant(
    workspace: Workspace,
    *,
    now: Any = None,
    actor: str = "kernel:warrant",
    session: str = "unknown",
) -> dict[str, Any]:
    path = workspace.path("plan/authorization-warrant.json")
    if not path.is_file():
        raise PolicyBlock("WARRANT_MISSING", "No MVP authorization warrant exists")
    warrant = load_json(path)
    validate_data(workspace, "authorization-warrant", warrant, policy_block=False)
    ledger = Ledger(workspace)
    ledger.verify()
    events = ledger.events()
    terminal_map = {
        "mvp_authorization_revoked": "revoked",
        "mvp_authorization_expired": "expired",
        "mvp_authorization_invalidated": "invalidated",
    }
    terminal = next(
        (
            terminal_map[event["event_type"]]
            for event in reversed(events)
            if event.get("relevant_ids", {}).get("warrant_id") == warrant["warrant_id"]
            and event.get("event_type") in terminal_map
        ),
        None,
    )
    if warrant["state"] != "active":
        _assert_warrant_ledger_binding(workspace, warrant, events)
        raise PolicyBlock(
            f"WARRANT_{warrant['state'].upper()}",
            f"Warrant is permanently {warrant['state']}",
        )
    if terminal:
        raise PolicyBlock(f"WARRANT_{terminal.upper()}", f"Warrant is permanently {terminal}")
    _assert_warrant_ledger_binding(workspace, warrant, events)
    current = now or utc_now()
    if current >= parse_datetime(warrant["expires_at"]):
        _record_terminal(
            workspace, warrant, "mvp_authorization_expired", actor=actor, session=session,
            reason_code="WARRANT_EXPIRED", state="EXPIRED",
        )
        try:
            StateStore(workspace).mark_exceptional("EXPIRED", "WARRANT_EXPIRED")
        except TempoError:
            pass
        raise PolicyBlock("WARRANT_EXPIRED", "Authorization warrant has expired")
    if current >= parse_datetime(warrant["deadline"]):
        raise PolicyBlock("DEADLINE_EXCEEDED", "MVP charter deadline has passed")
    if warrant["authorization_type"] == "demo_build":
        try:
            _, marker_hash = _demo_context_marker(workspace, mvp_ref=warrant["mvp_ref"])
        except TempoError as exc:
            marker_hash = None
            marker_reason = exc.reason_code
        else:
            marker_reason = None
        if marker_hash != warrant.get("demo_context_hash"):
            marker_drift = {
                "expected": warrant.get("demo_context_hash"),
                "actual": marker_hash,
                "cause": marker_reason,
            }
            _record_terminal(
                workspace,
                warrant,
                "mvp_authorization_invalidated",
                actor=actor,
                session=session,
                reason_code="DEMO_CONTEXT_DRIFT",
                state="REVOKED",
                details={"demo_context": marker_drift},
            )
            try:
                StateStore(workspace).mark_exceptional("REVOKED", "DEMO_CONTEXT_DRIFT")
            except TempoError:
                pass
            raise PolicyBlock(
                "DEMO_CONTEXT_DRIFT",
                "The isolated demo workspace binding changed; the warrant is permanently invalid",
                details={"demo_context": marker_drift},
            )
    actual = protected_hash_set(workspace)
    drift = {
        key: {"expected": warrant["hash_set"].get(key), "actual": value}
        for key, value in actual.items()
        if warrant["hash_set"].get(key) != value
    }
    if drift:
        _record_terminal(
            workspace, warrant, "mvp_authorization_invalidated", actor=actor, session=session,
            reason_code="PROTECTED_INPUT_DRIFT", state="REVOKED", details={"drift": drift},
        )
        try:
            StateStore(workspace).mark_exceptional("REVOKED", "PROTECTED_INPUT_DRIFT")
        except TempoError:
            pass
        raise PolicyBlock(
            "PROTECTED_INPUT_DRIFT",
            "A protected input changed after authorization; the warrant is permanently invalid",
            details={"drift": drift},
        )
    spent = sum(
        float(event.get("details", {}).get("cost_amount", 0) or 0)
        for event in events
        if event.get("event_type") == "verification_completed"
        and event.get("relevant_ids", {}).get("warrant_id") == warrant["warrant_id"]
    )
    if spent > float(warrant["budget_cap"]["amount"]):
        raise PolicyBlock(
            "BUDGET_CAP_EXCEEDED",
            "Machine-receipted spend exceeds the warrant budget",
            details={"spent": spent, "budget_cap": warrant["budget_cap"]},
        )
    return warrant


def _revoke_locked(
    workspace: Workspace,
    *,
    actor: str,
    session: str,
    reason_code: str,
) -> dict[str, Any]:
    path = workspace.path("plan/authorization-warrant.json")
    if not path.is_file():
        raise PolicyBlock("WARRANT_MISSING", "No warrant exists to revoke")
    warrant = load_json(path)
    validate_data(workspace, "authorization-warrant", warrant, policy_block=False)
    ledger = Ledger(workspace)
    ledger.verify()
    events = ledger.events()
    if warrant["state"] != "active":
        _assert_warrant_ledger_binding(workspace, warrant, events)
        return {
            "ok": True,
            "warrant_id": warrant["warrant_id"],
            "state": warrant["state"],
            "idempotent": True,
        }
    terminal = _terminal_event_exists(workspace, warrant["warrant_id"])
    if terminal:
        return {"ok": True, "warrant_id": warrant["warrant_id"], "state": terminal, "idempotent": True}
    _assert_warrant_ledger_binding(workspace, warrant, events)
    _record_terminal(
        workspace, warrant, "mvp_authorization_revoked", actor=actor, session=session,
        reason_code=reason_code, state="REVOKED",
    )
    try:
        StateStore(workspace).mark_exceptional("REVOKED", reason_code)
    except TempoError:
        pass
    return {"ok": True, "warrant_id": warrant["warrant_id"], "state": "revoked", "idempotent": False}


def revoke(
    workspace: Workspace,
    *,
    actor: str,
    session: str,
    reason_code: str,
) -> dict[str, Any]:
    """Serialize revocation against authorization and implementation start."""
    with _FileLock(workspace.path(".tempo/authorization.lock")):
        return _revoke_locked(
            workspace,
            actor=actor,
            session=session,
            reason_code=reason_code,
        )


def _scope_match(path: str, patterns: list[str]) -> bool:
    canonical = canonical_relpath(path)
    return any(fnmatch.fnmatchcase(canonical, pattern) for pattern in patterns)


def _load_task(workspace: Workspace, task_id: str) -> dict[str, Any]:
    candidates = [workspace.path(f"tasks/{task_id}.json")]
    for path in candidates:
        if path.is_file():
            task = load_json(path)
            if not isinstance(task, dict):
                break
            return task
    raise PolicyBlock("TASK_NOT_FOUND", f"Task record not found: {task_id}")


def _validate_traceability(
    task: dict[str, Any], charter: dict[str, Any], hypotheses: dict[str, Any]
) -> None:
    missing: list[str] = []
    hypothesis_ids = {item["hypothesis_id"] for item in hypotheses.get("hypotheses", [])}
    for reference in task.get("hypothesis_refs", []):
        if reference not in hypothesis_ids:
            missing.append(f"{task.get('task_id')} -> {reference}")
    if not task.get("hypothesis_refs"):
        missing.append(f"{task.get('task_id')} -> hypothesis")
    if task.get("charter_ref") != charter.get("mvp_id"):
        missing.append(f"{task.get('task_id')} -> {charter.get('mvp_id')}")
    if task.get("opportunity_ref") != charter.get("opportunity_ref"):
        missing.append(f"{charter.get('mvp_id')} -> {charter.get('opportunity_ref')}")
    if missing:
        raise PolicyBlock(
            "TRACEABILITY_BROKEN",
            "Task-to-hypothesis-to-charter traceability is incomplete",
            details={"missing_edges": missing},
        )


def _start_locked(
    workspace: Workspace,
    *,
    task_id: str,
    path: str,
    lane: str,
    action: str,
    actor: str,
    session: str,
) -> dict[str, Any]:
    warrant = validate_warrant(workspace, actor=actor, session=session)
    if action not in warrant["allowed_actions"]:
        raise PolicyBlock("ACTION_NOT_AUTHORIZED", f"Action is outside warrant: {action}")
    if lane not in warrant["allowed_lanes"]:
        raise PolicyBlock("LANE_NOT_AUTHORIZED", f"Lane is outside warrant: {lane}")
    if not _scope_match(path, warrant["allowed_scope"]):
        raise PolicyBlock("SCOPE_NOT_AUTHORIZED", f"Path is outside warrant scope: {path}")
    task = _load_task(workspace, task_id)
    charter = load_json(workspace.path("plan/mvp-charter.json"))
    hypotheses = load_json(workspace.path("plan/hypotheses.json"))
    _validate_traceability(task, charter, hypotheses)
    if task.get("lane") != lane:
        raise PolicyBlock("TASK_LANE_MISMATCH", "Task lane does not match requested lane")
    if not _scope_match(path, task.get("scope_in", [])):
        raise PolicyBlock("TASK_SCOPE_VIOLATION", f"Path is outside task scope: {path}")
    state = StateStore(workspace).initialize()
    if state["mvp"]["state"] == "AUTHORIZED":
        StateStore(workspace).transition("mvp", "BUILDING", "VALID_WARRANT_AND_TASK")
    active = {
        "warrant_id": warrant["warrant_id"],
        "mvp_id": warrant["mvp_ref"],
        "task_id": task_id,
        "path": canonical_relpath(path),
        "lane": lane,
        "action": action,
        "actor": actor,
        "session": session,
        "started_at": isoformat_z(),
    }
    atomic_write_json(workspace.path(".tempo/run/active.json"), active)
    Ledger(workspace).append(
        "mvp_started",
        actor=actor,
        session=session,
        relevant_ids={"warrant_id": warrant["warrant_id"], "mvp_id": warrant["mvp_ref"], "task_id": task_id},
        artifact_hashes={"plan/authorization-warrant.json": sha256_file(workspace.path("plan/authorization-warrant.json"))},
        evidence_refs=charter["evidence_baseline"]["evidence_refs"],
        reason_code="VALID_WARRANT_AND_SCOPE",
        resulting_state="BUILDING",
        details={"path": active["path"], "lane": lane, "action": action},
    )
    return {"ok": True, "build_allowed": True, **active}


def start(
    workspace: Workspace,
    *,
    task_id: str,
    path: str,
    lane: str,
    action: str,
    actor: str,
    session: str,
) -> dict[str, Any]:
    """Serialize start against warrant issue/revocation to close the decision race."""
    with _FileLock(workspace.path(".tempo/authorization.lock")):
        return _start_locked(
            workspace,
            task_id=task_id,
            path=path,
            lane=lane,
            action=action,
            actor=actor,
            session=session,
        )


def status(workspace: Workspace) -> dict[str, Any]:
    state = StateStore(workspace).initialize()
    try:
        warrant = validate_warrant(workspace)
        return {
            "ok": True,
            "readiness_state": state["business"]["state"],
            "mvp_state": state["mvp"]["state"],
            "authorization_valid": True,
            "build_allowed": state["mvp"]["state"] in {"AUTHORIZED", "BUILDING"},
            "warrant_id": warrant["warrant_id"],
            "expires_at": warrant["expires_at"],
        }
    except TempoError as exc:
        return {
            "ok": True,
            "readiness_state": state["business"]["state"],
            "mvp_state": state["mvp"]["state"],
            "authorization_valid": False,
            "build_allowed": False,
            "authorization_reason": exc.reason_code,
        }
