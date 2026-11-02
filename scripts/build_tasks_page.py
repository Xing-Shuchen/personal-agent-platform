"""Build a standalone HTML schedule from PAP's validated agent manifests."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from html import escape
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pap.schedule import _expand_field
from pap.spec import SpecError, load_platform, load_spec, yaml


WEEKDAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


def _times(minutes: str, hours: str) -> str:
    minute_values = sorted(_expand_field(minutes, 0, 59))
    hour_values = sorted(_expand_field(hours, 0, 23))
    return ", ".join(f"{hour:02d}:{minute:02d}" for hour in hour_values for minute in minute_values)


def describe_schedule(schedule: str) -> tuple[str, str]:
    """Return a readable recurrence and its explicit clock times."""
    anchor = re.fullmatch(r"every (\d+)([smhd]) from (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) tz (\S+)", schedule)
    if anchor:
        amount, unit, date, clock, zone = anchor.groups()
        unit_name = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}[unit]
        return f"Every {amount} {unit_name} from {date} ({zone})", clock

    interval = re.fullmatch(r"every (\d+)([smhd])", schedule)
    if interval:
        amount, unit = interval.groups()
        unit_name = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}[unit]
        return f"Every {amount} {unit_name}", "Repeating interval"

    clock = re.fullmatch(r"(\d{2}:\d{2})(?: tz (\S+))?", schedule)
    if clock:
        return "Daily" + (f" ({clock.group(2)})" if clock.group(2) else ""), clock.group(1)

    fields = (schedule[5:] if schedule.startswith("cron ") else schedule).split()
    if len(fields) != 5:
        return schedule, "See schedule"
    minute, hour, day, month, weekday = fields
    times = _times(minute, hour)
    if day == month == weekday == "*":
        recurrence = "Daily"
    elif day == month == "*":
        days = sorted(_expand_field(weekday, 0, 6, sunday=True))
        recurrence = "Weekly · " + ", ".join(WEEKDAYS[item] for item in days)
    elif month == weekday == "*":
        recurrence = f"Day {day} of every month"
    elif weekday == "*":
        months = sorted(_expand_field(month, 1, 12))
        recurrence = f"Day {day} of " + ", ".join(datetime(2000, item, 1).strftime("%b") for item in months)
    else:
        recurrence = f"Cron: {schedule}"
    return recurrence, times


def delivery_defaults(root: Path) -> tuple[str, str]:
    """Read optional local defaults using PAP's existing YAML parser."""
    delivery = {}
    try:
        config = yaml.safe_load((root / "var/config/agents.yaml").read_text(encoding="utf-8"))
        if isinstance(config, dict) and isinstance(config.get("delivery"), dict):
            delivery = config["delivery"]
    except (OSError, ValueError, yaml.YAMLError):
        pass

    def value(key: str, fallback: str) -> str:
        local = delivery.get(key)
        return local.strip() if isinstance(local, str) and local.strip() else fallback

    return (value("channel", os.environ.get("PAP_OPENCLAW_CHANNEL") or "feishu"),
            value("account", os.environ.get("PAP_OPENCLAW_ACCOUNT") or ""))


def feishu_app_names() -> dict[str, str]:
    """Return route account names; unavailable or malformed config is optional."""
    try:
        path = Path(os.environ.get("OPENCLAW_CONFIG_PATH") or "~/.openclaw/openclaw.json").expanduser()
        config = json.loads(path.read_text(encoding="utf-8"))
        entries = config.get("agents", {}).get("entries", {})
        # OpenClaw also represents entries as a list of objects with an id.
        if isinstance(entries, list):
            entries = {entry["id"]: entry for entry in entries
                       if isinstance(entry, dict) and isinstance(entry.get("id"), str)}
        names = {}
        for binding in config.get("bindings", []):
            if not isinstance(binding, dict) or binding.get("type") != "route":
                continue
            match = binding.get("match")
            if not isinstance(match, dict) or match.get("channel") != "feishu":
                continue
            account = match.get("accountId")
            agent = entries.get(binding.get("agentId"), {})
            identity = agent.get("identity", {}) if isinstance(agent, dict) else {}
            name = identity.get("name") if isinstance(identity, dict) else None
            if isinstance(account, str) and isinstance(name, str) and name:
                names.setdefault(account, name)
        return names
    except (OSError, ValueError, AttributeError, TypeError):
        return {}


