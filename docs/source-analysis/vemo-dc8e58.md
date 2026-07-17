# VEMO mechanism extraction at dc8e58

The comparison baseline is the exact public MIT-licensed commit
`dc8e58a5e3d6710fc26331f1cbb17284d9071217`. It is current `main` at inspection
time but is ahead of the repository's `v1.9.0` tag; this repository does not
describe it merely as “VEMO 1.9.0.”

Mechanisms adapted rather than copied wholesale:

- thin router and just-in-time policy loading;
- repository state as durable memory;
- R0/R1/R2 implementation blast-radius tiers;
- capability-scaled procedure with capability-invariant safety;
- path/scope and destructive/secret guards;
- executed receipts instead of typed pass claims;
- provenance-bound independent verification;
- bounded unattended execution and human control of outward/irreversible acts;
- truthful `ENFORCED-BY` and exact config-consumer checks;
- local feedback plus authoritative protected CI.

Not vendored: VEMO task/judge history, branding, HTML docs, fleet/product control
plane, provider-specific model routing, existing harness configuration, or its
dogfood commands. VEMO's generic stdin hook payload is useful, but the inspected
tree did not contain a verified Codex-specific hook adapter, so TEMPO does not
claim one.

Baseline verification on Windows: 20/20 unit tests, selfcheck, and hook selftest
passed; conformance was 109/110 because a Git Bash shim could not execute `sh`.
Windows-native hooks remain a disclosed gap in that pinned source. TEMPO's core
CLI is cross-platform, and CI exercises reproducible host/container profiles
without claiming an externally attested authority.
