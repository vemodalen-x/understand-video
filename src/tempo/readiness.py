"""Deterministic hard-blocker-first MVP readiness evaluation."""
from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path
from typing import Any
import uuid

from .config import config_value, load_config
from .errors import TempoError
from .evidence import evidence_payloads, read_manifest, validate_evidence_item
from .ledger import Ledger
from .schema import validate_data
from .state import StateStore
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

ENGINE_VERSION = "0.1.0"
DIMENSIONS = (
    "problem_evidence",
    "target_segment_clarity",
    "desirability",
    "economic_value",
    "distribution_feasibility",
    "differentiation",
    "technical_feasibility",
    "evidence_quality",
    "expected_decision_value",
    "implementation_cost",
    "strategic_fit",
    "risk_exposure",
)


def _optional_json(workspace: Workspace, relative: str) -> tuple[Any | None, str | None]:
    path = workspace.path(relative)
    if not path.is_file():
        return None, "missing"
    try:
        return load_json(path), None
    except TempoError as exc:
        return None, exc.reason_code


def _binding(workspace: Workspace, relative: str) -> dict[str, str]:
    path = workspace.path(relative)
    digest = sha256_file(path) if path.is_file() else sha256_json({"missing": relative})
    return {"artifact_ref": relative, "hash": digest}


def _block(
    blocker_id: str,
    reason_code: str,
    message: str,
    artifact_ref: str,
) -> dict[str, str]:
    return {
        "blocker_id": blocker_id,
        "reason_code": reason_code,
        "message": message,
        "artifact_ref": artifact_ref,
    }


def _party_present(value: Any) -> bool:
    return isinstance(value, dict) and all(bool(str(item).strip()) for item in value.values())


def _schema_error(
    workspace: Workspace,
    name: str,
    value: Any,
    artifact: str,
    blockers: list[dict[str, str]],
) -> None:
    if value is None:
        return
    try:
        validate_data(workspace, name, value)
    except TempoError as exc:
        blockers.append(
            _block("B18", "INPUT_SCHEMA_INVALID", f"{name}: {exc.message}", artifact)
        )


def _score_dimensions(
    opportunity: dict[str, Any],
    business_model: dict[str, Any],
    hypotheses: dict[str, Any],
    charter: dict[str, Any],
    evidence_results: list[tuple[dict[str, Any], dict[str, Any]]],
    decision_brief: dict[str, Any],
    *,
    allow_fixtures: bool,
) -> dict[str, float]:
    external = [
        payload
        for payload, result in evidence_results
        if result["valid"] and (result["external"] or (allow_fixtures and result["fixture"]))
    ]
    direct = [item for item in external if item.get("directness") == "direct"]
    supports = [item for item in external if item.get("stance") == "supports"]
    rank_one = next(
        (item for item in hypotheses.get("hypotheses", []) if item.get("rank") == 1),
        {},
    )
    rank_refs = set(rank_one.get("evidence_refs", []))
    problem_support = [item for item in supports if item.get("evidence_id") in rank_refs]
    risks = business_model.get("material_risks", [])
    unresolved = [item for item in risks if item.get("resolution_status") == "open"]
    projected = float(decision_brief.get("projected_experiment_cost", {}).get("amount", 0) or 0)
    budget = float(charter.get("budget_cap", {}).get("amount", 0) or 0)
    cost_score = 80.0 if budget and projected <= budget * 0.75 else 60.0 if budget and projected <= budget else 20.0
    fixture_cap = 70.0 if allow_fixtures and not any(result["external"] for _, result in evidence_results) else 100.0
    evidence_quality = min(
        fixture_cap,
        20.0 + len(external) * 18.0 + len(direct) * 12.0 + len(supports) * 5.0,
    )
    return {
        "problem_evidence": 85.0 if problem_support else 20.0,
        "target_segment_clarity": 90.0 if _party_present(opportunity.get("target_user")) else 0.0,
        "desirability": 80.0 if supports else 25.0,
        "economic_value": 75.0 if business_model.get("willingness_to_pay_or_internal_roi_hypothesis") and external else 45.0,
        "distribution_feasibility": 70.0 if business_model.get("acquisition_distribution_hypothesis") else 0.0,
        "differentiation": 75.0 if business_model.get("alternatives_and_differentiation") else 0.0,
        "technical_feasibility": 85.0 if charter.get("technical_boundaries") and not any(item.get("category") == "technical" for item in unresolved) else 30.0,
        "evidence_quality": round(evidence_quality, 2),
        "expected_decision_value": 85.0 if charter.get("decision_to_unlock") else 0.0,
        "implementation_cost": cost_score,
        "strategic_fit": 80.0 if opportunity.get("strategic_context") else 30.0,
        "risk_exposure": 85.0 if not unresolved else 20.0,
    }


