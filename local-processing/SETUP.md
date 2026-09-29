# 本地图像处理环境

当前 PC 已在 `local-processing/.venv/` 安装 CPU 推理环境。该目录不会进入 Git。本次实验的 22 张样本照片和 EPUB 已提交到探索分支。

| 用途 | 已安装版本 |
| --- | --- |
| OpenCV（含 `threshold`、形态学、连通域、投影/轮廓） | `opencv-contrib-python 4.10.0.84` |
| PaddleOCR 文本检测与识别 | `paddleocr 3.7.0`、`paddlepaddle 3.4.0`（CPU） |
| OCR 与 EPUB 模糊匹配 | `rapidfuzz 3.14.6` |
| EPUB XHTML 解析 | Python 标准库 `zipfile`，另有 `lxml 6.1.3` |
| 测试 | `pytest 8.4.2` |

已下载 `PP-OCRv5_mobile_det` 和 `PP-OCRv5_mobile_rec`，存放在本机 `~/.paddlex/official_models/`，同样不进入 Git。对一张样本照片成功完成本地推理，输出 75 个 OCR 检测结果；这只验证环境可运行，不代表划线分割或识别准确率。

在另一台 Linux x86_64 PC 上重建环境：

```bash
uv venv local-processing/.venv --python 3.11
uv pip install --python local-processing/.venv/bin/python --index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/ paddlepaddle==3.4.0
uv pip install --python local-processing/.venv/bin/python -r local-processing/requirements.lock
uv pip check --python local-processing/.venv/bin/python
```

显式下载／检查模型：

```bash
local-processing/.venv/bin/python -m bookscan prepare --config local-processing/config.yaml
```

`run` 只接受 `config.yaml` 指定的本地权重路径，缺少模型会失败，不会隐式下载。当前 CPU 环境需要禁用 oneDNN，否则一次样本推理出现 `ConvertPirAttribute2RuntimeAttribute` 错误。下面是直接调用 PaddleOCR 的等价示例：

```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    device="cpu",
    enable_mkldnn=False,
)
result = ocr.predict("local-processing/20260929-140150.979-1.jpg")
```

EPUB 的 XHTML 可直接用 `zipfile.ZipFile` 读取；这一环节无需下载模型。

`requirements.lock` 是这台 Linux x86_64 / Python 3.11 环境的完整已安装版本快照；其他平台需重新验证轮子兼容性。模型文件需在另一台 PC 上准备；本次实验的原始扫描件和 EPUB 随探索分支同步。
