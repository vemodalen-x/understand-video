from __future__ import annotations

import io

from tests import support as _support  # installs src/ on sys.path
from tests.support import HUMAN, SESSION, WorkspaceCase

from tempo.charter import sign_charter
from tempo.errors import PolicyBlock
from tempo.providers import JsonCommercialPlanningProvider


class ProviderAndSignatureBoundaryTests(WorkspaceCase):
    def test_provider_output_cannot_contain_authority_bearing_fields(self) -> None:
        provider = JsonCommercialPlanningProvider()
        forbidden = (
            "authorization_warrant",
            "warrant",
            "signed_charter",
            "human_signature",
            "build_allowed",
        )
        for field in forbidden:
            with self.subTest(field=field):
                with self.assertRaises(PolicyBlock) as caught:
                    provider.normalize({"proposal_id": "P-TEST-001", field: True})
                self.assertEqual(
                    caught.exception.reason_code,
                    "COMMERCIAL_PROVIDER_CANNOT_AUTHORIZE",
                )

    def test_provider_requires_structured_object_output(self) -> None:
        with self.assertRaises(PolicyBlock) as caught:
            JsonCommercialPlanningProvider().normalize("AUTHORIZE")
        self.assertEqual(caught.exception.reason_code, "PROVIDER_OUTPUT_INVALID")

    def test_agent_cannot_sign_charter(self) -> None:
        self.install_valid_case(signed_charter=False)

        with self.assertRaises(PolicyBlock) as caught:
            sign_charter(
                self.workspace,
                signer_ref="agent:commercial-provider",
                session=SESSION,
                input_stream=io.StringIO(),
            )

        self.assertEqual(caught.exception.reason_code, "SELF_AUTHORIZATION_FORBIDDEN")

    def test_human_charter_signature_requires_tty(self) -> None:
        self.install_valid_case(signed_charter=False)

        with self.assertRaises(PolicyBlock) as caught:
            sign_charter(
                self.workspace,
                signer_ref=HUMAN,
                session=SESSION,
                input_stream=io.StringIO(),
            )

        self.assertEqual(caught.exception.reason_code, "TTY_OR_ISOLATED_SIGNER_REQUIRED")


if __name__ == "__main__":
    import unittest

    unittest.main()
