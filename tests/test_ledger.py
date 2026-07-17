from __future__ import annotations

import json
import multiprocessing
from pathlib import Path
from unittest import mock

from tests import support as _support  # installs src/ on sys.path
from tests.support import SESSION, WorkspaceCase

from tempo.errors import CheckerFailure, PolicyBlock
from tempo.ledger import Ledger, ZERO_HASH
from tempo.util import Workspace


def _append_worker(root: str, index: int) -> None:
    workspace = Workspace.from_path(root)
    Ledger(workspace).append(
        "hypothesis_ranked",
        actor=f"agent:worker-{index}",
        session=f"session-worker-{index:03d}",
        relevant_ids={"hypothesis_id": f"H-WORKER-{index:03d}"},
        artifact_hashes={},
        evidence_refs=[],
        reason_code="CONCURRENT_TEST_APPEND",
        resulting_state="VALIDATING",
        details={"worker": index},
    )


class LedgerIntegrityTests(WorkspaceCase):
    def _append(self, index: int = 1):
        return Ledger(self.workspace).append(
            "hypothesis_ranked",
            actor="agent:researcher",
            session=SESSION,
            relevant_ids={"hypothesis_id": f"H-LEDGER-{index:03d}"},
            artifact_hashes={},
            evidence_refs=[],
            reason_code="HYPOTHESIS_PRIORITY_RECORDED",
            resulting_state="VALIDATING",
            details={"rank": index},
        )

    def test_append_creates_monotonic_hash_chain(self) -> None:
        first = self._append(1)
        second = self._append(2)

        result = Ledger(self.workspace).verify()

        self.assertEqual(first["sequence"], 1)
        self.assertEqual(first["previous_hash"], ZERO_HASH)
        self.assertEqual(second["sequence"], 2)
        self.assertEqual(second["previous_hash"], first["event_hash"])
        self.assertEqual(result["events"], 2)
        self.assertEqual(result["head_hash"], second["event_hash"])
        checkpoint = json.loads(
            (self.root / ".tempo/ledger.head.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            checkpoint,
            {
                "version": 1,
                "sequence": 2,
                "head_hash": second["event_hash"],
            },
        )

    def test_tail_truncation_is_detected_and_append_refuses_to_continue(self) -> None:
        first = self._append(1)
        self._append(2)
        path = self.root / ".tempo/ledger.jsonl"
        first_line = path.read_text(encoding="utf-8").splitlines(keepends=True)[0]
        path.write_text(first_line, encoding="utf-8")
        truncated = path.read_bytes()

        with self.assertRaises(PolicyBlock) as verify_error:
            Ledger(self.workspace).verify()
        self.assertEqual(
            verify_error.exception.reason_code,
            "LEDGER_CHECKPOINT_MISMATCH",
        )

        with self.assertRaises(PolicyBlock) as append_error:
            self._append(3)
        self.assertEqual(
            append_error.exception.reason_code,
            "LEDGER_CHECKPOINT_MISMATCH",
        )
        self.assertEqual(path.read_bytes(), truncated)
        self.assertEqual(json.loads(first_line)["event_hash"], first["event_hash"])

    def test_missing_checkpoint_blocks_verify_and_append(self) -> None:
        self._append(1)
        checkpoint = self.root / ".tempo/ledger.head.json"
        checkpoint.unlink()

        with self.assertRaises(PolicyBlock) as verify_error:
            Ledger(self.workspace).verify()
        self.assertEqual(
            verify_error.exception.reason_code,
            "LEDGER_CHECKPOINT_MISSING",
        )
        with self.assertRaises(PolicyBlock) as append_error:
            self._append(2)
        self.assertEqual(
            append_error.exception.reason_code,
            "LEDGER_CHECKPOINT_MISSING",
        )

    def test_checkpoint_hash_tampering_is_detected(self) -> None:
        self._append(1)
        checkpoint = self.root / ".tempo/ledger.head.json"
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        payload["head_hash"] = ZERO_HASH
        checkpoint.write_text(json.dumps(payload) + "\n", encoding="utf-8")

        with self.assertRaises(PolicyBlock) as caught:
            Ledger(self.workspace).events()

        self.assertEqual(caught.exception.reason_code, "LEDGER_CHECKPOINT_MISMATCH")

    def test_malformed_and_orphaned_checkpoints_fail_closed(self) -> None:
        self._append(1)
        checkpoint = self.root / ".tempo/ledger.head.json"
        checkpoint.write_text("{not-json}\n", encoding="utf-8")
        with self.assertRaises(PolicyBlock) as malformed:
            Ledger(self.workspace).verify()
        self.assertEqual(malformed.exception.reason_code, "LEDGER_CHECKPOINT_BROKEN")

        # Restore a valid checkpoint with a fresh workspace append, then remove
        # only the ledger to prove an anchor can never stand in for its subject.
        event = Ledger(self.workspace)
        checkpoint.write_text(
            json.dumps(
                {
                    "version": 1,
                    "sequence": 1,
                    "head_hash": json.loads(
                        (self.root / ".tempo/ledger.jsonl").read_text(encoding="utf-8")
                    )["event_hash"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / ".tempo/ledger.jsonl").unlink()
        with self.assertRaises(PolicyBlock) as orphaned:
            event.verify()
        self.assertEqual(orphaned.exception.reason_code, "LEDGER_CHECKPOINT_ORPHANED")

    def test_event_is_fsynced_before_checkpoint_update_is_attempted(self) -> None:
        observed: dict[str, bytes] = {}

        def fail_checkpoint(_path, _payload):
            observed["ledger"] = (self.root / ".tempo/ledger.jsonl").read_bytes()
            raise OSError("simulated checkpoint device failure")

        with mock.patch("tempo.ledger.atomic_write_json", side_effect=fail_checkpoint):
            with self.assertRaises(CheckerFailure) as caught:
                self._append(1)

        self.assertEqual(
            caught.exception.reason_code,
            "LEDGER_CHECKPOINT_WRITE_FAILED",
        )
        self.assertTrue(observed["ledger"].endswith(b"\n"))
        self.assertEqual(len(observed["ledger"].splitlines()), 1)
        self.assertFalse((self.root / ".tempo/ledger.head.json").exists())
        with self.assertRaises(PolicyBlock) as fail_closed:
            Ledger(self.workspace).verify()
        self.assertEqual(
            fail_closed.exception.reason_code,
            "LEDGER_CHECKPOINT_MISSING",
        )

    def test_payload_tampering_breaks_chain(self) -> None:
        self._append(1)
        path = self.root / ".tempo/ledger.jsonl"
        event = json.loads(path.read_text(encoding="utf-8"))
        event["reason_code"] = "TAMPERED_REASON"
        path.write_text(json.dumps(event) + "\n", encoding="utf-8")

        with self.assertRaises(PolicyBlock) as caught:
            Ledger(self.workspace).verify()

        self.assertEqual(caught.exception.reason_code, "LEDGER_CHAIN_BROKEN")

    def test_torn_final_line_fails_closed(self) -> None:
        self._append(1)
        path = self.root / ".tempo/ledger.jsonl"
        raw = path.read_bytes()
        path.write_bytes(raw[:-1])

        with self.assertRaises(PolicyBlock) as caught:
            Ledger(self.workspace).events()

        self.assertEqual(caught.exception.reason_code, "LEDGER_CHAIN_BROKEN")

    def test_invalid_event_is_not_appended(self) -> None:
        with self.assertRaises(CheckerFailure) as caught:
            Ledger(self.workspace).append(
                "not_a_real_event",
                actor="agent:researcher",
                session=SESSION,
                relevant_ids={"hypothesis_id": "H-LEDGER-001"},
                artifact_hashes={},
                evidence_refs=[],
                reason_code="INVALID_EVENT_TEST",
                resulting_state="VALIDATING",
                details={},
            )

        self.assertEqual(caught.exception.reason_code, "SCHEMA_VALIDATION_FAILED")
        self.assertFalse((self.root / ".tempo/ledger.jsonl").exists())

    def test_concurrent_processes_do_not_lose_or_fork_events(self) -> None:
        context = multiprocessing.get_context("spawn")
        processes = [
            context.Process(target=_append_worker, args=(str(self.root), index))
            for index in range(6)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=20)
        # Assert only after every worker is joined so a failure never leaves a
        # Windows lock handle alive during TemporaryDirectory cleanup.
        for process in processes:
            self.assertFalse(process.is_alive(), "ledger worker timed out")
            self.assertEqual(process.exitcode, 0)

        result = Ledger(self.workspace).verify()
        events = Ledger(self.workspace).events()
        self.assertEqual(result["events"], 6)
        self.assertEqual({event["details"]["worker"] for event in events}, set(range(6)))


if __name__ == "__main__":
    import unittest

    unittest.main()
