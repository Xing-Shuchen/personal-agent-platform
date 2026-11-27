---
name: cadre-crosslink
description: 为 World Historian 宏观叙事线程按需补充国内政经人物的仕途轨迹与关联震荡波背景（只读跨库联邦）。
---

# Cadre Crosslink（政经人事背景跨库联查）

当 `news-capture`、`news-follow` 或 `news-morning-brief` 识别到国内副省部级及以上政经人物实体时，可通过本技能按需调用只读联邦查询器 `cadre_lookup.py` 获取该官员的客观仕途纵深背景，严禁直接读写 `cadre.sqlite3`，也严禁将静默历史履历批量灌入 `world-historian` 的 `entities` 或 `events` 表。

## 调用方式

```bash
"$PAP_ROOT/.venv/bin/python" \
  "$PAP_ROOT/agents/world-historian/runtime/cadre_lookup.py" \
  --names "陈吉宁,夏林茂"
```

## 返回字段与使用边界

- `db_available`: 若 `cadre.sqlite3` 尚未初始化则返回 `false` 与空列表，直接跳过不阻塞原有流程。
- `entities[]`: 包含官员的 `current_rank`、`status`、`recent_tenures`（近 10 年关键主政地与职务）以及 `shockwave_context`（与近期已落马或现役高关联官员的紧密度指数 CI 摘要）。
- **克制使用**：仅将与当前宏观事件直接相关的关键主政背景与客观交集摘要融入编年卡片的上下文说明，不得将客观共事关系渲染为未经证实的因果断言。
