# Report bundle fields

Persist with `"$PAP_ROOT/.venv/bin/python"
"$PAP_ROOT/agents/world-historian/runtime/cli.py" store-bundle --json <path>`.

Use a top-level `reports` list. Each report requires `mode`, `window_end`,
`body`, and `significance` in 0..1; include `window_start` when known. The
runtime derives a stable ID from mode and window, so rerunning the same window
updates rather than duplicates the report.
