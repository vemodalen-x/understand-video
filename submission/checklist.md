# OpenAI Build Week submission checklist

Status: **not ready and not submitted**. This file tracks packaging; it does not
authorize publication, upload, deployment, or submission.

Authorities: [hackathon page](https://openai.devpost.com/),
[rules](https://openai.devpost.com/rules),
[resources](https://openai.devpost.com/resources), and
[FAQ](https://openai.devpost.com/details/faqs). Re-check them immediately before
submission in case the organizer changes a requirement.

Deadline recorded on 2026-07-17: **2026-07-22 00:00 UTC / 2026-07-21 17:00 PT /
2026-07-22 08:00 Singapore**.

## Hard blockers

- [x] Create the standalone remote repository and replace every
  `<repository-url>` placeholder.
- [ ] Push the intended release commit and verify the public remote contents.
- [ ] Make the repository public with `LICENSE`, or, if intentionally private,
  share it with `testing@devpost.com` and `build-week-event@openai.com` as
  specified by the current official FAQ.
- [ ] Confirm clean-clone setup and the one-command demo on an environment that
  did not build the project.
- [ ] Run the complete test/verification suite and inspect tool-generated
  receipts; do not type a receipt or passing status manually.
- [ ] Confirm the CI judge-container job passes with the configured digest,
  unprivileged UID, and network disabled.
- [ ] Run `/feedback` in the primary Codex task. Confirm the returned value,
  then update `submission/session.json` and the Devpost field. Candidate task:
  `019f6fc9-488b-7be0-9cff-2e9bfbd7a19f`.
- [x] Document material GPT-5.6 build-time contributions and the no-live-runtime
  boundary in `submission/ai-usage.json`, the project description, and video
  script.
- [ ] Record a demo with audio, keep the final cut under three minutes, upload
  it to YouTube, set visibility to public, and test playback in a signed-out
  browser.
- [ ] Record in English or provide the organizer-required English translation.
- [ ] Use only owned or properly licensed music, fonts, logos, trademarks, and
  other video/repository assets; retain attribution where required.
- [ ] Replace `<public-youtube-url>` everywhere and confirm the link resolves.
- [ ] Keep the repository and video free and judge-accessible through the end
  of the official judging period.
- [ ] Complete team/member fields in Devpost and confirm every listed member is
  eligible under the current rules.
- [ ] Human owner reviews the final description, category, repository, video,
  license/access, session ID, and all claims.
- [ ] Obtain explicit authority for the external Devpost submission action.

## Stage 1 viability

- [x] Category selected: **Work & Productivity**.
- [x] Problem framed as cross-functional workflow productivity, not only a
  developer control.
- [x] Working-project design uses Codex as the build environment.
- [x] Document meaningful GPT-5.6 use from the primary Codex build task.
- [ ] Confirm the public repository and public video are accessible to judges.
- [ ] Confirm the Devpost project includes the required description and category.

## Repository package

- [x] MIT license present.
- [x] README includes setup, run, sample/demo, architecture, security, and the
  OpenAI-provider truth boundary.
- [x] Source lineage and third-party notice present.
- [x] Work & Productivity and judging alignment documented.
- [x] Credential-free demo instructions present.
- [x] Security, sandbox, and traceability documents present.
- [ ] All automated tests pass on supported host platforms.
- [ ] No secrets, credential paths, private course material, source archives,
  build caches, or generated demo workspaces are committed.
- [ ] `git status`, tracked-file list, and public remote contents match the
  intended submission scope.
- [ ] Replace the remaining video placeholder and remove no longer relevant
  draft notes.

## Video content

- [ ] Opens with the work problem and target user in the first 20 seconds.
- [ ] Shows the clean one-command demo.
- [ ] Shows `EXPERIMENT_REQUIRED` and its actionable next experiment.
- [ ] Shows readiness eligibility while `build_allowed` remains false.
- [ ] Shows start blocked without a warrant.
- [ ] Shows one valid bounded start and one drift/out-of-scope denial.
- [ ] Shows a ledger/receipt and blank human verdict section.
- [ ] Explains concrete Codex and confirmed GPT-5.6 use.
- [ ] Clearly labels fixture evidence and demo-only/local-integrity signing.
- [ ] Does not claim live API use, production signing, real customer validation,
  measured savings, deployment, or external attestation unless independently
  added and verified before recording.

## Devpost fields

- [x] Draft project name: TEMPO.
- [x] Draft tagline and full description prepared.
- [x] Category: Work & Productivity.
- [ ] Final repository URL.
- [ ] Final public YouTube URL.
- [ ] Confirmed `/feedback` session ID.
- [x] Precise Codex/GPT-5.6 build-time usage statement drafted and mapped to
  repository artifacts.
- [ ] Team/member information and any organizer-required acknowledgements.
- [ ] Final preview checked for broken links, formatting, audio, and visibility.

## Final command pass

Run from a clean clone and retain actual outputs/receipts:

```bash
python bin/tempo context
python bin/tempo selfcheck
python bin/tempo demo
python bin/tempo verify --level all
python bin/tempo ledger verify
python bin/tempo submit-check
```

Only the human owner can mark the external publication/submission items done.
