# TEMPO — Devpost project description draft

> Status: draft, not submitted. Resolve every item in `submission/checklist.md`
> before copying this text to Devpost.

## Tagline

Turn “should we build?” into a testable, human-authorized workflow before coding
agents spend the budget.

## Inspiration

Coding agents have compressed implementation time, but the business decision
upstream is still messy. Teams often start an MVP before they agree on the
target user, rank-1 uncertainty, evidence threshold, economics, cheaper
experiment, budget, deadline, and kill condition. The result is fast output
without a clear decision.

TEMPO treats that as a Work & Productivity problem. Research, product, finance,
engineering, and the business owner need one reviewable path from question to
evidence to bounded execution.

## What it does

TEMPO is a deterministic business-to-MVP governance workflow for product and
innovation leads who supervise coding-agent work. A commercial planning
provider can propose an opportunity, business model, hypothesis, and
experiment. TEMPO normalizes that output as untrusted input, validates typed
measurements plus declared provenance and freshness, evaluates hard blockers
before scoring, and returns
either the cheapest next experiment or eligibility for a human authorization
decision.

Eligibility is not permission. A separate warrant binds the exact assessment,
charter, hypothesis set, evidence manifest, policy, scope, budget, and deadline.
Every implementation start revalidates that contract. Expiry, revocation,
protected-input drift, overspend, or an out-of-scope action fails closed.

The workflow records serialized hash-chained events with a durable local head,
produces machine verification receipts, and compiles a verdict memo whose final
decision remains human-owned.

## How we built it

The vertical slice is a dependency-light Python 3.10+ CLI with Draft 2020-12
schemas, deterministic state transitions, evidence freshness/provenance checks,
a hash-bound authorization gate, filesystem/action guards, a tamper-evident
local ledger, and receipt generation. A clean-clone demo requires no credentials and
uses visibly labeled fixtures. CI adds a digest-pinned, unprivileged,
network-disabled container profile.

The design adapts selected governance mechanisms from the supplied TEMPO v1.3
specification and the MIT-licensed VEMO framework at pinned commit
`dc8e58a5e3d6710fc26331f1cbb17284d9071217`. Private course-derived material
from the earlier commercial agent was not copied; only a normalized business
workflow contract was retained.

## How we used Codex and GPT-5.6

Codex Desktop with GPT-5.6 in the user-selected Sol Ultra mode was the primary
engineering environment for architecture, implementation, tests, and
documentation under the repository's checked-in `AGENTS.md` policy. GPT-5.6
materially reconciled the three design sources, surfaced the circularity between
readiness and authorization, helped turn that decision into deterministic
schemas and kernel logic, generated adversarial cases, shaped the credential-
free demo, and tightened this submission narrative. Those contributions map to
specific files in `submission/ai-usage.json`.

This is build-time GPT-5.6 use inside Codex. The release does not call the
OpenAI API at runtime. Its provider adapter normalizes recorded JSON, and the
`openai/gpt-5.6` sample proposal is explicitly a fixture rather than live API
evidence. The final Devpost form still requires the exact session value returned
by `/feedback` from the primary build task.

## Challenges

The hardest boundary was separating a machine's readiness decision from a
human's authority to spend implementation effort. Combining them creates a
circular or self-authorizing system. We resolved that with two explicit states:
`MVP_AUTHORIZED` means eligible for a human decision, while `build_allowed`
becomes true only after a valid warrant and start check.

We also had to make negative outcomes productive. A denial names the reason,
the governing artifact, the evidence gap, and one next action instead of only
returning “no.” Finally, we kept the demo reproducible without disguising
fixtures as external validation.

## Accomplishments

- One command demonstrates the full question-to-build control boundary.
- Model-generated synthesis cannot satisfy the external-evidence requirement.
- The local slice validates provenance declarations; it does not claim to
  authenticate a user-supplied source in the real world.
- Provider recommendations and high scores cannot create implementation
  authority.
- A valid build path is bounded by scope, lane, action, budget, deadline, and
  protected hashes.
- Drift and revocation persist terminal state in the warrant and a hash-bound
  ledger event; truncating the ledger tail is detected by its durable head
  checkpoint.
- Receipts record the command and environment that actually ran.
- The human verdict section cannot be filled by the compiler.

## What we learned

The best agent guardrail is sometimes a better team decision, not a more complex
runtime sandbox. Governance becomes useful when a blocker shortens the next
conversation: what do we need to learn, who owns it, what will it cost, and when
will we decide?

We also learned to separate evidence from inference. OpenAI's published UX and
approval guidance supports clear hierarchy, user control, confirmation at
consequential boundaries, and reproducible evals. It does not reveal private
judging preferences, so we designed for those public principles instead of
claiming inside knowledge.

## Potential impact

The primary user is a product or innovation lead repeatedly handing ambiguous
initiatives to coding agents; founders, research, finance, engineering, and
agencies are secondary workflow participants. TEMPO could reduce avoidable
implementation starts, make cross-functional handoffs explicit, and give the
business owner a reviewable decision trail. A real-team pilot would measure
avoidable starts blocked, decision-cycle duration, time to identify the next
experiment, and scope/budget drift caught. We do not yet claim measured time or
cost savings.

## What's next

Next steps are a small pilot measuring avoided starts and decision-cycle time,
a separately reviewed OpenAI Responses API provider adapter, remote signer
attestations, richer receipt verification, and a compact UI over the same
deterministic kernel. None of those future items are presented as implemented in
this submission.

## Try it

```bash
git clone https://github.com/vemodalen-x/TEMPO.git
cd TEMPO
python bin/tempo selfcheck
python bin/tempo demo
```

Repository: [github.com/vemodalen-x/TEMPO](https://github.com/vemodalen-x/TEMPO)

Video: `<public-youtube-url>`

Category: **Work & Productivity**
