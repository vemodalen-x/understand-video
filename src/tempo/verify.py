"""Subprocess verification with honest, tamper-evident machine receipts.

The verifier deliberately distinguishes three things that are easy to blur:

* a README-derived execution *plan* (never evidence of execution),
* a local subprocess receipt (local integrity only), and
* an actually-started, policy-constrained container execution.

No command is run through a shell.  Output bytes are hashed rather than copied
into receipts so a failing test cannot accidentally persist a secret.
"""
from __future__ import annotations

import mimetypes
import os
import platform
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable, Sequence
import uuid

from . import __version__
from .config import config_value, load_config
from .errors import CheckerFailure, PolicyBlock
from .ledger import Ledger
from .schema import validate_data
from .state import StateStore
from .util import (
    Workspace,
    atomic_write_json,
    canonical_relpath,
    isoformat_z,
    load_json,
    sha256_bytes,
    sha256_file,
    sha256_json,
)


_FENCE = re.compile(r"^\s*(`{3,}|~{3,})([^`]*)$")
_HEADING = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*#*\s*$")
_SHELL_LANGUAGES = {"", "bash", "console", "powershell", "ps1", "sh", "shell", "zsh"}


def _container_policy(workspace: Workspace) -> dict[str, Any]:
    config = load_config(workspace)
    consumer = "tempo.verify.readme_literal_plan"
    image = config_value(config, "verification.container.image", consumer)
    uid = config_value(config, "verification.container.uid", consumer)
    network = config_value(config, "verification.container.network", consumer)
    if not isinstance(image, str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9._/-]*:[A-Za-z0-9._-]+@sha256:[a-f0-9]{64}", image
    ):
        raise CheckerFailure("CONTAINER_IMAGE_INVALID", "Verification image must be digest-pinned")
    if not isinstance(uid, int) or isinstance(uid, bool) or uid <= 0:
        raise CheckerFailure("CONTAINER_UID_INVALID", "Verification container UID must be positive")
    if network not in {"none", "isolated", "default"}:
        raise CheckerFailure("CONTAINER_NETWORK_INVALID", "Unsupported container network policy")
    return {"image": image, "uid": uid, "network": network}


def _readme_blocks(text: str) -> dict[str, list[dict[str, Any]]]:
    """Extract fenced command blocks under second-level Setup and Run headings."""
    result: dict[str, list[dict[str, Any]]] = {"setup": [], "run": []}
    section: str | None = None
    fence: str | None = None
    language = ""
    captured: list[str] = []
    for line in text.splitlines():
        if fence is None:
            heading = _HEADING.match(line)
            if heading:
                depth = len(heading.group(1))
                title = re.sub(r"[^a-z0-9]+", " ", heading.group(2).casefold()).strip()
                if depth <= 2:
                    if title in {"setup", "installation", "install"}:
                        section = "setup"
                    elif title in {"run", "quickstart", "quick start"}:
                        section = "run"
                    else:
                        section = None
                continue
            opening = _FENCE.match(line)
            if opening and section:
                fence = opening.group(1)[0] * len(opening.group(1))
                language = opening.group(2).strip().split(maxsplit=1)[0].casefold()
                captured = []
            continue

        if line.strip().startswith(fence):
            if language in _SHELL_LANGUAGES:
                raw = "\n".join(captured).strip()
                if raw:
                    result[section or "run"].append(
                        {
                            "language": language or "shell-unspecified",
                            "raw": raw,
                            "commands": [item for item in captured if item.strip()],
                        }
                    )
            fence = None
            language = ""
            captured = []
        else:
            captured.append(line)
    return result


