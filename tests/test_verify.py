from __future__ import annotations

import json
import sys
from unittest import mock

from tests import support as _support  # installs src/ on sys.path
from tests.support import WorkspaceCase, read_json, write_json

from tempo.errors import PolicyBlock
from tempo.util import sha256_json
from tempo.verify import readme_literal_plan, run_verification, verify_receipt, write_receipt


class VerificationReceiptTests(WorkspaceCase):
    def _run(self, code: str, **kwargs):
        return run_verification(
            self.workspace,
            argv=[sys.executable, "-c", code],
            input_paths=["config/tempo.config.json"],
            session="session-verify-001",
            **kwargs,
        )

    def test_successful_subprocess_creates_verifiable_non_authoritative_receipt(self) -> None:
        receipt = self._run("raise SystemExit(0)", receipt_type="focused_tests")

        self.assertEqual(receipt["exit_code"], 0)
        self.assertEqual(receipt["outcome"], "passed")
        self.assertEqual(receipt["provenance"]["kind"], "local_tool")
        self.assertFalse(receipt["provenance"]["authoritative"])
        path = self.root / receipt["receipt_path"]
        self.assertTrue(path.is_file())
        integrity = verify_receipt(self.workspace, receipt["receipt_path"])
        self.assertTrue(integrity["ok"])
        self.assertEqual(integrity["receipt_hash"], receipt["receipt_hash"])

    def test_child_exit_codes_are_normalized_to_tempo_contract(self) -> None:
        policy = self._run("raise SystemExit(2)", receipt_type="focused_tests")
        warning = self._run("raise SystemExit(4)", receipt_type="focused_tests")
        unexpected = self._run("raise SystemExit(1)", receipt_type="focused_tests")

        self.assertEqual((policy["exit_code"], policy["outcome"]), (2, "policy_block"))
        self.assertEqual((warning["exit_code"], warning["outcome"]), (4, "warning"))
        self.assertEqual(
            (unexpected["exit_code"], unexpected["outcome"]),
            (3, "checker_failure"),
        )

    def test_unavailable_container_never_claims_container_execution(self) -> None:
        with mock.patch("tempo.verify.shutil.which", return_value=None):
            receipt = self._run(
                "raise SystemExit(0)",
                receipt_type="readme_literal",
                container=True,
            )

        self.assertEqual(receipt["exit_code"], 3)
        self.assertEqual(receipt["outcome"], "checker_failure")
        self.assertEqual(receipt["provenance"]["kind"], "local_tool")
        self.assertFalse(receipt["provenance"]["authoritative"])
        self.assertIsNone(receipt["environment"]["container_image"])
        self.assertEqual(receipt["command"]["argv"][0], "container-runtime-unavailable")

    def test_unverified_ci_attestation_is_rejected(self) -> None:
        with self.assertRaises(PolicyBlock) as caught:
            self._run(
                "raise SystemExit(0)",
                receipt_type="whole_suite",
                ci_attestation_ref="urn:ci:unsigned-claim",
            )
        self.assertEqual(caught.exception.reason_code, "ATTESTATION_VERIFIER_UNAVAILABLE")

    def test_manual_receipt_cannot_claim_custom_environment_or_provenance(self) -> None:
        common = {
            "workspace": self.workspace,
            "receipt_type": "judge_demo",
            "subject_ref": "repository:TEMPO",
            "session": "session-verify-001",
            "command_argv": ["python", "bin/tempo", "demo"],
            "checks": [{"name": "demo", "status": "passed", "details": "completed"}],
            "input_paths": ["config/tempo.config.json"],
        }
        with self.assertRaises(PolicyBlock) as caught:
            write_receipt(
                **common,
                provenance={
                    "kind": "ci",
                    "trust": "platform_attested",
                    "authoritative": True,
                    "attestation_ref": "urn:fake",
                },
            )
        self.assertEqual(caught.exception.reason_code, "CALLER_PROVENANCE_CLAIM_FORBIDDEN")

        with self.assertRaises(PolicyBlock) as caught:
            write_receipt(
                **common,
                environment={
                    "os": "linux/container",
                    "python_version": "3.13.14",
                    "container_image": "python:3.13.14-slim-bookworm@sha256:" + "0" * 64,
                    "uid": 65532,
                    "network": "none",
                },
            )
        self.assertEqual(caught.exception.reason_code, "CALLER_ENVIRONMENT_CLAIM_FORBIDDEN")

    def test_authoritative_receipt_requires_an_attestation_verifier(self) -> None:
        receipt = self._run("raise SystemExit(0)", receipt_type="whole_suite")
        path = self.root / receipt["receipt_path"]
        payload = read_json(path)
        payload["provenance"] = {
            "kind": "ci",
            "trust": "platform_attested",
            "authoritative": True,
            "attestation_ref": "urn:ci:unsigned-claim",
        }
        payload["receipt_hash"] = sha256_json(
            {key: value for key, value in payload.items() if key != "receipt_hash"}
        )
        write_json(path, payload)

        with self.assertRaises(PolicyBlock) as caught:
            verify_receipt(self.workspace, receipt["receipt_path"])
        self.assertEqual(caught.exception.reason_code, "RECEIPT_ATTESTATION_UNVERIFIED")

    def test_receipt_body_tampering_is_detected(self) -> None:
        receipt = self._run("raise SystemExit(0)", receipt_type="focused_tests")
        path = self.root / receipt["receipt_path"]
        payload = read_json(path)
        payload["subject_ref"] = "repository:TEMPO-tampered"
        write_json(path, payload)

        with self.assertRaises(PolicyBlock) as caught:
            verify_receipt(self.workspace, receipt["receipt_path"])

        self.assertEqual(caught.exception.reason_code, "RECEIPT_TAMPERED")

    def test_optional_current_input_check_reports_drift(self) -> None:
        receipt = self._run("raise SystemExit(0)", receipt_type="focused_tests")
        config = read_json(self.root / "config/tempo.config.json")
        config["project"]["track"] = "Changed after verification"
        write_json(self.root / "config/tempo.config.json", config)

        integrity = verify_receipt(
            self.workspace,
            receipt["receipt_path"],
            check_current_inputs=True,
        )

        self.assertFalse(integrity["ok"])
        self.assertEqual(integrity["input_drift"][0]["artifact"], "config/tempo.config.json")

    def test_readme_literal_plan_is_explicitly_not_execution_evidence(self) -> None:
        (self.root / "README.md").write_text(
            "# Test\n\n## Setup\n\n```powershell\npython -m pip install -e .\n```\n\n"
            "## Run\n\n```powershell\npython bin/tempo demo\n```\n",
            encoding="utf-8",
        )

        plan = readme_literal_plan(self.workspace)

        self.assertFalse(plan["executed"])
        self.assertEqual(plan["provenance"], "plan_only_not_a_verification_receipt")
        self.assertTrue(plan["container"]["read_only_root"])
        self.assertEqual(plan["container"]["network"], "none")
        self.assertEqual(plan["setup_blocks"][0]["commands"], ["python -m pip install -e ."])

    def test_readme_requires_both_setup_and_run_commands(self) -> None:
        (self.root / "README.md").write_text(
            "# Test\n\n## Setup\n\n```sh\npython -m pip install -e .\n```\n",
            encoding="utf-8",
        )

        with self.assertRaises(PolicyBlock) as caught:
            readme_literal_plan(self.workspace)

        self.assertEqual(caught.exception.reason_code, "README_COMMANDS_MISSING")
        self.assertEqual(caught.exception.details["missing_sections"], ["run"])


if __name__ == "__main__":
    import unittest

    unittest.main()
