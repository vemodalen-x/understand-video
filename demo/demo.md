# Judge demo

The demo is a deterministic, credential-free D0 journey for a product team
deciding whether to build an AI-enabled workflow. It should complete from a
clean clone with:

```bash
python bin/tempo demo
```

Use `python bin/tempo --json demo` for a machine-readable step report.

## Expected story

| Beat | Expected result | What it proves |
| --- | --- | --- |
| Context and import | Proposal is normalized, never trusted as authority | Models assist planning without self-approval |
| First readiness check | `EXPERIMENT_REQUIRED`, exit `2` | Missing/insufficient external evidence stops the build path |
| Explicit demo evidence | Typed fixture measurements and provenance stay visible | The demo is reproducible without pretending validation |
| Second readiness check | Rank-1 threshold passes; `MVP_AUTHORIZED`, but `build_allowed: false` | A measured eligibility decision is still not authorization |
| Start without warrant | Policy block, exit `2` | A score cannot cross the human boundary |
| Demo authorization | Local-integrity, demo-only warrant | Scope/budget/deadline/hashes are bound |
| In-scope start | Allowed | A valid bounded path exists |
| Out-of-scope or drift attempt | Policy block, exit `2` | Authority fails closed when the contract changes |
| Verification and ledger | Local-integrity receipt, valid chain, durable head checkpoint | Claims have inspectable, tamper-evident local execution evidence |
| Verdict memo | Human section remains blank | The system cannot grade itself into approval |

Exact generated identifiers and timestamps vary. Reason codes, exit semantics,
state transitions, and fixture labels are deterministic.

## What not to claim

- Fixture evidence is not a customer interview or real conversion signal.
- The demo signer is not a production identity or cryptographic remote signer.
- A local receipt is not externally attested.
- This slice does not deploy a product, contact users, spend money, or submit to
  Devpost.
- The runtime does not call GPT-5.6 or any other hosted model.

## Useful follow-up commands

```bash
python bin/tempo mvp status
python bin/tempo evidence validate
python bin/tempo ledger verify
python bin/tempo verify --level all
python bin/tempo verdict compile
python bin/tempo submit-check
```

`submit-check` is expected to remain blocked until the repository URL, public
video, confirmed `/feedback` session ID, and final owner review are present.
