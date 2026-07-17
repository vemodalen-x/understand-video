# Source conflict matrix

| Conflict | Resolution |
|---|---|
| Readiness requires a warrant, while a warrant requires readiness | Split readiness eligibility from authority; see ADR 0001 |
| TEMPO "L0 kernel" versus new L0 business layer | Call the inherited hook baseline K0; reserve L0 for business decisions |
| Old TEMPO milestone percentages versus business-gated profile | Use 8/12/15/20/45/62/70/76/82/95; retain old values only as history |
| Initial brief/default versus latest human track decision | Use `Work & Productivity`; the latest direct human decision supersedes the earlier Developer Tools default |
| YAML examples versus stdlib-only kernel | JSON/JSONL are authoritative; schemas remain explicit and dependency-free |
| Windows support versus POSIX/symlink hooks | Core CLI supports Python 3.10+ cross-platform; POSIX hooks are optional; CI is authoritative; platform gaps are disclosed |
| Local hashes/HMAC versus non-repudiation | Label them integrity checks; release/outward authority needs protected CI or an external signer |
| Local JSONL append-only versus tamper proofing | Append-only is a tool contract and hash chain, not protection from the same OS identity; protected CI is the backstop |
| VEMO 1.9.0 label versus current commit | Pin the exact commit; do not claim tag equivalence |
| VEMO Codex adapter claims versus evidence | Reuse the generic stdin/exit-code contract only; do not claim a verified Codex-specific adapter |
| README container requirement versus local Windows without Docker | Generate and validate the literal plan locally; require the isolated container execution in CI and disclose local non-execution |
