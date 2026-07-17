"""Hash-chained append-only decision and evidence ledger."""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any, Iterator
import uuid

from .errors import CheckerFailure, PolicyBlock, TempoError
from .schema import validate_data
from .util import (
    Workspace,
    atomic_write_json,
    canonical_json_bytes,
    isoformat_z,
    sha256_bytes,
)

ZERO_HASH = "sha256:" + "0" * 64
CHECKPOINT_VERSION = 1


class _FileLock:
    """Small cross-platform advisory lock covering tail-read through fsync."""

    def __init__(self, path: Path, timeout: float = 10.0) -> None:
        self.path = path
        self.timeout = timeout
        self.stream: Any = None

    def __enter__(self) -> "_FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a+b")
        if os.name == "nt" and self.stream.seek(0, os.SEEK_END) == 0:
            self.stream.write(b"\0")
            self.stream.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    self.stream.seek(0)
                    msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError as exc:
                if time.monotonic() >= deadline:
                    self.stream.close()
                    raise CheckerFailure("LEDGER_LOCK_TIMEOUT", "Timed out locking ledger") from exc
                time.sleep(0.02)

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.stream is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
        finally:
            self.stream.close()


def _decode_lines(raw: bytes, path: Path) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PolicyBlock("LEDGER_CHAIN_BROKEN", f"Ledger is not UTF-8: {path}") from exc
    if not text.endswith("\n"):
        raise PolicyBlock("LEDGER_CHAIN_BROKEN", f"Ledger has a torn final line: {path}")
    events: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PolicyBlock(
                "LEDGER_CHAIN_BROKEN",
                f"Ledger line {number} is invalid JSON",
            ) from exc
        if not isinstance(event, dict):
            raise PolicyBlock("LEDGER_CHAIN_BROKEN", f"Ledger line {number} is not an object")
        events.append(event)
    return events


def _event_hash(event: dict[str, Any]) -> str:
    body = {key: value for key, value in event.items() if key != "event_hash"}
    return sha256_bytes(canonical_json_bytes(body))


