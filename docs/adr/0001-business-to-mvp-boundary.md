# ADR 0001: Separate business readiness from implementation authority

- Status: accepted
- Date: 2026-07-17
- Decision owners: human business owner (intent), deterministic kernel (mechanism)

## Context

The source brief requires readiness to precede a human warrant, but also lists
"no valid human authorization" among readiness blockers and restricts the
outcome vocabulary to `MVP_AUTHORIZED`, `EXPERIMENT_REQUIRED`,
`PIVOT_REQUIRED`, `KILL_RECOMMENDED`, and `BLOCKED_INVALID_INPUT`. Applying the
authorization blocker inside the pre-authorization assessment would create a
cycle: the assessment could never pass, so a warrant could never be issued.

The term "L0" is also overloaded: TEMPO v1.3 uses it for its small legacy hook
kernel, while this project uses L0 for the upstream business-decision layer.

## Decision

1. `tempo mvp assess` makes a deterministic **business-readiness** decision.
   `MVP_AUTHORIZED` in that response means "eligible for a human authorization
   decision". The response also exposes `eligible_for_authorization`,
   `authorization_valid`, and an `assessment_hash`; it never starts a build.
2. `tempo mvp authorize` is a separate authority transition. It consumes the
   current assessment hash and requires a real TTY confirmation or a separately
   verified signer attestation. A proposal provider cannot invoke this
   transition through its import contract.
3. `tempo mvp start` revalidates the warrant, protected hashes, scope, budget,
   and deadline. Missing authorization is a hard blocker at this implementation
   gate, not a circular prerequisite for calculating readiness.
4. Documentation calls the inherited TEMPO v0.1.1 mechanism the **legacy K0
   kernel**. L0 is reserved for business decision artifacts.
5. The hackathon profile uses the new 8/12/15/20/45/62/70/76/82/95 schedule.

## Consequences

- A machine may say a case is ready to be considered, but only a human/signer
  can create authority.
- The exact assessment is hash-bound into the warrant, so reassessment or
  protected-input drift invalidates authority.
- Status and JSON output must keep readiness and authorization visibly separate.
- Tests must prove that a high score, provider recommendation, or typed `pass`
  cannot cross the implementation boundary.
