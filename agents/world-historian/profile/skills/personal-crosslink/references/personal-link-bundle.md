# PersonalLink bundle fields

Persist with `"$PAP_ROOT/.venv/bin/python"
"$PAP_ROOT/agents/world-historian/runtime/cli.py" store-bundle --json <path>`.

Use a top-level `personal_links` list. Each item requires `world_event_ref`,
`personal_event_id`, an allowed `relation_type`, `explanation`, `confidence`,
and minimal evidence IDs. The runtime rejects relation types outside the
privacy taxonomy and commits the entire bundle atomically.
