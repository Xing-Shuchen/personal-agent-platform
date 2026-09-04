# Report bundle fields

Persist with `"/home/xingzeng/personal-agent-platform/.venv/bin/python"
"/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py" store-bundle --json <path>`.

Use a top-level `reports` list. Each report requires `mode`, `window_end`,
`body`, and `significance` in 0..1; include `window_start` when known. The
runtime derives a stable ID from mode and window, so rerunning the same window
updates rather than duplicates the report.
