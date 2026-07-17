# Video script (target: 2:40)

The final video must be public on YouTube, shorter than three minutes, and
include audio. This is a script only; no upload has been performed.

## 0:00–0:20 — Problem first

**Screen:** title, then the workflow diagram in the README.

**Voice:** “Coding agents made implementation fast, but teams still waste time
building before they agree on the user, evidence, economics, budget, or kill
condition. TEMPO turns ‘should we build?’ into a testable next action—and only
then, with separate human authority, a bounded MVP build.”

## 0:20–0:35 — One-command judge path

**Screen:** clean terminal; run:

```bash
python bin/tempo demo
```

**Voice:** “This is a credential-free fixture, so every judge can run the same
path. Fixture provenance stays visible; I am not presenting it as customer
validation.”

## 0:35–1:05 — Productive blocker

**Screen:** first readiness output, emphasizing outcome, reason, evidence, and
next action.

**Voice:** “For the product lead, the planning proposal is useful but untrusted. With insufficient
declared non-model evidence, the deterministic kernel returns
`EXPERIMENT_REQUIRED` and the cheapest next experiment. This demo validates
typed declarations; it does not turn model confidence into business truth or
claim source attestation.”

## 1:05–1:35 — Readiness is not authority

**Screen:** second assessment, then start-before-warrant denial.

**Voice:** “Research gives the product lead typed sample measurements that reach
the rank-one threshold, so the case becomes eligible. Notice `build_allowed` is still
false. When the agent tries to start, TEMPO blocks it: a passing business gate
is not permission.”

## 1:35–2:05 — Bounded work and fail-closed drift

**Screen:** demo warrant, one permitted start, then charter drift denial.

**Voice:** “Engineering receives a demo-only, short-lived warrant bound to scope,
budget, deadline, and protected hashes. One in-scope start succeeds. Change the
charter, and the warrant invalidates immediately. Restoring bytes cannot erase
the terminal event.”

## 2:05–2:25 — Inspectable proof

**Screen:** ledger verification, receipt, and blank human verdict markers.

**Voice:** “Ledger writes are serialized and hash chained, and a durable head
detects tail deletion. Verification produces a local-integrity receipt with its
real environment and command. The verdict compiler preserves a blank human-
owned section, so the system cannot approve itself.”

## 2:25–2:40 — Codex/GPT-5.6 and close

**Screen:** `AGENTS.md`, `submission/session.json`, then project tagline.

**Voice:** “In our primary Codex Desktop task, GPT-5.6 reconciled three design
sources, caught the readiness-versus-authority circularity, helped encode that
decision in schemas and kernel logic, and generated adversarial tests. That is
material build-time use, mapped to files in the repo—not a live model call in
the product. TEMPO spends agent speed only after the decision is ready.”

Before recording, paste the confirmed `/feedback` value into the submission
record. Do not imply a live runtime API call; this release has none.

## Recording checklist

- Keep the timer below 2:55 to leave upload/transcoding margin.
- Use legible terminal zoom and a clean theme; do not rely on color alone.
- Narrate the work outcome before implementation details.
- Show at least one denial and the actionable next step.
- Show that fixture, local-integrity, and human-owned labels remain visible.
- Verify the final YouTube URL is public and audio plays in a private browser.
