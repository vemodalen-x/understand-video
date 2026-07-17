# Sandbox contract

This contract separates TEMPO's deterministic policy controls from execution
isolation. A gate can deny an action; it cannot make arbitrary code safe.

## Profiles

| Profile | Isolation | Network | Identity | Claim allowed |
| --- | --- | --- | --- | --- |
| Local CLI | Host process | Host default | Current user | Local integrity only |
| Judge container | Digest-pinned container | None | UID/GID 65532 | Isolated execution |
| CI | Hosted runner plus judge container | Disabled inside judge container | Unprivileged in container | Reproducible CI evidence; non-authoritative without verified attestation |

The configured judge image is
`python:3.13.14-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64`.
The digest, UID, network mode, and timeout are consumed from
`config/tempo.config.json`; documentation is not the authority for those
values.

## Judge-container requirements

An isolated run must:

- use the exact configured image digest;
- use `--network none` and an unprivileged numeric user;
- drop Linux capabilities and enable `no-new-privileges`;
- mount repository inputs read-only;
- provide only a bounded temporary writable location for test output; the host
  records the non-authoritative receipt after the container exits;
- inject no host credential directories, Docker socket, SSH agent, cloud
  configuration, or API keys; and
- enforce the configured whole-suite timeout.

The CI workflow is the executable reference for this profile. If the host lacks
Docker or another explicitly supported container runtime, local verification
must not claim the container profile ran.

With Docker or Podman available, reproduce the profile from the repository
root:

```bash
python bin/tempo verify --level all --require-container
```

## Filesystem and action policy

Before a valid warrant exists, only planning, evidence, fixture, documentation,
and receipt paths are eligible for writes. Once a warrant exists, the start gate
independently checks:

- task identity and declared scope;
- action and lane;
- upstream hypothesis and charter references;
- protected artifact hashes;
- remaining budget and deadline; and
- terminal revocation, expiry, or drift events.

Path containment rejects absolute paths, traversal, and resolved paths outside
the workspace. This protects the workflow's own operations; it is not a claim
that arbitrary child processes are contained on the local profile.

## Evidence and receipt semantics

Fixture evidence is permitted only in the explicitly labeled demo path. It is
not external market evidence. Model-generated synthesis can organize evidence
but cannot independently satisfy the external-evidence gate.

A receipt records the actual command, time bounds, exit code, checks,
environment, artifacts, input hashes, and provenance. A missing, malformed, or
manually asserted trust claim is not verification evidence. Container and CI
receipts remain non-authoritative until TEMPO can verify a signed attestation
against an explicit trust policy. The human verdict section remains human-owned
even when a memo is compiled from machine results.

## Out of scope

This release does not provide VM isolation, syscall filtering on every host,
remote signer identity, secret storage, multi-tenant authorization, production
deployment, or automatic Devpost submission.
