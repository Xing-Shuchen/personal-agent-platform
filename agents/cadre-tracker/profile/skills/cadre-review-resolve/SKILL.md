---
name: cadre-review-resolve
description: 交互式清理同名干部消歧队列与存疑时间线冲突。
---

# Cadre Review Resolve（消歧队列人工裁决）

当 `resolver.py` 遇到同名官员得分落入模糊区间（$0.40 \le S < 0.85$ 或前两名分差 $\Delta S < 0.30$）时，会将记录挂起至 `claims_and_clues`（`review_status='needs_review'`）。本技能用于引导用户逐条拍板。

## 执行步骤

1. **列出待审核队列**：
   ```bash
   "$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/cli.py" review-list --pretty
   ```
2. **向用户清晰呈现每条冲突**：
   - 原文证据句（`evidence_quote`）与信源等级。
   - 候选人物清单（`person_id`、姓名、出生年月、籍贯、最近任职与匹配得分）。
   - 给出推荐选项：`bind`（绑定至指定 `person_id`）、`create`（新建独立人物档案）、`reject`（驳回无效/噪音线索）。
3. **执行用户确认后的裁决**：
   ```bash
   "$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/cli.py" review-decide \
     --claim-id "<claim_id>" \
     --action "<bind|create|reject>" \
     [--person-id "<person_id>"] --pretty
   ```
4. 若队列已清空，简洁汇报处理结果并结束。
