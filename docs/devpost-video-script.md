# TEMPO explainer demo video plan

Status: pre-production plan. Target duration: 165 seconds; hard limit: less than
180 seconds.

| Time | Visual | Narration purpose | Evidence |
| --- | --- | --- | --- |
| 0–12 s | Understand Video CLI selects TEMPO commit `4afc6a3` | State the developer-onboarding problem and show the product working immediately | Product inspect receipt |
| 12–29 s | Generated architecture map and source links | Explain that the video is compiled from an exact repository snapshot, not a free-form summary | `C-TEMPO-001`, product claim map |
| 29–51 s | TEMPO provider/readiness code | Model output is advice; deterministic readiness can recommend an MVP without granting build authority | `C-TEMPO-002`, `C-TEMPO-003` |
| 51–78 s | `python bin/tempo demo` terminal beats | Show `WARRANT_MISSING`, bounded in-scope start, and `SCOPE_NOT_AUTHORIZED` | `C-TEMPO-004`, live demo |
| 78–102 s | Protected file changes, then invalid status | Explain hash-bound protected inputs and permanent invalidation after drift | `C-TEMPO-005` |
| 102–124 s | Audit console timeline with synthetic label visible | Explain serialized ledger, checkpoint, receipts, and blank human verdict without presenting the fixture as real evidence | `C-TEMPO-006` |
| 124–143 s | Understand Video render and verify screen | Show MP4, SRT/VTT, source coverage, duration, audio, and zero-overlap checks | Product verification receipt |
| 143–159 s | Codex task/commit evidence and GPT-5.6 provider boundary | Explain where Codex accelerated architecture/testing and where GPT-5.6 was used; distinguish build-time use from any real runtime provider call | README and provider receipt |
| 159–165 s | Final video beside source-linked transcript | Close with the product outcome and honest local-integrity boundary | Final local receipt |

## Production checkpoints

1. Approve a 10–15 second voice sample for naturalness and pronunciation.
2. Approve keyframes with the caption band and safe regions visible.
3. Review a low-resolution full draft with sidecar captions.
4. Run deterministic verification on the final local render.
5. Obtain a separate human publication decision before YouTube upload.

The narration must be written in the submitter's own voice before final use.
This plan supplies evidence and timing structure, not a submission-ready human
statement.
