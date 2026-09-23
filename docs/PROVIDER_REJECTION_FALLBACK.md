# Provider 拒绝与兜底（provider rejection fallback）

2026-09-23 夜里 feishu4 连续几轮「Agent couldn't generate a response」引出的排查结论与改动记录。给以后遇到同类失败的人（和 agent）看。

## 症状

用户可见：

```text
⚠️ Agent couldn't generate a response. Note: some tool actions may have already been executed — please verify before retrying.
LLM request failed: provider rejected the request schema or tool payload.
⚠️ zai/glm-5.3 request failed (request format rejected, HTTP 400).
```

排查入口：

- OpenClaw：`~/.openclaw/agents/<agentId>/agent/openclaw-agent.sqlite`
  - `trajectory_runtime_events`（按 `run_id` 取该 run 的 `model.*` / `trace.artifacts.finalStatus` / `session.ended.stopReason`）
  - `transcript_events`（按内容检索历史同类失败）
- PAP：`var/state/runs.jsonl` 的 `failure_kind`、`run.fallback`（`from` / `to` / `failure_kind` / `error`）

## 这是哪一类错误

不是配额（那是 `Weekly/Monthly Limit Exhausted`）、不是 Qwen 输出内容审核（那是 `data_inspection_failed: Output data may contain inappropriate content.`）、也不是模型路由故障。2026-09-23 实测排除：

- 同一条 `qwen/deepseek-v4.1-flash` 在正常会话里工作正常；最小请求打 `zai/glm-5.3` 也秒回。
- 失败总是紧跟在「大块工具输出 / 长文档刚进上下文」之后的下一次模型调用上；同一错误在别的会话、别的主题上出现过（09-18 的 skill-collection-review 自动化、09-21 的建线子代理）。
- 换句话说：**拒绝的是这一次请求的载荷**，而且拒绝方（qwen、zai）都是 China 侧校验严格的路线。

## 两层兜底

### 1. PAP 侧（每个 run 一次固定模型重试）

- `pap/run.py`：`PROVIDER_REJECTION_MARKERS` 命中即以 `provider_rejection` 记失败类别，并且**不进入可重试的 `runner` 桶**；当 `spec.provider_rejection_fallback` 声明时，用该模型再跑一次（重新派发），并写 `run.fallback` 事件留痕。
- 现有 markers：`inappropriate content`、`content exists risk`、`data_inspection_failed`、`content_filter`、`malformed diagnostic json`，以及 2026-09-24 新增的 `provider rejected the request schema or tool payload`、`request format rejected, http 400`。
- 声明了 `provider_rejection_fallback: deepseek/deepseek-flash` 的 agent：`compiler-news`、`personal-historian`、`wechat-archivist`、`world-historian`（`agent.yaml`）。
- 依据（2026-09-24，用户决定）：两个拒绝方都在 China 侧路线上，而官方 DeepSeek API（`https://api.deepseek.com`）是另一家、另一套校验，值得再试一次。这取代了早先「malformed-400 重发同样失败、故排除」的判断。

### 2. OpenClaw agent 侧（模型链）

OpenClaw 的模型 failover 只在「可 failover 的错误」上换模型；**被判为 final provider refusal 的错误会直接结束这一轮，不换模型**（这是产品设计，不是配置能改的）。实测我们这一类会走链（能看到 qwen → zai 的尝试），所以链上要有落点。

当前链（2026-09-24 配置，`openclaw config patch`，无需重启）：

- `agents.defaults.model`：`qwen/deepseek-v4.1-flash` → `[deepseek/deepseek-flash, zai/glm-5.3]`
- `feishu1 / feishu3 / feishu4 / feishu5 / xiaohao`：同上（此前 feishu1/3/5/xiaohao 是无 fallback 的严格单模型，等于一拒即死）
- `intelligence / serendipity`：`zai-intelligence-serendipity/glm-5.2` → `[qwen/deepseek-v4.1-flash, deepseek/deepseek-flash]`
- `feishu2`、`main` 继承 defaults
- PAP agent（world-historian / compiler-news / wechat-archivist / personal-historian）走 PAP 派发，模型由 `spec` 固定，靠第 1 层兜底

## 载荷纪律（治本的那一半）

兜底只是安全网；这次真正让它跑通的是把载荷变小：

- 工具输出保持小：查询结果截断到几十行；不要 `ls` 整个 vault / 仓库目录、不要 dump 整张表、不要打印长文件全文。
- 参考文档只取需要的段落，不要一次性把长参考文件读进上下文。
- 检索一次一条，不要并发多个大 `web_search` / `web_fetch`。
- 写库分步走：先把要写的内容落盘（bundle JSON），再执行 `store-bundle` / 渲染命令。
- 撞上这个错误时**不要原样重试**：把这一步的载荷拆小再试。

feishu4 的 workspace `AGENTS.md` 已把这段写成常驻规则。

## 相关改动（2026-09-24）

- `b00366a`：PAP markers 扩类 + `news-follow` / `news-capture` 的「Vault completion」要求（改了 vault 文件必须走 SOP：拉取 → 批注守卫 → 分组提交 → 推送 → 再同步核验；步骤在 `agents/world-historian/profile/skills/news-follow/references/vault-completion-sop.md`）。
- OpenClaw 配置：上表的模型链（`agents.defaults.model` 与各 agent 条目）。
- feishu4 `~/.openclaw/workspace-feishu4/AGENTS.md`：新增「工具输出与载荷纪律」。

## 边界

- 被 OpenClaw 判为 **final provider refusal** 的错误不会走链，任何 fallback 配置都救不了；只能改派发方（换主模型）或拆小载荷。
- 兜底不改变「载荷本身不合规」这个事实：它提高成功率，不是万能。
- 不要把这一类和配额/内容审核混为一谈，处理方式不同（配额与内容审核各有自己的规则）。