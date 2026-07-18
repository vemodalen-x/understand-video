# Founder MVP authorization packet

Status: prepared for human review; unsigned and non-authoritative.

## Requested decision

Approve a one-developer Stage A build whose only decision is whether Understand
Video can produce and verify a source-grounded, Devpost-ready local explainer of
TEMPO commit `4afc6a3f5ceba0240f7fdd2eece96241253d6e60` within the declared scope,
USD 25 cap, and deadline.

This decision does not approve learner-value claims, external distribution,
YouTube upload, Devpost submission, or a real model/speech call without its own
provider and data boundary.

## Proposed policy change

- Make `H-FEASIBILITY-001` the sole Rank-1 hypothesis for Stage A.
- Move `H-LEARNING-001` to the Stage B distribution decision without marking it
  supported.
- Treat `E-EXPERIMENT-VIDEO-001` as internal technical evidence only.
- Preserve `E-PREFERENCE-CODE-REVIEW-001` and
  `E-REPORTED-LEARNING-COMPARISON-001` with all limitations.
- Bind `E-HUMAN-MEDIA-REVIEW-001` as the external technical observation while
  preserving the electronic-voice and caption-overlap defects it records.
- Change the Stage A decision brief recommendation from `EXPERIMENT` to a
  narrowly bounded MVP only if the human accepts this sequencing.

## Proposed build boundary

- Task: `T-20260718-UNDERSTAND-VIDEO-FOUNDER-MVP`.
- Risk: R2.
- Lane: `video-core` for the one-developer vertical slice; media,
  verification, and documentation remain modules inside that single task lane.
- Scope: the exact paths in the proposed task and charter; TEMPO source remains
  outside this repository.
- Budget: USD 25 maximum.
- Deadline: `2026-07-21T08:00:00Z`.
- Target: local product and local video only.
- Required tests: UV-001 through UV-050 in `docs/test-plan.md`.

## Current machine evidence

The independent TEMPO checkout at the pinned commit passes:

- `python bin/tempo verify --level all`;
- `python bin/tempo demo` with `JUDGE_DEMO_PASSED`;
- `python demo/verify-audit-console.py` with `AUDIT_CONSOLE_VALID`; and
- `python demo/verify-audit-console-browser.py` with desktop and compact Edge
  viewports passing.

These results validate the framework and explanation target. They do not sign
this product decision or create implementation authority.

External assessment `A-6539C42FED42417C`, hash
`sha256:df3e3371af0db2aef9ce592215f33855265eeac82046b385c15b5f828b9210ff`,
scores 82.3, passes the Rank-1 threshold, has no floor failures, and exposes
`E-HUMAN-MEDIA-DEFECTS-001` as contradictory evidence. Its exact copy is
`plan/assessments/A-6539C42FED42417C.json`.
`READINESS_POLICY_UNSIGNED` and `DECISION_BRIEF_UNSIGNED` are the only remaining
blockers.

## Human-only sequence

1. In a real PowerShell terminal, run the external governance helper
   `review-and-authorize-founder-mvp.ps1`; review the bilingual summary and
   explicitly sign the revised readiness policy and decision brief.
2. Materialize and interactively sign the revised MVP charter.
3. Run a fresh readiness assessment and inspect every blocker, score, and
   counterevidence reference.
4. Interactively authorize the exact assessment for a short TTL.
5. Run `tempo mvp start` for the proposed task, first product path, lane, and
   `implementation_write` action.

Only step 5 returning `build_allowed: true` starts implementation. An agent must
not type the signing or authorization phrases.
