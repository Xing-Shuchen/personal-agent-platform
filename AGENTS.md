# Codex setup guide for a new user

This repository is a reusable Personal Agent Platform. Its tracked files must stay free of the current user's identity, credentials, private data, hardware details, absolute home paths, delivery targets, and provider-specific model routes.

When the user asks you to set it up:

1. Read `README.md`, list the agents with `.venv/bin/pap agents`, and explain what each selected agent does. Ask which agents the user wants and whether scheduled runs are wanted. Do not infer consent to read personal files or send messages from merely opening the repository.
2. Set up Python with `make setup`, then run `make validate` and `make test`.
3. Copy `config/agents.example.yaml` to `var/config/agents.yaml`. Set `enabled: true` only for agents the user selected. This file is ignored by Git. Agent-level `enabled` gates both manual invocation and scheduled jobs. A job-level `enabled: false` in a manifest remains off.
4. Configure the selected agent's OpenClaw workspace and model/provider with the user's own credentials and routes. Use `python3 scripts/install_agents.py --list-only` before applying skills. Set `PAP_ROOT` to this checkout's absolute path for skills and commands.
5. If personal context is requested, configure `PAP_VAULT` and/or `PAP_PERSONAL_INPUTS` with the user's own paths. For WeChat export, require the user's own `WECHAT_DBROOT` and `WECHAT_KEYS`. Do not copy source data into the repository.
6. If outbound delivery is requested, set `PAP_OPENCLAW_CHANNEL`, `PAP_OPENCLAW_ACCOUNT`, and `PAP_OPENCLAW_DELIVERY_TARGET` in a local environment or service file. Do not write them into tracked files. Preview `pap tick --dry-run` before enabling a recurring `pap tick` service or cron entry.
7. Run `pap validate`, `pap agents`, and `pap tick --dry-run`; report selected agents, any unmet dependencies, and what is scheduled. Never start recurring jobs or external delivery until the user has selected them.

Do not create or edit OpenClaw automations for PAP jobs; `pap tick` is the sole scheduler. Keep all personal configuration under `var/` or in ignored environment files. If a tracked skill contains an example path, replace it with a generic path or an environment variable rather than the new user's path.