def _next_action(
    outcome: str,
    blockers: list[dict[str, str]],
    opportunity: dict[str, Any],
    charter: dict[str, Any],
    decision_brief: dict[str, Any],
    assessed_at: Any,
) -> dict[str, Any] | None:
    if outcome == "MVP_AUTHORIZED":
        return None
    explicit = decision_brief.get("cheaper_sufficient_experiment")
    if isinstance(explicit, dict):
        return explicit
    codes = {item["reason_code"] for item in blockers}
    if outcome == "KILL_RECOMMENDED":
        action_type = "stop"
        description = "Stop implementation and preserve the evidence behind the kill trigger."
    elif outcome == "PIVOT_REQUIRED":
        action_type = "pivot"
        description = "Revise the target segment or value proposition before another readiness cycle."
    elif "INPUT_SCHEMA_INVALID" in codes or any(code.startswith("MISSING_") for code in codes):
        action_type = "revise_input"
        description = "Complete or correct the blocked business decision artifacts."
    else:
        action_type = "interview"
        description = "Run a small customer interview test against the rank-1 hypothesis."
    currency = charter.get("budget_cap", {}).get("currency", "USD")
    return {
        "action_id": f"X-{uuid.uuid4().hex[:12].upper()}",
        "type": action_type,
        "description": description,
        "decision_to_unlock": opportunity.get("decision_question") or "Resolve the current rank-1 uncertainty",
        "estimated_cost": {"amount": 0, "currency": currency},
        "deadline": isoformat_z(assessed_at + timedelta(days=7)),
    }


def _weighted_score(scores: dict[str, float], weights: dict[str, float]) -> float:
    denominator = sum(float(weights[name]) for name in DIMENSIONS)
    if denominator <= 0:
        return 0.0
    return round(sum(scores[name] * float(weights[name]) for name in DIMENSIONS) / denominator, 2)


def _threshold_compare(observed: Any, operator: str, target: Any) -> bool:
    if operator == ">":
        return observed > target
    if operator == ">=":
        return observed >= target
    if operator == "<":
        return observed < target
    if operator == "<=":
        return observed <= target
    if operator == "==":
        return observed == target
    if operator == "!=":
        return observed != target
    if operator == "contains":
        return str(target) in str(observed)
    if operator == "not_contains":
        return str(target) not in str(observed)
    raise ValueError(f"unsupported operator: {operator}")


def _aggregate_threshold(
    measurements: list[tuple[dict[str, Any], Any]], aggregation: str
) -> Any:
    values = [value for _, value in measurements]
    if aggregation == "count":
        return len(values)
    if aggregation == "latest":
        payload, value = max(
            measurements,
            key=lambda item: parse_datetime(item[0]["captured_at"]),
        )
        return value
    if aggregation == "any":
        if not all(isinstance(value, bool) for value in values):
            raise TypeError("any aggregation requires boolean measurements")
        return any(values)
    if aggregation == "all":
        if not all(isinstance(value, bool) for value in values):
            raise TypeError("all aggregation requires boolean measurements")
        return all(values)
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
        raise TypeError(f"{aggregation} aggregation requires numeric measurements")
    if aggregation == "sum":
        return sum(values)
    if aggregation == "mean":
        return sum(values) / len(values)
    if aggregation == "minimum":
        return min(values)
    if aggregation == "maximum":
        return max(values)
    raise ValueError(f"unsupported aggregation: {aggregation}")


