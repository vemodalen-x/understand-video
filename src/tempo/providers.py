"""Vendor-neutral commercial-planning proposal adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .errors import PolicyBlock
from .ledger import Ledger
from .schema import validate_data
from .util import Workspace, atomic_write_json, sha256_json


class CommercialPlanningProvider(ABC):
    """Normalize untrusted provider output into TEMPO's strict proposal contract."""

    name: str

    @abstractmethod
    def normalize(self, payload: Any) -> dict[str, Any]:
        raise NotImplementedError


class JsonCommercialPlanningProvider(CommercialPlanningProvider):
    """Pass through an already normalized JSON proposal without inventing fields."""

    name = "json"

    def normalize(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise PolicyBlock("PROVIDER_OUTPUT_INVALID", "Provider output must be a JSON object")
        forbidden = {
            "authorization_warrant",
            "warrant",
            "signed_charter",
            "human_signature",
            "build_allowed",
        }.intersection(payload)
        if forbidden:
            raise PolicyBlock(
                "COMMERCIAL_PROVIDER_CANNOT_AUTHORIZE",
                "Commercial provider output contains authority-bearing fields",
                details={"forbidden_fields": sorted(forbidden)},
            )
        return deepcopy(payload)


PROVIDERS: dict[str, type[CommercialPlanningProvider]] = {
    JsonCommercialPlanningProvider.name: JsonCommercialPlanningProvider,
}


def import_proposal(
    workspace: Workspace,
    provider_name: str,
    input_path: Path,
    *,
    actor: str,
    session: str,
) -> dict[str, Any]:
    provider_type = PROVIDERS.get(provider_name)
    if provider_type is None:
        raise PolicyBlock(
            "PROVIDER_UNKNOWN",
            f"Unknown commercial provider: {provider_name}",
            details={"available": sorted(PROVIDERS)},
        )
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PolicyBlock("PROVIDER_INPUT_MISSING", f"Provider input not found: {input_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyBlock("PROVIDER_INPUT_INVALID", f"Cannot read provider input: {exc}") from exc

    normalized = provider_type().normalize(payload)
    validate_data(workspace, "commercial-proposal", normalized)
    digest = sha256_json(normalized)
    proposal_id = normalized["proposal_id"]
    destination = workspace.path(f"plan/proposals/commercial-agent/{proposal_id}.json")
    if destination.exists():
        existing = json.loads(destination.read_text(encoding="utf-8"))
        if sha256_json(existing) != digest:
            raise PolicyBlock(
                "PROPOSAL_ID_IMMUTABLE",
                f"Proposal ID {proposal_id} already exists with different content",
            )
        return {
            "ok": True,
            "proposal_id": proposal_id,
            "path": workspace.relative(destination),
            "proposal_hash": digest,
            "idempotent": True,
        }

    atomic_write_json(destination, normalized)
    Ledger(workspace).append(
        "commercial_proposal_imported",
        actor=actor,
        session=session,
        relevant_ids={"proposal_id": proposal_id, "opportunity_id": normalized["opportunity_ref"]},
        artifact_hashes={workspace.relative(destination): digest},
        evidence_refs=normalized.get("evidence_refs", []) + normalized.get("counterevidence_refs", []),
        reason_code="PROPOSAL_SCHEMA_VALID",
        resulting_state="VALIDATING",
        details={"provider": provider_name, "recommendation_is_advisory": True},
    )
    return {
        "ok": True,
        "proposal_id": proposal_id,
        "path": workspace.relative(destination),
        "proposal_hash": digest,
        "idempotent": False,
        "authorization_created": False,
    }
