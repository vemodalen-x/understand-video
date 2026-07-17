"""Generate and human-sign the MVP charter without granting build authority."""
from __future__ import annotations

from copy import deepcopy
import sys
from typing import Any, TextIO

from .errors import PolicyBlock
from .evidence import read_manifest
from .ledger import Ledger
from .schema import validate_data
from .util import Workspace, atomic_write_json, isoformat_z, load_json, sha256_file


def generate_charter(
    workspace: Workspace,
    *,
    actor: str,
    session: str,
) -> dict[str, Any]:
    """Materialize a complete draft from a human-owned charter proposal."""
    source = workspace.path("plan/charter-proposal.json")
    if not source.is_file():
        raise PolicyBlock(
            "CHARTER_PROPOSAL_MISSING",
            "Create plan/charter-proposal.json before generating the charter",
            next_action="Complete the proposed scope, thresholds, budget, deadline, and exclusions.",
        )
    proposal = load_json(source)
    if not isinstance(proposal, dict):
        raise PolicyBlock("CHARTER_PROPOSAL_INVALID", "Charter proposal must be an object")
    destination = workspace.path("plan/mvp-charter.json")
    if destination.exists():
        existing = load_json(destination)
        if existing.get("state") == "signed":
            raise PolicyBlock(
                "SIGNED_CHARTER_IMMUTABLE",
                "A signed charter cannot be overwritten; create a new decision cycle/version",
            )
    charter = deepcopy(proposal)
    charter["state"] = "draft"
    charter["signed_by"] = None
    charter["signed_at"] = None
    charter["updated_at"] = isoformat_z()
    charter.setdefault("created_at", charter["updated_at"])
    manifest = workspace.path("plan/evidence/manifest.jsonl")
    entries = read_manifest(workspace)
    charter["evidence_baseline"] = {
        "manifest_ref": "plan/evidence/manifest.jsonl",
        "manifest_hash": sha256_file(manifest) if manifest.is_file() else "sha256:" + "0" * 64,
        "evidence_refs": [entry["evidence_id"] for entry in entries],
        "captured_at": isoformat_z(),
    }
    validate_data(workspace, "mvp-charter", charter)
    atomic_write_json(destination, charter)
    digest = sha256_file(destination)
    Ledger(workspace).append(
        "mvp_charter_drafted",
        actor=actor,
        session=session,
        relevant_ids={"mvp_id": charter["mvp_id"], "opportunity_id": charter["opportunity_ref"]},
        artifact_hashes={"plan/mvp-charter.json": digest},
        evidence_refs=charter["evidence_baseline"]["evidence_refs"],
        reason_code="CHARTER_GENERATED_FROM_PROPOSAL",
        resulting_state="MVP_CANDIDATE",
        details={"authority_granted": False},
    )
    return {
        "ok": True,
        "mvp_id": charter["mvp_id"],
        "state": "draft",
        "path": "plan/mvp-charter.json",
        "charter_hash": digest,
        "authority_granted": False,
    }

def sign_charter(
    workspace: Workspace,
    *,
    signer_ref: str,
    session: str,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    demo_fixture: bool = False,
) -> dict[str, Any]:
    """Sign a charter at a real TTY; the demo fixture path is internal-only."""
    if not signer_ref.startswith("human:") and not (demo_fixture and signer_ref.startswith("platform:demo")):
        raise PolicyBlock("SELF_AUTHORIZATION_FORBIDDEN", "Only a human or isolated demo signer may sign a charter")
    stdin = input_stream or sys.stdin
    stdout = output_stream or sys.stdout
    if not demo_fixture:
        if not stdin.isatty():
            raise PolicyBlock(
                "TTY_OR_ISOLATED_SIGNER_REQUIRED",
                "Signing a charter requires an interactive human terminal",
            )
    path = workspace.path("plan/mvp-charter.json")
    charter = load_json(path)
    validate_data(workspace, "mvp-charter", charter)
    if charter["state"] == "signed":
        return {
            "ok": True,
            "mvp_id": charter["mvp_id"],
            "state": "signed",
            "charter_hash": sha256_file(path),
            "idempotent": True,
        }
    phrase = f"SIGN {charter['mvp_id']}"
    if not demo_fixture:
        stdout.write(
            f"This signs the charter without granting build authority. Type {phrase!r} to continue: "
        )
        stdout.flush()
        if stdin.readline().strip() != phrase:
            raise PolicyBlock("HUMAN_CONFIRMATION_MISMATCH", "Charter signing confirmation did not match")
    charter["state"] = "signed"
    charter["signed_by"] = signer_ref
    charter["signed_at"] = isoformat_z()
    charter["updated_at"] = charter["signed_at"]
    validate_data(workspace, "mvp-charter", charter)
    atomic_write_json(path, charter)
    digest = sha256_file(path)
    Ledger(workspace).append(
        "mvp_charter_signed",
        actor=signer_ref,
        session=session,
        relevant_ids={"mvp_id": charter["mvp_id"]},
        artifact_hashes={"plan/mvp-charter.json": digest},
        evidence_refs=charter["evidence_baseline"]["evidence_refs"],
        reason_code="HUMAN_CHARTER_SIGNATURE" if not demo_fixture else "DEMO_FIXTURE_CHARTER_SIGNATURE",
        resulting_state="MVP_CANDIDATE",
        details={"authority_granted": False, "provenance": "tty_human" if not demo_fixture else "demo_fixture"},
    )
    return {
        "ok": True,
        "mvp_id": charter["mvp_id"],
        "state": "signed",
        "charter_hash": digest,
        "idempotent": False,
        "authority_granted": False,
    }