def readme_literal_plan(workspace: Workspace) -> dict[str, Any]:
    """Return the literal README command plan without executing or endorsing it.

    The returned ``executed`` flag is intentionally always false.  Callers that
    need evidence must pass an explicit argv to :func:`run_verification`.
    """
    path = workspace.path("README.md")
    if not path.is_file():
        raise PolicyBlock("README_MISSING", "README.md is required for literal verification")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckerFailure("README_UNREADABLE", f"Cannot read README.md: {exc}") from exc
    blocks = _readme_blocks(text)
    missing = [name for name in ("setup", "run") if not blocks[name]]
    if missing:
        raise PolicyBlock(
            "README_COMMANDS_MISSING",
            "README must contain literal fenced commands under Setup and Run",
            details={"missing_sections": missing},
        )
    policy = _container_policy(workspace)
    return {
        "ok": True,
        "readme": "README.md",
        "readme_hash": sha256_file(path),
        "setup_blocks": blocks["setup"],
        "run_blocks": blocks["run"],
        "container": {
            **policy,
            "read_only_root": True,
            "capabilities": "drop_all",
            "no_new_privileges": True,
            "tmpfs": "/tmp:rw,noexec,nosuid,nodev,size=64m",
        },
        "executed": False,
        "provenance": "plan_only_not_a_verification_receipt",
    }


def _input_bindings(workspace: Workspace, paths: Iterable[str] | None) -> list[dict[str, str]]:
    selected = list(paths or ("config/tempo.config.json", "MANIFEST.json"))
    if paths is None and workspace.path("README.md").is_file():
        selected.append("README.md")
    bindings: list[dict[str, str]] = []
    for raw in sorted(set(selected)):
        relative = canonical_relpath(raw)
        path = workspace.path(relative)
        if not path.is_file():
            raise PolicyBlock(
                "VERIFICATION_INPUT_MISSING",
                f"Verification input is missing: {relative}",
                details={"artifact": relative},
            )
        bindings.append({"artifact_ref": relative, "hash": sha256_file(path)})
    if not bindings:
        raise PolicyBlock("VERIFICATION_INPUTS_EMPTY", "At least one hashed input is required")
    return bindings


def _workdir(workspace: Workspace, relative: str) -> tuple[Path, str]:
    if relative in ("", "."):
        return workspace.root, "."
    canonical = canonical_relpath(relative)
    path = workspace.path(canonical)
    if not path.is_dir():
        raise PolicyBlock("VERIFICATION_CWD_MISSING", f"Verification cwd is missing: {canonical}")
    return path, canonical


def _container_argv(
    workspace: Workspace,
    engine: str,
    inner_argv: Sequence[str],
    policy: dict[str, Any],
    receipt_cwd: str,
) -> list[str]:
    command = list(inner_argv)
    if command and Path(command[0]).name.casefold().startswith("python"):
        command[0] = "python"
    return [
        engine,
        "run",
        "--rm",
        "--network",
        str(policy["network"]),
        "--user",
        f"{policy['uid']}:{policy['uid']}",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--mount",
        f"type=bind,src={workspace.root},dst=/workspace,readonly",
        "--workdir",
        "/workspace" if receipt_cwd == "." else f"/workspace/{receipt_cwd}",
        str(policy["image"]),
        *command,
    ]


def _python_from_image(image: str) -> str:
    match = re.search(r"python:([0-9]+\.[0-9]+(?:\.[0-9]+)?)", image)
    return match.group(1) if match else platform.python_version()


def _normalized_result(raw_exit: int | None, timed_out: bool) -> tuple[int, str, str]:
    if timed_out or raw_exit is None:
        return 3, "checker_failure", "failed"
    if raw_exit == 0:
        return 0, "passed", "passed"
    if raw_exit == 2:
        return 2, "policy_block", "blocked"
    if raw_exit == 4:
        return 4, "warning", "warning"
    return 3, "checker_failure", "failed"


def _persist_receipt(
    workspace: Workspace,
    receipt: dict[str, Any],
    *,
    receipt_dir: str,
    actor: str,
    session: str,
) -> dict[str, Any]:
    validate_data(workspace, "receipt", receipt, policy_block=False)
    relative = (
        f"{canonical_relpath(receipt_dir).rstrip('/')}/{receipt['receipt_id']}.json"
    )
    destination = workspace.path(relative)
    atomic_write_json(destination, receipt)
    current_state = StateStore(workspace).read()["mvp"]["state"]
    reason_code = {
        "passed": "VERIFICATION_PASSED",
        "policy_block": "VERIFICATION_POLICY_BLOCK",
        "checker_failure": "VERIFICATION_CHECKER_FAILURE",
        "warning": "VERIFICATION_WARNING",
    }[receipt["outcome"]]
    Ledger(workspace).append(
        "verification_completed",
        actor=actor,
        session=session,
        relevant_ids={"receipt_id": receipt["receipt_id"]},
        artifact_hashes={relative: sha256_file(destination)},
        evidence_refs=[],
        reason_code=reason_code,
        resulting_state=current_state,
        details={
            "receipt_path": relative,
            "receipt_type": receipt["receipt_type"],
            "outcome": receipt["outcome"],
            "authoritative": receipt["provenance"]["authoritative"],
            "cost_amount": 0,
        },
    )
    return {**receipt, "receipt_path": relative}


