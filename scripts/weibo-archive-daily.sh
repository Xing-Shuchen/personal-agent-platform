#!/bin/sh
# Deterministic daily Weibo archive for 卢诗翰 + sven_shi.
# The archiver lives in the OpenClaw skills tree; keep this repo free of personal paths.
set -eu
exec /usr/bin/python3 "$HOME/.openclaw/skills/weibo-archive/scripts/daily_run.py" "$@"
