---
name: news-thread-relations
description: 每晚比较当天有更新的 Chronicle Threads，保存带证据和推断边界的关联并同步 vault。
---

# 当日更新 Threads 的夜间关联发现

由 PAP 的 `world-thread-relations-nightly` 每天 23:50（Asia/Shanghai）运行。
只使用 Chronicle 已有材料，不联网，不读取个人资料，不修改调度或模型配置。
这项任务只关联**两端都在当天更新集合中**的 Threads，不扩展为全库任意组合。

## 准备当日材料

以 Asia/Shanghai 的当天日期为 `YYYY-MM-DD`，启动时固定该日期；同次任务跨零点继续或重试时沿用原日期，补跑可显式指定日期。扫描范围为该日 00:00 起至准备材料时已入库的更新，不承诺覆盖任务运行后才发生的更新。

```bash
"${PAP_ROOT:?}/.venv/bin/python" \
  "${PAP_ROOT:?}/agents/world-historian/runtime/daily_thread_relations.py" \
  --day YYYY-MM-DD \
  --output "${PAP_ROOT:?}/var/world-historian/reports/thread-relations/YYYY-MM-DD"
```

日期须替换为实际日期。目录记为本轮 `review_dir`。读取其 `manifest.json` 与 `pairs.json`；逐个按需读取 `evidence_file`，不要把所有全文一次塞入上下文。脚本按新建或修改的 Thread、事件成员关系、Event、Claim、Quote、当前状态、问题及后见解释选择更新集合，按入库更新时间而非新闻发生日期计算。与 `last_checked_at` 同时更新的纯检查元数据不单独入选；文件重渲染和关系新增不作为新闻更新。旧专题可以作为入选 Thread 内的历史上下文，但不能作为集合外的新关系端点。

集合少于两个 Thread 时，记录本地 `review.json`（日期、集合、0 对、无新增原因），然后返回 `NO_REPLY`。

## 发现与复核

1. 筛选清单中的每一对 Thread，先看共享事件、明确相互引用、事件级关系和特定机制，再阅读双方完整证据。按需核对已存来源、原文摘录和后见解释。
2. 同一公司、人物、泛主题或相近日期不足以建立关系。没有具体桥接证据就不写入；不要为达到数量目标连边。
3. 直接共享记录或明确回应可设 `active`；机制类比、背景假说、评论推断只能设 `candidate`。置信度衡量关联支持程度，不代表基础新闻已被独立证实。保留原记录的不确定性与反证。
4. 检查两种关系表的已有记录以及双向端点。相同端点与语义关系不重复写入；已有关系（包括 rejected）没有实质新证据时保持原样。出现新证据时沿用既有 `relations.id`，合并保留原证据；不要用另一类型绕过已有的否定结论。
5. 写入前再次只读检查现有关系，防止与其他跟进／反思任务重复。新关系采用稳定 ID：`rel_daily_` 加 `sha256('|'.join(sorted([src_id,dst_id])) + '|' + relation_type)` 的前 20 个十六进制字符，不把日期加入 ID。回应、背景等有向关系仍按实际语义保存 src/dst。

## 保存与 vault 渲染

只生成 `relations` bundle，不创建或改写 Threads、Events、Claims，不更改成员关系。每条必填：

- `id`、`src_type: thread`、`dst_type: thread`、两个已入选的真实 ID（`src_ref`、`dst_ref`）。
- `relation_type`、`status`（active/candidate）、`confidence`。
- `evidence` 至少包含 `关联理由：<具体说明>`、`推断边界：<哪些结论尚不能推出>`，以及双方实际 Event／Claim／Source ID 和已有来源 URL。候选关联不得省略推断边界。

将 bundle 保存为本轮目录的 `relations.json`，通过现有原子入库入口保存：

```bash
"${PAP_ROOT:?}/.venv/bin/python" \
  "${PAP_ROOT:?}/agents/world-historian/runtime/cli.py" store-bundle \
  --json "${PAP_ROOT:?}/var/world-historian/reports/thread-relations/YYYY-MM-DD/relations.json"
```

该入口会同步受影响的 vault 笔记，展示关联说明、边界及 `[[...]]` 双链。检查返回的 `obsidian.errors` 与 `skipped`；若同步失败，保留已成功入库的 ID，修复后仅重试对应 Thread 的 `sync --thread <id>`，不要再创建一批关系。

每次保留 `review.json`：日期与更新集合、每对组合的采用／已有／未采用结论及原因、新增或更新 ID、各状态计数、入库和 vault 同步结果。零发现也记录。失败时明确报错供 PAP 运行日志审计，不要假称完成；正常完成只返回 `NO_REPLY`。这是本地后台任务，不发送额外日报。
