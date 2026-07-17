# OpenAI and commercial-provider boundary

## What exists in this release

TEMPO contains a vendor-neutral commercial planning provider contract and a JSON
adapter. It can normalize a recorded proposal into governed planning artifacts.
The sample proposal is a fixture. The runtime does **not** make a live OpenAI API
call and does not require an API key.

That boundary is intentional: a model may help frame an opportunity, propose a
hypothesis, summarize evidence, or recommend an experiment. The deterministic
kernel independently validates schemas, provenance, freshness, thresholds,
costs, risks, and authorization. Provider text is untrusted input.

The provider adapter cannot:

- emit its own synthesis through the adapter as external evidence;
- suppress counterevidence;
- write the signed human decision brief;
- sign an MVP charter or authorization warrant;
- select a passing verification result; or
- fill the human verdict section.

This boundary is about typed, declared provenance. The local release does not
authenticate the real-world identity or truthfulness of a user-supplied source;
a production evidence path would require an independently reviewed signer or
attestation policy.

## How Codex and GPT-5.6 relate to the submission

Codex Desktop with GPT-5.6 in the user-selected Sol Ultra mode is the primary
engineering environment for this repository. The model's build-time work is
material and artifact-linked: source reconciliation, architecture decisions,
deterministic schemas and kernel logic, adversarial cases, the fixture journey,
and the submission narrative. `submission/ai-usage.json` records those links.

The primary task candidate is recorded in `submission/session.json`. Before
submission, the owner must run `/feedback` in that task and confirm the returned
session ID. A thread identifier must not be presented as `/feedback` output
unless they are confirmed to match.

The Build Week description should call this **build-time GPT-5.6 use in
Codex**. It must not say the repository calls GPT-5.6 at runtime: it currently
does not. The recorded `openai/gpt-5.6` proposal is a labeled fixture and is not
counted as live API evidence.

## Optional live adapter, outside this vertical slice

A future OpenAI Responses API adapter can implement the same provider contract:

1. send only the minimum business context required for proposal generation;
2. request schema-constrained output;
3. record model, request, response, and prompt-template provenance without
   storing secrets;
4. validate and normalize the response through the existing adapter boundary;
5. keep model-generated content labeled as synthesis; and
6. require the same evidence, readiness, and human-warrant gates.

Adding a live adapter would require explicit network/credential authorization,
threat-model review, tests for malformed and adversarial output, and honest cost
and latency reporting. It is not necessary for the credential-free judge demo.
