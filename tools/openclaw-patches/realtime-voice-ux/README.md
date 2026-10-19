# OpenClaw realtime voice repair

This optional patch targets the compiled OpenClaw **2026.10.3** runtime. It removes the hardcoded “I’ll check that request.” announcement before native voice delegations and accepts explicit Chinese confirmation and cancellation. The original confirmation prompt could be translated into Chinese while its parser accepted only English, causing repeated confirmation requests.

The voice instructions also ask the model to wait silently for results and preserve the difference between a completed local write and pending publishing or synchronization.

Confirmation still requires later, persisted speech from the same agent and voice call. It authorizes one exact action, with unchanged execution arguments, for one run and one execution within the existing two-minute expiry. Repeated assent does not grant blanket access. Questions, quoted assent, conditions, and conflicting denials do not authorize an action.

## Apply and verify

Requirements: Python 3, GNU `patch`, the supported OpenClaw installation, and the Node runtime used by that installation. The regression suite was validated with Node 24.

Set `OPENCLAW_DIST` to your own installation's `dist` directory. From this directory:

```bash
python3 install.py status --dist "$OPENCLAW_DIST"
python3 install.py apply --dist "$OPENCLAW_DIST"
node --test test-voice-ux.mjs
```

Restart your Gateway using its existing service manager after the tests pass. The installer does not change configuration, restart services, execute agent actions, or enable scheduling.

The installer checks the package version and the original or patched SHA-256 of all three affected modules. It prepares and verifies every output before replacing installed files. Unknown files, partial installations, other builds, and unrelated edits are rejected. Already-applied patches are a no-op.

To roll back, then restart the Gateway:

```bash
python3 install.py rollback --dist "$OPENCLAW_DIST"
```

## Files and validation

- `changes.patch`: minimal unified diff, retaining upstream source-region names.
- `manifest.json`: supported version and original/patched file hashes.
- `install.py`: guarded application, status inspection, and rollback.
- `test-voice-ux.mjs`: 52 synthetic regressions using runtime code regions, installed helpers, and a fake provider transport.

All 52 regressions pass against the repaired runtime; 22 fail against the original modules. Tests cover assent, cancellation, persistence, call isolation, expiry, changed arguments, one-shot execution, silent delegation admission, final results, and aborted calls. They do not exercise speech recognition or microphone-to-speaker audio. To inspect a separate candidate directory while retaining the installed helper modules, set `VOICE_PATCH_CANDIDATE` as well as `OPENCLAW_DIST`.

This is an installation-specific runtime patch, not an upstream release. Updates can replace it; review the new implementation before porting the diff. The bundle contains no configuration, credentials, conversation records, or original runtime copies. Keep local backups and diagnostics outside tracked files.
