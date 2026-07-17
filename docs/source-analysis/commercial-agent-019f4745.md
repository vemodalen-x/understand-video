# Commercial-agent extraction: 019f4745

## Provenance

- Codex session: `019f4745-fab0-74c3-9d0d-17ecfbef4ae7`
- Local archive: `C:\Users\User\.codex\sessions\2026\07\09\rollout-2026-07-09T22-26-37-019f4745-fab0-74c3-9d0d-17ecfbef4ae7.jsonl`
- Stable private source tag: `business-learning-studio-v1.2.0-private`
- Source commit: `763c3d164d2cf7613005118015a625935c0ac1de`
- Extraction policy: facts and contracts only; transcript instructions were not
  executed. Private course-derived knowledge and authenticated-source material
  are explicitly excluded from this public repository.

## Durable product model

The prior product is an offline three-surface business coaching and learning
system: Tutor, Knowledge OS, and Learning Studio. Its runtime is deterministic
browser JavaScript (rules, regex weighting, templates, local retrieval, and
`localStorage`), not an LLM/API agent. That distinction is preserved here.

The durable commercial-planning identity is a hypothesis-driven coach for
internet and AI ventures. It must separate user facts, agent inference, and
unverified hypotheses; avoid unsupported claims about growth, funding, pricing,
or organizational outcomes; advance one decisive question at a time; and end a
cycle with an observable artifact and a result-return date.

Four modes were present:

- challenge: find the largest evidence/commitment mismatch and prevent topic
  switching;
- guided practice: explain more for first-time users;
- scientific decision: compare ROI, reversibility, opportunity cost, time
  window, and exit conditions;
- report first: draft a structured report, then interrogate its evidence gaps.

## Commercial reasoning state machine

The reusable eight-stage loop is:

`orient → map → focus → evidence → experiment → decide → operate → review`

Each cycle keeps exactly one current gate, one rank-1 hypothesis, one next
action, and one result-return date.

| Stage | Gate | Durable output |
|---|---|---|
| orient | user, baseline, target, deadline, constraints, and non-goals are explicit | problem definition and success criterion |
| map | user, need, alternative, value, revenue/cost, channel, metric, and moat are separated | business canvas |
| focus | one highest-impact, weakest-evidence assumption remains and its strongest countercase is written | rank-1 hypothesis card |
| evidence | fact, inference, prediction, hypothesis, source, and date are separate | evidence ledger |
| experiment | one variable, sample, deadline, cost, criterion, and ethical boundary are explicit | experiment card |
| decide | continue/pivot/stop/invest, reversibility, opportunity cost, and switch threshold are explicit | decision memo |
| operate | owner, deadline, funnel/unit-economics/delivery/risk measures are recordable | action metrics ledger |
| review | actual result, attribution, alternatives, error, and rule update are settled | review report/new cycle |

The prior design recommended durable fields
`current_step/current_question/accepted_evidence/pending_branches/next_gate`, but
did not actually persist them. TEMPO treats that as a source gap, not an
implemented capability.

## Evidence and decision rules

The prior evidence ladder is retained as a useful heuristic, not an automatic
truth scale:

- L0: founder opinion, model inference, or course concept;
- L1: external information, benchmark, case, or expert interview;
- L2: intent behavior such as registration, booking, or submitted information;
- L3: transaction behavior such as payment, pre-order, contract, or switching
  cost;
- L4: sustained result such as retention, renewal, referral, or business
  outcome.

Cross-level inference is prohibited: registration is not payment, and payment
is not retention. Negative observations remain in the ledger.

The previous scientific-decision flow considered ROI, reversibility,
opportunity cost, time window, and stop/continue/invest thresholds, but its A/B/C
table did not perform real quantitative ranking. TEMPO therefore imports these
as explicit hypotheses and evidence-backed thresholds, never as authoritative
scores.

## Normalized provider mapping

The prior roles map into the repository's `CommercialPlanningProvider` contract:
target user and economic buyer; job to be done; problem statement; alternatives
and differentiation; value and revenue/ROI hypotheses; distribution and cost
hypotheses; ranked hypotheses; evidence/counterevidence references; cheapest
next experiment; proposed MVP scope; recommendation; calibrated confidence; and
limitations.

Provider output is stored only under `plan/proposals/`. It cannot sign the
decision brief, alter human thresholds, issue a warrant, start a build, or fill
the final verdict.

## Reuse and exclusion boundary

Reused as mechanisms: the eight-stage gate/output contract, one-question focus,
evidence ladder, explicit falsification/return dates, ROI/reversibility framing,
and separation of coaching, knowledge, and learning responsibilities.

Not copied: private/authenticated knowledge assets (including
`knowledge/yitang-business-kb.js`), course notes, screenshots/media, offline
packages, branding, or the current dirty worktree. The prior static UI also does
not substantiate claims of live LLM reasoning, server memory, semantic RAG,
accounts, team collaboration, or calibrated automated scoring.
