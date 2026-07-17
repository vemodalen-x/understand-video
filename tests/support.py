"""Deterministic, schema-valid repository fixtures for kernel tests."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from tempo.evidence import add_evidence  # noqa: E402
from tempo.readiness import assess  # noqa: E402
from tempo.util import Workspace, sha256_file  # noqa: E402
from tempo.warrant import authorize, initialize_demo_context  # noqa: E402


NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
NOW_TEXT = "2026-07-17T12:00:00Z"
FUTURE = "2035-07-22T08:00:00Z"
SESSION = "session-test-001"
HUMAN = "human:qa-user"
DEMO_SIGNER = "platform:demo-fixture-signer"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def opportunity() -> dict[str, Any]:
    return {
        "opportunity_id": "O-TEMPO-001",
        "version": 1,
        "state": "VALIDATING",
        "decision_question": "Should product teams use TEMPO before coding an MVP?",
        "decision_owner": HUMAN,
        "decision_at": FUTURE,
        "initiating_context": "Coding agents can spend implementation budget before business uncertainty is resolved.",
        "target_user": {
            "segment": "product and innovation teams",
            "description": "Teams coordinating humans and coding agents",
            "usage_context": "Before authorizing implementation work",
        },
        "economic_buyer": {
            "same_as_target_user": False,
            "description": "Head of product or innovation",
            "value_recipient": "The product delivery organization",
        },
        "job_to_be_done": "Make a reviewable build-or-experiment decision before implementation begins.",
        "observed_problem": "Teams lack a deterministic boundary between promising research and permission to code.",
        "current_alternatives": ["Ad hoc approval in chat", "Manual stage-gate documents"],
        "expected_value": "Less wasted implementation time and clearer accountability.",
        "strategic_context": "Increase safe productivity of teams using coding agents.",
        "constraints": [
            {
                "constraint_id": "C-BUDGET-001",
                "type": "budget",
                "description": "Keep the governed experiment below the signed cap.",
            }
        ],
        "created_at": NOW_TEXT,
        "updated_at": NOW_TEXT,
    }


def business_model() -> dict[str, Any]:
    return {
        "business_model_id": "BM-TEMPO-001",
        "version": 1,
        "opportunity_ref": "O-TEMPO-001",
        "state": "supported",
        "value_proposition": "Convert build-or-not uncertainty into a fast, reviewable, bounded workflow.",
        "target_segment": "Product and innovation teams using coding agents",
        "target_user": {
            "description": "Product leads and agent operators",
            "value_or_need": "Reach evidence-backed decisions without losing delivery speed",
        },
        "economic_buyer": {
            "description": "Head of product or innovation",
            "value_or_need": "Reduce waste and authorization risk",
        },
        "willingness_to_pay_or_internal_roi_hypothesis": "Saving one unnecessary implementation sprint creates positive internal ROI.",
        "revenue_or_economic_value_model": "Economic value equals avoided build hours plus faster decision throughput.",
        "acquisition_distribution_hypothesis": "Adoption begins in repositories already used by coding-agent teams.",
        "adoption_friction": ["Teams must write explicit thresholds"],
        "key_partners_or_dependencies": ["Repository host", "Python runtime"],
        "rough_cost_drivers": [
            {
                "driver": "Team onboarding",
                "basis": "One facilitated decision cycle",
                "uncertainty": "medium",
            }
        ],
        "alternatives_and_differentiation": [
            {
                "alternative": "Chat approval",
                "differentiation": "TEMPO binds approval to immutable evidence and scope hashes.",
            }
        ],
        "defensibility_hypothesis": "A portable policy kernel and audit trail compound trust over time.",
        "material_risks": [
            {
                "risk_id": "BR-TRUST-001",
                "category": "trust",
                "description": "Users may mistake model recommendations for authorization.",
                "resolution_status": "mitigated",
            }
        ],
        "hypothesis_refs": ["H-PROBLEM-001"],
        "evidence_refs": ["E-INTERVIEW-001", "E-INTERVIEW-002"],
        "owner": HUMAN,
        "created_at": NOW_TEXT,
        "updated_at": NOW_TEXT,
    }


def hypotheses(*, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    refs = evidence_refs if evidence_refs is not None else ["E-INTERVIEW-001", "E-INTERVIEW-002"]
    return {
        "hypothesis_set_id": "HS-TEMPO-001",
        "version": 1,
        "opportunity_ref": "O-TEMPO-001",
        "owner": HUMAN,
        "review_at": FUTURE,
        "hypotheses": [
            {
                "hypothesis_id": "H-PROBLEM-001",
                "rank": 1,
                "type": "problem",
                "statement": "Product leads lose material time when build authority is implicit.",
                "why_it_matters": "This is the core problem TEMPO must resolve.",
                "falsification_condition": "Fewer than two of five qualified teams report this problem.",
                "evidence_threshold": {
                    "metric": "qualified teams reporting the problem",
                    "aggregation": "sum",
                    "operator": ">=",
                    "target": 2,
                    "unit": "teams",
                    "minimum_evidence_items": 2,
                    "required_source_types": ["customer_interview"],
                },
                "kill_or_pivot_trigger": {
                    "action": "pivot",
                    "condition": "The evidence threshold is not reached by the review date.",
                    "reason_code": "PROBLEM_THRESHOLD_NOT_MET",
                },
                "status": "supported",
                "evidence_refs": refs,
                "confidence": {
                    "score": 75,
                    "scale": "0-100",
                    "rationale": "Two direct observations support the decision problem.",
                },
                "owner": HUMAN,
                "review_at": FUTURE,
                "expires_at": FUTURE,
            }
        ],
        "created_at": NOW_TEXT,
        "updated_at": NOW_TEXT,
    }


def evidence(
    evidence_id: str = "E-INTERVIEW-001",
    *,
    source_type: str = "customer_interview",
    kind: str = "external",
    stance: str = "supports",
    expires_at: str | None = FUTURE,
    fixture: bool = False,
    measurement_value: int | float | bool | str | None = None,
) -> dict[str, Any]:
    directness = "synthesis" if source_type == "model_generated_synthesis" else "direct"
    return {
        "evidence_id": evidence_id,
        "source_type": source_type,
        "source_reference": f"urn:test:{evidence_id.lower()}",
        "captured_at": NOW_TEXT,
        "freshness": {"policy": "default", "expires_at": expires_at},
        "content_hash": None,
        "claim_tested": "Product teams experience ambiguity about when implementation is authorized.",
        "stance": stance,
        "directness": directness,
        "sample_context": {
            "description": "Structured product-team interview",
            "sample_size": 3,
            "population": "Product and innovation leads",
        },
        "collector": HUMAN,
        "limitations": ["Small non-random sample"],
        "hypothesis_refs": ["H-PROBLEM-001"],
        "measurements": [
            {
                "metric": "qualified teams reporting the problem",
                "value": measurement_value if measurement_value is not None else (2 if stance == "supports" else 0),
                "unit": "teams",
            }
        ],
        "provenance": {
            "kind": kind,
            "collection_method": "Recorded test fixture" if fixture else "Structured interview",
            "is_fixture": fixture,
            "untrusted_input": True,
        },
    }


def readiness_policy() -> dict[str, Any]:
    dimensions = [
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
    ]
    return {
        "policy_id": "RP-TEMPO-001",
        "version": 1,
        "state": "signed",
        "effective_at": NOW_TEXT,
        "owner": HUMAN,
        "approved_by": HUMAN,
        "approved_at": NOW_TEXT,
        "hard_blockers": [
            {
                "blocker_id": f"B{index:02d}",
                "reason_code": f"POLICY_BLOCKER_{index:02d}",
                "description": f"Deterministic blocker {index:02d}",
            }
            for index in range(1, 20)
        ],
        "weights": {
            "problem_evidence": 14,
            "target_segment_clarity": 8,
            "desirability": 10,
            "economic_value": 10,
            "distribution_feasibility": 8,
            "differentiation": 7,
            "technical_feasibility": 8,
            "evidence_quality": 12,
            "expected_decision_value": 8,
            "implementation_cost": 5,
            "strategic_fit": 5,
            "risk_exposure": 5,
        },
        "floors": {
            "problem_evidence": 60,
            "target_segment_clarity": 50,
            "desirability": 50,
            "economic_value": 45,
            "distribution_feasibility": 40,
            "differentiation": 35,
            "technical_feasibility": 50,
            "evidence_quality": 60,
            "expected_decision_value": 50,
            "implementation_cost": 40,
            "strategic_fit": 35,
            "risk_exposure": 50,
        },
        "aggregate_threshold": 70,
        "external_evidence": {
            "minimum_items": 2,
            "model_generated_counts_as_external": False,
            "require_contradictions_acknowledged": True,
        },
        "cheaper_experiment_types": ["interview", "clickable_prototype"],
    }


def decision_brief(*, acknowledged: list[str] | None = None) -> dict[str, Any]:
    return {
        "decision_brief_id": "DB-TEMPO-001",
        "version": 1,
        "opportunity_ref": "O-TEMPO-001",
        "state": "signed",
        "recommendation": "MVP",
        "rationale": "Proceed only if deterministic readiness passes and a human issues a warrant.",
        "acknowledged_counterevidence_refs": acknowledged or [],
        "projected_experiment_cost": {"amount": 50, "currency": "USD"},
        "cheaper_sufficient_experiment": None,
        "owner": HUMAN,
        "approved_by": HUMAN,
        "approved_at": NOW_TEXT,
        "signing_provenance": "tty_human",
        "created_at": NOW_TEXT,
        "updated_at": NOW_TEXT,
    }


def charter(*, evidence_refs: list[str], manifest_hash: str, signed: bool = True) -> dict[str, Any]:
    return {
        "mvp_id": "M-TEMPO-001",
        "version": 1,
        "state": "signed" if signed else "draft",
        "opportunity_ref": "O-TEMPO-001",
        "decision_question_ref": "O-TEMPO-001#/decision_question",
        "decision_to_unlock": "Decide whether governed build authorization improves team productivity.",
        "hypothesis_refs": ["H-PROBLEM-001"],
        "evidence_baseline": {
            "manifest_ref": "plan/evidence/manifest.jsonl",
            "manifest_hash": manifest_hash,
            "evidence_refs": evidence_refs,
            "captured_at": NOW_TEXT,
        },
        "d0_user_journey": [
            {
                "step_id": "J-ASSESS-001",
                "order": 1,
                "actor": "Product lead",
                "action": "Assess the current business case",
                "observable_result": "A deterministic outcome and cheapest next action are shown",
            }
        ],
        "in_scope": ["src/**", "tests/**"],
        "out_of_scope": ["Production deployment", "External communications"],
        "success_metrics": [
            {
                "metric_id": "SM-BLOCK-001",
                "name": "Unauthorized implementation attempts blocked",
                "operator": "==",
                "threshold": 1,
                "unit": "attempt",
                "measurement_method": "Run the deterministic start-boundary test",
            }
        ],
        "kill_and_pivot_triggers": [
            {
                "trigger_id": "KP-DEMO-001",
                "action": "pivot",
                "condition": "The judge path cannot demonstrate the authority boundary.",
                "reason_code": "DEMO_BOUNDARY_MISSING",
            }
        ],
        "budget_cap": {"amount": 100, "currency": "USD"},
        "deadline": FUTURE,
        "owner": HUMAN,
        "technical_boundaries": ["Standard-library Python kernel", "Local repository only"],
        "data_boundaries": ["Synthetic or fixture data only"],
        "supported_audience": ["Product leads", "Coding-agent operators"],
        "supported_environment": ["Windows", "macOS", "Linux"],
        "implementation_risk_tier": "R0",
        "allowed_lanes": ["core", "tests"],
        "demo_beats": [
            {
                "beat_id": "B-D0-001",
                "order": 1,
                "demo_tier": "D0",
                "description": "Show a blocked start before authorization",
                "acceptance": "The command exits two with WARRANT_MISSING.",
            }
        ],
        "post_mvp_decision_meeting": {
            "scheduled_at": FUTURE,
            "owner": HUMAN,
            "required_participants": [HUMAN, "human:engineering-lead"],
            "decision_question": "Should the governed workflow proceed beyond the local MVP?",
        },
        "rollback_or_disposal_plan": "Delete local generated artifacts and retain only the audit evidence.",
        "created_at": NOW_TEXT,
        "updated_at": NOW_TEXT,
        "signed_by": HUMAN if signed else None,
        "signed_at": NOW_TEXT if signed else None,
    }


def task() -> dict[str, Any]:
    return {
        "task_id": "T-TEST-001",
        "lane": "core",
        "scope_in": ["src/**"],
        "scope_out": ["docs/**"],
        "hypothesis_refs": ["H-PROBLEM-001"],
        "charter_ref": "M-TEMPO-001",
        "opportunity_ref": "O-TEMPO-001",
    }


class WorkspaceCase(unittest.TestCase):
    """A test case with an isolated repository carrying real schemas/config."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="tempo-test-")
        self.root = Path(self._temporary.name)
        shutil.copytree(REPOSITORY_ROOT / "schemas", self.root / "schemas")
        shutil.copytree(REPOSITORY_ROOT / "config", self.root / "config")
        self.workspace = Workspace.from_path(self.root)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def install_valid_case(
        self,
        *,
        evidence_items: list[dict[str, Any]] | None = None,
        signed_charter: bool = True,
        brief: dict[str, Any] | None = None,
    ) -> None:
        items = evidence_items or [
            evidence("E-INTERVIEW-001"),
            evidence("E-INTERVIEW-002", source_type="observed_user_behavior"),
        ]
        write_json(self.root / "plan/opportunity.json", opportunity())
        model = business_model()
        model["evidence_refs"] = [item["evidence_id"] for item in items]
        write_json(self.root / "plan/business-model.json", model)
        write_json(
            self.root / "plan/hypotheses.json",
            hypotheses(evidence_refs=[item["evidence_id"] for item in items]),
        )
        write_json(self.root / "plan/readiness-policy.json", readiness_policy())
        write_json(self.root / "plan/decision-brief.json", brief or decision_brief())
        for index, payload in enumerate(items):
            input_path = self.root / ".inputs" / f"evidence-{index}.json"
            write_json(input_path, payload)
            add_evidence(
                self.workspace,
                input_path,
                actor=HUMAN,
                session=SESSION,
            )
        manifest = self.root / "plan/evidence/manifest.jsonl"
        write_json(
            self.root / "plan/mvp-charter.json",
            charter(
                evidence_refs=[item["evidence_id"] for item in items],
                manifest_hash=sha256_file(manifest),
                signed=signed_charter,
            ),
        )
        write_json(self.root / "tasks/T-TEST-001.json", task())

    def assess_valid(self, *, allow_fixtures: bool = False) -> dict[str, Any]:
        assessment, exit_code = assess(
            self.workspace,
            actor="kernel:readiness",
            session=SESSION,
            allow_fixtures=allow_fixtures,
            now=NOW,
        )
        self.assertEqual(exit_code, 0, assessment)
        self.assertEqual(assessment["primary_outcome"], "MVP_AUTHORIZED")
        return assessment

    def authorize_demo(self) -> tuple[dict[str, Any], dict[str, Any]]:
        policy = read_json(self.root / "plan/readiness-policy.json")
        policy["approved_by"] = DEMO_SIGNER
        write_json(self.root / "plan/readiness-policy.json", policy)
        brief = read_json(self.root / "plan/decision-brief.json")
        brief["approved_by"] = DEMO_SIGNER
        brief["signing_provenance"] = "demo_fixture"
        write_json(self.root / "plan/decision-brief.json", brief)
        signed_charter = read_json(self.root / "plan/mvp-charter.json")
        signed_charter["signed_by"] = DEMO_SIGNER
        write_json(self.root / "plan/mvp-charter.json", signed_charter)
        initialize_demo_context(
            self.workspace,
            mvp_ref=signed_charter["mvp_id"],
            session=SESSION,
        )
        assessment = self.assess_valid(allow_fixtures=True)
        result = authorize(
            self.workspace,
            assessment_hash=assessment["assessment_hash"],
            signer_ref=DEMO_SIGNER,
            signer_session=SESSION,
            ttl_hours=1,
            demo_fixture=True,
        )
        return assessment, result


def clone(value: Any) -> Any:
    return deepcopy(value)
