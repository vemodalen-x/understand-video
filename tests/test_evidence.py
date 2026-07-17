from __future__ import annotations

import json

from tests import support as _support  # installs src/ on sys.path
from tests.support import HUMAN, SESSION, WorkspaceCase, evidence, write_json

from tempo.errors import PolicyBlock
from tempo.evidence import add_evidence, read_manifest, validate_all_evidence
from tempo.ledger import Ledger


class EvidenceIntegrityTests(WorkspaceCase):
    def test_identical_evidence_add_is_idempotent(self) -> None:
        payload = evidence("E-IDEMPOTENT-001")
        source = self.root / ".inputs/evidence.json"
        write_json(source, payload)

        first = add_evidence(self.workspace, source, actor=HUMAN, session=SESSION)
        second = add_evidence(self.workspace, source, actor=HUMAN, session=SESSION)

        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["file_hash"], second["file_hash"])
        self.assertEqual(len(read_manifest(self.workspace)), 1)

    def test_same_id_with_different_bytes_is_rejected(self) -> None:
        source = self.root / ".inputs/evidence.json"
        payload = evidence("E-IMMUTABLE-001")
        write_json(source, payload)
        add_evidence(self.workspace, source, actor=HUMAN, session=SESSION)
        payload["stance"] = "contradicts"
        write_json(source, payload)

        with self.assertRaises(PolicyBlock) as caught:
            add_evidence(self.workspace, source, actor=HUMAN, session=SESSION)

        self.assertEqual(caught.exception.reason_code, "EVIDENCE_IMMUTABLE")

    def test_retry_recovers_file_written_before_manifest_and_ledger(self) -> None:
        payload = evidence("E-RECOVER-001")
        source = self.root / ".inputs/evidence.json"
        write_json(source, payload)
        write_json(self.root / "plan/evidence/E-RECOVER-001.json", payload)

        result = add_evidence(self.workspace, source, actor=HUMAN, session=SESSION)

        self.assertFalse(result["idempotent"])
        self.assertTrue(result["recovered_partial_write"])
        self.assertEqual(len(read_manifest(self.workspace)), 1)
        events = [
            item for item in Ledger(self.workspace).events()
            if item["event_type"] == "evidence_added"
        ]
        self.assertEqual(len(events), 1)

    def test_manifest_chain_tampering_fails_closed(self) -> None:
        source = self.root / ".inputs/evidence.json"
        write_json(source, evidence("E-TAMPER-001"))
        add_evidence(self.workspace, source, actor=HUMAN, session=SESSION)
        path = self.root / "plan/evidence/manifest.jsonl"
        entry = json.loads(path.read_text(encoding="utf-8"))
        entry["file_hash"] = "sha256:" + "1" * 64
        path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

        with self.assertRaises(PolicyBlock) as caught:
            read_manifest(self.workspace)

        self.assertEqual(caught.exception.reason_code, "EVIDENCE_MANIFEST_BROKEN")

    def test_evidence_file_tampering_fails_closed(self) -> None:
        source = self.root / ".inputs/evidence.json"
        write_json(source, evidence("E-FILE-001"))
        result = add_evidence(self.workspace, source, actor=HUMAN, session=SESSION)
        stored = self.root / result["path"]
        stored.write_text(stored.read_text(encoding="utf-8") + " ", encoding="utf-8")

        with self.assertRaises(PolicyBlock) as caught:
            validate_all_evidence(self.workspace)

        self.assertEqual(caught.exception.reason_code, "EVIDENCE_IMMUTABLE")


if __name__ == "__main__":
    import unittest

    unittest.main()
