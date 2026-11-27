---
name: cadre-intake
description: 日常增量中纪委通报、人社部/新华社任免、深度报道与官网 DOM 异动的结构化抽取与校验入库。
---

# Cadre Intake（增量信源结构化摄入）

本技能负责将 `gate_precheck.py` 捕获的待解析公开信源转化为符合 `cadre-bundle` v1.0 契约的结构化 JSON，并调用确定性 CLI 校验入库。

## 固定参考文件

执行前先阅读：
- `$PAP_ROOT/agents/cadre-tracker/profile/references/cadre-bundle.md`
- `$PAP_ROOT/agents/cadre-tracker/profile/references/org-reform-lineage.md`
- `$PAP_ROOT/agents/cadre-tracker/profile/references/ccdi-violation-lexicon.md`

## 执行步骤

1. **门控预检（零空转）**：若非手工指定 `source_id`，先运行：
   ```bash
   "$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/gate_precheck.py"
   ```
   若输出 `gate_open: false`，立即停止并返回 `NO_REPLY`。
2. **拉取待解析原始信源**：
   ```bash
   "$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/cli.py" fetch-pending --pretty
   ```
3. **严格按拆解规则生成 `cadre-bundle` JSON**（写入 `$PAP_ROOT/var/cadre-tracker/bundles/<source_id>.json`）：
   - **一揽子兼职原子化拆分**：遇到 `2021.02—2023.01 北京市委常委、教育工委书记`，严禁合并为一条记录！必须拆成两条 `tenures`：
     - 一条挂载 `中共北京市委员会`（`role_title="常委"`, `role_tier="member"`, `is_concurrent=0`）
     - 一条挂载 `中共北京市委教育工作委员会`（`role_title="书记"`, `role_tier="chief"`, `is_concurrent=1`）
   - **“其间”嵌套经历不断裂原则**：遇到 `2011.02—2017.05 北京市石景山区委副书记、区长（其间：2014.03—2014.07中央党校中青年干部培训一班学习）`，主职务保持 `2011-02` 至 `2017-05` 完整连续区间不变；括号内党校学习单独生成一条 `education_records`，并在 `tenures` 生成一条 `is_concurrent=1` 的党校培训记录。
   - **党政序列严格剥离**：带“省委/市委/区委”且职务为“书记/副书记/常委/委员”归入 `中共XX委员会`（`party_local`）；“省长/市长/副市长/区长/厅长/局长”归入 `XX人民政府` 或对应委办局（`gov_local`）。
   - **事实与推测隔离**：媒体推测性关联仅写入 `claims` 且 `certainty` 必须为 `SPECULATION` 或 `RUMOR`，不得改动 `persons.status` 或 `tenures`。
4. **校验并幂等入库**（严禁直接操作 SQLite）：
   ```bash
   "$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/cli.py" ingest-bundle --file "$PAP_ROOT/var/cadre-tracker/bundles/<source_id>.json" --pretty
   ```
5. **异动升级触发**：
   - 若入库结果触发了 `under_investigation`、`expelled`、`anomaly_watch` 或核心正省部级主官换帅，立即转入 `cadre-shockwave-brief` 流程生成关联快报。
   - 若产生了 `disambiguation_conflict`（`review_status='needs_review'`），在摘要中提示用户调用 `cadre-review-resolve` 裁决。
   - 若仅为常规无异动静默入库，结束并返回 `NO_REPLY`。
