#!/usr/bin/env python3
"""Generic stdin-JSON hook adapter: exit 0 allow, 2 block, 3 checker failure."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from tempo.errors import TempoError  # noqa: E402
from tempo.guards import evaluate_event  # noqa: E402
from tempo.util import Workspace  # noqa: E402


def main() -> int:
    try:
        event = json.load(sys.stdin)
        result = evaluate_event(Workspace.from_path(ROOT), event)
        print(json.dumps(result, sort_keys=True))
        return 0
    except TempoError as exc:
        print(json.dumps(exc.as_dict(), sort_keys=True), file=sys.stderr)
        return exc.exit_code
    except Exception as exc:  # fail closed without a traceback/secret echo
        print(json.dumps({"ok": False, "reason_code": "HOOK_CHECKER_FAILED", "message": type(exc).__name__}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
