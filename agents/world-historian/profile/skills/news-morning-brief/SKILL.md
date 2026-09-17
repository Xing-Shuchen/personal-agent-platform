---
name: news-morning-brief
description: Simple morning brief — collect and filter the last 24h of important news for the user, delivered once daily.
---

# Morning brief (past 24h)

Produce a compact Chinese morning news brief covering roughly the past 24
hours. This is a news collection/summary job, NOT a chronicle synthesis — do
not write anything to the Chronicle and do not run the gate.

1. Check what is already local first:

   ```bash
   "/home/xingzeng/personal-agent-platform/.venv/bin/python" \
     "/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py" feeds recent --hours 24
   ```

2. Read `config.yaml` from this profile directory for the preferred `sources`
   list (远川研究所矩阵、腾讯科技、新潮沉思录、36氪、量子位、机器之心、智能
   涌现、凤凰网、八点一氪、派早报、AIHOT 日报, plus vetted RSS feeds). Prefer those outlets for coverage.

3. Select about 20 items (15–25 acceptable) that are genuinely important over
   the window, with explicit domain diversity:
   - roughly half from China domestic news (政策/监管、经济与财经、社会民生、
     产业与企业、文娱体育, etc.);
   - a substantial international block (~6–8 items): geopolitics/diplomacy,
     major conflicts and security developments, elections and government
     changes, international economy/trade, global health/environment,
     significant happenings across Asia/Europe/Americas/Middle East/Africa —
     do not let international coverage collapse into US tech news;
   - 社会/时事热点 (~3–5 items): notable accidents/disasters and responses,
     public-safety events, education/health/livelihood policy effects,
     stories with broad public attention in China or worldwide;
   - AI/科技 is a minority — cap it at ~4–5 items, and only items with real
     consequences (major releases with market impact, regulation,
     significant research), not routine product churn;
   - prefer: major policy shifts, market/economy moves, company events with
     real consequences, significant social/people stories, genuine
     international developments;
   - items tied to active tracked threads — first obtain their titles, then
     flag them as 「追踪中」:

     ```bash
     "/home/xingzeng/personal-agent-platform/.venv/bin/python" \
       "/home/xingzeng/personal-agent-platform/agents/world-historian/runtime/cli.py" \
       active-thread-titles
     ```
   - when both a domestic and a foreign story cover the same topic, prefer the
     domestic one.

   Exclude:
   - hype/炒作 without real consequences (AI 安全恐慌叙事、智能体逃逸类
     转述评论、纯流量话题、标题党);
   - celebrity trivia, routine showbiz gossip;
   - yesterday's news that already moved on, duplicates, minor product
     releases.

   If fewer than 10 items survive the filter, say so briefly and list only
   those; never pad the list with junk.

4. Output a compact Chinese brief, one short bullet per item:
   - bold title;
   - one line on why it matters;
   - source (title + outlet) inline;
   - mark tracked-thread items with 「追踪中」.
   No long lists, no filler. If fewer than 3 items are worth reporting, say
   so briefly and list only those.

5. End with a single line: 晨间早报 · 过去 24 小时. Even if fewer than three
   items are worth reporting, always deliver the brief and state explicitly
   「过去 24 小时暂无重要更新」 when there is nothing worth reporting. Never
   return `[SILENT]`, `NO_REPLY`, or another silent marker for this user-facing
   morning brief.
