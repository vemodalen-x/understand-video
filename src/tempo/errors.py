"""Stable exit-code and error contracts for machine-facing commands."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EXIT_ALLOWED = 0
EXIT_POLICY_BLOCK = 2
EXIT_CHECKER_FAILURE = 3
EXIT_WARNING = 4


@dataclass
class TempoError(Exception):
    """A user-facing error with a stable reason code and exit status."""

    reason_code: str
    message: str
    exit_code: int
    details: dict[str, Any] = field(default_factory=dict)
    next_action: str | None = None

    def __str__(self) -> str:
        return self.message

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": False,
            "reason_code": self.reason_code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        if self.next_action:
            payload["next_action"] = self.next_action
        return payload


class PolicyBlock(TempoError):
    """A deterministic governance decision that denies an action."""

    def __init__(
        self,
        reason_code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        next_action: str | None = None,
    ) -> None:
        super().__init__(
            reason_code,
            message,
            EXIT_POLICY_BLOCK,
            details or {},
            next_action,
        )

class CheckerFailure(TempoError):
    """A failed or unavailable checker; authority-sensitive calls fail closed."""

    def __init__(
        self,
        reason_code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        next_action: str | None = None,
    ) -> None:
        super().__init__(
            reason_code,
            message,
            EXIT_CHECKER_FAILURE,
            details or {},
            next_action,
        )


class TempoWarning(TempoError):
    """A non-blocking warning; never used for safety or authorization failures."""

    def __init__(
        self,
        reason_code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        next_action: str | None = None,
    ) -> None:
        super().__init__(
            reason_code,
            message,
            EXIT_WARNING,
            details or {},
            next_action,
        )
