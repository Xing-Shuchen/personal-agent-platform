# Personal Agent Platform (PAP)

PAP provides declarative agents, a single scheduler, run records, an artifact log, and isolated state. It is a code template: no personal files, credentials, delivery targets, or model routes are required to inspect and validate it.

## Set up with Codex

Clone the repository, open it in Codex, and ask:

> Read AGENTS.md and help me configure this PAP checkout. Show me the available agents, let me choose which ones to enable, then validate the local setup. Keep my paths, accounts, and private data out of Git.

Codex should complete the local setup interactively. The tracked manifests ship with every agent disabled. Configuration goes in ignored `var/config/agents.yaml`; the example is [config/agents.example.yaml](config/agents.example.yaml). Do not enable every agent unless you want all of their scheduled jobs.

## Agents

| Agent | Capability |
| --- | --- |
| `compiler-news` | AI compiler and HPC news brief |
| `intelligence` | High value changes tied to selected context |
| `librarian` | Reading capture and provenance search |
| `personal-historian` | Personal event cards and period summaries |
| `red-team` | Adversarial review on request |
| `serendipity` | Cross-context connections |
| `wechat-archivist` | Local incremental WeChat archive, when explicitly configured |
| `world-historian` | Sourced public events, claims, threads, and reports |

Agent definitions and reusable skills live under `agents/<name>/`. Set `agents.<name>.enabled: true` in `var/config/agents.yaml` to activate one. Enabling an agent makes its manifest jobs eligible for `pap tick`; a job with `enabled: false` stays off. Existing model selection is delegated to the user's OpenClaw configuration. Job-specific models may be set later in a local deployment, but provider names from this project's author are not shipped as defaults.

## Local commands

```bash
make setup
.venv/bin/pap validate
.venv/bin/pap agents
.venv/bin/pap jobs
.venv/bin/pap tick --dry-run
make test
```

`make setup` creates `.venv` and installs the package. `pap validate` checks manifests. `pap tick --dry-run` previews due jobs without executing or delivering them. For scheduled use, run `.venv/bin/pap tick` once per minute from the repository root through your own cron or service after selecting agents and configuring any delivery channel. PAP is the only scheduler for manifest jobs; do not duplicate them as OpenClaw automations.

Install skills into already created OpenClaw agent workspaces:

```bash
python3 scripts/install_agents.py --list-only
python3 scripts/install_agents.py --apply --openclaw-home "$HOME/.openclaw"
```

The installer only copies skills for enabled agents. It does not create OpenClaw agents, credentials, automations, or scheduled jobs.

## Local configuration

All runtime state and local activation settings belong under ignored `var/`. `.env` files are ignored too. Set `PAP_ROOT` to the absolute checkout path when skills or services run outside the repository. Set `PAP_VAULT` only if you opt into Obsidian context. The personal history lookup reads only files named in the path-separated `PAP_PERSONAL_INPUTS`. The WeChat archivist requires `WECHAT_DBROOT` and `WECHAT_KEYS`. Outbound delivery requires `PAP_OPENCLAW_CHANNEL`, `PAP_OPENCLAW_ACCOUNT`, and `PAP_OPENCLAW_DELIVERY_TARGET` in the local environment. Never commit these values.

The World Historian database defaults to `var/world-historian/chronicle.sqlite`. The disabled snapshot job creates a local SQLite backup; it does not push to a remote destination. The Obsidian dashboard in `obsidian/world-historian-dashboard/` is optional.

## Sharing this project

Share a fresh checkout or an archive of the current files without `.git/`, `var/`, `.venv/`, `.env*`, local media, or OpenClaw trajectories. Previous Git history may contain earlier personal paths or data; a new repository should start from a clean snapshot rather than pushing this history. Run `python3 scripts/check_release.py` before sharing.

Architecture and protocol details are in `docs/`. This repository's `AGENTS.md` is the setup contract for Codex; users may customize their local installation without changing tracked defaults.
