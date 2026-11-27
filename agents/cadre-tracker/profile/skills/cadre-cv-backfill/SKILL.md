---
name: cadre-cv-backfill
description: 冷启动底库建设与官员全量历史履历双源互校回填（Batch 0/1/2）。
---

# Cadre CV Backfill（冷启动与全量履历回填）

本技能用于构建全国副省部级及以上官员底库，或针对新入库官员补齐其早年厅局级、县处级完整仕途与学缘经历。

## 三批次冷启动规程

1. **Batch 0（机构骨架与改革沿革初始化）**：
   ```bash
   "$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/cli.py" migrate --pretty
   "$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/cli.py" seed-orgs --pretty
   ```
2. **Batch 1（顶层 ~500 人核心池）**：
   - 使用 `cli.py poll --source wiki` 拉取二十届中央委员、候补委员、中纪委委员的 Wikidata / Wikitext 原始记录。
   - 对照人民网/中经网地方领导资料库官方标准简历做双源互校（Tier 2 优先于 Tier 3）。
3. **Batch 2（省部级全量 ~2,600 人扩展池）**：
   - 补齐 31 省区市四套班子、法检两长、国务院部委副部长、中管央企与中管高校正副职历史履历。

## 强制拆解与精度规范

- 严格遵守 `cadre-intake` 的三条拆解铁律：
  1. 一揽子兼职原子化拆分（不合并多机构头衔）。
  2. “其间”嵌套党校/挂职不断裂主职务时间区间。
  3. 党政序列严格剥离（`party_local` vs `gov_local`）。
- 仅记载年份的早期履历（如“1992年毕业”）统一规范为 `YYYY-07`（毕业季）或 `YYYY-01`，并设置 `date_precision="YEAR"`。
- 已入库副部级以上官员的早年厅局级、县处级、科级履历必须完整录入，确保早年上下级共事与提拔链可被图查询穿透。
- 所有产出通过 `cli.py ingest-bundle` 幂等落库，严禁直接写 SQL。
