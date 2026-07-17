"""Repository conformance, environment diagnostics, and honesty checks."""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from typing import Any

from .config import load_config, verify_config_consumers
from .errors import PolicyBlock
from .ledger import Ledger
from .util import Workspace, load_json, sha256_file


def _command_version(argv: list[str]) -> str | None:
    executable = shutil.which(argv[0])
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, *argv[1:]],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if output else executable


def selfcheck(workspace: Workspace) -> dict[str, Any]:
    """Fail when executable contracts and declared repository metadata diverge."""
    checks: list[dict[str, Any]] = []
    manifest = load_json(workspace.path("MANIFEST.json"))
    if not isinstance(manifest, dict):
        raise PolicyBlock("MANIFEST_INVALID", "MANIFEST.json must be an object")

    schema_count = 0
    for item in manifest.get("schemas", []):
        path = workspace.path(str(item.get("path", "")))
        if not path.is_file():
            raise PolicyBlock("MANIFEST_PATH_MISSING", f"Declared schema is missing: {path}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicyBlock("SCHEMA_INVALID", f"Cannot parse {path}: {exc}") from exc
        if not isinstance(value, dict) or value.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise PolicyBlock("SCHEMA_DRAFT_MISMATCH", f"Schema is not declared as Draft 2020-12: {path}")
        schema_count += 1
    checks.append({"name": "schemas", "status": "passed", "count": schema_count})

    config_result = verify_config_consumers(workspace)
    config = load_config(workspace)
    weights = config["readiness"]["weights"]
    floors = config["readiness"]["floors"]
    if set(weights) != set(floors) or abs(sum(float(value) for value in weights.values()) - 100.0) > 1e-9:
        raise PolicyBlock(
            "READINESS_POLICY_INVALID",
            "Readiness weight and floor dimensions must match and weights must sum to 100",
        )
    checks.append({"name": "config_consumers", "status": "passed", **config_result})

    missing_paths: list[str] = []
    dishonest_status: list[str] = []
    for mechanism in manifest.get("planned_mechanisms", []):
        expected = [str(value) for value in mechanism.get("expected_paths", [])]
        present = all(workspace.path(path).is_file() or workspace.path(path).is_dir() for path in expected)
        if not present:
            missing_paths.extend(path for path in expected if not workspace.path(path).exists())
        if mechanism.get("status") == "implemented" and not present:
            dishonest_status.append(str(mechanism.get("mechanism")))
    if dishonest_status:
        raise PolicyBlock(
            "IMPLEMENTATION_CLAIM_UNSUPPORTED",
            "An implemented mechanism is missing executable evidence",
            details={"mechanisms": dishonest_status, "missing_paths": sorted(set(missing_paths))},
        )
    checks.append(
        {
            "name": "manifest_paths",
            "status": "passed" if not missing_paths else "warning",
            "missing_paths": sorted(set(missing_paths)),
        }
    )

    ledger = Ledger(workspace).verify()
    checks.append({"name": "ledger", "status": "passed", **ledger})
    return {
        "ok": True,
        "outcome": "SELF_CHECK_PASSED",
        "checks": checks,
        "manifest_hash": sha256_file(workspace.path("MANIFEST.json")),
    }


def honesty_check(workspace: Workspace) -> dict[str, Any]:
    """Report claims that still require external evidence or human completion."""
    result = selfcheck(workspace)
    blockers: list[str] = []
    session_path = workspace.path("submission/session.json")
    if session_path.is_file():
        session = load_json(session_path)
        if session.get("status") != "confirmed_feedback_session":
            blockers.append("CONFIRM_FEEDBACK_SESSION_ID")
    else:
        blockers.append("FEEDBACK_SESSION_MISSING")
    video = workspace.path("submission/video-url.txt")
    if not video.is_file() or not video.read_text(encoding="utf-8").strip():
        blockers.append("PUBLIC_DEMO_VIDEO_MISSING")
    return {
        "ok": True,
        "outcome": "HONESTY_CHECK_COMPLETE",
        "kernel_conformance": result["outcome"],
        "external_submission_blockers": blockers,
        "claim": "No fixture is treated as external customer validation or platform attestation.",
    }


def doctor(workspace: Workspace) -> dict[str, Any]:
    """Return judge-facing environment facts without mutating the workspace."""
    return {
        "ok": True,
        "outcome": "ENVIRONMENT_INSPECTED",
        "workspace": str(workspace.root),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "python_supported": sys.version_info >= (3, 10),
        "git": _command_version(["git", "--version"]),
        "docker": _command_version(["docker", "--version"]),
        "podman": _command_version(["podman", "--version"]),
        "container_note": "CI can run the true-container README check, but receipts remain non-authoritative until signed-attestation verification exists.",
    }


def narrate(workspace: Workspace) -> dict[str, Any]:
    """Condense current governance truth into one decision-oriented status."""
    from .state import StateStore
    from .warrant import status

    state = StateStore(workspace).initialize()
    authority = status(workspace)
    business = state["business"]["state"]
    if authority["build_allowed"]:
        outcome = "BOUNDED_BUILD_ALLOWED"
        next_action = "Work only inside the active warrant and task scope."
    elif business == "EXPERIMENT_REQUIRED":
        outcome = "LEARN_BEFORE_BUILDING"
        next_action = "Run the cheapest sufficient experiment, then reassess."
    elif business == "MVP_CANDIDATE":
        outcome = "HUMAN_AUTHORIZATION_REQUIRED"
        next_action = "Review the signed charter and issue a fresh warrant from a real TTY."
    else:
        outcome = "BUSINESS_CASE_IN_PROGRESS"
        next_action = "Complete the current business evidence cycle."
    return {
        "ok": True,
        "outcome": outcome,
        "business_state": business,
        "mvp_state": state["mvp"]["state"],
        "build_allowed": authority["build_allowed"],
        "why": authority.get("authorization_reason", "ACTIVE_BOUNDED_WARRANT"),
        "next_action": next_action,
    }
