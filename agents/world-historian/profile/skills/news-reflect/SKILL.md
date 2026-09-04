---
name: news-reflect
description: Re-examine Chronicle history without web search to find later-supported interpretations and cross-thread relations.
---

# Reflect on the event graph

Do not search the internet in this mode. Work only from stored sources, claims,
events, threads, entities, and relations in the requested time window.

Look for later events that materially change how an earlier event may be
understood. Store these as `Interpretation` records with evidence, confidence,
and cautious language. Never modify the earlier event to state a later
explanation as contemporaneous fact.

Also identify converging threads, newly visible causal chains, and previously
missing relations. Prefer a few inspectable relations over broad semantic
similarity. Read
[the reflection bundle fields](references/reflection-bundle.md), then
persist the result atomically through `/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py store-bundle`.
This background mode does not produce a user-facing digest; finish with exactly
`[SILENT]` after persistence.
