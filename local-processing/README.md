# 划线扫描件本地实验

实现依据：[local-processing-spec.md](local-processing-spec.md)。运行时不向云端发送图片、OCR 文本或 EPUB；只有显式 `prepare` 可以下载预训练模型。所有命令从仓库根目录执行。

跨 PC 迁移与提交范围见 [MIGRATION.md](MIGRATION.md)。

## 运行

```bash
local-processing/.venv/bin/python -m bookscan inspect --root local-processing --manifest local-processing/manifest.json
local-processing/.venv/bin/python -m bookscan prepare --config local-processing/config.yaml
local-processing/.venv/bin/python -m bookscan run --config local-processing/config.yaml
```

`manifest.json` 明确记录文件顺序、逐页旋转、倾斜角、有效页面 ROI，以及目视圈定的手写批注和角括号区域。当前样本的文件编号并非印刷页码顺序；程序保持 manifest 顺序并报告连续性冲突，不按 OCR 页码重排。`--scan-index 21` 可单页重跑。输出写入新的 `output/<run_id>/`，不覆盖原图和旧实验。机器输出、样本照片、EPUB、模型和缓存都不进 Git。

打开 `output/<run_id>/review.html` 逐页核验。绿色框是已选行，红框是下划线证据，橙框是待核对候选，蓝框是识别出的印刷页码。可点击打开原图和裁图；零结果页也会显示。
展开每页的“逐页人工核验”，先检查整页，再逐条判定已选下划线行。漏检行可在原始扫描件上拖框补入，或手工输入原图坐标。人工转录框默认留空，只有逐字核对后才填写；留空的行不计入 CER。每个阅读组还可单独判定标记范围和 EPUB 文本。草稿自动保存在当前浏览器；通过页面底部的“下载核验草稿 JSON”备份，在另一台 PC 上可导入同一运行目录的草稿。全部页面及已选行确认后，下载 `ground-truth.jsonl` 并执行下方的 `evaluate`。不同运行 ID 的草稿不能混用。
紫框是目视圈定的手写批注；每处有独立裁图和未经核实的 OCR 猜测。可在页面中填写人工转录，草稿存于当前浏览器的 localStorage，并可下载 `annotation-review.json`。
青框是目视圈定的手画 `「」` 范围；`groups.jsonl` 将其与下划线一样作为阅读组处理，`brackets.jsonl` 另存端点及跨行证据。无下划线的页面仍会处理手写批注和角括号。

`pages.jsonl` 包含每页状态、页码候选和推断来源；`lines.jsonl` 保留逐行 OCR 和坐标；`groups.jsonl` 把相邻划线行合成阅读组，保留整行 OCR、红线覆盖字位估算、对应 EPUB 区间和标点扩展文本。`annotations.jsonl` 单独保存手写批注裁图、源图坐标和未经核实的 OCR 猜测；当前样本的手写区域由目视检查写入 manifest，并非自动发现。EPUB 定位使用整行 OCR 作为上下文，但扩展从红线覆盖的区间开始。`review_candidates.jsonl`、`failures.jsonl`、`epub-index.json` 与 `debug/` 提供复核依据。对外 bbox 均为原图像素坐标；整页预览先裁成单页并转正。`run.json` 记录模型哈希、依赖版本、配置和耗时。

视觉检测和逐行 OCR 缓存在 `.cache/bookscan-v0.1/`。更换 EPUB 或对齐阈值后会重新对齐，但可复用视觉结果；更换 ROI、模型或检测配置会使相应缓存失效。`run` 默认使用本地模型路径并关闭模型来源检查。

## 人工真值与评估

先完整看完每页，包括零结果页，再使用离线页面导出 `ground-truth.jsonl`。每页一条 JSON，`page_id` 来自该次 `pages.jsonl`；`bbox` 为原图坐标。**漏检行也必须加入真值**。也可手工创建，示意：

```json
{"page_id":"page-000-...","page_number":39,"lines":[{"bbox":[100,200,800,250],"text":"照片中实际可见的整行文字"}]}
```

不确定是否有划线的行可用 `"ambiguous": true` 标注，评估时另计。某页确认无划线时写 `"lines": []`；真值必须覆盖所有页面。人工决定保存在独立的 `review-decisions.json` 草稿中，机器输出不会被覆盖。「」组可在页面上核验，但不计入下划线行选择指标。运行：

```bash
local-processing/.venv/bin/python -m bookscan evaluate --run local-processing/output/<run_id> --ground-truth local-processing/ground-truth.jsonl
```

评估采用一对一 bbox IoU ≥ 0.5，报告行级 precision/recall/F1、已匹配行的 OCR 与当前文本 CER、接受校正的精确率和已识别／推断页码准确率。无人工真值时 `experiment-report.md` 明确写“未评估”，机器选中数量不是准确率。

## 第一轮真实样本

22 张 JPEG 和一本本地 EPUB 已跑通。用户核验后，整页预览改为裁切转正，波浪线加入曲线候选，相邻划线行改为同组，EPUB 改为按标点扩展并单独标注来源。当前文件顺序与页码连续顺序冲突。**尚未得到逐页人工真值，不能把机器输出数量当作准确率或召回率**。请以最新运行目录中的报告为准；下一步优先核对波浪线漏检、短印刷笔画误收、分组及 EPUB 匹配位置。
