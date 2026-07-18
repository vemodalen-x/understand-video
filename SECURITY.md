# Security policy

Understand Video analyzes untrusted repositories and produces local media. It
must not execute target code, install target dependencies, expose repository
credentials, or transmit source content to an undeclared provider.

## Product security boundaries

- Pin every analyzed repository to an immutable revision and reject source
  paths that escape the snapshot root, including unsafe symlinks.
- Treat source text, documentation, model output, imported experiment records,
  and media metadata as untrusted data rather than instructions.
- Bind every explanatory claim to a resolvable source location; unsupported
  claims fail the render.
- Send only explicitly approved narration text to a declared speech provider.
  Never send secrets, credentials, participant data, or arbitrary source files.
- Keep participant observations anonymous and preserve contradictory results.
- Verify media duration, codecs, audio levels, caption timing, and caption-safe
  layout before a human preview.
- Keep upload, publication, deployment, and submission outside local rendering;
  each requires separate human authorization.

TEMPO controls are evaluated from the separate repository pinned in
`TEMPO_BASELINE.json`. This repository intentionally contains no local copy of
the TEMPO enforcement implementation.

Report vulnerabilities through the repository's private GitHub security
advisory. Do not place secrets, private source, personal data, or exploit
details in a public issue.
