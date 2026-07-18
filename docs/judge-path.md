# Credential-free judge path

Status: implemented and acceptance-tested. The included bundle remains
non-authoritative and uses only synthetic fixture input.

## Prepared bundle

The release artifact should contain compiled JavaScript, a tiny synthetic
repository with a matching graph, a deterministic fixture storyboard and
voice, `run.ps1`, `run.sh`, and expected verification hashes. It must not copy
TEMPO source. Judges need only Node.js 22+, Git, FFmpeg, and FFprobe; pnpm and a
source rebuild are not required.

Golden hashes cover bundled inputs, compiled JavaScript, and deterministic SVG
frames. MP4 bytes are not expected to match across operating systems or FFmpeg
builds; each run verifies media structure and quality, then binds that run's
actual media hash into its receipt.

## One-command path

Windows:

```powershell
.\run.ps1 demo --offline
```

macOS/Linux:

```bash
./run.sh demo --offline
```

The command must visibly execute:

1. environment doctor;
2. exact synthetic fixture graph/source inspection;
3. fixture storyboard validation;
4. deterministic fixture narration and caption-safe render;
5. source, media, audio, caption, duration, and receipt verification; and
6. local preview location output.

Expected final outcome: `UNDERSTAND_VIDEO_DEMO_PASSED` with a machine-readable
receipt. The receipt must say `planner_mode: fixture`, `voice_mode: fixture`,
and `authoritative: false`.

## Real TEMPO dogfood path

The recorded Devpost demo uses a separate TEMPO checkout and a separately
generated graph bound to the same revision. Neither is embedded in this
repository or the offline fixture bundle.

```powershell
$tempoCliCheckout = 'C:\path\to\TEMPO'
$governanceRoot = 'C:\path\to\understand-video-governance'
$targetRepo = $tempoCliCheckout
$tempoGraph = 'C:\path\to\tempo-4a73350-graph-bundle'

pnpm uv doctor --tempo-cli-checkout $tempoCliCheckout --governance-root $governanceRoot --repo $targetRepo --graph $tempoGraph
pnpm uv inspect --repo $targetRepo --graph $tempoGraph --rev 4a73350f6eefff80b11d862a5ac65b7194530442
pnpm uv plan --profile devpost --planner fixture
pnpm uv render --voice fixture
pnpm uv verify --profile devpost
pnpm uv preview
```

A real provider run replaces `--planner fixture` only after its own network,
data, model, and budget boundary is authorized. Codex credits are not assumed to
be API credits.

## Failure contract

Every command returns a stable non-zero exit for missing tools, dirty or stale
source, escaping paths, secret-like input, invalid model JSON, unresolved source
references, duration overflow, media failure, unsafe caption overlap, audio
failure, receipt drift, or invalid TEMPO authority. No failure is converted to
a simulated pass.
