"""Containment, secret, destructive-command, freeze, and authorization guards."""
from __future__ import annotations

import fnmatch
import math
import os
from pathlib import Path
import re
from typing import Any

from .config import config_value, load_config
from .errors import CheckerFailure, PolicyBlock
from .util import Workspace, canonical_relpath, load_json
from .warrant import validate_warrant

SECRET_PREFIX = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_\-]{16,}"
    r"|AKIA[0-9A-Z]{16}|xoxb-[A-Za-z0-9\-]{10,}|glpat-[A-Za-z0-9\-_]{15,}"
    r"|AIza[0-9A-Za-z\-_]{30,})"
)
KEYWORDED = re.compile(
    r"(api[_-]?key|secret|password|token)[\"' ]*[:=][\"' ]*([A-Za-z0-9/_+=\-]+)",
    re.I,
)

DESTRUCTIVE: tuple[tuple[str, str], ...] = (
    (r"(^|[^\w])rm\b(?=[^|;&\n]*(?:-[a-zA-Z]*[rR]|--recursive))(?=[^|;&\n]*(?:-[a-zA-Z]*f|--force))", "recursive force delete"),
    (r"\b(wget|curl|fetch)\b[^|;&\n]*\|\s*(sh|bash|zsh|dash)\b", "pipe-to-shell install"),
    (r"\b(python3?|perl|ruby|node)\b\s+[^\n]*(-c|-e)\s[^\n]*(rmtree|unlink\(|rimraf|fs\.rm|rmSync|File\.delete)", "interpreter-escape delete"),
    (r"\brsync\b[^|;&\n]*--delete", "rsync --delete"),
    (r"git\s+branch\s+-D\b", "git branch -D"),
    (r"git\s+(stash\s+(drop|clear)|reset\s+--hard|clean\s+-[a-zA-Z]*f)", "git history/worktree destruction"),
    (r"git\s+push\b[^|;&\n]*?(--force\b(?!-with-lease)|(?<![\w-])-f\b)", "force push"),
    (r"git\s+(commit|push|merge)\s[^|;&\n]*--no-verify", "gate evasion --no-verify"),
    (r"core\.hooksPath", "gate evasion core.hooksPath"),
    (r"\bfind\s[^|;&\n]*-delete", "find -delete"),
    (r"(^|\s)(sudo|doas)\s", "privilege escalation"),
    (r"\bdd\b[^|;&\n]*of=/dev/", "dd onto device"),
    (r"\bmkfs(\.| )", "filesystem format"),
    (r"\b(Remove-Item|del|erase|rd|rmdir)\b[^\n]*(?:-Recurse|/s)", "recursive Windows delete"),
)

PREAUTH_WRITE_PREFIXES = (
    "plan/",
    "docs/",
    "tasks/",
    "samples/",
    "demo/",
    "submission/",
    ".tempo/",
)
SIGNER_OWNED = {
    "plan/decision-brief.json",
    "plan/mvp-charter.json",
    "plan/authorization-warrant.json",
    "plan/readiness-policy.json",
}
SIGNER_OWNED_CASEFOLDED = {path.casefold() for path in SIGNER_OWNED}
PREAUTH_WRITE_PREFIXES_CASEFOLDED = tuple(prefix.casefold() for prefix in PREAUTH_WRITE_PREFIXES)


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    return -sum(
        count / len(value) * math.log2(count / len(value))
        for count in (value.count(char) for char in set(value))
    )


def _secret_hit(text: str, entropy_min: float, keyword_min_length: int) -> str | None:
    if SECRET_PREFIX.search(text):
        return "vendor-prefix token"
    match = KEYWORDED.search(text)
    if (
        match
        and len(match.group(2)) >= keyword_min_length
        and _entropy(match.group(2)) > entropy_min
    ):
        return "keyworded high-entropy credential"
    return None


def _credential_reference(text: str, paths: list[str]) -> str | None:
    home = os.path.expanduser("~").replace("\\", "/")
    haystack = str(text).replace("\\", "/")
    for configured in paths:
        raw = str(configured).replace("\\", "/").rstrip("/")
        expanded = os.path.expanduser(raw).replace("\\", "/").rstrip("/")
        aliases = {raw, expanded}
        if expanded.startswith(home + "/"):
            suffix = expanded[len(home):]
            aliases.update({"~" + suffix, "$HOME" + suffix, "${HOME}" + suffix})
        if any(alias and alias in haystack for alias in aliases):
            return raw
    return None


def _freeze_active(workspace: Workspace) -> bool:
    active = False
    for relative in (".tempo/freeze.json", "governance/feature-freeze.json"):
        path = workspace.path(relative)
        if not path.exists():
            continue
        value = load_json(path)
        if not isinstance(value, dict) or not isinstance(value.get("active"), bool):
            raise CheckerFailure(
                "FREEZE_STATE_INVALID",
                f"Freeze state is malformed at {relative}; failing closed",
            )
        active = active or value["active"]
    return active


def _matches(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in globs)