def run_verification(
    workspace: Workspace,
    *,
    level: str = "all",
    argv: Sequence[str] | None = None,
    session: str = "local:verification",
    actor: str = "verifier:tempo.verify",
    receipt_type: str | None = None,
    subject_ref: str = "repository:TEMPO",
    cwd: str = ".",
    timeout_seconds: int | None = None,
    input_paths: Iterable[str] | None = None,
    require_container: bool = False,
    container: bool | None = None,
    ci_attestation_ref: str | None = None,
) -> dict[str, Any]:
    """Run one command and persist a schema-valid receipt for every outcome.

    Child return codes are normalized to TEMPO's stable ``0/2/3/4`` contract.
    A timeout or launch failure is a checker failure (3), not a policy denial.
    ``require_container=True`` requires Docker or Podman and runs the command with the
    digest, UID, network, read-only, capability, and privilege controls from
    configuration.  Merely requesting a container never changes provenance.
    """
    receipt_types = {"focused": "focused_tests", "all": "whole_suite", "judge": "judge_demo"}
    if ci_attestation_ref is not None:
        raise PolicyBlock(
            "ATTESTATION_VERIFIER_UNAVAILABLE",
            "TEMPO cannot accept a CI attestation until a signature verifier and trust policy are configured",
        )
    if level not in receipt_types:
        raise PolicyBlock(
            "VERIFICATION_LEVEL_INVALID",
            f"Unknown verification level: {level}",
            details={"allowed": sorted(receipt_types)},
        )
    if level == "judge" and argv is None:
        raise PolicyBlock(
            "JUDGE_COMMAND_REQUIRED",
            "Judge verification requires an explicit demo command or write_receipt step evidence",
        )
    selected_receipt_type = receipt_type or receipt_types[level]
    if container is not None and require_container and container != require_container:
        raise CheckerFailure("CONTAINER_MODE_CONFLICT", "Conflicting container mode arguments")
    use_container = require_container if container is None else container
    config = load_config(workspace)
    configured_timeout = config_value(
        config,
        "verification.whole_suite_timeout_seconds",
        "tempo.verify.run_verification",
    )
    receipt_dir = config_value(
        config,
        "verification.receipt_dir",
        "tempo.verify.run_verification",
    )
    if not isinstance(configured_timeout, int) or isinstance(configured_timeout, bool):
        raise CheckerFailure("VERIFICATION_TIMEOUT_INVALID", "Configured timeout must be an integer")
    timeout = configured_timeout if timeout_seconds is None else timeout_seconds
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise CheckerFailure("VERIFICATION_TIMEOUT_INVALID", "Timeout must be a positive integer")
    if timeout > configured_timeout:
        raise PolicyBlock(
            "VERIFICATION_TIMEOUT_EXCEEDS_POLICY",
            "Requested timeout exceeds the configured whole-suite ceiling",
            details={"requested": timeout, "maximum": configured_timeout},
        )
    if not isinstance(receipt_dir, str):
        raise CheckerFailure("RECEIPT_DIR_INVALID", "Receipt directory must be repository-relative")

    if argv is None and level == "focused":
        default_argv: Sequence[str] = (
            sys.executable,
            "-m",
            "unittest",
            "tests.test_readiness",
            "tests.test_authorization",
            "tests.test_verify",
            "tests.test_verdict",
        )
    else:
        default_argv = (
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
        )
    selected_argv = default_argv if argv is None else argv
    inner = [str(item) for item in selected_argv]
    if not inner or any(not item or len(item) > 2000 for item in inner):
        raise CheckerFailure("VERIFICATION_COMMAND_INVALID", "Verification argv is invalid")
    run_cwd, receipt_cwd = _workdir(workspace, cwd)
    input_hashes = _input_bindings(workspace, input_paths)

    policy: dict[str, Any] | None = None
    engine: str | None = None
    executed_argv = inner
    if use_container:
        policy = _container_policy(workspace)
        engine = shutil.which("docker") or shutil.which("podman")
        if engine:
            executed_argv = _container_argv(workspace, engine, inner, policy, receipt_cwd)
        else:
            executed_argv = ["container-runtime-unavailable", *inner]

    started_at = isoformat_z()
    started_clock = time.monotonic()
    stdout = b""
    stderr = b""
    raw_exit: int | None = None
    timed_out = False
    launch_error: str | None = None
    if use_container and engine is None:
        launch_error = "Docker or Podman was not found; no container was started"
    else:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            completed = subprocess.run(
                executed_argv,
                cwd=run_cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
                shell=False,
            )
            raw_exit = completed.returncode
            stdout = completed.stdout or b""
            stderr = completed.stderr or b""
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = exc.stdout if isinstance(exc.stdout, bytes) else (exc.stdout or "").encode()
            stderr = exc.stderr if isinstance(exc.stderr, bytes) else (exc.stderr or "").encode()
        except OSError as exc:
            launch_error = f"{type(exc).__name__}: {exc}"

    elapsed_ms = max(0, int((time.monotonic() - started_clock) * 1000))
    finished_at = isoformat_z()
    exit_code, outcome, check_status = _normalized_result(raw_exit, timed_out)
    if launch_error is not None:
        exit_code, outcome, check_status = 3, "checker_failure", "failed"
    output_bytes = stdout + b"\0" + stderr
    output_hash = sha256_bytes(output_bytes)
    if timed_out:
        detail = f"timed out after {timeout}s; captured_bytes={len(output_bytes) - 1}; output_hash={output_hash}"
    elif launch_error:
        detail = f"command not started: {launch_error}; output_hash={output_hash}"
    else:
        detail = (
            f"raw_exit_code={raw_exit}; captured_bytes={len(output_bytes) - 1}; "
            f"output_hash={output_hash}"
        )

    actual_container = bool(use_container and engine and not timed_out and raw_exit != 125)
    if actual_container and policy is not None:
        environment_record = {
            "os": "linux/container",
            "python_version": _python_from_image(str(policy["image"])),
            "container_image": policy["image"],
            "uid": policy["uid"],
            "network": policy["network"],
        }
        provenance = {
            "kind": "container",
            "trust": "isolated_execution",
            "authoritative": False,
            "attestation_ref": None,
        }
    else:
        environment_record = {
            "os": f"{platform.system()} {platform.release()}".strip(),
            "python_version": platform.python_version(),
            "container_image": None,
            "uid": None,
            "network": "unknown",
        }
        provenance = {
            "kind": "local_tool",
            "trust": "local_integrity_only",
            "authoritative": False,
            "attestation_ref": None,
        }

    receipt_id = f"R-{uuid.uuid4().hex.upper()}"
    receipt: dict[str, Any] = {
        "receipt_id": receipt_id,
        "receipt_type": selected_receipt_type,
        "subject_ref": subject_ref,
        "session": session,
        "generated_at": finished_at,
        "started_at": started_at,
        "finished_at": finished_at,
        "generator": {"name": "tempo.verify", "version": __version__, "actor": actor},
        "command": {"argv": executed_argv, "cwd": receipt_cwd, "timeout_seconds": timeout},
        "exit_code": exit_code,
        "outcome": outcome,
        "checks": [
            {
                "check_id": f"CHK-{uuid.uuid4().hex[:16].upper()}",
                "name": "isolated command" if actual_container else "local command",
                "status": check_status,
                "duration_ms": elapsed_ms,
                "details": detail[:4000],
            }
        ],
        "input_hashes": input_hashes,
        "artifacts": [],
        "environment": environment_record,
        "provenance": provenance,
        "receipt_hash": "sha256:" + "0" * 64,
    }
    receipt["receipt_hash"] = sha256_json(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )
    return _persist_receipt(
        workspace,
        receipt,
        receipt_dir=receipt_dir,
        actor=actor,
        session=session,
    )


