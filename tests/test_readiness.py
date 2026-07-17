from __future__ import annotations

from tests import support as _support  # installs src/ on sys.path
from tests.support import (
    FUTURE,
    NOW,
    SESSION,
    WorkspaceCase,
    decision_brief,
    evidence,
    read_json,
    write_json,
)
from tempo.readiness import assess


class ReadinessBoundaryTests(WorkspaceCase):
    def _assess(self, *, allow_fixtures: bool = False):
        return assess(
            self.workspace,
            actor="kernel:readiness",
            session=SESSION,
            allow_fixtures=allow_fixtures,
            now=NOW,
        )

    def test_valid_business_case_is_eligible_but_never_build_authorized(self) -> None:
        self.install_valid_case()

        result, exit_code = self._assess()

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["primary_outcome"], "MVP_AUTHORIZED")
        self.assertTrue(result["eligible_for_authorization"])
        self.assertFalse(result["authorization_valid"])
        self.assertFalse(result["build_allowed"])
        self.assertEqual(result["reasons"], ["ALL_HARD_BLOCKERS_CLEARED"])

    def test_signed_policy_must_match_runtime_config(self) -> None:
        self.install_valid_case()
        policy = read_json(self.root / "plan/readiness-policy.json")
        policy["aggregate_threshold"] = 71
        write_json(self.root / "plan/readiness-policy.json", policy)

        result, exit_code = self._assess()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["primary_outcome"], "BLOCKED_INVALID_INPUT")
        self.assertIn("POLICY_CONFIG_MISMATCH", result["reasons"])

    def test_missing_decision_question_and_owner_are_hard_blockers(self) -> None:
        self.install_valid_case()
        payload = read_json(self.root / "plan/opportunity.json")
        payload["decision_question"] = ""
        payload["decision_owner"] = ""
        write_json(self.root / "plan/opportunity.json", payload)

        result, exit_code = self._assess()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["primary_outcome"], "BLOCKED_INVALID_INPUT")
        self.assertIn("MISSING_DECISION_QUESTION", result["reasons"])
        self.assertIn("MISSING_DECISION_OWNER", result["reasons"])
        self.assertFalse(result["eligible_for_authorization"])

    def test_exactly_one_rank_one_hypothesis_is_required(self) -> None:
        self.install_valid_case()
        payload = read_json(self.root / "plan/hypotheses.json")
        payload["hypotheses"][0]["rank"] = 2
        write_json(self.root / "plan/hypotheses.json", payload)

        result, exit_code = self._assess()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["primary_outcome"], "BLOCKED_INVALID_INPUT")
        self.assertIn("MISSING_RANK_1_HYPOTHESIS", result["reasons"])

    def test_rank_one_must_have_measurable_falsification_contract(self) -> None:
        self.install_valid_case()
        payload = read_json(self.root / "plan/hypotheses.json")
        rank_one = payload["hypotheses"][0]
        rank_one["falsification_condition"] = ""
        rank_one.pop("evidence_threshold")
        write_json(self.root / "plan/hypotheses.json", payload)

        result, exit_code = self._assess()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["primary_outcome"], "BLOCKED_INVALID_INPUT")
        self.assertIn("NON_FALSIFIABLE_RANK_1", result["reasons"])
        self.assertIn("HYPOTHESIS_THRESHOLD_OR_TRIGGER_MISSING", result["reasons"])

    def test_model_only_material_cannot_satisfy_external_evidence(self) -> None:
        items = [
            evidence(
                "E-MODEL-001",
                source_type="model_generated_synthesis",
                kind="model_generated",
            ),
            evidence(
                "E-MODEL-002",
                source_type="model_generated_synthesis",
                kind="model_generated",
            ),
        ]
        self.install_valid_case(evidence_items=items)

        result, exit_code = self._assess()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["primary_outcome"], "EXPERIMENT_REQUIRED")
        self.assertIn("EXTERNAL_EVIDENCE_REQUIRED", result["reasons"])
        self.assertIn("MODEL_ONLY_EVIDENCE", result["reasons"])

    def test_stale_evidence_is_visible_and_cannot_authorize(self) -> None:
        items = [
            evidence("E-STALE-001", expires_at="2026-07-16T12:00:00Z"),
            evidence(
                "E-STALE-002",
                source_type="observed_user_behavior",
                expires_at="2026-07-16T12:00:00Z",
            ),
        ]
        self.install_valid_case(evidence_items=items)

        result, exit_code = self._assess()

        self.assertEqual(exit_code, 2)
        self.assertIn("EVIDENCE_STALE", result["reasons"])
        self.assertIn("EXTERNAL_EVIDENCE_REQUIRED", result["reasons"])

    def test_counterevidence_requires_explicit_acknowledgement(self) -> None:
        items = [
            evidence("E-SUPPORT-001"),
            evidence(
                "E-COUNTER-001",
                source_type="observed_user_behavior",
                stance="contradicts",
            ),
        ]
        self.install_valid_case(evidence_items=items)

        blocked, blocked_code = self._assess()
        self.assertEqual(blocked_code, 2)
        self.assertIn("COUNTEREVIDENCE_UNACKNOWLEDGED", blocked["reasons"])
        self.assertEqual(blocked["contradictory_evidence_refs"], ["E-COUNTER-001"])

        write_json(
            self.root / "plan/decision-brief.json",
            decision_brief(acknowledged=["E-COUNTER-001"]),
        )
        passed, passed_code = self._assess()
        self.assertEqual(passed_code, 0, passed)
        self.assertEqual(passed["primary_outcome"], "MVP_AUTHORIZED")
        self.assertIn("E-COUNTER-001", passed["contradictory_evidence_refs"])

    def test_cheaper_sufficient_experiment_overrides_high_scores(self) -> None:
        brief = decision_brief()
        brief["cheaper_sufficient_experiment"] = {
            "action_id": "X-CHEAP-001",
            "type": "interview",
            "description": "Interview one more decision owner before building.",
            "decision_to_unlock": "Resolve whether the buyer will adopt the workflow.",
            "estimated_cost": {"amount": 0, "currency": "USD"},
            "deadline": FUTURE,
        }
        self.install_valid_case(brief=brief)

        result, exit_code = self._assess()

        self.assertGreaterEqual(result["weighted_score"], 70)
        self.assertEqual(exit_code, 2)
        self.assertEqual(result["primary_outcome"], "EXPERIMENT_REQUIRED")
        self.assertIn("CHEAPER_SUFFICIENT_EXPERIMENT", result["reasons"])
        self.assertEqual(result["cheapest_next_action"]["action_id"], "X-CHEAP-001")

    def test_rank_one_measurement_must_reach_the_declared_threshold(self) -> None:
        items = [
            evidence("E-LOW-001", measurement_value=0.5),
            evidence(
                "E-LOW-002",
                source_type="observed_user_behavior",
                measurement_value=0.5,
            ),
        ]
        self.install_valid_case(evidence_items=items)

        result, exit_code = self._assess()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["primary_outcome"], "EXPERIMENT_REQUIRED")
        self.assertIn("HYPOTHESIS_THRESHOLD_NOT_REACHED", result["reasons"])
        self.assertEqual(result["rank_one_threshold"]["status"], "not_reached")
        self.assertEqual(result["rank_one_threshold"]["observed"], 1.0)

    def test_high_aggregate_cannot_override_distribution_blocker(self) -> None:
        self.install_valid_case()
        payload = read_json(self.root / "plan/business-model.json")
        payload["acquisition_distribution_hypothesis"] = ""
        write_json(self.root / "plan/business-model.json", payload)

        result, exit_code = self._assess()

        self.assertGreaterEqual(result["weighted_score"], 70)
        self.assertEqual(exit_code, 2)
        self.assertEqual(result["primary_outcome"], "BLOCKED_INVALID_INPUT")
        self.assertIn("DISTRIBUTION_HYPOTHESIS_MISSING", result["reasons"])

    def test_fixture_evidence_requires_explicit_internal_demo_mode(self) -> None:
        items = [
            evidence("E-FIXTURE-001", kind="fixture", fixture=True),
            evidence(
                "E-FIXTURE-002",
                source_type="observed_user_behavior",
                kind="fixture",
                fixture=True,
            ),
        ]
        self.install_valid_case(evidence_items=items)

        blocked, blocked_code = self._assess(allow_fixtures=False)
        self.assertEqual(blocked_code, 2)
        self.assertIn("EXTERNAL_EVIDENCE_REQUIRED", blocked["reasons"])

        demo, demo_code = self._assess(allow_fixtures=True)
        self.assertEqual(demo_code, 0, demo)
        self.assertEqual(demo["primary_outcome"], "MVP_AUTHORIZED")
        self.assertEqual(demo["evaluation_mode"], "fixture_demo")
        self.assertEqual(demo["authorization_ceiling"], "demo_only")
        self.assertLessEqual(demo["dimension_scores"]["evidence_quality"], 70)


if __name__ == "__main__":
    import unittest

    unittest.main()