def _implementation_guard(
    workspace: Workspace,
    path: str,
    event: dict[str, Any],
) -> None:
    policy_path = path.casefold()
    if policy_path in SIGNER_OWNED_CASEFOLDED and not str(event.get("actor", "")).startswith(("human:", "platform:")):
        raise PolicyBlock(
            "SIGNER_OWNED_ARTIFACT",
            f"Only a human/signer workflow may change {path}",
        )
    if policy_path.startswith(PREAUTH_WRITE_PREFIXES_CASEFOLDED):
        return
    warrant = validate_warrant(
        workspace,
        actor=str(event.get("actor", "agent:unknown")),
        session=str(event.get("session", "unknown")),
    )
    action = str(event.get("action", "implementation_write"))
    lane = event.get("lane")
    if action not in warrant["allowed_actions"]:
        raise PolicyBlock("ACTION_NOT_AUTHORIZED", f"Action is outside warrant: {action}")
    if lane not in warrant["allowed_lanes"]:
        raise PolicyBlock("LANE_NOT_AUTHORIZED", "Implementation event must name an authorized lane")
    if not _matches(path, warrant["allowed_scope"]):
        raise PolicyBlock("SCOPE_NOT_AUTHORIZED", f"Path is outside warrant scope: {path}")


def evaluate_event(workspace: Workspace, event: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one generic harness event without executing it."""
    if not isinstance(event, dict) or not isinstance(event.get("tool"), str):
        raise CheckerFailure("HOOK_EVENT_INVALID", "Hook event requires a string tool field")
    payload = event.get("input", {})
    if not isinstance(payload, dict):
        raise CheckerFailure("HOOK_EVENT_INVALID", "Hook event input must be an object")
    config = load_config(workspace)
    freeze_allow = config_value(config, "guards.freeze_allow", "tempo.guards.evaluate_event")
    credential_paths = config_value(config, "guards.credential_paths", "tempo.guards.evaluate_event")
    entropy_min = float(config_value(config, "guards.secret_entropy_min", "tempo.guards.evaluate_event"))
    keyword_min = int(config_value(config, "guards.secret_keyword_min_length", "tempo.guards.evaluate_event"))
    tool = event["tool"]

    if tool in ("write_file", "edit_file"):
        raw_path = payload.get("path")
        if not isinstance(raw_path, str):
            raise CheckerFailure("HOOK_EVENT_INVALID", "Write/edit event requires input.path")
        path = canonical_relpath(raw_path)
        workspace.path(path)  # containment and escaping-symlink check
        content = payload.get("content", payload.get("new_string", ""))
        if not isinstance(content, str):
            raise CheckerFailure("HOOK_EVENT_INVALID", "Write/edit content must be text")
        finding = _secret_hit(content, entropy_min, keyword_min)
        if finding:
            raise PolicyBlock("SECRET_DETECTED", f"{finding} in write to {path}")
        if _freeze_active(workspace) and not _matches(path, freeze_allow):
            raise PolicyBlock("FEATURE_FREEZE_ACTIVE", f"Path is not in the post-freeze allowlist: {path}")
        merged = {**event, "actor": event.get("actor", "agent:unknown")}
        _implementation_guard(workspace, path, merged)
        return {"ok": True, "allowed": True, "tool": tool, "path": path}

    if tool == "run_command":
        command = payload.get("command")
        if not isinstance(command, str):
            raise CheckerFailure("HOOK_EVENT_INVALID", "run_command event requires input.command")
        credential = _credential_reference(command, credential_paths)
        if credential:
            raise PolicyBlock("CREDENTIAL_PATH_BLOCKED", f"Command references protected credential root: {credential}")
        for pattern, reason in DESTRUCTIVE:
            if re.search(pattern, command, re.I):
                raise PolicyBlock("DESTRUCTIVE_COMMAND_BLOCKED", reason)
        finding = _secret_hit(command, entropy_min, keyword_min)
        if finding:
            raise PolicyBlock("SECRET_DETECTED", f"{finding} in command")
        if event.get("phase") == "implementation":
            warrant = validate_warrant(
                workspace,
                actor=str(event.get("actor", "agent:unknown")),
                session=str(event.get("session", "unknown")),
            )
            if event.get("action", "build") not in warrant["allowed_actions"]:
                raise PolicyBlock("ACTION_NOT_AUTHORIZED", "Implementation command is outside warrant")
        return {"ok": True, "allowed": True, "tool": tool}

    if tool == "read":
        raw_path = payload.get("path")
        if not isinstance(raw_path, str):
            raise CheckerFailure("HOOK_EVENT_INVALID", "read event requires input.path")
        credential = _credential_reference(raw_path, credential_paths)
        if credential:
            raise PolicyBlock("CREDENTIAL_PATH_BLOCKED", f"Read references protected credential root: {credential}")
        return {"ok": True, "allowed": True, "tool": tool}

    raise CheckerFailure("HOOK_TOOL_UNSUPPORTED", f"Unsupported hook tool: {tool}")
