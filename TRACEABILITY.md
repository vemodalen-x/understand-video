# Requirement traceability

This table points from the submission claim to its authority, implementation,
and repeatable proof. A file path alone is not evidence that a check passed;
run the listed command and inspect the generated receipt or exit code.

| Requirement | Authority / control | Implementation surface | Repeatable proof |
| --- | --- | --- | --- |
| Work & Productivity track | `config/tempo.config.json` | Cross-functional decision-to-build workflow | `python bin/tempo submit-check` |
| Deterministic readiness | Readiness policy plus hard blockers | `src/tempo/readiness.py`, assessment schema | `python bin/tempo --json mvp assess` |
| Declared non-model evidence required | Evidence type, declared provenance, freshness, fixture flags | `src/tempo/evidence.py`, evidence schema | `python bin/tempo --json evidence validate`; authenticity is not externally attested |
| Model output cannot self-validate | Provider normalization and provenance boundary | `src/tempo/providers.py`, commercial-proposal schema | Demo's first assessment remains blocked |
| One rank-1 falsifiable hypothesis | Hypothesis schema and hard blockers | hypotheses schema, readiness evaluator | Readiness conformance tests |
| Rank-1 threshold actually reached | Typed evidence measurements plus declared aggregation/operator/target | `src/tempo/readiness.py`, hypotheses/evidence/assessment schemas | Threshold pass/fail readiness tests and demo report |
| Cheaper experiment before MVP | Decision brief and hard blocker | readiness evaluator | Demo reports `CHEAPER_SUFFICIENT_EXPERIMENT` when present |
| Human authority is separate | ADR 0001 and warrant schema | `src/tempo/warrant.py` | Start-before-warrant demo step exits `2` |
| Scope, budget, deadline, drift | Hash-bound warrant and task record | warrant validator and start gate | Warrant conformance tests and demo drift step |
| Tamper-evident local history | Ledger-event schema, serialized append, durable head checkpoint | `src/tempo/ledger.py` | Ledger truncation/concurrency tests; `python bin/tempo --json ledger verify` |
| Secret, credential, destructive, freeze guards | Repository policy | `src/tempo/guards.py`, hook adapter | Guard regression tests |
| Machine-generated verification | Receipt schema | `src/tempo/verify.py` | `python bin/tempo --json verify --level all` |
| Human-owned verdict | Human markers in verdict memo | `src/tempo/verdict.py` | `python bin/tempo verdict compile`; preservation tests |
| Credential-free judge path | Explicit fixture provenance | `src/tempo/demo.py`, `samples/business-mvp/` | `python bin/tempo --json demo` |
| Clean-clone instructions | README setup/run sections | `README.md`, `bin/tempo` | `python bin/tempo --json verify --level all` |
| True isolated verification | Sandbox contract and pinned config | `.github/workflows/ci.yml` | CI judge-container job |
| Submission completeness | Official Build Week requirements | `src/tempo/submit.py`, submission draft/checklist | `python bin/tempo --json submit-check` |
| Codex `/feedback` record | Organizer submission field | `submission/session.json` | Confirm the actual `/feedback` output before submission |

## Source lineage

- The supplied TEMPO v1.3 design archive is a specification source and is not
  redistributed.
- VEMO mechanisms are adapted from commit
  `dc8e58a5e3d6710fc26331f1cbb17284d9071217`; see
  `THIRD_PARTY_NOTICES.md`.
- The earlier commercial-agent workflow is reduced to a normalized contract.
  Private course-derived content is not copied into this repository.

See `docs/source-analysis/` for hashes, version distinctions, conflicts, and
Windows-specific baseline limitations.
