# TEMPO 4afc6a3 source-grounded video map

Target repository: `https://github.com/vemodalen-x/TEMPO`

Target commit: `4afc6a3f5ceba0240f7fdd2eece96241253d6e60`

All claims below were checked against the independent TEMPO checkout. They are
storyboard inputs, not permission to implement or publish.

## Required explanation claims

| ID | Claim | Source references |
| --- | --- | --- |
| C-TEMPO-001 | TEMPO separates business readiness from engineering authority. | `README.md:25-39`; `docs/adr/0001-business-to-mvp-boundary.md:19-33` |
| C-TEMPO-002 | Provider/model output is advice and cannot carry warrant, human signature, or build-allowed fields. | `src/tempo/providers.py:16-47`; `src/tempo/providers.py:97-116`; `tests/test_provider_boundary.py:14-35` |
| C-TEMPO-003 | Readiness is deterministic; even `MVP_AUTHORIZED` writes `authorization_valid: false` and `build_allowed: false`. | `src/tempo/readiness.py:243-346`; `src/tempo/readiness.py:529-610`; `tests/test_readiness.py:27-37` |
| C-TEMPO-004 | A real warrant is human-controlled, TTY-gated, time-limited, and bound to scope, lane, action, budget, deadline, and protected hashes. | `src/tempo/warrant.py:238-317`; `src/tempo/warrant.py:350-416`; `tests/test_authorization.py:31-72` |
| C-TEMPO-005 | Every start revalidates task traceability and authority; protected drift permanently invalidates a warrant. | `src/tempo/warrant.py:541-644`; `src/tempo/warrant.py:753-804`; `tests/test_authorization.py:333-356` |
| C-TEMPO-006 | Audit events form a serialized hash chain with a durable head checkpoint; receipts remain local-integrity evidence and the human verdict stays blank. | `src/tempo/ledger.py:130-194`; `src/tempo/ledger.py:242-294`; `src/tempo/verify.py:597-663`; `src/tempo/verdict.py:15-25`; `src/tempo/verdict.py:159-244` |
| C-TEMPO-007 | The credential-free demo shows both allowed and rejected paths and deliberately finishes with `build_allowed: false`. | `src/tempo/demo.py:113-384` |

## Live demo contract

Run from the pinned TEMPO checkout:

```powershell
python bin/tempo demo
```

Expected top-level outcome: `JUDGE_DEMO_PASSED`.

Required visible beats:

1. model-only evidence returns `EXPERIMENT_REQUIRED`;
2. readiness passes without creating authority;
3. start without a warrant returns `WARRANT_MISSING`;
4. a bounded fixture warrant permits one in-scope start;
5. out-of-scope start returns `SCOPE_NOT_AUTHORIZED`;
6. protected drift returns `PROTECTED_INPUT_DRIFT`;
7. restoring bytes does not revive the invalidated warrant;
8. the ledger chain verifies and the human verdict remains blank.

The read-only audit-console B-roll may show `SCOPE_NOT_AUTHORIZED`,
`VALID_WARRANT_AND_SCOPE`, and `PROTECTED_INPUT_DRIFT` in sequence. Its
synthetic-fixture label must remain visible.

## Claim boundaries

- TEMPO is a hackathon vertical slice, not a production authorization service.
- Local commands are not a hostile-code sandbox; local ledger and receipts are
  not external notarization.
- Demo and audit-console fixtures prove mechanisms, not customer demand,
  production identity, or market impact.
- The current TEMPO runtime does not call the OpenAI API. GPT-5.6 is accurately
  described as materially used through Codex during the build.
- No measured time or cost savings are claimed.
