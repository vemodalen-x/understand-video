"""Explicit legal business-case and MVP state transitions."""
from __future__ import annotations

from copy import deepcopy
from typing import Any
import uuid

from .errors import PolicyBlock
from .util import Workspace, atomic_write_json, isoformat_z, load_json

BUSINESS_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"DISCOVERY"},
    "DISCOVERY": {"VALIDATING"},
    "VALIDATING": {"MVP_CANDIDATE", "EXPERIMENT_REQUIRED", "PIVOTED", "KILLED"},
    "MVP_CANDIDATE": {"VALIDATING", "MVP_AUTHORIZED", "EXPERIMENT_REQUIRED", "PIVOTED", "KILLED"},
    "MVP_AUTHORIZED": set(),
    "EXPERIMENT_REQUIRED": set(),
    "PIVOTED": set(),
    "KILLED": set(),
}

MVP_TRANSITIONS: dict[str, set[str]] = {
    "NOT_AUTHORIZED": {"AUTHORIZED"},
    "AUTHORIZED": {"BUILDING", "REVOKED", "EXPIRED"},
    "BUILDING": {"DEMO_GREEN", "REVOKED"},
    "DEMO_GREEN": {"PILOT_READY"},
    "PILOT_READY": {"VERDICT_RECORDED"},
    "VERDICT_RECORDED": set(),
    "REVOKED": set(),
    "EXPIRED": set(),
}

BUSINESS_TERMINAL = {name for name, targets in BUSINESS_TRANSITIONS.items() if not targets}


def initial_state() -> dict[str, Any]:
    now = isoformat_z()
    return {
        "version": 1,
        "business": {
            "cycle_id": f"BC-{uuid.uuid4().hex[:12].upper()}",
            "cycle_number": 1,
            "state": "DRAFT",
            "history": [{"state": "DRAFT", "at": now, "reason_code": "WORKSPACE_INITIALIZED"}],
        },
        "mvp": {
            "state": "NOT_AUTHORIZED",
            "history": [
                {"state": "NOT_AUTHORIZED", "at": now, "reason_code": "WORKSPACE_INITIALIZED"}
            ],
        },
        "updated_at": now,
    }


class StateStore:
    """Persist state history without rewriting terminal truth."""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.path = workspace.path(".tempo/state.json")

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return initial_state()
        value = load_json(self.path)
        if not isinstance(value, dict) or value.get("version") != 1:
            raise PolicyBlock("STATE_INVALID", "Unsupported or malformed state file")
        return value

    def initialize(self) -> dict[str, Any]:
        value = self.read()
        if not self.path.exists():
            atomic_write_json(self.path, value)
        return value

    def transition(self, machine: str, target: str, reason_code: str) -> dict[str, Any]:
        value = self.read()
        if machine not in ("business", "mvp"):
            raise PolicyBlock("STATE_MACHINE_UNKNOWN", f"Unknown state machine: {machine}")
        current = value[machine]["state"]
        transitions = BUSINESS_TRANSITIONS if machine == "business" else MVP_TRANSITIONS
        if target not in transitions.get(current, set()):
            raise PolicyBlock(
                "ILLEGAL_STATE_TRANSITION",
                f"Illegal {machine} transition: {current} -> {target}",
                details={"machine": machine, "current": current, "target": target},
            )
        now = isoformat_z()
        value[machine]["state"] = target
        value[machine]["history"].append(
            {"state": target, "at": now, "reason_code": reason_code}
        )
        value["updated_at"] = now
        atomic_write_json(self.path, value)
        return deepcopy(value)

    def new_business_cycle(self, reason_code: str) -> dict[str, Any]:
        """Open a new immutable decision cycle after a terminal outcome."""
        value = self.read()
        business = value["business"]
        if business["state"] not in BUSINESS_TERMINAL:
            raise PolicyBlock(
                "BUSINESS_CYCLE_STILL_ACTIVE",
                f"Cannot open a new cycle from {business['state']}",
            )
        archive = value.setdefault("business_cycle_history", [])
        archive.append(deepcopy(business))
        now = isoformat_z()
        value["business"] = {
            "cycle_id": f"BC-{uuid.uuid4().hex[:12].upper()}",
            "cycle_number": business["cycle_number"] + 1,
            "state": "DISCOVERY",
            "history": [{"state": "DISCOVERY", "at": now, "reason_code": reason_code}],
        }
        value["updated_at"] = now
        atomic_write_json(self.path, value)
        return deepcopy(value)

    def mark_exceptional(self, target: str, reason_code: str) -> dict[str, Any]:
        """Idempotently move MVP authority to REVOKED or EXPIRED."""
        if target not in ("REVOKED", "EXPIRED"):
            raise PolicyBlock("STATE_TARGET_INVALID", f"Exceptional target not allowed: {target}")
        value = self.read()
        current = value["mvp"]["state"]
        if current == target:
            return value
        if target not in MVP_TRANSITIONS.get(current, set()):
            raise PolicyBlock(
                "ILLEGAL_STATE_TRANSITION",
                f"Illegal mvp transition: {current} -> {target}",
            )
        return self.transition("mvp", target, reason_code)
