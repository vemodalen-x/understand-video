"""Filesystem, hashing, canonical JSON, and workspace utilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import tempfile
from typing import Any, Iterable

from .errors import CheckerFailure, PolicyBlock


def _comparison_path(path: Path) -> str:
    """Normalize equivalent Win32 extended/non-extended paths for containment."""
    value = os.path.normcase(os.path.abspath(str(path)))
    if os.name == "nt":
        if value.startswith("\\\\?\\UNC\\"):
            value = "\\\\" + value[8:]
        elif value.startswith("\\\\?\\"):
            value = value[4:]
    return os.path.normpath(value)


def _is_within(candidate: Path, root: Path) -> bool:
    candidate_value = _comparison_path(candidate)
    root_value = _comparison_path(root)
    try:
        return os.path.commonpath((candidate_value, root_value)) == root_value
    except ValueError:
        return False


def utc_now() -> datetime:
    """Return a timezone-aware UTC time; isolated for deterministic tests."""
    return datetime.now(timezone.utc)


def isoformat_z(value: datetime | None = None) -> str:
    """Render a UTC timestamp with a stable `Z` suffix."""
    current = value or utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_datetime(value: str) -> datetime:
    """Parse an RFC3339/ISO timestamp and require an explicit timezone."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise CheckerFailure("INVALID_TIMESTAMP", f"Invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise CheckerFailure("TIMEZONE_REQUIRED", f"Timestamp must include a timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def canonical_json_bytes(value: Any) -> bytes:
    """Encode data for stable cross-platform hashing."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise CheckerFailure("ARTIFACT_UNREADABLE", f"Cannot hash {path}: {exc}") from exc
    return "sha256:" + digest.hexdigest()


def load_json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError as exc:
        raise PolicyBlock(
            "ARTIFACT_MISSING",
            f"Required artifact is missing: {path}",
            details={"path": str(path)},
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckerFailure(
            "ARTIFACT_INVALID_JSON",
            f"Cannot read JSON artifact {path}: {exc}",
            details={"path": str(path)},
        ) from exc


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a text artifact in its own directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise PolicyBlock("SYMLINK_WRITE_BLOCKED", f"Refusing to replace symlink: {path}")
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def canonical_relpath(raw: str) -> str:
    """Validate and normalize one repository-relative path."""
    if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
        raise PolicyBlock("INVALID_REPO_PATH", "Repository path must be a non-empty string")
    normalized = raw.replace("\\", "/")
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(raw)
    if posix.is_absolute() or windows.is_absolute() or bool(windows.drive):
        raise PolicyBlock("PATH_OUTSIDE_REPOSITORY", f"Absolute path is not allowed: {raw}")
    # NTFS aliases (alternate data streams, trailing dot/space elision, and
    # reserved device names) can make two spellings address the same object.
    # Reject them on every host so policy decisions remain cross-platform.
    if ":" in raw:
        raise PolicyBlock("INVALID_REPO_PATH", f"Colon/alternate-stream syntax is not allowed: {raw}")
    if ".." in posix.parts:
        raise PolicyBlock("PATH_OUTSIDE_REPOSITORY", f"Parent traversal is not allowed: {raw}")
    parts = [part for part in posix.parts if part not in ("", ".")]
    if not parts:
        raise PolicyBlock("INVALID_REPO_PATH", "Path resolves to repository root")
    reserved = {"con", "prn", "aux", "nul", "clock$"}
    reserved.update({f"com{index}" for index in range(1, 10)})
    reserved.update({f"lpt{index}" for index in range(1, 10)})
    for part in parts:
        if part.endswith((".", " ")):
            raise PolicyBlock(
                "INVALID_REPO_PATH",
                f"Windows-trimmed path segments are not allowed: {raw}",
            )
        device_stem = part.split(".", 1)[0].casefold()
        if device_stem in reserved:
            raise PolicyBlock("INVALID_REPO_PATH", f"Reserved Windows device name: {raw}")
    return PurePosixPath(*parts).as_posix()


@dataclass(frozen=True)
class Workspace:
    """A resolved repository root and containment-aware path resolver."""

    root: Path

    @classmethod
    def from_path(cls, raw: str | Path) -> "Workspace":
        root = Path(raw).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise CheckerFailure("WORKSPACE_INVALID", f"Workspace is not a directory: {root}")
        return cls(root)

    @classmethod
    def discover(cls, start: str | Path = ".") -> "Workspace":
        current = Path(start).expanduser().resolve(strict=True)
        if current.is_file():
            current = current.parent
        for candidate in (current, *current.parents):
            if (candidate / "MANIFEST.json").exists() or (candidate / ".git").exists():
                return cls(candidate)
        raise CheckerFailure("WORKSPACE_NOT_FOUND", "No TEMPO or Git workspace found")

    def path(self, relative: str) -> Path:
        canonical = canonical_relpath(relative)
        root = self.root.resolve(strict=True)
        candidate = root.joinpath(*PurePosixPath(canonical).parts).resolve(strict=False)
        if not _is_within(candidate, root):
            raise PolicyBlock(
                "PATH_OUTSIDE_REPOSITORY",
                f"Path escapes repository through a symlink: {relative}",
            )
        return candidate

    def relative(self, path: Path) -> str:
        resolved = path.resolve(strict=False)
        root = self.root.resolve(strict=True)
        if not _is_within(resolved, root):
            raise PolicyBlock("PATH_OUTSIDE_REPOSITORY", f"Path is outside workspace: {path}")
        relative = os.path.relpath(_comparison_path(resolved), _comparison_path(root))
        return PurePosixPath(relative.replace("\\", "/")).as_posix()

    def ensure_directories(self, relatives: Iterable[str]) -> None:
        for relative in relatives:
            self.path(relative).mkdir(parents=True, exist_ok=True)


def artifact_hashes(workspace: Workspace, relatives: Iterable[str]) -> dict[str, str]:
    """Hash required protected inputs, failing closed when one is unavailable."""
    result: dict[str, str] = {}
    for relative in relatives:
        path = workspace.path(relative)
        if not path.is_file():
            raise PolicyBlock(
                "PROTECTED_ARTIFACT_MISSING",
                f"Protected artifact is missing: {relative}",
                details={"artifact": relative},
            )
        result[relative] = sha256_file(path)
    return result
