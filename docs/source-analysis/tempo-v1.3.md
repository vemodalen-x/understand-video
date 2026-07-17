# TEMPO v1.3 factual extraction

The package separates three versions: documentation release 1.3, full framework
specification 0.3.0, and implemented legacy K0 kernel 0.1.1. Documentation
volume is not implementation evidence.

Implemented K0 mechanisms are canonical path containment, feature-freeze globs,
secret/credential-path detection, destructive-command detection, fail-closed
checker errors, exact config-consumer checks, document/manifest drift checks,
and a release acceptance driver. CLI orchestration, task/beat state, lanes,
ledger, sessions, receipts, replay/judge gates, authorization, narration, and
submission checks are specified rather than implemented.

Baseline execution on Windows with Python 3.10.12 produced 32 passing ordinary
behavior cases, passing selfcheck and doccheck, five compiling Python sources,
three valid JSON authorities, and a valid 33-entry ZIP. The full acceptance run
then stopped because the escaping-symlink case requires a Windows privilege not
present (`WinError 1314`). This repository does not report that baseline as a
cross-platform green run.

Mechanisms retained: capability-invariant safety, time-anchored verification,
README-as-tested-interface, D-tier demo criticality, truthful `ENFORCED-BY`
claims, evidence compilation, and a human-only final verdict.
