# Understand Video credential-free judge bundle

Prerequisites: Node.js 22+, Git, FFmpeg, and FFprobe. No credentials, pnpm,
`node_modules`, dependency installation, or source rebuild are required.

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1 demo --offline
```

macOS/Linux:

```sh
./run.sh demo --offline
```

The bundle creates only a synthetic repository and generated outputs below
`.understand-video/judge-demo` (or the explicit `--workdir`). It does not embed,
import, install, or execute TEMPO. The fixture receipt is intentionally marked
`plannerMode: fixture`, `voiceMode: fixture`, and `authoritative: false`.

`UNDERSTAND_VIDEO_DEMO_PASSED` is printed only after doctor, inspect, plan,
render, media verification, and canonical receipt verification all pass. A
missing tool or failed check exits non-zero and never prints the sentinel.
