# Credential-free judge scenario

This directory contains deliberately labeled fixtures for the runnable demo. The
interview records are **not customer validation**, and the demo signer is **not a
platform attestation**. They exist to exercise the exact same schema, blocker,
authorization, drift, ledger, and receipt code paths without secrets or network
access.

Run the scenario from the repository root:

```bash
python bin/tempo demo
```

The generated workspace is written under `.tempo/demo-workspaces/` and is ignored
by Git.