def write_receipt(
    workspace: Workspace,
    *,
    receipt_type: str,
    subject_ref: str,
    session: str,
    command_argv: Sequence[str],
    checks: Sequence[dict[str, Any]],
    exit_code: int = 0,
    actor: str = "verifier:tempo.demo",
    input_paths: Iterable[str] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    environment: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
    artifacts: Iterable[str | dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Persist deterministic step results without launching another command.

    This is intended for a demo runner that has already executed each supplied
    check.  Its defaults are deliberately local and non-authoritative.  Artifact
    hashes and sizes are always recomputed from repository bytes; caller-supplied
    hash claims are ignored.
    """
    outcome_for_exit = {
        0: "passed",
        2: "policy_block",
        3: "checker_failure",
        4: "warning",
    }
    if exit_code not in outcome_for_exit:
        raise CheckerFailure("RECEIPT_EXIT_CODE_INVALID", "Receipt exit code must be 0, 2, 3, or 4")
    argv = [str(item) for item in command_argv]
    if not argv or any(not item or len(item) > 2000 for item in argv):
        raise CheckerFailure("VERIFICATION_COMMAND_INVALID", "Receipt command argv is invalid")
    if not checks:
        raise CheckerFailure("RECEIPT_CHECKS_EMPTY", "At least one executed check is required")
    normalized_checks: list[dict[str, Any]] = []
    allowed_status = {"passed", "failed", "blocked", "warning", "skipped"}
    for item in checks:
        if not isinstance(item, dict):
            raise CheckerFailure("RECEIPT_CHECK_INVALID", "Every receipt check must be an object")
        status = item.get("status", "passed")
        if status not in allowed_status:
            raise CheckerFailure("RECEIPT_CHECK_INVALID", f"Unsupported check status: {status}")
        duration = item.get("duration_ms", 0)
        if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
            raise CheckerFailure("RECEIPT_CHECK_INVALID", "Check duration_ms must be non-negative")
        name = str(item.get("name") or item.get("step") or "deterministic demo step")
        details = str(item.get("details") or item.get("message") or "check completed")
        normalized_checks.append(
            {
                "check_id": str(item.get("check_id") or f"CHK-{uuid.uuid4().hex[:16].upper()}"),
                "name": name[:500],
                "status": status,
                "duration_ms": duration,
                "details": details[:4000],
            }
        )
    statuses = {item["status"] for item in normalized_checks}
    if exit_code == 0 and statuses.intersection({"failed", "blocked", "warning"}):
        raise CheckerFailure(
            "RECEIPT_OUTCOME_INCONSISTENT",
            "A passing receipt cannot contain failed, blocked, or warning checks",
        )
    if exit_code == 2 and not statuses.intersection({"blocked", "failed"}):
        raise CheckerFailure("RECEIPT_OUTCOME_INCONSISTENT", "Policy-block receipt needs a blocked check")
    if exit_code == 3 and "failed" not in statuses:
        raise CheckerFailure("RECEIPT_OUTCOME_INCONSISTENT", "Checker-failure receipt needs a failed check")
    if exit_code == 4 and "warning" not in statuses:
        raise CheckerFailure("RECEIPT_OUTCOME_INCONSISTENT", "Warning receipt needs a warning check")

    config = load_config(workspace)
    timeout = config_value(
        config,
        "verification.whole_suite_timeout_seconds",
        "tempo.verify.run_verification",
    )
    receipt_dir = config_value(
        config,
        "verification.receipt_dir",
        "tempo.verify.run_verification",
    )
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise CheckerFailure("VERIFICATION_TIMEOUT_INVALID", "Configured timeout must be positive")
    if not isinstance(receipt_dir, str):
        raise CheckerFailure("RECEIPT_DIR_INVALID", "Receipt directory must be repository-relative")
    now = isoformat_z()
    start = started_at or now
    finish = finished_at or now
    local_environment = {
        "os": f"{platform.system()} {platform.release()}".strip(),
        "python_version": platform.python_version(),
        "container_image": None,
        "uid": None,
        "network": "unknown",
    }
    local_provenance = {
        "kind": "local_tool",
        "trust": "local_integrity_only",
        "authoritative": False,
        "attestation_ref": None,
    }
    if environment is not None and environment != local_environment:
        raise PolicyBlock(
            "CALLER_ENVIRONMENT_CLAIM_FORBIDDEN",
            "write_receipt records the current local host and cannot accept caller-supplied environment claims",
        )
    if provenance is not None and provenance != local_provenance:
        raise PolicyBlock(
            "CALLER_PROVENANCE_CLAIM_FORBIDDEN",
            "write_receipt is local-integrity-only and cannot accept caller-supplied trust or attestation claims",
        )
    environment_record = local_environment
    provenance_record = local_provenance

    artifact_records: list[dict[str, Any]] = []
    for artifact in artifacts or ():
        raw_path = artifact.get("path") if isinstance(artifact, dict) else artifact
        relative = canonical_relpath(str(raw_path))
        path = workspace.path(relative)
        if not path.is_file():
            raise PolicyBlock("VERIFICATION_ARTIFACT_MISSING", f"Receipt artifact is missing: {relative}")
        media_type = (
            artifact.get("media_type") if isinstance(artifact, dict) else None
        ) or mimetypes.guess_type(relative)[0] or "application/octet-stream"
        artifact_records.append(
            {
                "path": relative,
                "hash": sha256_file(path),
                "media_type": media_type,
                "size_bytes": path.stat().st_size,
            }
        )

    receipt: dict[str, Any] = {
        "receipt_id": f"R-{uuid.uuid4().hex.upper()}",
        "receipt_type": receipt_type,
        "subject_ref": subject_ref,
        "session": session,
        "generated_at": finish,
        "started_at": start,
        "finished_at": finish,
        "generator": {"name": "tempo.verify", "version": __version__, "actor": actor},
        "command": {"argv": argv, "cwd": ".", "timeout_seconds": timeout},
        "exit_code": exit_code,
        "outcome": outcome_for_exit[exit_code],
        "checks": normalized_checks,
        "input_hashes": _input_bindings(workspace, input_paths),
        "artifacts": artifact_records,
        "environment": environment_record,
        "provenance": provenance_record,
        "receipt_hash": "sha256:" + "0" * 64,
    }
    receipt["receipt_hash"] = sha256_json(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )
    return _persist_receipt(
        workspace,
        receipt,
        receipt_dir=receipt_dir,
        actor=actor,
        session=session,
    )


def verify_receipt(
    workspace: Workspace,
    receipt_path: str,
    *,
    check_current_inputs: bool = False,
) -> dict[str, Any]:
    """Verify schema and receipt-body hash, optionally checking current inputs."""
    relative = canonical_relpath(receipt_path)
    value = load_json(workspace.path(relative))
    if not isinstance(value, dict):
        raise PolicyBlock("RECEIPT_INVALID", "Verification receipt is not a JSON object")
    validate_data(workspace, "receipt", value)
    expected = sha256_json({key: item for key, item in value.items() if key != "receipt_hash"})
    if value.get("receipt_hash") != expected:
        raise PolicyBlock(
            "RECEIPT_TAMPERED",
            f"Receipt body hash does not match: {relative}",
            details={"expected": expected, "actual": value.get("receipt_hash")},
        )
    if value["provenance"]["authoritative"]:
        raise PolicyBlock(
            "RECEIPT_ATTESTATION_UNVERIFIED",
            "Authoritative receipts require a configured signature and trust-policy verifier",
        )
    drift: list[dict[str, str | None]] = []
    if check_current_inputs:
        for binding in value["input_hashes"]:
            artifact = binding["artifact_ref"]
            try:
                path = workspace.path(canonical_relpath(artifact))
            except PolicyBlock:
                drift.append({"artifact": artifact, "expected": binding["hash"], "actual": None})
                continue
            actual = sha256_file(path) if path.is_file() else None
            if actual != binding["hash"]:
                drift.append({"artifact": artifact, "expected": binding["hash"], "actual": actual})
    return {
        "ok": not drift,
        "receipt_id": value["receipt_id"],
        "receipt_hash": expected,
        "outcome": value["outcome"],
        "authoritative": value["provenance"]["authoritative"],
        "input_drift": drift,
    }
