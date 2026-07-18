# Founder MVP acceptance-test inventory

Status: implemented core contract plus delivery extensions. The charter target
remains exactly 50 declared core cases. A case counts only when executable,
deterministic, and passing in CI. Four source-integration and delivery cases are
tracked separately as post-charter extensions.

## Snapshot and security — 10

| ID | Required behavior |
| --- | --- |
| UV-001 | Accept an exact clean Git revision and record its full SHA. |
| UV-002 | Reject an unknown revision. |
| UV-003 | Reject strict mode when the selected working tree is dirty. |
| UV-004 | Reject a source path containing `..` traversal. |
| UV-005 | Reject an absolute source path outside the snapshot. |
| UV-006 | Reject a symlink whose resolved target escapes the snapshot. |
| UV-007 | Treat prompt-injection text in source as data, never as an instruction. |
| UV-008 | Redact or block secret-like excerpts without recording their values. |
| UV-009 | Never execute target repository code or install its dependencies. |
| UV-010 | Reject target revision drift between inspect and render. |

## Contracts, claims, and planning — 10

| ID | Required behavior |
| --- | --- |
| UV-011 | Validate a repository snapshot contract. |
| UV-012 | Reject an unknown field in a strict claim contract. |
| UV-013 | Resolve every material claim to an existing file and line span. |
| UV-014 | Reject a claim whose file no longer exists. |
| UV-015 | Reject a claim whose referenced line hash drifted. |
| UV-016 | Reject malformed planner JSON without partial execution. |
| UV-017 | Reject a storyboard containing an unsupported scene type. |
| UV-018 | Duration pruning removes optional scenes before required claims. |
| UV-019 | Duration pruning fails if required narration still exceeds the cap. |
| UV-020 | Fixture and real provider provenance remain distinguishable. |

## Narration and captions — 10

| ID | Required behavior |
| --- | --- |
| UV-021 | Produce deterministic fixture narration for identical inputs. |
| UV-022 | Prevent a speech provider from receiving raw source content. |
| UV-023 | Require an approved voice-sample checkpoint for production mode. |
| UV-024 | Reject narration clips containing digital clipping. |
| UV-025 | Reject integrated loudness outside -18 through -14 LUFS. |
| UV-026 | Reject true peak above -1 dBTP. |
| UV-027 | Reject leading/trailing silence over 500 ms or an internal silent gap over 1200 ms. |
| UV-028 | Produce monotonic SRT cues within media duration. |
| UV-029 | Produce semantically equivalent WebVTT cues. |
| UV-030 | Wrap captions to at most 42 Latin characters per line, two lines, 52 px font, and 64 px line height. |

## Rendering and media — 10

| ID | Required behavior |
| --- | --- |
| UV-031 | Reserve the 1920 x 1080 caption band `x=96..1824`, `y=820..1008` in every visual mode. |
| UV-032 | Report zero intersection and at least a 40 px gap between captions and diagram regions bounded above `y=780`. |
| UV-033 | Report zero intersection and at least a 40 px gap between captions and code regions bounded above `y=780`. |
| UV-034 | Render identical deterministic SVG frames for identical inputs. |
| UV-035 | Fall back to the SVG renderer when Hyperframes is unavailable. |
| UV-036 | Invoke FFmpeg with an argument array and reject shell metacharacter injection. |
| UV-037 | Produce an H.264 video stream and AAC audio stream. |
| UV-038 | Produce 1920 x 1080 video at constant 30 fps. |
| UV-039 | Reject final duration greater than or equal to 180000 ms. |
| UV-040 | Reject missing, undecodable, truncated, or zero-frame media. |

## Governance, receipt, and judge path — 10

| ID | Required behavior |
| --- | --- |
| UV-041 | In governance-enforced mode, reject a missing independent TEMPO checkout; fixture mode requires no checkout. |
| UV-042 | In governance-enforced mode, reject TEMPO checkout drift; fixture mode validates pinned baseline metadata. |
| UV-043 | Reject a missing, expired, revoked, or invalidated warrant. |
| UV-044 | Reject an implementation path, lane, action, or task outside the warrant. |
| UV-045 | Bind snapshot, claims, storyboard, narration, captions, media, and provider mode into one receipt. |
| UV-046 | Detect any receipt or bound-artifact hash tampering. |
| UV-047 | Complete the offline inspect → plan → render → verify path without credentials. |
| UV-048 | Run the prepared judge bundle without pnpm or a source rebuild. |
| UV-049 | Resolve every required TEMPO golden source reference at the pinned commit. |
| UV-050 | Emit `UNDERSTAND_VIDEO_DEMO_PASSED` only when every required check passes. |

## Non-counting human checkpoints

Voice naturalness, pronunciation, visual hierarchy, code readability, pacing,
and final narrative coherence remain explicit human reviews. They complement
the 50 machine cases and are never converted into fabricated automated passes.

## Post-charter delivery extensions — 4

| ID | Required behavior |
| --- | --- |
| UV-051 | Bind the reviewed Understand-Anything graph, metadata, fingerprints, provenance, configuration, and review record to exact hashes. |
| UV-052 | Ground every authored TEMPO narration scene in exact lines from the pinned clean snapshot. |
| UV-053 | Render explicit readable typography and a dedicated caption band without CSS font shorthand ambiguity. |
| UV-054 | Record the natural-voice development candidate without granting publication authority. |
