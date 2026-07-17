from __future__ import annotations

from tests import support as _support  # installs src/ on sys.path
from tests.support import WorkspaceCase

from tempo.errors import PolicyBlock
from tempo.ledger import Ledger
from tempo.verdict import (
    HUMAN_VERDICT_END,
    HUMAN_VERDICT_START,
    compile_verdict,
)


class VerdictPreservationTests(WorkspaceCase):
    def _replace_human_section(self, raw: bytes, replacement: bytes) -> bytes:
        start = raw.index(HUMAN_VERDICT_START)
        end = raw.index(HUMAN_VERDICT_END) + len(HUMAN_VERDICT_END)
        return raw[:start] + replacement + raw[end:]

    def test_first_compile_creates_blank_human_owned_section(self) -> None:
        result = compile_verdict(self.workspace, session="session-verdict-001")
        raw = (self.root / result["path"]).read_bytes()

        self.assertIn(HUMAN_VERDICT_START, raw)
        self.assertIn(HUMAN_VERDICT_END, raw)
        protected = raw[
            raw.index(HUMAN_VERDICT_START) :
            raw.index(HUMAN_VERDICT_END) + len(HUMAN_VERDICT_END)
        ]
        self.assertIn(b"Decision:\n\nSigned by:\n\nSigned at:", protected)
        self.assertFalse(result["human_verdict_filled"])

    def test_recompile_preserves_human_section_byte_for_byte(self) -> None:
        first = compile_verdict(self.workspace, session="session-verdict-001")
        path = self.root / first["path"]
        human = (
            HUMAN_VERDICT_START
            + b"\n## Human verdict and signature\n\nDecision: PROCEED\n\n"
            + b"Signed by: human:reviewer\n\nSigned at: 2026-07-17T12:00:00Z\n"
            + HUMAN_VERDICT_END
        )
        path.write_bytes(self._replace_human_section(path.read_bytes(), human))

        compile_verdict(self.workspace, session="session-verdict-002")
        after = path.read_bytes()
        protected_after = after[
            after.index(HUMAN_VERDICT_START) :
            after.index(HUMAN_VERDICT_END) + len(HUMAN_VERDICT_END)
        ]

        self.assertEqual(protected_after, human)
        events = [event for event in Ledger(self.workspace).events() if event["event_type"] == "verdict_compiled"]
        self.assertEqual(len(events), 2)
        self.assertTrue(all(event["details"]["human_section_preserved"] for event in events))

    def test_nonempty_unmarked_memo_fails_closed(self) -> None:
        path = self.root / "plan/verdict-memo.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        original = b"Human decision: do not overwrite this text.\n"
        path.write_bytes(original)

        with self.assertRaises(PolicyBlock) as caught:
            compile_verdict(self.workspace)

        self.assertEqual(caught.exception.reason_code, "HUMAN_VERDICT_MARKERS_MISSING")
        self.assertEqual(path.read_bytes(), original)

    def test_duplicate_or_reversed_markers_fail_closed(self) -> None:
        path = self.root / "plan/verdict-memo.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        cases = (
            HUMAN_VERDICT_START + b"\n" + HUMAN_VERDICT_START + b"\n" + HUMAN_VERDICT_END,
            HUMAN_VERDICT_END + b"\n" + HUMAN_VERDICT_START,
        )
        for raw in cases:
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                with self.assertRaises(PolicyBlock) as caught:
                    compile_verdict(self.workspace)
                self.assertEqual(caught.exception.reason_code, "HUMAN_VERDICT_MARKERS_INVALID")
                self.assertEqual(path.read_bytes(), raw)


if __name__ == "__main__":
    import unittest

    unittest.main()
