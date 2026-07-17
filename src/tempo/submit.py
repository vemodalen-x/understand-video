"""Offline, read-only Devpost submission readiness and schedule reporting.

This module never calls Devpost, GitHub, YouTube, or any other publishing API.
It only reports whether local artifacts contain the evidence needed for a human
to perform the final submission.
"""
from __future__ import annotations

import re
import subprocess
from typing import Any
from urllib.parse import urlparse

from .config import config_value, load_config
from .errors import CheckerFailure, EXIT_ALLOWED, EXIT_POLICY_BLOCK, PolicyBlock
from .util import Workspace, load_json
from .verify import verify_receipt


_YOUTUBE = re.compile(
    r"^https://(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)[A-Za-z0-9_-]+",
    re.IGNORECASE,
)


def _optional_json(workspace: Workspace, relative: str) -> dict[str, Any]:
    path = workspace.path(relative)
    if not path.is_file():
        return {}
    value = load_json(path)
    if not isinstance(value, dict):
        raise CheckerFailure("SUBMISSION_METADATA_INVALID", f"{relative} must be a JSON object")
    return value


def _optional_text(workspace: Workspace, relative: str) -> str:
    path = workspace.path(relative)
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckerFailure("SUBMISSION_ARTIFACT_UNREADABLE", f"Cannot read {relative}: {exc}") from exc


def _git_remote(workspace: Workspace) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace.root), "remote", "get-url", "origin"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
            text=True,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    evidence: str | None = None,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "passed" if passed else ("failed" if required else "warning"),
        "required": required,
        "message": message,
        "evidence": evidence,
    }