class Ledger:
    """Append and verify typed hash-chained events."""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.path = workspace.path(".tempo/ledger.jsonl")
        self.lock_path = workspace.path(".tempo/ledger.lock")
        self.checkpoint_path = workspace.path(".tempo/ledger.head.json")

    def events(self) -> list[dict[str, Any]]:
        # Preserve a read-only empty-workspace fast path. Once either durable
        # artifact exists, take the same lock as append so readers cannot see
        # the intentional event-fsync/checkpoint-replace interval.
        if not self.path.exists() and not self.checkpoint_path.exists():
            return []
        with _FileLock(self.lock_path):
            return self._read_verified_events()

    def verify(self) -> dict[str, Any]:
        events = self.events()
        self._verify_events(events)
        head = events[-1]["event_hash"] if events else ZERO_HASH
        return {"ok": True, "events": len(events), "head_hash": head}

    def append(
        self,
        event_type: str,
        *,
        actor: str,
        session: str,
        relevant_ids: dict[str, str] | None = None,
        artifact_hashes: dict[str, str] | None = None,
        evidence_refs: list[str] | None = None,
        reason_code: str,
        resulting_state: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with _FileLock(self.lock_path):
            events = self._read_verified_events()
            previous = events[-1]["event_hash"] if events else ZERO_HASH
            normalized_ids = {
                str(key): str(value)
                for key, value in (relevant_ids or {}).items()
                if value is not None and str(value) not in ("", "unknown")
            }
            if not normalized_ids:
                normalized_ids = {"event_ref": f"LE-{uuid.uuid4().hex[:12].upper()}"}
            event: dict[str, Any] = {
                "event_id": f"EVT-{uuid.uuid4().hex.upper()}",
                "event_type": event_type,
                "sequence": len(events) + 1,
                "timestamp": isoformat_z(),
                "actor": actor,
                "session": session,
                "relevant_ids": normalized_ids,
                "artifact_hashes": artifact_hashes or {},
                "evidence_refs": evidence_refs or [],
                "reason_code": reason_code,
                "resulting_state": resulting_state,
                "details": details or {},
                "previous_hash": previous,
            }
            event["event_hash"] = _event_hash(event)
            validate_data(self.workspace, "ledger-event", event, policy_block=False)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            with self.path.open("ab") as stream:
                stream.write(line.encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            # The event is durable before the checkpoint advances. A crash or
            # failed replace between these operations leaves a detectable
            # mismatch and all subsequent readers fail closed.
            checkpoint = {
                "version": CHECKPOINT_VERSION,
                "sequence": event["sequence"],
                "head_hash": event["event_hash"],
            }
            try:
                atomic_write_json(self.checkpoint_path, checkpoint)
            except TempoError:
                raise
            except OSError as exc:
                raise CheckerFailure(
                    "LEDGER_CHECKPOINT_WRITE_FAILED",
                    f"Ledger event was persisted but its head checkpoint could not be updated: {exc}",
                    next_action="Do not use the ledger until checkpoint integrity is repaired.",
                ) from exc
            return event

    def _read_verified_events(self) -> list[dict[str, Any]]:
        ledger_exists = self.path.exists()
        raw = self.path.read_bytes() if ledger_exists else b""
        events = _decode_lines(raw, self.path)
        self._verify_events(events)
        self._verify_checkpoint(events, ledger_exists=ledger_exists)
        return events

    def _read_checkpoint(self, *, required: bool) -> dict[str, Any] | None:
        if not self.checkpoint_path.exists():
            if required:
                raise PolicyBlock(
                    "LEDGER_CHECKPOINT_MISSING",
                    "Ledger exists without its durable head checkpoint",
                )
            return None
        try:
            checkpoint = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PolicyBlock(
                "LEDGER_CHECKPOINT_BROKEN",
                "Ledger head checkpoint is unreadable or malformed",
            ) from exc
        expected_keys = {"version", "sequence", "head_hash"}
        valid_hash = (
            isinstance(checkpoint, dict)
            and isinstance(checkpoint.get("head_hash"), str)
            and checkpoint["head_hash"].startswith("sha256:")
            and len(checkpoint["head_hash"]) == 71
            and all(character in "0123456789abcdef" for character in checkpoint["head_hash"][7:])
        )
        if (
            not isinstance(checkpoint, dict)
            or set(checkpoint) != expected_keys
            or checkpoint.get("version") != CHECKPOINT_VERSION
            or not isinstance(checkpoint.get("sequence"), int)
            or isinstance(checkpoint.get("sequence"), bool)
            or checkpoint["sequence"] < 1
            or not valid_hash
        ):
            raise PolicyBlock(
                "LEDGER_CHECKPOINT_BROKEN",
                "Ledger head checkpoint violates its strict contract",
            )
        return checkpoint

    def _verify_checkpoint(
        self,
        events: list[dict[str, Any]],
        *,
        ledger_exists: bool,
    ) -> None:
        if not ledger_exists:
            if self.checkpoint_path.exists():
                raise PolicyBlock(
                    "LEDGER_CHECKPOINT_ORPHANED",
                    "Ledger head checkpoint exists without the ledger",
                )
            return
        checkpoint = self._read_checkpoint(required=True)
        if not events:
            raise PolicyBlock(
                "LEDGER_CHECKPOINT_MISMATCH",
                "Ledger is empty but its checkpoint claims a durable head",
            )
        tail = events[-1]
        if (
            checkpoint is None
            or checkpoint["sequence"] != tail["sequence"]
            or checkpoint["head_hash"] != tail["event_hash"]
        ):
            raise PolicyBlock(
                "LEDGER_CHECKPOINT_MISMATCH",
                "Ledger tail does not match its durable head checkpoint",
                details={
                    "checkpoint_sequence": checkpoint.get("sequence") if checkpoint else None,
                    "ledger_sequence": tail.get("sequence"),
                    "checkpoint_hash": checkpoint.get("head_hash") if checkpoint else None,
                    "ledger_hash": tail.get("event_hash"),
                },
            )

    def _verify_events(self, events: list[dict[str, Any]]) -> None:
        previous = ZERO_HASH
        for sequence, event in enumerate(events, start=1):
            try:
                validate_data(self.workspace, "ledger-event", event)
            except TempoError as exc:
                raise PolicyBlock(
                    "LEDGER_CHAIN_BROKEN",
                    f"Ledger event {sequence} violates the event schema",
                    details={"cause": exc.reason_code},
                ) from exc
            if (
                event.get("sequence") != sequence
                or event.get("previous_hash") != previous
                or event.get("event_hash") != _event_hash(event)
            ):
                raise PolicyBlock("LEDGER_CHAIN_BROKEN", f"Ledger integrity failed at event {sequence}")
            previous = event["event_hash"]
