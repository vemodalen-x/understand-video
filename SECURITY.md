# Security policy

TEMPO is an early-stage governance kernel for deciding whether an agent may
begin a bounded MVP build. It is not a general-purpose operating-system
sandbox, an identity provider, or a substitute for legal, privacy, security,
or financial review.

## Security invariants

- Imported web pages, proposals, interview notes, model output, and fixture
  data are untrusted evidence. They cannot authorize implementation.
- Business readiness and implementation authority are separate decisions. A
  readiness result of `MVP_AUTHORIZED` means *eligible for human
  authorization*; it does not permit a build by itself.
- A build requires a current, scope-bounded, budget-bounded, deadline-bounded
  warrant. Protected-input drift, expiry, or revocation invalidates it.
- A commercial planning provider may propose normalized artifacts but cannot
  sign a charter, create a warrant, fill the human verdict, or mark a receipt
  as passed.
- Ledger writes are serialized and hash chained; a durable local head
  checkpoint detects tail truncation. Verification receipts must be generated
  from executed checks, not written as narrative evidence.
- Secret-like content, credential paths, destructive actions, freeze
  violations, and out-of-scope writes are policy blocks.
- Exit codes are stable: `0` pass, `2` policy block, `3` checker failure, and
  `4` non-blocking warning.

The kernel-construction instruction is recorded in
`governance/bootstrap-authorization.json`; the user's separate request to
create and publish this standalone submission repository is recorded in
`governance/repository-publication-authorization.json`. Neither record is a
reusable product warrant, and neither authorizes deployment, video upload, or
Devpost submission.

## Trust and isolation boundary

Local Python execution provides deterministic validation and integrity checks,
not hostile-code containment. The stronger verification profile runs in a
digest-pinned container as an unprivileged user with networking disabled; see
[SANDBOX_CONTRACT.md](SANDBOX_CONTRACT.md). A local receipt truthfully records
`local_integrity_only` unless an isolated or externally attested execution
actually occurred.

The credential-free demo uses explicit fixture provenance and a demo-only
signer bound to one disposable workspace, MVP, and session. It demonstrates
control flow; it does not represent customer validation, a production
signature, or an external attestation.

Evidence source type, collector, and provenance are validated declarations,
not proof of real-world authenticity. The built-in provider path forces its own
output to model-synthesis provenance, but a production external-evidence path
would additionally need trusted identity and signed source attestations.

## Supported environment

The command-line workflow targets Python 3.10 or later on Windows, macOS, and
Linux. CI exercises the POSIX and isolated-container profiles, but remains
non-authoritative until a signed-attestation verifier and trust policy exist.
Platform limitations or missing container tooling must be reported as warnings
or checker failures, never silently converted into a pass.

## Reporting a vulnerability

Do not include secrets, tokens, customer data, or exploit details in a public
issue. Once the repository is public, use its private GitHub security-advisory
channel. Until that channel exists, contact the repository owner through a
private channel and include:

1. the affected version and platform;
2. a minimal reproduction without live credentials;
3. the invariant or trust boundary that can be bypassed; and
4. the practical impact and any known mitigation.

No response-time SLA is promised for this hackathon release.
