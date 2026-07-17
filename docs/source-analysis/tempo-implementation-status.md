# TEMPO implementation status

Baseline: `40ad40f639fff09f433ced9ac22f1ad236b22a0b`

The repository's `MANIFEST.json`, executable paths, tests, demo, and local
verification were inspected. The following distinction avoids treating prose
as enforcement.

## Executably implemented

- Draft 2020-12 schemas and runtime validation for opportunity, business model,
  hypotheses, evidence, policy, decision brief, charter, assessment, warrant,
  receipt, and ledger event records.
- Immutable evidence files with a serialized hash-linked manifest, freshness
  validation, model/fixture classification, contradiction retention, and typed
  hypothesis measurements.
- Hard-blocker-first deterministic readiness scoring with dimension floors,
  aggregate threshold, cheaper-experiment output, and stable exit codes.
- Charter materialization from a proposal and TTY-required human charter
  signing. Signing does not grant authority.
- A distinct warrant boundary with TTY-required human authorization, protected
  input hashes, TTL, revocation, scope, budget, deadline, lane, action, and
  implementation-start checks.
- Serialized hash-chained ledger events and a durable local head checkpoint.
- Machine-generated local verification receipts and a compiler that keeps the
  final human verdict/signature blank.
- Secret, credential-path, freeze, destructive-action, external-action, scope,
  and budget guards exposed through the CLI/hook path.
- A repository hook adapter, GitHub Actions workflow, deterministic test suite,
  clean demo, submission checker, and digest-pinned unprivileged network-off
  container verification profile.
- Risk tiers in the charter (`R0`-`R2`), D-tier demo beats (`D0`-`D3`), task
  records, explicit allowed lanes, and the current implementation manifest.

The local practice run produced `JUDGE_DEMO_PASSED`, a complete local
verification receipt, and `LEDGER_VALID`.

## Mixed or local-integrity only

- A human signer is represented by a declared actor string plus interactive TTY
  confirmation. This prevents agent/non-interactive self-signing in the normal
  CLI but is not production identity proof or non-repudiation.
- Evidence source, collector, and provenance are validated declarations. TEMPO
  does not authenticate a supplied real-world source.
- The local ledger and head checkpoint detect ordinary drift and truncation but
  cannot stop the same operating-system identity from rewriting all local
  history. The isolated CI profile is stronger, not an external notarization.
- Local commands provide policy and integrity checks, not hostile-code
  containment. Container isolation exists as a verification profile.
- Hooks are implemented but enforcement depends on installation and the host;
  the CI workflow is the reproducible backstop.

## Specified, intentionally absent, or external

- Production signing, trusted identity, externally attested evidence, and
  remote authorization services are not implemented.
- The commercial planning provider normalizes fixtures and does not make a live
  OpenAI API call.
- Deployment, video upload, and Devpost submission are not implemented or
  authorized.
- No current TEMPO control proves the proposed video's learner outcome; that
  requires observed external evidence.
- The existing tracked task applies to TEMPO's completed vertical slice. No
  task or warrant currently authorizes the Understand Video implementation.
