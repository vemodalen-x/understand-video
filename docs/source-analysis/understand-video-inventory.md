# Understand Video source inventory

| Source | Pinned identity | Observed status | Intended use |
|---|---|---|---|
| TEMPO | `https://github.com/vemodalen-x/TEMPO`, `4a73350f6eefff80b11d862a5ac65b7194530442` | Pulled and exercised in a clean separate checkout; 97 tests pass, one skips, and demo, selfcheck, verify, ledger, exact start, and atomic lease rotation pass | External business-to-MVP governance dependency and first real explanation target |
| Understand-Anything | `https://github.com/Egonex-AI/Understand-Anything`, `b9ac6be178b2fbc68ae45456cd9a902bdcac6dac`, v2.9.4 | Live `main` equals the requested pin | Graph schema, analyzer output, guided-tour and freshness baseline |
| OpenAI Build Week Devpost requirements | `docs/DEVPOST_DELIVERY_PROFILE.md`, fetched through the Devpost connector 2026-07-18 | Submission period open; deadline 2026-07-21 17:00 PT; public YouTube demo with audio, Codex/GPT-5.6 coverage, repository URL, README, and `/feedback` session ID required | Live constraint snapshot, submission profile, and judge path |
| Human product brief | Attachment `93e9e4e1-20fd-4b0c-a44c-f1f100a74e76/pasted-text.txt`, 1832 lines | Direct task instruction; product claims remain hypotheses until measured | Scope, invariants, acceptance tests, and non-goals |
| Dashboard sample graph | Upstream file `understand-anything-plugin/packages/dashboard/public/knowledge-graph.json`, SHA-256 `f7a2f3b2b0ea6d37814c9e7f34efca633cecc00027832313243b4466a34ce7ac` | 97 nodes, 183 edges, 7 layers, 12 tour steps; graph commit exists in upstream history but predates selected source snapshot | Bounded feasibility experiment only, never strict Hackathon provenance |

Local comparison clones and experiment artifacts remain under ignored
`.source-cache/` and `.understand-video/` paths. TEMPO state remains in its
separate checkout.
