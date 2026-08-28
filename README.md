# personal-agent-platform

个人 Agent 平台：声明式 agent spec（`pap/v1`）+ 共享主动门控（proactive gate）。

## 结构

```
agents/<name>/agent.yaml        # 声明式 agent spec（pap/v1）
agents/<name>/profile/          # SOUL.md、config.yaml、distribution.yaml、skills/
pap/                            # Python 包：spec 校验 + 共享 gate + CLI
scripts/install_agents.py       # 安装器：把 agents 装进 Hermes profile（默认 dry-run）
var/state/                      # 运行时状态（gate 状态、审计日志）
```

## 当前 agents

| Agent | 职责 | 主动性 |
|---|---|---|
| `serendipity` | 跨时间/跨领域的罕见、有证据关联 | every 4h（serendipity-pulse） |
| `intelligence` | 只报告会更新世界模型的外部进展 | every 1h（intelligence-pulse） |
| `red-team` | 论证/设计/假设的对抗性审查 | 关闭 |

## 快速开始

```bash
make setup        # venv + pip install -e . pytest
make validate     # 校验所有 agents/*/agent.yaml
make test         # pytest -q

# 安装到 Hermes（默认 dry-run，确认后加 --apply）
python scripts/install_agents.py --list-only
python scripts/install_agents.py --apply --hermes-profile <profile>
```

## 共享主动门控（pap gate）

所有主动投递必须过 gate；不过则输出 `[SILENT]`（沉默即成功）：

```bash
pap gate --agent serendipity --dedupe-key '<stable-key>' --priority 80 --message '...'
```

规则（`pap/gate.py`）：
- 白天优先级 ≥ 70；本地安静时段（22:00–08:00）≥ 90；
- 同一 `dedupe_key`（由概念生成，而非措辞）7 天内不重复投递；
- 连续被拒触发指数退避静默地板（4h → 8h → 16h → 32h 封顶），成功投递后重置；
- 全部决策落盘 `var/state/gate-log.jsonl` 可审计。
