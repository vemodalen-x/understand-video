from __future__ import annotations

import json

from tests import support as _support  # installs src/ on sys.path
from tests.support import WorkspaceCase, opportunity

from tempo.config import (
    CONFIG_CONSUMERS,
    flatten_leaves,
    load_config,
    verify_config_consumers,
)
from tempo.errors import PolicyBlock
from tempo.schema import validate_data
from tempo.state import StateStore


class SchemaAndConfigConformanceTests(WorkspaceCase):
    def test_every_schema_is_declared_as_draft_2020_12_and_strict_at_root(self) -> None:
        schemas = sorted((self.root / "schemas").glob("*.schema.json"))
        self.assertGreaterEqual(len(schemas), 12)
        for path in schemas:
            with self.subTest(schema=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    payload.get("$schema"),
                    "https://json-schema.org/draft/2020-12/schema",
                )
                self.assertIs(payload.get("additionalProperties"), False)

    def test_unknown_input_property_is_rejected(self) -> None:
        payload = opportunity()
        payload["model_says_authorized"] = True

        with self.assertRaises(PolicyBlock) as caught:
            validate_data(self.workspace, "opportunity", payload)

        self.assertEqual(caught.exception.reason_code, "SCHEMA_VALIDATION_FAILED")
        self.assertTrue(
            any("unknown property" in message for message in caught.exception.details["errors"])
        )

    def test_config_has_exactly_one_registered_consumer_per_leaf(self) -> None:
        leaves = flatten_leaves(load_config(self.workspace))

        self.assertEqual(set(leaves), set(CONFIG_CONSUMERS))
        self.assertEqual(len(leaves), len(CONFIG_CONSUMERS))
        result = verify_config_consumers(self.workspace)
        self.assertTrue(result["ok"])
        self.assertEqual(result["leaf_count"], result["consumer_count"])

    def test_readiness_weights_sum_to_one_hundred_and_match_floors(self) -> None:
        config = load_config(self.workspace)
        weights = config["readiness"]["weights"]
        floors = config["readiness"]["floors"]

        self.assertEqual(set(weights), set(floors))
        self.assertAlmostEqual(sum(float(value) for value in weights.values()), 100.0)

    def test_illegal_state_transition_is_rejected_without_history_rewrite(self) -> None:
        store = StateStore(self.workspace)
        initial = store.initialize()

        with self.assertRaises(PolicyBlock) as caught:
            store.transition("business", "VALIDATING", "SKIP_DISCOVERY")

        self.assertEqual(caught.exception.reason_code, "ILLEGAL_STATE_TRANSITION")
        after = store.read()
        self.assertEqual(after["business"], initial["business"])

    def test_legal_state_transition_appends_history(self) -> None:
        store = StateStore(self.workspace)
        initial = store.initialize()

        changed = store.transition("business", "DISCOVERY", "HUMAN_DISCOVERY_START")

        self.assertEqual(changed["business"]["state"], "DISCOVERY")
        self.assertEqual(len(changed["business"]["history"]), 2)
        self.assertEqual(initial["business"]["history"][0]["state"], "DRAFT")


if __name__ == "__main__":
    import unittest

    unittest.main()
