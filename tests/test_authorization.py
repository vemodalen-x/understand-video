from __future__ import annotations

from datetime import timedelta
import io
import json

from tests import support as _support  # installs src/ on sys.path
from tests.support import (
    DEMO_SIGNER,
    HUMAN,
    SESSION,
    WorkspaceCase,
    evidence,
    read_json,
    write_json,
)

from tempo.errors import PolicyBlock
from tempo.ledger import Ledger
from tempo.util import parse_datetime
from tempo.warrant import authorize, revoke, start, validate_warrant


class AuthorizationBoundaryTests(WorkspaceCase):
    def assert_policy_code(self, expected: str, callable_, *args, **kwargs) -> PolicyBlock:
        with self.assertRaises(PolicyBlock) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(caught.exception.reason_code, expected)
        return caught.exception

    def test_start_without_warrant_fails_closed(self) -> None:
        self.install_valid_case()

        self.assert_policy_code(
            "WARRANT_MISSING",
            start,
            self.workspace,
            task_id="T-TEST-001",
            path="src/tempo/new.py",
            lane="core",
            action="implementation_write",
            actor="agent:builder",
            session=SESSION,
        )

    def test_agent_or_provider_cannot_self_authorize(self) -> None:
        self.install_valid_case()
        assessment = self.assess_valid()

        self.assert_policy_code(
            "SELF_AUTHORIZATION_FORBIDDEN",
            authorize,
            self.workspace,
            assessment_hash=assessment["assessment_hash"],
            signer_ref="agent:commercial-provider",
            signer_session=SESSION,
            input_stream=io.StringIO(),
        )

    def test_non_tty_human_authorization_is_rejected(self) -> None:
        self.install_valid_case()
        assessment = self.assess_valid()

        self.assert_policy_code(
            "TTY_OR_ISOLATED_SIGNER_REQUIRED",
            authorize,
            self.workspace,
            assessment_hash=assessment["assessment_hash"],
            signer_ref=HUMAN,
            signer_session=SESSION,
            input_stream=io.StringIO(),
        )

    def test_fixture_assessment_cannot_issue_a_human_warrant(self) -> None:
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
        assessment = self.assess_valid(allow_fixtures=True)

        class InteractiveInput(io.StringIO):
            def isatty(self) -> bool:
                return True

        self.assert_policy_code(
            "FIXTURE_ASSESSMENT_DEMO_ONLY",
            authorize,
            self.workspace,
            assessment_hash=assessment["assessment_hash"],
            signer_ref=HUMAN,
            signer_session=SESSION,
            input_stream=InteractiveInput(),
        )

    def test_unsigned_charter_cannot_issue_warrant(self) -> None:
        self.install_valid_case(signed_charter=False)
        assessment = self.assess_valid()

        self.assert_policy_code(
            "SIGNED_CHARTER_REQUIRED",
            authorize,
            self.workspace,
            assessment_hash=assessment["assessment_hash"],
            signer_ref=DEMO_SIGNER,
            signer_session=SESSION,
            demo_fixture=True,
        )

    def test_assessment_hash_and_current_inputs_are_both_required(self) -> None:
        self.install_valid_case()
        assessment = self.assess_valid()

        self.assert_policy_code(
            "ASSESSMENT_HASH_MISMATCH",
            authorize,
            self.workspace,
            assessment_hash="sha256:" + "0" * 64,
            signer_ref=DEMO_SIGNER,
            signer_session=SESSION,
            demo_fixture=True,
        )

        brief = read_json(self.root / "plan/decision-brief.json")
        brief["rationale"] += " Inputs changed after assessment."
        write_json(self.root / "plan/decision-brief.json", brief)
        self.assert_policy_code(
            "ASSESSMENT_STALE",
            authorize,
            self.workspace,
            assessment_hash=assessment["assessment_hash"],
            signer_ref=DEMO_SIGNER,
            signer_session=SESSION,
            demo_fixture=True,
        )

    def test_human_confirmation_rechecks_inputs_after_readline(self) -> None:
        self.install_valid_case()
        assessment = self.assess_valid()
        brief_path = self.root / "plan/decision-brief.json"

        class MutatingInteractiveInput(io.StringIO):
            def isatty(inner_self) -> bool:
                return True

            def readline(inner_self, *args, **kwargs) -> str:
                payload = read_json(brief_path)
                payload["rationale"] += " Changed while the signer was reviewing."
                write_json(brief_path, payload)
                return f"AUTHORIZE M-TEMPO-001 {assessment['assessment_hash']}\n"

        self.assert_policy_code(
            "ASSESSMENT_STALE",
            authorize,
            self.workspace,
            assessment_hash=assessment["assessment_hash"],
            signer_ref=HUMAN,
            signer_session=SESSION,
            input_stream=MutatingInteractiveInput(),
            output_stream=io.StringIO(),
        )
        self.assertFalse((self.root / "plan/authorization-warrant.json").exists())

    def test_demo_flag_without_bound_workspace_marker_is_rejected(self) -> None:
        self.install_valid_case()
        policy = read_json(self.root / "plan/readiness-policy.json")
        policy["approved_by"] = DEMO_SIGNER
        write_json(self.root / "plan/readiness-policy.json", policy)
        brief = read_json(self.root / "plan/decision-brief.json")
        brief["approved_by"] = DEMO_SIGNER
        brief["signing_provenance"] = "demo_fixture"
        write_json(self.root / "plan/decision-brief.json", brief)
        charter = read_json(self.root / "plan/mvp-charter.json")
        charter["signed_by"] = DEMO_SIGNER
        write_json(self.root / "plan/mvp-charter.json", charter)
        assessment = self.assess_valid(allow_fixtures=True)

        self.assert_policy_code(
            "DEMO_CONTEXT_MISSING",
            authorize,
            self.workspace,
            assessment_hash=assessment["assessment_hash"],
            signer_ref=DEMO_SIGNER,
            signer_session=SESSION,
            demo_fixture=True,
        )

    def test_ttl_above_policy_cap_is_rejected(self) -> None:
        self.install_valid_case()
        assessment = self.assess_valid()

        self.assert_policy_code(
            "WARRANT_TTL_INVALID",
            authorize,
            self.workspace,
            assessment_hash=assessment["assessment_hash"],
            signer_ref=DEMO_SIGNER,
            signer_session=SESSION,
            ttl_hours=25,
            demo_fixture=True,
        )

    def test_past_charter_deadline_is_rejected_at_authorization(self) -> None:
        self.install_valid_case()
        payload = read_json(self.root / "plan/mvp-charter.json")
        payload["deadline"] = "2026-07-17T11:00:00Z"
        write_json(self.root / "plan/mvp-charter.json", payload)
        assessment = self.assess_valid()

        self.assert_policy_code(
            "DEADLINE_EXCEEDED",
            authorize,
            self.workspace,
            assessment_hash=assessment["assessment_hash"],
            signer_ref=DEMO_SIGNER,
            signer_session=SESSION,
            demo_fixture=True,
        )

    def test_demo_warrant_enables_only_bounded_start(self) -> None:
        self.install_valid_case()
        _, authorization = self.authorize_demo()

        result = start(
            self.workspace,
            task_id="T-TEST-001",
            path="src/tempo/new.py",
            lane="core",
            action="implementation_write",
            actor="agent:builder",
            session=SESSION,
        )

        self.assertTrue(result["build_allowed"])
        self.assertEqual(result["warrant_id"], authorization["warrant_id"])
        self.assertEqual(result["path"], "src/tempo/new.py")

    def test_scope_lane_and_action_are_independently_enforced(self) -> None:
        self.install_valid_case()
        self.authorize_demo()
        common = {
            "workspace": self.workspace,
            "task_id": "T-TEST-001",
            "path": "src/tempo/new.py",
            "lane": "core",
            "action": "implementation_write",
            "actor": "agent:builder",
            "session": SESSION,
        }
        outside = dict(common, path="docs/escape.md")
        bad_lane = dict(common, lane="release")
        bad_action = dict(common, action="deploy")

        self.assert_policy_code("SCOPE_NOT_AUTHORIZED", start, **outside)
        self.assert_policy_code("LANE_NOT_AUTHORIZED", start, **bad_lane)
        self.assert_policy_code("ACTION_NOT_AUTHORIZED", start, **bad_action)

    def test_task_traceability_is_required(self) -> None:
        self.install_valid_case()
        self.authorize_demo()
        payload = read_json(self.root / "tasks/T-TEST-001.json")
        payload["hypothesis_refs"] = ["H-UNKNOWN-999"]
        write_json(self.root / "tasks/T-TEST-001.json", payload)

        error = self.assert_policy_code(
            "TRACEABILITY_BROKEN",
            start,
            self.workspace,
            task_id="T-TEST-001",
            path="src/tempo/new.py",
            lane="core",
            action="implementation_write",
            actor="agent:builder",
            session=SESSION,
        )
        self.assertTrue(error.details["missing_edges"])

    def test_revocation_is_terminal_and_idempotent(self) -> None:
        self.install_valid_case()
        _, authorization = self.authorize_demo()

        first = revoke(
            self.workspace,
            actor=HUMAN,
            session=SESSION,
            reason_code="HUMAN_STOP",
        )
        second = revoke(
            self.workspace,
            actor=HUMAN,
            session=SESSION,
            reason_code="HUMAN_STOP",
        )

        self.assertEqual(first["warrant_id"], authorization["warrant_id"])
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assert_policy_code("WARRANT_REVOKED", validate_warrant, self.workspace)
        persisted = read_json(self.root / "plan/authorization-warrant.json")
        self.assertEqual(persisted["state"], "revoked")
        self.assertTrue(persisted["revocation"]["revoked"])

    def test_expiry_records_terminal_event(self) -> None:
        self.install_valid_case()
        _, authorization = self.authorize_demo()
        future = parse_datetime(authorization["expires_at"]) + timedelta(seconds=1)

        self.assert_policy_code(
            "WARRANT_EXPIRED",
            validate_warrant,
            self.workspace,
            now=future,
            actor="kernel:warrant",
            session=SESSION,
        )
        self.assert_policy_code("WARRANT_EXPIRED", validate_warrant, self.workspace)
        self.assertEqual(
            read_json(self.root / "plan/authorization-warrant.json")["state"],
            "expired",
        )
        terminal = [
            event
            for event in Ledger(self.workspace).events()
            if event["event_type"] == "mvp_authorization_expired"
        ]
        self.assertEqual(len(terminal), 1)

    def test_protected_input_drift_permanently_invalidates_warrant(self) -> None:
        self.install_valid_case()
        self.authorize_demo()
        path = self.root / "plan/decision-brief.json"
        original = path.read_bytes()
        payload = read_json(path)
        payload["rationale"] += " Unauthorized post-signature drift."
        write_json(path, payload)

        error = self.assert_policy_code(
            "PROTECTED_INPUT_DRIFT",
            validate_warrant,
            self.workspace,
            actor="kernel:warrant",
            session=SESSION,
        )
        self.assertIn("signed_decision_brief", error.details["drift"])

        path.write_bytes(original)
        self.assert_policy_code("WARRANT_INVALIDATED", validate_warrant, self.workspace)
        self.assertEqual(
            read_json(self.root / "plan/authorization-warrant.json")["state"],
            "invalidated",
        )

    def test_demo_marker_drift_permanently_invalidates_warrant(self) -> None:
        self.install_valid_case()
        self.authorize_demo()
        marker_path = self.root / ".tempo/demo-fixture.json"
        marker = read_json(marker_path)
        marker["nonce"] = "0" * 32
        write_json(marker_path, marker)

        self.assert_policy_code("DEMO_CONTEXT_DRIFT", validate_warrant, self.workspace)
        self.assertEqual(
            read_json(self.root / "plan/authorization-warrant.json")["state"],
            "invalidated",
        )

    def test_deleting_terminal_ledger_tail_does_not_resurrect_warrant(self) -> None:
        self.install_valid_case()
        self.authorize_demo()
        revoke(self.workspace, actor=HUMAN, session=SESSION, reason_code="HUMAN_STOP")
        ledger_path = self.root / ".tempo/ledger.jsonl"
        lines = ledger_path.read_text(encoding="utf-8").splitlines(keepends=True)
        ledger_path.write_text("".join(lines[:-1]), encoding="utf-8")

        self.assert_policy_code("LEDGER_CHECKPOINT_MISMATCH", validate_warrant, self.workspace)

    def test_runtime_config_drift_invalidates_warrant(self) -> None:
        self.install_valid_case()
        self.authorize_demo()
        path = self.root / "config/tempo.config.json"
        payload = read_json(path)
        payload["project"]["track"] = "Changed after authorization"
        write_json(path, payload)

        error = self.assert_policy_code(
            "PROTECTED_INPUT_DRIFT",
            validate_warrant,
            self.workspace,
            actor="kernel:warrant",
            session=SESSION,
        )
        self.assertIn("runtime_config", error.details["drift"])

    def test_machine_receipted_cost_above_cap_blocks_warrant(self) -> None:
        self.install_valid_case()
        _, authorization = self.authorize_demo()
        Ledger(self.workspace).append(
            "verification_completed",
            actor="verifier:tests",
            session=SESSION,
            relevant_ids={"warrant_id": authorization["warrant_id"]},
            artifact_hashes={},
            evidence_refs=[],
            reason_code="TEST_COST_RECORDED",
            resulting_state="BUILDING",
            details={"cost_amount": 101, "currency": "USD"},
        )

        error = self.assert_policy_code("BUDGET_CAP_EXCEEDED", validate_warrant, self.workspace)
        self.assertEqual(error.details["spent"], 101)

    def test_budget_decision_refuses_tampered_ledger_data(self) -> None:
        self.install_valid_case()
        _, authorization = self.authorize_demo()
        Ledger(self.workspace).append(
            "verification_completed",
            actor="verifier:tests",
            session=SESSION,
            relevant_ids={"warrant_id": authorization["warrant_id"]},
            artifact_hashes={},
            evidence_refs=[],
            reason_code="TEST_COST_RECORDED",
            resulting_state="BUILDING",
            details={"cost_amount": 101, "currency": "USD"},
        )
        ledger_path = self.root / ".tempo/ledger.jsonl"
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
        last = json.loads(lines[-1])
        last["details"]["cost_amount"] = 0
        lines[-1] = json.dumps(last, sort_keys=True, separators=(",", ":"))
        ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        self.assert_policy_code("LEDGER_CHAIN_BROKEN", validate_warrant, self.workspace)


if __name__ == "__main__":
    import unittest

    unittest.main()
