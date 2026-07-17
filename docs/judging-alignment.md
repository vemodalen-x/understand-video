# OpenAI Build Week judging alignment

TEMPO is entered in **Work & Productivity**, which the organizer defines as
tools that make teams faster or more effective, including workflow automation,
analytics, sales, and back-office operations. TEMPO shortens a
cross-functional workflow that currently leaks product, research, design, and
engineering time. It turns an ambiguous “should we build?” request into an
evidence-backed next action or a bounded, human-authorized MVP build.

## Official requirements and criteria

The [OpenAI Build Week site](https://openai.devpost.com/),
[rules](https://openai.devpost.com/rules), and
[FAQ](https://openai.devpost.com/details/faqs) are the authorities. The project
must first pass theme/tool viability. Eligible entries are then judged on four
equally weighted criteria:

1. technological implementation;
2. design;
3. potential impact; and
4. quality of idea.

The published tie-break order is technological implementation, design,
potential impact, then quality of idea. Submission packaging also requires a
runnable repository, license/access for judges, a public YouTube video shorter
than three minutes with audio, a description, category, and the Codex session
ID produced by `/feedback`. Both Codex and GPT-5.6 must be used meaningfully,
not incidentally or decoratively, and their roles must be explained in the
README and video. `submission/ai-usage.json` maps the material build-time use to
repository artifacts; `submission/checklist.md` tracks the remaining external
items without pretending they are complete.

## How the runnable slice answers each criterion

### Technological implementation

- Deterministic hard-blocker-first scoring, not an LLM opinion presented as a
  gate.
- The rank-1 business hypothesis is evaluated from typed evidence measurements
  using an explicit aggregation, operator, target, unit, source mix, and
  minimum sample count; a declared threshold is not merely checked for syntax.
- Draft 2020-12 schemas and runtime validation for business artifacts,
  assessments, warrants, receipts, and ledger events.
- Human authorization separated from readiness, hash-bound to protected
  inputs, reloaded after interactive confirmation, and revalidated at
  implementation start; issue, revoke, and start share one serialization lock.
- Revocation, expiry, protected drift, and demo-context drift persist terminal
  warrant state plus a ledger binding, so restoring earlier bytes is not a
  supported recovery path.
- A serialized hash-chained ledger with a durable head checkpoint, machine-
  generated local-integrity receipts, stable exit codes, and containment,
  secret, freeze, and action guards.
- A credential-free end-to-end fixture plus an isolated CI profile.
- Artifact-linked evidence of how Codex with GPT-5.6 reconciled source designs,
  resolved the readiness/authority circularity, implemented the kernel, and
  generated adversarial conformance tests (`submission/ai-usage.json`).

The demo deliberately shows denials as well as the happy path. A control that
cannot prove it stops work is not persuasive governance.

### Design

The interface follows a consistent information order:
**Outcome → Why → Evidence → Next action**. Blockers name the artifact to fix;
status output keeps readiness and authority visually and semantically separate;
JSON output supports automation while readable terminal output supports a
business owner. The shortest judge path is one command, with deeper artifacts
available through progressive disclosure.

### Potential impact

The primary user is a product or innovation lead who repeatedly hands ambiguous
initiatives to coding agents. TEMPO can reduce avoidable implementation starts
and make the decision trail reviewable.

| Before | With TEMPO | Pilot measure |
| --- | --- | --- |
| Ambiguous request moves directly into coding | Evidence gap returns one cheapest next experiment | Time to identify next experiment |
| Approval lives in chat | Readiness and human authority are separate, inspectable states | Decision-cycle duration |
| Scope or budget changes silently | Each start revalidates the bounded warrant | Avoidable starts blocked; drift caught |

This repository does **not** claim measured time or cost savings; avoided
starts, decision-cycle time, next-experiment latency, and drift detection are
the explicit metrics for a real-team pilot.

### Quality of idea

Common coding-agent permissions begin after a task is accepted. Chat approval
is fast but unbound; conventional stage gates are reviewable but often detached
from the repository; post-task agent permissions constrain execution without
testing whether the work is worth starting. TEMPO's differentiator is the
upstream, repository-native boundary: evidence quality, falsifiability,
alternatives, economic value, cheaper experiments, and separate human authority
decide whether implementation may begin at all.

## Design sensibilities: evidence versus inference

No public source describes private preferences of individual judges. We do not
claim otherwise. The following choices are product inferences from OpenAI's
public [Apps SDK UX principles](https://developers.openai.com/apps-sdk/concepts/ux-principles),
[UI guidelines](https://developers.openai.com/apps-sdk/concepts/ui-guidelines),
[app guidelines](https://developers.openai.com/apps-sdk/app-guidelines),
[agent approval and security guidance](https://developers.openai.com/codex/agent-approvals-security),
and [agent evaluation guidance](https://developers.openai.com/api/docs/guides/agent-evals):

- make the value and current state obvious before exposing mechanics;
- use restrained, consistent hierarchy instead of decorative complexity;
- require confirmation at consequential boundaries;
- make denials actionable and preserve user control;
- distinguish generated suggestions from authoritative decisions; and
- demonstrate reliability with reproducible evals and receipts.

These are defensible UX decisions, not inside knowledge about the panel.

## Judge path

1. Run the clean-clone setup in `README.md`.
2. Execute the one-command demo.
3. Observe model-only/insufficient evidence blocked.
4. Observe an evidence-backed case become eligible for authorization.
5. Observe start blocked without a warrant.
6. Observe one in-scope start succeed after demo authorization.
7. Observe protected-input drift invalidate the warrant.
8. Inspect the ledger, assessment, receipt, and blank human verdict section.

The video script keeps that sequence under three minutes and spends its opening
seconds on the work problem rather than the architecture.
