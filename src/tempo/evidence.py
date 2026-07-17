"""Immutable evidence storage, provenance/freshness validation, and manifest chain."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any

from .errors import CheckerFailure, PolicyBlock
from .ledger import Ledger, ZERO_HASH, _FileLock
from .schema import validate_data
from .util import (
    Workspace,
    atomic_write_json,
    canonical_json_bytes,
    isoformat_z,
    load_json,
    parse_datetime,
    sha256_bytes,
    sha256_file,
    sha256_json,
    utc_now,
)


def _manifest_entry_hash(entry: dict[str, Any]) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_hash"}
    return sha256_bytes(canonical_json_bytes(body))


def read_manifest(workspace: Workspace) -> list[dict[str, Any]]:
    path = workspace.path("plan/evidence/manifest.jsonl")
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CheckerFailure("EVIDENCE_MANIFEST_UNREADABLE", f"Cannot read evidence manifest: {exc}") from exc
    result: list[dict[str, Any]] = []
    previous = ZERO_HASH
    for sequence, line in enumerate(lines, start=1):
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PolicyBlock("EVIDENCE_MANIFEST_BROKEN", f"Invalid manifest line {sequence}") from exc
        expected_sequence = len(result) + 1
        if (
            entry.get("sequence") != expected_sequence
            or entry.get("previous_hash") != previous
            or entry.get("entry_hash") != _manifest_entry_hash(entry)
        ):
            raise PolicyBlock(
                "EVIDENCE_MANIFEST_BROKEN",
                f"Evidence manifest integrity failed at sequence {expected_sequence}",
            )
        result.append(entry)
        previous = entry["entry_hash"]
    return result


def _append_manifest(workspace: Workspace, evidence_id: str, relative: str, digest: str) -> dict[str, Any]:
    path = workspace.path("plan/evidence/manifest.jsonl")
    entries = read_manifest(workspace)
    if any(entry["evidence_id"] == evidence_id for entry in entries):
        raise PolicyBlock("EVIDENCE_IMMUTABLE", f"Evidence ID already exists: {evidence_id}")
    entry = {
        "sequence": len(entries) + 1,
        "evidence_id": evidence_id,
        "path": relative,
        "file_hash": digest,
        "recorded_at": isoformat_z(),
        "previous_hash": entries[-1]["entry_hash"] if entries else ZERO_HASH,
    }
    entry["entry_hash"] = _manifest_entry_hash(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    with path.open("ab") as stream:
        stream.write(line.encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    return entry


def add_evidence(
    workspace: Workspace,
    input_path: Path,
    *,
    actor: str,
    session: str,
) -> dict[str, Any]:
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PolicyBlock("EVIDENCE_INPUT_MISSING", f"Evidence input not found: {input_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyBlock("EVIDENCE_INPUT_INVALID", f"Cannot read evidence input: {exc}") from exc
    validate_data(workspace, "evidence", payload)
    evidence_id = payload["evidence_id"]
    relative = f"plan/evidence/{evidence_id}.json"
    destination = workspace.path(relative)
    canonical_digest = sha256_json(payload)
    with _FileLock(workspace.path(".tempo/evidence.lock")):
        file_existed = destination.exists()
        if file_existed:
            existing = load_json(destination)
            if sha256_json(existing) != canonical_digest:
                raise PolicyBlock("EVIDENCE_IMMUTABLE", f"Evidence ID already exists: {evidence_id}")
        else:
            atomic_write_json(destination, payload)
        # atomic_write_json uses pretty JSON; bind the actual stored bytes.
        digest = sha256_file(destination)

        entries = read_manifest(workspace)
        existing_entries = [item for item in entries if item["evidence_id"] == evidence_id]
        if existing_entries:
            entry = existing_entries[0]
            if entry["path"] != relative or entry["file_hash"] != digest:
                raise PolicyBlock(
                    "EVIDENCE_MANIFEST_BROKEN",
                    f"Manifest binding differs for evidence ID: {evidence_id}",
                )
            manifest_existed = True
        else:
            entry = _append_manifest(workspace, evidence_id, relative, digest)
            manifest_existed = False

        ledger = Ledger(workspace)
        ledger.verify()
        ledger_existed = any(
            event.get("event_type") == "evidence_added"
            and event.get("relevant_ids", {}).get("evidence_id") == evidence_id
            for event in ledger.events()
        )
        if not ledger_existed:
            ledger.append(
                "evidence_added",
                actor=actor,
                session=session,
                relevant_ids={"evidence_id": evidence_id},
                artifact_hashes={relative: digest, "manifest_entry": entry["entry_hash"]},
                evidence_refs=[evidence_id],
                reason_code="EVIDENCE_RECORDED",
                resulting_state="VALIDATING",
                details={"stance": payload["stance"], "source_type": payload["source_type"]},
            )
    idempotent = file_existed and manifest_existed and ledger_existed
    return {
        "ok": True,
        "evidence_id": evidence_id,
        "path": relative,
        "file_hash": digest,
        "manifest_entry_hash": entry["entry_hash"],
        "idempotent": idempotent,
        "recovered_partial_write": (file_existed or manifest_existed) and not idempotent,
    }


def validate_evidence_item(
    workspace: Workspace,
    payload: dict[str, Any],
    *,
    now: Any = None,
) -> dict[str, Any]:
    validate_data(workspace, "evidence", payload)
    current = now or utc_now()
    freshness = payload["freshness"]
    expiry = freshness.get("expires_at")
    stale = bool(expiry and parse_datetime(expiry) <= current)
    provenance = payload["provenance"]
    model_generated = (
        payload["source_type"] == "model_generated_synthesis"
        or provenance["kind"] == "model_generated"
    )
    fixture = bool(provenance.get("is_fixture") or provenance["kind"] == "fixture")
    external = provenance["kind"] == "external" and not model_generated and not fixture
    return {
        "evidence_id": payload["evidence_id"],
        "valid": not stale,
        "stale": stale,
        "model_generated": model_generated,
        "fixture": fixture,
        "external": external,
        "counterevidence": payload["stance"] == "contradicts",
        "hypothesis_refs": payload["hypothesis_refs"],
    }


def validate_all_evidence(workspace: Workspace, *, now: Any = None) -> dict[str, Any]:
    entries = read_manifest(workspace)
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        evidence_id = entry["evidence_id"]
        if evidence_id in seen:
            raise PolicyBlock("EVIDENCE_MANIFEST_BROKEN", f"Duplicate evidence ID: {evidence_id}")
        seen.add(evidence_id)
        path = workspace.path(entry["path"])
        if not path.is_file() or sha256_file(path) != entry["file_hash"]:
            raise PolicyBlock(
                "EVIDENCE_IMMUTABLE",
                f"Evidence bytes no longer match manifest: {evidence_id}",
            )
        payload = load_json(path)
        if payload.get("evidence_id") != evidence_id:
            raise PolicyBlock("EVIDENCE_MANIFEST_BROKEN", f"Evidence ID/path mismatch: {evidence_id}")
        results.append(validate_evidence_item(workspace, payload, now=now))
    stale = [item["evidence_id"] for item in results if item["stale"]]
    if stale:
        raise PolicyBlock(
            "EVIDENCE_STALE",
            "One or more evidence items are stale",
            details={"evidence_refs": stale},
            next_action="Refresh or explicitly replace stale evidence in a new decision cycle.",
        )
    return {
        "ok": True,
        "count": len(results),
        "external_count": sum(1 for item in results if item["external"]),
        "model_generated_count": sum(1 for item in results if item["model_generated"]),
        "fixture_count": sum(1 for item in results if item["fixture"]),
        "counterevidence_refs": [item["evidence_id"] for item in results if item["counterevidence"]],
        "items": results,
    }


def evidence_payloads(workspace: Workspace) -> list[dict[str, Any]]:
    return [load_json(workspace.path(entry["path"])) for entry in read_manifest(workspace)]