def _evaluate_rank_one_threshold(
    hypothesis: dict[str, Any],
    evidence_results: list[tuple[dict[str, Any], dict[str, Any]]],
    *,
    allow_fixtures: bool,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    threshold = hypothesis.get("evidence_threshold")
    if not hypothesis or not isinstance(threshold, dict):
        return {
            "hypothesis_ref": hypothesis.get("hypothesis_id") if hypothesis else None,
            "metric": None,
            "aggregation": None,
            "operator": None,
            "target": None,
            "observed": None,
            "unit": None,
            "minimum_evidence_items": 0,
            "matching_evidence_refs": [],
            "missing_source_types": [],
            "status": "not_evaluated",
        }, []

    hypothesis_id = hypothesis.get("hypothesis_id")
    referenced = set(hypothesis.get("evidence_refs", []))
    eligible: list[dict[str, Any]] = []
    for payload, result in evidence_results:
        if not result["valid"] or result["stale"]:
            continue
        if not (result["external"] or (allow_fixtures and result["fixture"])):
            continue
        if hypothesis_id not in payload.get("hypothesis_refs", []):
            continue
        if referenced and payload.get("evidence_id") not in referenced:
            continue
        eligible.append(payload)

    required_types = set(threshold.get("required_source_types", []))
    present_types = {payload.get("source_type") for payload in eligible}
    missing_types = sorted(required_types - present_types)
    metric = threshold.get("metric")
    unit = threshold.get("unit")
    measurements: list[tuple[dict[str, Any], Any]] = []
    matching_refs: list[str] = []
    for payload in eligible:
        match = next(
            (
                item
                for item in payload.get("measurements", [])
                if item.get("metric") == metric and item.get("unit") == unit
            ),
            None,
        )
        if match is not None:
            measurements.append((payload, match.get("value")))
            matching_refs.append(payload["evidence_id"])

    minimum_items = int(threshold.get("minimum_evidence_items", 1) or 1)
    result: dict[str, Any] = {
        "hypothesis_ref": hypothesis_id,
        "metric": metric,
        "aggregation": threshold.get("aggregation"),
        "operator": threshold.get("operator"),
        "target": threshold.get("target"),
        "observed": None,
        "unit": unit,
        "minimum_evidence_items": minimum_items,
        "matching_evidence_refs": matching_refs,
        "missing_source_types": missing_types,
        "status": "insufficient_measurement",
    }
    if missing_types or len(measurements) < minimum_items:
        return result, [
            _block(
                "B06",
                "HYPOTHESIS_MEASUREMENT_REQUIRED",
                f"Rank-1 threshold has {len(measurements)} matching evidence items; required {minimum_items}; missing source types: {', '.join(missing_types) or 'none'}",
                "plan/evidence/manifest.jsonl",
            )
        ]
    try:
        observed = _aggregate_threshold(measurements, str(threshold.get("aggregation")))
        reached = _threshold_compare(observed, str(threshold.get("operator")), threshold.get("target"))
    except (TypeError, ValueError) as exc:
        result["status"] = "invalid_measurement"
        return result, [
            _block(
                "B18",
                "HYPOTHESIS_MEASUREMENT_INVALID",
                f"Rank-1 threshold cannot be evaluated: {exc}",
                "plan/hypotheses.json",
            )
        ]
    result["observed"] = observed
    result["status"] = "passed" if reached else "not_reached"
    if reached:
        return result, []
    return result, [
        _block(
            "B06",
            "HYPOTHESIS_THRESHOLD_NOT_REACHED",
            f"Rank-1 threshold observed {observed!r} {threshold.get('unit')}; target {threshold.get('operator')} {threshold.get('target')!r}",
            "plan/hypotheses.json",
        )
    ]


def assess(
    workspace: Workspace,
    *,
    actor: str = "kernel:readiness",
    session: str = "unknown",
    allow_fixtures: bool = False,
    now: Any = None,
) -> tuple[dict[str, Any], int]:
    """Assess business readiness; never create or imply implementation authority."""
    assessed_at = now or utc_now()
    config = load_config(workspace)
    weights = config_value(config, "readiness.weights", "tempo.readiness.assess")
    floors = config_value(config, "readiness.floors", "tempo.readiness.assess")
    aggregate_threshold = float(
        config_value(config, "readiness.aggregate_threshold", "tempo.readiness.assess")
    )
    external_source_types = set(
        config_value(config, "evidence.external_source_types", "tempo.readiness.assess")
    )

    opportunity, _ = _optional_json(workspace, "plan/opportunity.json")
    business_model, _ = _optional_json(workspace, "plan/business-model.json")
    hypotheses, _ = _optional_json(workspace, "plan/hypotheses.json")
    policy, _ = _optional_json(workspace, "plan/readiness-policy.json")
    charter, _ = _optional_json(workspace, "plan/mvp-charter.json")
    decision_brief, _ = _optional_json(workspace, "plan/decision-brief.json")
    opportunity = opportunity if isinstance(opportunity, dict) else {}
    business_model = business_model if isinstance(business_model, dict) else {}
    hypotheses = hypotheses if isinstance(hypotheses, dict) else {}
    policy = policy if isinstance(policy, dict) else {}
    charter = charter if isinstance(charter, dict) else {}
    decision_brief = decision_brief if isinstance(decision_brief, dict) else {}

    blockers: list[dict[str, str]] = []
    if not opportunity.get("decision_question"):
        blockers.append(_block("B01", "MISSING_DECISION_QUESTION", "Decision question is required", "plan/opportunity.json"))
    if not opportunity.get("decision_owner"):
        blockers.append(_block("B01", "MISSING_DECISION_OWNER", "Decision owner is required", "plan/opportunity.json"))
    if not opportunity.get("decision_at"):
        blockers.append(_block("B01", "MISSING_DECISION_DATE", "Decision date is required", "plan/opportunity.json"))
    if not _party_present(opportunity.get("target_user")):
        blockers.append(_block("B02", "MISSING_TARGET_USER", "Target user is undefined", "plan/opportunity.json"))
    buyer = opportunity.get("economic_buyer")
    if not isinstance(buyer, dict) or not buyer.get("description") or not buyer.get("value_recipient"):
        blockers.append(_block("B03", "AMBIGUOUS_ECONOMIC_BUYER", "Economic buyer or value recipient is ambiguous", "plan/opportunity.json"))

    _schema_error(workspace, "opportunity", opportunity or None, "plan/opportunity.json", blockers)
    _schema_error(workspace, "business-model", business_model or None, "plan/business-model.json", blockers)
    _schema_error(workspace, "hypotheses", hypotheses or None, "plan/hypotheses.json", blockers)
    _schema_error(workspace, "readiness-policy", policy or None, "plan/readiness-policy.json", blockers)
    _schema_error(workspace, "mvp-charter", charter or None, "plan/mvp-charter.json", blockers)
    _schema_error(workspace, "decision-brief", decision_brief or None, "plan/decision-brief.json", blockers)
    if policy.get("state") != "signed" or not policy.get("approved_by"):
        blockers.append(
            _block(
                "B19",
                "READINESS_POLICY_UNSIGNED",
                "A human/signer-approved readiness policy is required",
                "plan/readiness-policy.json",
            )
        )
    if decision_brief.get("state") != "signed" or not decision_brief.get("approved_by"):
        blockers.append(
            _block(
                "B19",
                "DECISION_BRIEF_UNSIGNED",
                "A human/signer-approved decision brief is required",
                "plan/decision-brief.json",
            )
        )
    if policy:
        policy_controls = {
            "weights": weights,
            "floors": floors,
            "aggregate_threshold": aggregate_threshold,
        }
        mismatched = sorted(
            key for key, expected in policy_controls.items() if policy.get(key) != expected
        )
        if mismatched:
            blockers.append(
                _block(
                    "B19",
                    "POLICY_CONFIG_MISMATCH",
                    f"Signed readiness policy and runtime config differ: {', '.join(mismatched)}",
                    "plan/readiness-policy.json",
                )
            )

    rank_one = [item for item in hypotheses.get("hypotheses", []) if item.get("rank") == 1]
    ranks = [item.get("rank") for item in hypotheses.get("hypotheses", []) if isinstance(item.get("rank"), int)]
    if len(ranks) != len(set(ranks)):
        blockers.append(
            _block(
                "B05",
                "DUPLICATE_HYPOTHESIS_RANK",
                "Hypothesis ranks must be unique",
                "plan/hypotheses.json",
            )
        )
    if not rank_one:
        blockers.append(_block("B05", "MISSING_RANK_1_HYPOTHESIS", "Exactly one rank-1 hypothesis is required", "plan/hypotheses.json"))
        current_hypothesis: dict[str, Any] = {}
    else:
        current_hypothesis = rank_one[0]
        threshold = current_hypothesis.get("evidence_threshold")
        falsification = current_hypothesis.get("falsification_condition")
        if not isinstance(threshold, dict) or not all(key in threshold for key in ("metric", "operator", "target")) or not falsification:
            blockers.append(_block("B05", "NON_FALSIFIABLE_RANK_1", "Rank-1 hypothesis lacks a measurable falsification contract", "plan/hypotheses.json"))
        if not threshold or not current_hypothesis.get("kill_or_pivot_trigger"):
            blockers.append(_block("B06", "HYPOTHESIS_THRESHOLD_OR_TRIGGER_MISSING", "Evidence threshold and kill/pivot trigger are required", "plan/hypotheses.json"))

    evidence_results: list[tuple[dict[str, Any], dict[str, Any]]] = []
    stale_refs: list[str] = []
    for payload in evidence_payloads(workspace):
        try:
            result = validate_evidence_item(workspace, payload, now=assessed_at)
        except TempoError:
            continue
        evidence_results.append((payload, result))
        if result["stale"]:
            stale_refs.append(result["evidence_id"])
    external = [
        (payload, result)
        for payload, result in evidence_results
        if payload.get("source_type") in external_source_types
        and (result["external"] or (allow_fixtures and result["fixture"]))
        and not result["stale"]
    ]
    model_only = bool(evidence_results) and all(result["model_generated"] for _, result in evidence_results)
    minimum_external = int(policy.get("external_evidence", {}).get("minimum_items", 1) or 1)
    if len(external) < minimum_external:
        blockers.append(
            _block(
                "B04",
                "EXTERNAL_EVIDENCE_REQUIRED",
                f"Valid concrete external evidence: {len(external)}; required: {minimum_external}",
                "plan/evidence/manifest.jsonl",
            )
        )
    if stale_refs:
        blockers.append(_block("B07", "EVIDENCE_STALE", f"Stale evidence: {', '.join(stale_refs)}", "plan/evidence/manifest.jsonl"))
    if model_only:
        blockers.append(_block("B07", "MODEL_ONLY_EVIDENCE", "Model synthesis cannot independently validate a business claim", "plan/evidence/manifest.jsonl"))
    threshold_result, threshold_blockers = _evaluate_rank_one_threshold(
        current_hypothesis,
        evidence_results,
        allow_fixtures=allow_fixtures,
    )
    blockers.extend(threshold_blockers)
    counter_refs = [result["evidence_id"] for _, result in evidence_results if result["counterevidence"]]
    acknowledgements = set(decision_brief.get("acknowledged_counterevidence_refs", []))
    unacknowledged = sorted(set(counter_refs) - acknowledgements)
    if unacknowledged:
        blockers.append(_block("B08", "COUNTEREVIDENCE_UNACKNOWLEDGED", f"Counterevidence is not acknowledged: {', '.join(unacknowledged)}", "plan/decision-brief.json"))

    if not opportunity.get("current_alternatives") or not business_model.get("alternatives_and_differentiation"):
        blockers.append(_block("B09", "ALTERNATIVES_OR_DIFFERENTIATION_MISSING", "Alternatives and differentiation must be considered", "plan/business-model.json"))
    if not business_model.get("willingness_to_pay_or_internal_roi_hypothesis") or not business_model.get("revenue_or_economic_value_model"):
        blockers.append(_block("B10", "VALUE_OR_ROI_PATH_MISSING", "Economic value or ROI path is missing", "plan/business-model.json"))
    if not business_model.get("acquisition_distribution_hypothesis"):
        blockers.append(_block("B11", "DISTRIBUTION_HYPOTHESIS_MISSING", "Distribution or adoption hypothesis is missing", "plan/business-model.json"))
    if not charter.get("technical_boundaries"):
        blockers.append(_block("B12", "TECHNICAL_FEASIBILITY_UNBOUNDED", "Technical feasibility is not bounded", "plan/mvp-charter.json"))
    unresolved_risks = [risk for risk in business_model.get("material_risks", []) if risk.get("resolution_status") == "open"]
    if unresolved_risks:
        blockers.append(_block("B13", "MATERIAL_RISK_UNRESOLVED", "Material security, privacy, legal, regulatory, or trust risk remains open", "plan/business-model.json"))
    if not charter.get("decision_to_unlock"):
        blockers.append(_block("B14", "MVP_DECISION_UNLOCK_MISSING", "MVP does not name the decision it will unlock", "plan/mvp-charter.json"))
    charter_required = ("d0_user_journey", "success_metrics", "budget_cap", "deadline", "out_of_scope")
    if any(not charter.get(field) for field in charter_required):
        blockers.append(_block("B15", "MVP_CHARTER_INCOMPLETE", "D0 journey, success threshold, budget, deadline, and out-of-scope list are required", "plan/mvp-charter.json"))
    cheaper = decision_brief.get("cheaper_sufficient_experiment")
    if isinstance(cheaper, dict) and cheaper.get("type") != "mvp":
        blockers.append(_block("B16", "CHEAPER_SUFFICIENT_EXPERIMENT", "A cheaper, materially faster experiment can resolve rank-1", "plan/decision-brief.json"))
    projected = float(decision_brief.get("projected_experiment_cost", {}).get("amount", 0) or 0)
    budget = float(charter.get("budget_cap", {}).get("amount", 0) or 0)
    if budget and projected > budget:
        blockers.append(_block("B17", "PROJECTED_COST_EXCEEDS_BUDGET", "Projected experiment cost exceeds the signed budget", "plan/decision-brief.json"))

    scores = _score_dimensions(
        opportunity,
        business_model,
        hypotheses,
        charter,
        evidence_results,
        decision_brief,
        allow_fixtures=allow_fixtures,
    )
    weighted = _weighted_score(scores, weights)
    floor_failures = [name for name in DIMENSIONS if scores[name] < float(floors[name])]

    codes = {item["reason_code"] for item in blockers}
    invalid_codes = {
        "MISSING_DECISION_QUESTION", "MISSING_DECISION_OWNER", "MISSING_DECISION_DATE",
        "MISSING_TARGET_USER", "AMBIGUOUS_ECONOMIC_BUYER", "MISSING_RANK_1_HYPOTHESIS",
        "NON_FALSIFIABLE_RANK_1", "HYPOTHESIS_THRESHOLD_OR_TRIGGER_MISSING", "INPUT_SCHEMA_INVALID",
        "DUPLICATE_HYPOTHESIS_RANK", "HYPOTHESIS_MEASUREMENT_INVALID",
        "ALTERNATIVES_OR_DIFFERENTIATION_MISSING", "VALUE_OR_ROI_PATH_MISSING",
        "DISTRIBUTION_HYPOTHESIS_MISSING", "TECHNICAL_FEASIBILITY_UNBOUNDED",
        "MATERIAL_RISK_UNRESOLVED", "MVP_DECISION_UNLOCK_MISSING", "MVP_CHARTER_INCOMPLETE",
        "PROJECTED_COST_EXCEEDS_BUDGET", "DECISION_BRIEF_UNSIGNED", "READINESS_POLICY_UNSIGNED",
        "POLICY_CONFIG_MISMATCH",
    }
    if current_hypothesis.get("status") == "falsified" and current_hypothesis.get("kill_or_pivot_trigger", {}).get("action") == "kill":
        outcome = "KILL_RECOMMENDED"
        resulting_state = "KILLED"
    elif current_hypothesis.get("status") == "falsified":
        outcome = "PIVOT_REQUIRED"
        resulting_state = "PIVOTED"
    elif codes.intersection(invalid_codes):
        outcome = "BLOCKED_INVALID_INPUT"
        resulting_state = "EXPERIMENT_REQUIRED"
    elif blockers or floor_failures or weighted < aggregate_threshold:
        outcome = "EXPERIMENT_REQUIRED"
        resulting_state = "EXPERIMENT_REQUIRED"
    else:
        outcome = "MVP_AUTHORIZED"
        resulting_state = "MVP_CANDIDATE"

    input_paths = (
        "plan/opportunity.json",
        "plan/business-model.json",
        "plan/hypotheses.json",
        "plan/evidence/manifest.jsonl",
        "plan/readiness-policy.json",
        "plan/mvp-charter.json",
        "plan/decision-brief.json",
        "config/tempo.config.json",
    )
    assessment: dict[str, Any] = {
        "assessment_id": f"A-{uuid.uuid4().hex[:16].upper()}",
        "engine_version": ENGINE_VERSION,
        "assessed_at": isoformat_z(assessed_at),
        "assessor": actor,
        "policy_ref": policy.get("policy_id"),
        "opportunity_ref": opportunity.get("opportunity_id"),
        "business_model_ref": business_model.get("business_model_id"),
        "hypothesis_set_ref": hypotheses.get("hypothesis_set_id"),
        "evidence_manifest_ref": "plan/evidence/manifest.jsonl",
        "charter_ref": charter.get("mvp_id"),
        "primary_outcome": outcome,
        "evaluation_mode": "fixture_demo" if allow_fixtures else "standard",
        "authorization_ceiling": "demo_only" if allow_fixtures else "human_warrant",
        "eligible_for_authorization": outcome == "MVP_AUTHORIZED",
        "authorization_valid": False,
        "build_allowed": False,
        "hard_blockers": blockers,
        "dimension_scores": scores,
        "weighted_score": weighted,
        "floor_failures": floor_failures,
        "contradictory_evidence_refs": counter_refs,
        "rank_one_threshold": threshold_result,
        "reasons": sorted(codes) or (["DIMENSION_FLOOR_OR_AGGREGATE_NOT_MET"] if outcome == "EXPERIMENT_REQUIRED" else ["ALL_HARD_BLOCKERS_CLEARED"]),
        "cheapest_next_action": _next_action(outcome, blockers, opportunity, charter, decision_brief, assessed_at),
        "input_hashes": [_binding(workspace, path) for path in input_paths],
        "assessment_hash": "sha256:" + "0" * 64,
        "resulting_business_state": resulting_state,
    }
    assessment["assessment_hash"] = sha256_bytes(
        canonical_json_bytes({key: value for key, value in assessment.items() if key != "assessment_hash"})
    )
    validate_data(workspace, "assessment", assessment, policy_block=False)
    destination = workspace.path(f".tempo/assessments/{assessment['assessment_id']}.json")
    atomic_write_json(destination, assessment)
    atomic_write_json(workspace.path(".tempo/assessments/latest.json"), assessment)

    state = StateStore(workspace).initialize()
    current = state["business"]["state"]
    store = StateStore(workspace)
    try:
        if current == "DISCOVERY":
            state = store.transition("business", "VALIDATING", "READINESS_ASSESSMENT_STARTED")
            current = state["business"]["state"]
        if current == "VALIDATING" and resulting_state in {"MVP_CANDIDATE", "EXPERIMENT_REQUIRED", "PIVOTED", "KILLED"}:
            store.transition("business", resulting_state, f"ASSESSMENT_{outcome}")
    except TempoError:
        # State history must not prevent an otherwise truthful immutable assessment;
        # a new cycle is opened by evidence/business commands, not by silent rewrite.
        pass

    Ledger(workspace).append(
        "readiness_assessed",
        actor=actor,
        session=session,
        relevant_ids={
            "assessment_id": assessment["assessment_id"],
            "opportunity_id": opportunity.get("opportunity_id", "unknown"),
            "mvp_id": charter.get("mvp_id", "unknown"),
        },
        artifact_hashes={item["artifact_ref"]: item["hash"] for item in assessment["input_hashes"]},
        evidence_refs=[payload["evidence_id"] for payload, _ in evidence_results],
        reason_code=outcome,
        resulting_state=resulting_state,
        details={
            "assessment_hash": assessment["assessment_hash"],
            "weighted_score": weighted,
            "fixture_mode": allow_fixtures,
        },
    )
    return assessment, 0 if outcome == "MVP_AUTHORIZED" else 2
