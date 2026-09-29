# 本地图像处理方案迁移到另一台 PC

本文件是当前探索分支的交接清单。完整的处理链为：按 `manifest.json` 转正并裁切单页 → PaddleOCR 检测正文行 → OpenCV 检测波浪下划线并关联行，另处理目视圈定的 `「」` → 合并相邻标记行 → PaddleOCR 识别 → 与 EPUB XHTML 索引模糊对齐并按标点扩展 → 独立裁取手写批注 → 生成离线核验页与实验报告。处理和核验均在本机运行。

## 1. 从 Git 获取方案

在另一台 Linux x86_64 PC（或 Windows 上的 WSL2 Linux x86_64）安装 Git、Python 3.11 和 `uv`，然后：

```bash
git clone git@github.com:Xing-Shuchen/personal-agent-platform.git
cd personal-agent-platform
git switch explore/segement-ocr-alignment
```

Git 中包含 `bookscan/` 实现、`tests/test_bookscan.py`、配置、依赖版本快照、规范、逐页 `manifest.json`、`inputs.sha256`，以及这次实验的 22 张扫描照片和一本 EPUB。当前分支是探索交接分支；不要把它当作已达到正式使用准确率的发布版本。

## 2. 校验输入素材

克隆探索分支后，`local-processing/` 下应已有 22 张 `20260929-140150.979-*.jpg` 和 `社会理论二十讲.epub`，无需单独复制。`manifest.json` 中的坐标、旋转和手写区域都针对这批**原始字节**，不适用于重压缩或改名后的文件。

在另一台 PC 验证 23 个文件完整：

```bash
cd local-processing
sha256sum -c inputs.sha256
cd ..
```

全部显示 `OK` 后再运行。如果只使用另一批扫描件和 EPUB，需要新建对应的 manifest、修改 `config.yaml` 的 EPUB 文件名，并重新核验区域和参数；当前 manifest 不能直接套用。

## 3. 重建 Python 环境和本地模型

```bash
uv venv local-processing/.venv --python 3.11
uv pip install --python local-processing/.venv/bin/python --index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/ paddlepaddle==3.4.0
uv pip install --python local-processing/.venv/bin/python -r local-processing/requirements.lock
uv pip check --python local-processing/.venv/bin/python
local-processing/.venv/bin/python -m bookscan prepare --config local-processing/config.yaml
```

`prepare` 是唯一允许下载 OCR 权重的步骤，会准备 `PP-OCRv5_mobile_det` 和 `PP-OCRv5_mobile_rec`。默认模型位置是 `~/.paddlex/official_models/`；路径不同则修改 `config.yaml` 的 `models.*_dir`。模型和虚拟环境不进 Git。`run` 只使用本地模型，禁用模型来源检查和 Hugging Face 在线访问。版本快照来自本机 Python 3.11 / Linux x86_64；其他 CPU、Python 或操作系统组合需要单独验证。

## 4. 验证和处理

以下命令均从仓库根目录执行：

```bash
local-processing/.venv/bin/python -m pytest tests/test_bookscan.py -q
local-processing/.venv/bin/python -m bookscan inspect --root local-processing --manifest local-processing/manifest.json
local-processing/.venv/bin/python -m bookscan run --config local-processing/config.yaml
```

`inspect` 应看到 22 页、一本可解析 EPUB 和已准备好的模型。`run` 会打印新建的 `local-processing/output/<run_id>/`。每次运行使用新目录，不覆盖原图。可用 `--scan-index 12` 对 manifest 中从 0 开始的单页重跑。视觉和逐行 OCR 缓存在 `local-processing/.cache/`；更换 EPUB 或对齐阈值不必重跑视觉阶段，更换 ROI 或视觉参数会产生新的缓存键。

在 `output/<run_id>/` 中打开 `review.html`：可查看转正单页、标记框、证据裁图、OCR、EPUB 对齐、手写批注及零结果页。逐页人工确认误收和漏检；在原始图上拖框补漏检。浏览器本地保存草稿，也能下载 `review-decisions.json` 并在另一台 PC 导入**同一 run ID** 的报告。只有全部页面和已选行确认后，才导出 `ground-truth.jsonl`：

```bash
local-processing/.venv/bin/python -m bookscan evaluate --run local-processing/output/<run_id> --ground-truth local-processing/ground-truth.jsonl
```

人工转录需要逐字核对后填写。留空时不纳入 CER；`「」` 行不纳入下划线行选择指标。机器输出和人工判断分开保存。`annotation-review.json` 用于手写批注转录。

## 5. 若要延续当前 PC 的核验状态

Git 中不包含旧运行目录、缓存或浏览器 localStorage。若需要直接继续旧报告，另行复制完整 `local-processing/output/<run_id>/`，以及下载的 `review-decisions.json` 草稿，再在目标浏览器导入。旧报告中的原始照片链接依赖仓库布局和相同文件名。只需复现结果时，按第 4 步重新运行即可；新运行会有新的 run ID，旧草稿不可直接导入。

## 6. 当前结果与尚未完成的核验

本机最近一次完整运行处理 22 页，输出 126 条标记行、51 组（49 组下划线、2 组 `「」`）及 15 处手写批注候选，未记录处理失败；这些是**机器计数**，不是正确率。手写区域和 `「」` 端点目前来自目视写入 manifest，未实现自动发现。未取得逐页人工真值，因此 precision、recall、CER 和 EPUB 误改率均未评估。另一台 PC 应先用核验页面完成全页真值，再据实决定是否把方法接入正式 Librarian 流程。

代码结构与参数详见 [README.md](README.md)、[SETUP.md](SETUP.md) 和 [local-processing-spec.md](local-processing-spec.md)。
