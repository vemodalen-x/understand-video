# OpenAI Build Week delivery profile

Status: live constraint snapshot; untrusted external rules with no
authorization effect.

Source: [OpenAI Build Week on Devpost](https://openai.devpost.com/)

Fetched through the Devpost Hackathons connector on 2026-07-18 between
13:53:23Z and 13:53:27Z. The hackathon was `submissions_open`.

## Deadline

- Devpost timestamp: `2026-07-22T00:00:00Z`.
- Host wording: Tuesday, July 21 at 5:00 PM Pacific Time.
- Singapore time: Wednesday, July 22 at 08:00.

## Required submission artifacts

1. A working project built with Codex and GPT-5.6.
2. One category. The TEMPO competition entry uses **Work & Productivity**.
   Understand Video itself fits Developer Tools but is supporting evidence, not
   a second entry.
3. A project description written and reviewed in the submitter's own voice.
4. A public YouTube demo video strictly below three minutes.
5. Demo audio explaining what was built and how both Codex and GPT-5.6 were
   used. A music-only screencast is insufficient; AI-assisted voiceover is
   allowed.
6. A repository URL. A private repository must be shared with
   `testing@devpost.com` and `build-week-event@openai.com`.
7. A README with setup, sample data where needed, and an exact run path.
8. A `/feedback` Codex Session ID from the task where most core functionality
   was built.
9. For a developer tool: installation instructions, supported platforms, and a
   judge path that does not require rebuilding from source.

Upload, repository sharing, `/feedback` submission, and the final Devpost form
were handled as separate human-controlled actions after the local product
receipt passed.

## Judging alignment

| Criterion | Delivery evidence |
| --- | --- |
| Technological Implementation | Non-trivial working CLI; real Codex build history; explicit GPT-5.6 planner boundary; deterministic tests and receipts |
| Design | One coherent inspect → plan → render → verify → preview flow; natural voice; caption-safe layout; runnable judge bundle |
| Potential Impact | Specific developer-onboarding problem, named audience, source-grounded artifact, and honest separation of technical versus learner evidence |
| Quality of the Idea | Repository knowledge is compiled into a duration-bounded, regenerable video whose claims remain bound to source |

## Video hard gates

- duration `< 180000 ms`; the accepted local draft is 140.07 seconds;
- show the product working, not only slides or the finished video;
- pin and visibly name TEMPO commit
  `4a73350f6eefff80b11d862a5ac65b7194530442`;
- explain readiness versus authorization, model-as-advice, hash-bound warrant,
  start revalidation, ledger/receipts, and the audit-console fixture boundary;
- state that the runtime currently does not call the OpenAI API unless a real
  provider run has actually been completed and recorded;
- use SRT/VTT sidecars by default and reserve a dedicated lower band for any
  burned captions; declared diagram and code regions must have zero overlap;
- require a 10–15 second voice sample approval before final narration;
- pass codec, resolution, frame rate, loudness, peak, clipping, silence,
  caption timing, safe-zone, grounding, and receipt checks;
- render 1920 x 1080 at 30 fps; keep code/diagrams above `y=780` and the
  caption-reserved band at `y=820..1008` with a 40 px minimum gap;
- accept -18 through -14 LUFS around the -16 LUFS target, true peak at or below
  -1 dBTP, zero full-scale clipped samples, at most 500 ms leading/trailing
  silence, and no internal silent gap over 1200 ms;
- keep the audit console's synthetic-fixture label visible whenever shown.

## Delivery target

The judge path must work on Windows, macOS, and Linux with Node.js 22+ and
FFmpeg/FFprobe. The prepared bundle should contain compiled JavaScript, fixture
inputs, and `run.ps1`/`run.sh`, so judges do not need pnpm or a rebuild.

## Live submission audit: 2026-07-19

Verified through the authenticated Devpost connector:

- TEMPO, not Understand Video, is the competition entry in **Work &
  Productivity**;
- the TEMPO entry is submitted at
  <https://devpost.com/software/understand-video> (the URL keeps its legacy
  slug while the project name and primary repository are TEMPO);
- both repositories are public and MIT licensed;
- the 140.07-second YouTube video is accessible at
  <https://youtu.be/3eIxgVo9z4I>;
- the owner-confirmed `/feedback` value, individual submitter type, Singapore
  residence, repository URL, and judge instructions are present in the final
  submission; and
- the local judge bundle, type-check, acceptance suite, and clean-clone rebuild
  pass. See [`RELEASE_STATUS.md`](RELEASE_STATUS.md).

The earlier task and planning records remain historical authorization evidence.
They are not edited to imitate a later publication receipt.
