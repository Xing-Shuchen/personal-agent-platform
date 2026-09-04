# Reflection bundle fields

Persist with `"/home/xingzeng/personal-agent-platform/.venv/bin/python"
"/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py" store-bundle --json <path>`.

An interpretation requires `earlier_event_ref`, `later_event_ref`, `statement`,
`confidence`, `evidence`, and optionally `status`. A graph relation requires
`src_ref`, `dst_ref`, `src_type`, `dst_type`, `relation_type`, `confidence`,
`evidence`, and `status` (`active` or `candidate`). Use existing Chronicle IDs;
do not duplicate either event merely to add a later interpretation.
