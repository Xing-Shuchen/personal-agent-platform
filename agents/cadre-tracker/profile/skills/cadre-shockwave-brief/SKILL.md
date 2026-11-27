---
name: cadre-shockwave-brief
description: 落马震荡波扫描、上下级穿透、Obsidian 人物档案刷新与政经人事关联快报合成。
---

# Cadre Shockwave Brief（落马震荡波与关联快报）

当目标官员进入 `under_investigation`（被查）、`expelled`（双开）、`anomaly_watch`（官网异常撤下）或关键正省部级主官换帅时调用本技能。

## 执行步骤

1. **震荡波紧密度扫描**：
   ```bash
   "$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/cli.py" shockwave --person "<姓名>" --top 20 --pretty
   ```
2. **核心关联人物双人深度穿透**（对 `already_fallen_associates` 与 `active_watch_list` 前 5 名执行）：
   ```bash
   "$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/cli.py" overlap --a "<目标姓名>" --b "<关联姓名>" --pretty
   ```
3. **关键一把手岗位前腐后继链检查**：
   ```bash
   "$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/cli.py" succession --org "<主政机构>" --role "<书记/市长>" --pretty
   ```
4. **按需刷新 Obsidian 档案**（仅当配置了 `OBSIDIAN_VAULT` / `PAP_VAULT` 时）：
   ```bash
   "$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/cli.py" project-obsidian --person "<目标姓名>" --pretty
   ```
5. **合成《政经人事异动与关联快报》**（简体中文）：
   - **事实通报**：逐字引用 Tier 1 官方通报及事件时间。
   - **历史已爆雷关联人（`already_fallen_associates`）**：列明 CI 指数、共事机构、重合年月与上下级关系（反向溯源传导链）。
   - **现役高危观察名单（`active_watch_list`）**：列明 Top-10 现役关联官员与客观交集维度；必须加注免责声明：“客观共事/辖属/学缘交集仅反映履历相关性，不构成涉案结论”。
   - **外围线索与推测**（如有）：单独成节，强制标注 `SPECULATION` / `RUMOR` 及来源。
   - 通过 `pap gate` 审核推送优先级（`ccdi_investigation`/`ccdi_sanction`/`dom_removal_anomaly` 为 `priority >= 90`）。