def _metadata_value(metadata: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in metadata:
            return metadata[name]
    return None


def _receipt_evidence(workspace: Workspace, receipt_type: str) -> tuple[bool, str | None]:
    candidates: list[Any] = []
    directory = workspace.path(".tempo/receipts")
    if directory.is_dir():
        candidates.extend(directory.glob("*.json"))
    demo_root = workspace.path(".tempo/demo-workspaces")
    if demo_root.is_dir():
        candidates.extend(demo_root.glob("*/.tempo/receipts/*.json"))
    for path in sorted(candidates, reverse=True):
        relative = workspace.relative(path)
        try:
            integrity = verify_receipt(workspace, relative)
            value = load_json(path)
        except (PolicyBlock, CheckerFailure):
            continue
        if value.get("receipt_type") == receipt_type and value.get("outcome") == "passed":
            return True, f"{relative} ({integrity['receipt_hash']})"
    return False, None


def _milestone_evidence(workspace: Workspace, name: str) -> tuple[bool, list[str]]:
    files = lambda *items: all(workspace.path(item).is_file() for item in items)
    if name == "business_framing_complete":
        root_evidence = ["plan/opportunity.json", "plan/business-model.json", "plan/hypotheses.json"]
        sample_evidence = [
            "samples/business-mvp/opportunity.json",
            "samples/business-mvp/business-model.json",
            "samples/business-mvp/hypotheses.json",
        ]
        if files(*root_evidence):
            return True, root_evidence
        return files(*sample_evidence), sample_evidence
    if name == "readiness_assessment":
        evidence = [".tempo/assessments/latest.json"]
        if files(*evidence):
            return True, evidence
        matches = sorted(
            workspace.path(".tempo/demo-workspaces").glob("*/.tempo/assessments/latest.json"),
            reverse=True,
        )
        return bool(matches), [workspace.relative(matches[0])] if matches else evidence
    if name == "mvp_authorized_or_rejected":
        relative = ".tempo/assessments/latest.json"
        candidates = [workspace.path(relative)]
        candidates.extend(
            sorted(
                workspace.path(".tempo/demo-workspaces").glob("*/.tempo/assessments/latest.json"),
                reverse=True,
            )
        )
        selected = next((path for path in candidates if path.is_file()), None)
        assessment = load_json(selected) if selected is not None else {}
        if assessment and not isinstance(assessment, dict):
            raise CheckerFailure("SCHEDULE_EVIDENCE_INVALID", "Readiness assessment must be an object")
        decided = assessment.get("primary_outcome") in {
            "MVP_AUTHORIZED",
            "EXPERIMENT_REQUIRED",
            "PIVOT_REQUIRED",
            "KILL_RECOMMENDED",
            "BLOCKED_INVALID_INPUT",
        }
        return decided, [workspace.relative(selected)] if selected is not None else [relative]
    if name == "runnable_skeleton":
        evidence = ["bin/tempo", "src/tempo/cli.py", "pyproject.toml"]
        return files(*evidence), evidence
    if name == "happy_path":
        sample = workspace.path("samples/business-mvp")
        evidence = ["samples/business-mvp/", "src/tempo/demo.py"]
        return sample.is_dir() and any(path.is_file() for path in sample.rglob("*")) and files("src/tempo/demo.py"), evidence
    if name == "de_mock":
        tests = workspace.path("tests")
        evidence = ["tests/", "src/tempo/providers.py", "src/tempo/verify.py"]
        return tests.is_dir() and any(tests.glob("test_*.py")) and files("src/tempo/providers.py", "src/tempo/verify.py"), evidence
    if name == "coherent_product":
        evidence = ["README.md", "SECURITY.md", "LICENSE", "docs/adr/0002-work-productivity-positioning.md"]
        return files(*evidence), evidence
    if name == "feature_freeze":
        candidates = ["governance/feature-freeze.json", ".tempo/freeze.json"]
        selected = next((item for item in candidates if workspace.path(item).is_file()), None)
        if selected is None:
            return False, candidates
        value = load_json(workspace.path(selected))
        active = isinstance(value, dict) and value.get("active") is True
        return active, [selected]
    if name == "judge_runnable":
        passed, receipt = _receipt_evidence(workspace, "judge_demo")
        return passed, [receipt or ".tempo/receipts/<judge_demo>.json"]
    if name == "submission_filed":
        metadata = _optional_json(workspace, "submission/devpost.json")
        external = metadata.get("external_actions") if isinstance(metadata.get("external_actions"), dict) else {}
        submitted = metadata.get("submitted") is True or external.get("devpost_submitted") is True
        return submitted, ["submission/devpost.json#external_actions.devpost_submitted"]
    return False, ["no deterministic evidence rule registered"]


def schedule_status(workspace: Workspace) -> dict[str, Any]:
    """Infer milestone progress from local artifacts; never mark a milestone itself."""
    config = load_config(workspace)
    milestones = config_value(config, "schedule.milestones", "tempo.submit.schedule_status")
    if not isinstance(milestones, list) or not milestones:
        raise CheckerFailure("SCHEDULE_INVALID", "schedule.milestones must be a non-empty list")
    reported: list[dict[str, Any]] = []
    previous_percent = -1
    contiguous_percent = 0
    contiguous = True
    for item in milestones:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise CheckerFailure("SCHEDULE_INVALID", "Every milestone requires a name")
        percent = item.get("percent")
        if not isinstance(percent, (int, float)) or isinstance(percent, bool) or not 0 <= percent <= 100:
            raise CheckerFailure("SCHEDULE_INVALID", f"Invalid percent for {item['name']}")
        if percent <= previous_percent:
            raise CheckerFailure("SCHEDULE_INVALID", "Milestone percentages must increase")
        previous_percent = percent
        evidenced, evidence = _milestone_evidence(workspace, item["name"])
        if contiguous and evidenced:
            contiguous_percent = percent
        else:
            contiguous = False
        reported.append(
            {
                "name": item["name"],
                "percent": percent,
                "status": "evidenced" if evidenced else "not_evidenced",
                "evidence": evidence,
            }
        )
    next_item = next((item for item in reported if item["status"] != "evidenced"), None)
    return {
        "ok": True,
        "current_percent": contiguous_percent,
        "basis": "contiguous_locally_evidenced_milestones",
        "next_milestone": next_item["name"] if next_item else None,
        "milestones": reported,
        "side_effects": "none",
    }


def submission_status(workspace: Workspace) -> dict[str, Any]:
    """Evaluate local submission evidence without publishing or changing state."""
    config = load_config(workspace)
    track = config_value(config, "project.track", "tempo.submit.submission_status")
    metadata = _optional_json(workspace, "submission/devpost.json")
    session = _optional_json(workspace, "submission/session.json")
    readme = _optional_text(workspace, "README.md")
    project = metadata.get("project") if isinstance(metadata.get("project"), dict) else {}
    openai_usage = metadata.get("openai_usage") if isinstance(metadata.get("openai_usage"), dict) else {}
    feedback = metadata.get("feedback_session") if isinstance(metadata.get("feedback_session"), dict) else {}
    external_actions = metadata.get("external_actions") if isinstance(metadata.get("external_actions"), dict) else {}
    description_path = (
        _metadata_value(metadata, "description_path")
        or _metadata_value(project, "description_path", "description_file")
        or "submission/project-description.md"
    )
    description = _optional_text(workspace, str(description_path))
    license_text = _optional_text(workspace, "LICENSE")
    video = metadata.get("video") if isinstance(metadata.get("video"), dict) else {
        "url": project.get("video_url"),
        "duration_seconds": project.get("video_duration_seconds"),
        "has_audio": project.get("video_has_audio"),
        "visibility": project.get("video_visibility"),
    }
    repository = metadata.get("repository") if isinstance(metadata.get("repository"), dict) else {
        "url": project.get("repository_url"),
        "visibility": project.get("repository_visibility"),
        "judge_access_confirmed": project.get("judge_access_confirmed"),
    }
    remote = repository.get("url") or _metadata_value(metadata, "repository_url") or _git_remote(workspace)
    metadata_track = _metadata_value(metadata, "track", "category") or project.get("category")
    title = _metadata_value(metadata, "title", "project_title") or _metadata_value(project, "name", "title")

    setup_heading = bool(re.search(r"(?im)^##\s+(?:setup|installation|install)\s*$", readme))
    run_heading = bool(re.search(r"(?im)^##\s+(?:run|quickstart|quick start)\s*$", readme))
    readme_openai = "codex" in readme.casefold() and bool(
        re.search(r"gpt[\s-]*5\.?6", readme, re.IGNORECASE)
    )
    sample_dir = workspace.path("samples/business-mvp")
    sample_present = sample_dir.is_dir() and any(path.is_file() for path in sample_dir.rglob("*"))
    source_present = workspace.path("src/tempo/cli.py").is_file() and workspace.path("bin/tempo").is_file()

    duration = video.get("duration_seconds")
    video_ok = (
        isinstance(video.get("url"), str)
        and bool(_YOUTUBE.match(video["url"]))
        and isinstance(duration, (int, float))
        and not isinstance(duration, bool)
        and 0 < duration < 180
        and video.get("has_audio") is True
        and video.get("visibility") in {"public", "unlisted"}
    )
    visibility = repository.get("visibility")
    if visibility is None and external_actions.get("repository_published") is True:
        visibility = "public"
    parsed_remote = urlparse(str(remote)) if remote else None
    repository_link_ok = bool(
        parsed_remote
        and parsed_remote.scheme == "https"
        and parsed_remote.netloc
        and parsed_remote.path.strip("/")
    )
    repo_ok = repository_link_ok and (
        visibility == "public"
        or (visibility == "private" and repository.get("judge_access_confirmed") is True)
    )
    feedback_status = session.get("feedback_session_id_status") or session.get("status")
    feedback_id = session.get("feedback_session_id")
    if feedback.get("confirmed") is True and feedback.get("feedback_value"):
        feedback_id = feedback["feedback_value"]
        feedback_status = "confirmed"
    feedback_ok = bool(feedback_id) and feedback_status in {
        "confirmed",
        "feedback_confirmed",
        "confirmed_by_feedback_command",
    }

    checks = [
        _check(
            "REQ-TRACK",
            track == "Work & Productivity" and metadata_track == track,
            "Devpost category is explicitly Work & Productivity",
            evidence=f"config={track!r}, submission={metadata_track!r}",
        ),
        _check(
            "REQ-TITLE",
            isinstance(title, str) and 3 <= len(title.strip()) <= 100,
            "Project title is present in submission/devpost.json",
            evidence=str(title) if title else None,
        ),
        _check(
            "REQ-WORKING-PROJECT",
            source_present and sample_present,
            "Runnable CLI source and credential-free business-to-MVP sample are present",
            evidence="bin/tempo, src/tempo/cli.py, samples/business-mvp/",
        ),
        _check(
            "REQ-README-SETUP",
            bool(readme) and setup_heading,
            "README contains a Setup section",
            evidence="README.md",
        ),
        _check(
            "REQ-README-RUN",
            bool(readme) and run_heading,
            "README contains a Run or Quickstart section",
            evidence="README.md",
        ),
        _check(
            "REQ-README-SAMPLE",
            sample_present and "samples/business-mvp" in readme.replace("\\", "/"),
            "README points judges to the checked-in sample",
            evidence="README.md + samples/business-mvp/",
        ),
        _check(
            "REQ-OPENAI-USAGE",
            readme_openai,
            "README explains both Codex and GPT-5.6 usage",
            evidence="README.md",
        ),
        _check(
            "REQ-GPT-5.6-CONFIRMATION",
            openai_usage.get("gpt_5_6_usage_confirmed") is True,
            "Submission metadata confirms the truthful GPT-5.6 build-workflow claim",
            evidence="submission/devpost.json#openai_usage.gpt_5_6_usage_confirmed",
        ),
        _check(
            "REQ-DESCRIPTION",
            len(description.strip()) >= 200,
            "Submission project description is present and substantive",
            evidence=str(description_path),
        ),
        _check(
            "REQ-LICENSE",
            "MIT License" in license_text and "Permission is hereby granted" in license_text,
            "Repository includes a recognizable MIT license grant",
            evidence="LICENSE",
        ),
        _check(
            "REQ-REPOSITORY-ACCESS",
            repo_ok,
            "Repository URL and judge access mode are declared",
            evidence=(
                f"{remote} ({visibility})" if remote else "No origin or repository URL declared"
            ),
        ),
        _check(
            "REQ-VIDEO",
            video_ok,
            "Publicly accessible YouTube demo metadata declares audio and duration under 180 seconds",
            evidence=video.get("url") if isinstance(video.get("url"), str) else None,
        ),
        _check(
            "REQ-FEEDBACK-SESSION",
            feedback_ok,
            "The /feedback session ID is explicitly confirmed",
            evidence=f"{feedback_id or 'missing'} ({feedback_status or 'unconfirmed'})",
        ),
    ]
    failures = [item["check_id"] for item in checks if item["required"] and item["status"] == "failed"]
    warnings = [item["check_id"] for item in checks if item["status"] == "warning"]
    ready = not failures
    return {
        "ok": True,
        "ready": ready,
        "exit_code": EXIT_ALLOWED if ready else EXIT_POLICY_BLOCK,
        "reason_code": "SUBMISSION_READY" if ready else "SUBMISSION_NOT_READY",
        "track": track,
        "checks": checks,
        "failed_requirements": failures,
        "warnings": warnings,
        "schedule": schedule_status(workspace),
        "external_verification_note": (
            "URLs and access claims are read from local metadata and are not fetched by this offline checker."
        ),
        "side_effects": "none; no publish or submit operation exists in this module",
    }


def submit_check(workspace: Workspace, *, session: str = "local:submit-check") -> dict[str, Any]:
    """CLI-facing alias; ``session`` is reported but never used to mutate state."""
    result = submission_status(workspace)
    return {**result, "session": session}


def require_submission_ready(workspace: Workspace) -> dict[str, Any]:
    """Raise the stable policy-block exception when required evidence is absent."""
    result = submission_status(workspace)
    if not result["ready"]:
        raise PolicyBlock(
            "SUBMISSION_NOT_READY",
            "One or more required Devpost submission artifacts are missing or unconfirmed",
            details={"failed_requirements": result["failed_requirements"]},
            next_action="Resolve the failed local checks, then rerun submit-check.",
        )
    return result
