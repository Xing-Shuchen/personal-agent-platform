# Agent-led Bailian voice

Local adapter for the specific Bailian bridge build identified by `install.py`.
It leaves the current agent's model, workspace, skill permissions and OpenClaw
voice confirmation checks in place. It does not enable delivery or scheduling.

Every final user ASR turn is delegated verbatim through OpenClaw's native
`runAgentConsult` callback, without asking the voice model or App to choose a
workflow or paraphrase the request. The synthetic `openclaw_agent_consult` path
is retained only as a fallback for hosts without the native callback.
Adjacent final fragments are joined with newlines. Server VAD uses
a 1600 ms silence window, followed by 650 ms to collect adjacent fragments.
Direct provider responses and native tool calls are suppressed. The same agent
owns ordinary answers, next/skip requests, stage transitions and execution.

Agent results are read aloud only after a whole-response transcript comparison
matches the requested text (ignoring punctuation, spacing, case and Unicode
compatibility forms). Until then audio is bounded and buffered. A mismatch is
reported as a playback error and no unverified assistant transcript or audio is
published. Validated PCM is paced in 100 ms frames so the App is not flooded by
the buffered response, and queued playback is cleared on interruption.
This intentionally trades first-audio latency for predictable speech.
Different spoken numeral spellings can cause a conservative rejection. This
does not prove that ASR or the primary agent is factually correct.

The native host observes and binds spoken confirmation itself. On the fallback
tool path, pending confirmation IDs stay in the bridge and are supplied only on
a later explicit affirmation. OpenClaw checks persisted speech, agent/call identity, expiry,
unchanged tool arguments and one-shot use. Questions, cancellation and altered
instructions do not carry a grant. No alternate scheduler or tool bypass is used.
Interrupted calls cannot replay stale tool results; closing clears local state.

## Install and roll back

Set `BAILIAN_PLUGIN_DIR` to the installed plugin directory, outside this checkout:

```sh
node --test test-agent-led.mjs
python3 install.py status --plugin-dir "$BAILIAN_PLUGIN_DIR"
python3 install.py apply --plugin-dir "$BAILIAN_PLUGIN_DIR"
openclaw plugins reload bailian-voice
```

The installer refuses unknown bridge hashes, checks JavaScript syntax and keeps
`bridge.js.before-agent-led` alongside the original installation. Backups and
credentials must remain outside tracked files. To restore the old bridge:

```sh
python3 install.py rollback --plugin-dir "$BAILIAN_PLUGIN_DIR"
openclaw plugins reload bailian-voice
```

Plugin upgrades may replace this adapter. Review the new version before porting
the patch. Synthetic tests cover routing, fragment collection, speech validation,
confirmation metadata, interruption and closure. Live tests must additionally
exercise actual ASR, agent tool execution, TTS and the App's audio playback.

## Specific confirmation prompts

`install-confirmation.py` layers onto the exact already-repaired 2026.10.3 host
module from `../realtime-voice-ux`. It labels the pending action (using the tool
title, or the date scope of a recognized minutes search), preserves the first
challenge if the same blocked turn tries a different tool, and recognizes exact
Chinese assent such as “确认批准这项操作”. The existing call identity, persisted
speech, expiry, fingerprint and single-use checks remain enforced. It does not
approve future commands or a broader session. Shell arguments and credentials
are never copied into the spoken label.

```sh
python3 install-confirmation.py apply --dist "$OPENCLAW_DIST"
node --test test-agent-led.mjs
node --test test-confirmation-loop.mjs
```

Restart the existing Gateway service to load the host module. The installer saves
the previous host beside it. To roll back, use `install-confirmation.py rollback`
with the same `--dist` and restart; roll this layer back before rolling back
`../realtime-voice-ux`. Each distinct operation still requires its own grant.