def build_html(root: Path) -> str:
    try:
        specs = load_platform(root)
    except (OSError, UnicodeError, SpecError) as exc:
        # Optional local configuration must not prevent a manifest-only view.
        if str(root / "var/config/agents.yaml") not in str(exc):
            raise
        specs = [load_spec(path) for path in sorted((root / "agents").glob("*/agent.yaml"))]
    default_channel, default_account = delivery_defaults(root)
    app_names = feishu_app_names()
    rows = []
    agent_names = []
    for spec in specs:
        if not spec.jobs:
            continue
        agent_names.append(spec.name)
        for job in spec.jobs:
            recurrence, times = describe_schedule(job.schedule)
            active = spec.enabled and job.enabled
            status = "Enabled" if active else "Disabled"
            destination = "Message" if job.delivery == "user-home" else "Local"
            channel = job.delivery_channel or default_channel
            account = job.delivery_account or default_account
            app_name = app_names.get(account, account) if channel == "feishu" else account
            channel_name = "飞书" if channel == "feishu" else channel
            delivery_text = "本地（不投送）" if job.delivery == "local" else f"{channel_name} · {app_name}"
            delivery_cell = (escape(delivery_text) if job.delivery == "local" else
                             f'{escape(channel_name)} · <small>{escape(app_name)}</small>')
            zone = job.timezone or ("Asia/Shanghai" if "tz Asia/Shanghai" in job.schedule else "Host local time")
            delivery_note = f"deliver {job.deliver_at}" if job.deliver_at else ""
            search = " ".join((spec.name, job.name, job.skill, recurrence, times, status, destination, delivery_note, delivery_text)).lower()
            rows.append(
                f'<tr data-agent="{escape(spec.name)}" data-status="{status.lower()}" data-search="{escape(search, quote=True)}">'
                f'<td><span class="agent-dot"></span><span class="agent-name">{escape(spec.name)}</span></td>'
                f'<td><strong>{escape(job.name)}</strong><small>{escape(job.skill)}</small></td>'
                f'<td><span class="recurrence">{escape(recurrence)}</span><small class="timezone">{escape(zone)}</small></td>'
                f'<td class="time-cell">{escape(times)}</td>'
                f'<td><span class="badge {"enabled" if active else "disabled"}">{status}</span></td>'
                f'<td class="delivery">{delivery_cell}</td>'
                f'<td><span class="delivery">{destination}</span><small>{escape(delivery_note)}</small></td>'
                f'<td><code>{escape(job.schedule)}</code></td></tr>'
            )
    filters = '<button class="filter active" data-agent="all" type="button">All agents</button>' + "".join(
        f'<button class="filter" data-agent="{escape(name)}" type="button">{escape(name)}</button>'
        for name in agent_names
    )
    total = len(rows)
    enabled = sum(spec.enabled and job.enabled for spec in specs for job in spec.jobs)
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PAP task schedule</title>
  <style>
    :root {{ color-scheme: light; --ink:#1c2929; --muted:#647171; --line:#dce4df; --paper:#fbfcf8; --green:#16614e; --accent:#e0f0e4; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:linear-gradient(160deg,#e9f2e9 0,#f6f8f1 28%,#f7f6f0 100%); color:var(--ink); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }}
    main {{ max-width:1680px; margin:0 auto; padding:44px 28px 72px; }}
    .eyebrow {{ color:var(--green); font-size:12px; font-weight:800; letter-spacing:.16em; text-transform:uppercase; }}
    h1 {{ margin:8px 0 8px; font-size:clamp(32px,4vw,52px); letter-spacing:-.04em; line-height:1.06; }}
    .intro {{ max-width:760px; margin:0; color:var(--muted); font-size:16px; }}
    .summary {{ display:flex; flex-wrap:wrap; gap:12px; margin:28px 0 30px; }}
    .stat {{ min-width:150px; padding:13px 18px; background:#fff; border:1px solid var(--line); border-radius:16px; box-shadow:0 8px 22px #2b59400a; }}
    .stat b {{ display:block; font-size:26px; line-height:1.15; letter-spacing:-.04em; }} .stat span {{ color:var(--muted); font-size:12px; }}
    .panel {{ overflow:hidden; background:var(--paper); border:1px solid var(--line); border-radius:20px; box-shadow:0 16px 48px #355c4712; }}
    .toolbar {{ display:flex; align-items:center; flex-wrap:wrap; gap:14px; padding:20px; border-bottom:1px solid var(--line); }}
    .search {{ flex:1 1 280px; max-width:420px; padding:11px 14px; border:1px solid #bfcfc5; border-radius:10px; background:white; color:var(--ink); font:inherit; }}
    .search:focus {{ outline:3px solid #a5d7b7; outline-offset:1px; }}
    .filters {{ display:flex; flex-wrap:wrap; gap:7px; }}
    .filter {{ border:1px solid var(--line); background:white; color:#3a5550; border-radius:999px; padding:7px 11px; cursor:pointer; font:600 12px system-ui,sans-serif; }}
    .filter:hover,.filter:focus-visible {{ border-color:var(--green); }} .filter.active {{ background:var(--green); border-color:var(--green); color:white; }}
    .count {{ margin-left:auto; color:var(--muted); white-space:nowrap; font-size:13px; }}
    .table-wrap {{ overflow-x:auto; }} table {{ width:100%; min-width:1200px; border-collapse:collapse; text-align:left; }}
    th {{ padding:13px 16px; background:#f1f5ee; color:#577068; font-size:11px; letter-spacing:.1em; text-transform:uppercase; }}
    td {{ padding:17px 16px; border-top:1px solid var(--line); vertical-align:top; }} tbody tr:hover {{ background:#f4f8f2; }}
    .agent-name {{ font-weight:650; white-space:nowrap; }} .agent-dot {{ display:inline-block; width:8px; height:8px; margin-right:8px; border-radius:50%; background:#4b9b75; }}
    td strong {{ display:block; font-weight:650; white-space:nowrap; }} td small {{ display:block; margin-top:3px; color:var(--muted); font-size:12px; }}
    .recurrence {{ font-weight:600; white-space:nowrap; }} .time-cell {{ min-width:180px; max-width:315px; font-variant-numeric:tabular-nums; font-weight:650; color:#225c48; }}
    .badge {{ display:inline-block; border-radius:999px; padding:3px 9px; font-size:12px; font-weight:700; }} .badge.enabled {{ color:#126345; background:#e1f3e6; }} .badge.disabled {{ color:#795e27; background:#f8ecd0; }}
    .delivery {{ color:#47655c; }} code {{ color:#6a7472; font-size:12px; white-space:nowrap; }}
    .empty {{ padding:28px; text-align:center; color:var(--muted); }}
    footer {{ margin-top:18px; color:var(--muted); font-size:12px; }} footer p {{ margin:5px 0; }}
    @media (max-width:700px) {{ main {{ padding:27px 14px 50px; }} .toolbar {{ padding:15px; }} .search {{ max-width:none; }} .count {{ margin-left:0; }} }}
  </style>
</head>
<body>
<main>
  <div class="eyebrow">Personal Agent Platform / schedule</div>
  <h1>All PAP tasks</h1>
  <p class="intro">A readable view of every scheduled job declared in the PAP agent manifests. Times below are planned schedule slots, shown in each job’s stated time zone or the scheduler host’s local time.</p>
  <div class="summary" aria-label="Schedule summary">
    <div class="stat"><b>{total}</b><span>scheduled jobs</span></div>
    <div class="stat"><b>{enabled}</b><span>enabled</span></div>
    <div class="stat"><b>{len(agent_names)}</b><span>agents with jobs</span></div>
  </div>
  <section class="panel" aria-label="PAP tasks">
    <div class="toolbar">
      <input id="search" class="search" type="search" placeholder="Search task, skill, time…" aria-label="Search tasks">
      <div class="filters" role="group" aria-label="Filter by agent">{filters}</div>
      <span id="count" class="count">Showing {total} of {total}</span>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Agent</th><th>Task / skill</th><th>Repeats</th><th>Scheduled time</th><th>Status</th><th>投送渠道</th><th>Output</th><th>Raw schedule</th></tr></thead>
      <tbody id="rows">{''.join(rows)}</tbody>
    </table></div>
    <div id="empty" class="empty" hidden>No tasks match this search.</div>
  </section>
  <footer>
    <p>PAP may shift an enabled job’s actual dispatch by up to 5 minutes before or after its scheduled slot. Runs can start later if the scheduler or runner is delayed.</p>
    <p>Source: <code>agents/*/agent.yaml</code> · Generated {escape(generated)}. Regenerate with <code>.venv/bin/python scripts/build_tasks_page.py</code>.</p>
  </footer>
</main>
<script>
  const search = document.getElementById('search');
  const rows = Array.from(document.querySelectorAll('#rows tr'));
  const filters = Array.from(document.querySelectorAll('.filter'));
  let agent = 'all';
  function update() {{
    const query = search.value.trim().toLowerCase();
    let shown = 0;
    for (const row of rows) {{
      const visible = (agent === 'all' || row.dataset.agent === agent) && row.dataset.search.includes(query);
      row.hidden = !visible;
      if (visible) shown++;
    }}
    document.getElementById('count').textContent = `Showing ${{shown}} of ${{rows.length}}`;
    document.getElementById('empty').hidden = shown !== 0;
  }}
  search.addEventListener('input', update);
  for (const button of filters) button.addEventListener('click', () => {{
    agent = button.dataset.agent;
    for (const item of filters) item.classList.toggle('active', item === button);
    update();
  }});
</script>
</body>
</html>
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "pap-tasks.html")
    args = parser.parse_args()
    try:
        html = build_html(args.root)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.write_text(html, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
