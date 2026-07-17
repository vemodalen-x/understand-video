"""Runtime configuration with an exact leaf-to-consumer contract."""
from __future__ import annotations

from collections.abc import Mapping
import importlib
from typing import Any

from .errors import CheckerFailure, PolicyBlock
from .util import Workspace, load_json


# Every leaf in config/tempo.config.json must appear exactly once here. Consumers
# call config_value with their own qualified name; selfcheck also imports each
# callable so a prose-only or dangling control cannot pass.
CONFIG_CONSUMERS: dict[str, str] = {
    "project.track": "tempo.submit.submission_status",
    "readiness.weights": "tempo.readiness.assess",
    "readiness.floors": "tempo.readiness.assess",
    "readiness.aggregate_threshold": "tempo.readiness.assess",
    "evidence.external_source_types": "tempo.readiness.assess",
    "evidence.model_generated_type": "tempo.evidence.validate_evidence_item",
    "evidence.default_freshness_days": "tempo.cli.business_init",
    "warrant.protected_artifacts": "tempo.warrant.protected_hash_set",
    "warrant.max_ttl_hours": "tempo.warrant.authorize",
    "schedule.milestones": "tempo.submit.schedule_status",
    "guards.freeze_allow": "tempo.guards.evaluate_event",
    "guards.credential_paths": "tempo.guards.evaluate_event",
    "guards.secret_entropy_min": "tempo.guards.evaluate_event",
    "guards.secret_keyword_min_length": "tempo.guards.evaluate_event",
    "verification.whole_suite_timeout_seconds": "tempo.verify.run_verification",
    "verification.receipt_dir": "tempo.verify.run_verification",
    "verification.container.image": "tempo.verify.readme_literal_plan",
    "verification.container.uid": "tempo.verify.readme_literal_plan",
    "verification.container.network": "tempo.verify.readme_literal_plan",
}


def flatten_leaves(value: Any, prefix: str = "") -> dict[str, Any]:
    """Treat mappings as branches and arrays/scalars as consumed leaves."""
    # Some controls are intentionally consumed atomically as one mapping (for
    # example the complete readiness weight vector). Stop at a registered
    # parent instead of inventing child keys that no runtime consumer owns.
    if prefix and prefix in CONFIG_CONSUMERS:
        return {prefix: value}
    if not isinstance(value, Mapping):
        return {prefix: value}
    leaves: dict[str, Any] = {}
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(child, Mapping):
            leaves.update(flatten_leaves(child, path))
        else:
            leaves[path] = child
    return leaves


def load_config(workspace: Workspace) -> dict[str, Any]:
    config = load_json(workspace.path("config/tempo.config.json"))
    if not isinstance(config, dict):
        raise CheckerFailure("CONFIG_INVALID", "Runtime config must be a JSON object")
    return config


def config_value(config: Mapping[str, Any], path: str, consumer: str) -> Any:
    expected = CONFIG_CONSUMERS.get(path)
    if expected is None:
        raise CheckerFailure("UNCONSUMED_CONFIG_KEY", f"No consumer is registered for {path}")
    if expected != consumer:
        raise CheckerFailure(
            "CONFIG_CONSUMER_MISMATCH",
            f"{consumer} attempted to consume {path}; registered consumer is {expected}",
        )
    current: Any = config
    try:
        for part in path.split("."):
            current = current[part]
    except (KeyError, TypeError) as exc:
        raise CheckerFailure("CONFIG_KEY_MISSING", f"Runtime config is missing {path}") from exc
    return current


def verify_config_consumers(workspace: Workspace) -> dict[str, Any]:
    config = load_config(workspace)
    leaves = flatten_leaves(config)
    declared = set(CONFIG_CONSUMERS)
    present = set(leaves)
    if present != declared:
        raise PolicyBlock(
            "CONFIG_CONSUMER_SET_MISMATCH",
            "Runtime config leaves and registered consumers differ",
            details={
                "unconsumed": sorted(present - declared),
                "missing_config": sorted(declared - present),
            },
        )
    missing_callables: list[str] = []
    for qualified in sorted(set(CONFIG_CONSUMERS.values())):
        module_name, attribute = qualified.rsplit(".", 1)
        try:
            module = importlib.import_module(module_name)
            value = getattr(module, attribute)
        except (ImportError, AttributeError):
            missing_callables.append(qualified)
            continue
        if not callable(value):
            missing_callables.append(qualified)
    if missing_callables:
        raise PolicyBlock(
            "CONFIG_CONSUMER_MISSING",
            "One or more config consumers are not real callables",
            details={"consumers": missing_callables},
        )
    return {"ok": True, "leaf_count": len(leaves), "consumer_count": len(declared)}
