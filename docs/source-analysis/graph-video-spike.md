# Graph-to-video feasibility spike

Experiment: `X-GRAPH-VIDEO-SPIKE-001`

The bounded, zero-cost experiment used the committed Understand-Anything
dashboard sample graph. It selected three grounded scenes, synthesized English
narration locally with Microsoft Zira Desktop, derived SRT and WebVTT cues from
measured speech clips, rendered deterministic frames with burned subtitles,
and verified the MP4 with FFprobe.

## Observed result

- Result: pass for technical feasibility only.
- Graph: 97 nodes, 183 edges, 7 layers, and 12 tour steps.
- Storyboard: 3 scenes and 122 narration words.
- Media: H.264 video plus AAC mono audio, 1280x720, 30 fps, 48 kHz.
- Actual duration: 56.592 seconds.
- Subtitle scene coverage: 100 percent.
- Graph node, layer, and tour references: valid.
- Video SHA-256: `d93fa9554a6eab4412675175f929fea8dadc2bd581132f4698a1265bc521816d`.

## Limits

The graph commit resolves but is stale relative to the selected upstream
implementation snapshot. The proof is 720p, a long subtitle cue can exceed two
rendered lines, no GPT-5.6 runtime planner was called, and the voice is an
offline system adapter rather than the final configured production provider.
The repository owner directly reported a severe electronic voice character and
captions obscuring diagrams. Those defects are preserved as counterevidence;
the delivery build must pass a natural-voice sample review and the fixed
caption-safe layout contract before a full render.
The experiment therefore does not satisfy the strict Hackathon profile and
does not validate the Rank-1 learner outcome.

Generated media and the detailed verification artifact are kept under the
ignored `.understand-video/experiments/graph-video-spike/` directory.
