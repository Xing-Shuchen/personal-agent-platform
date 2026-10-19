---
name: zhihu-collections
description: Incrementally pull Zhihu collections into the Obsidian vault, commit and push new notes, verify Remotely Save, and report by collection.
---

# 知乎收藏夹增量归档

PAP 每周日 10:00（Asia/Shanghai）运行本技能。按以下顺序执行，使用已有
登录态和增量状态文件；不要自行扫码、启动或重启 Obsidian，也不要直接上传 COS。

1. **检查登录态。** 运行 `~/.local/bin/zhihu status`。如果未登录，立即停止并
   报告「知乎登录态失效，需要重新扫码」；不要自行扫码登录。

2. **RS 前置同步。** 用 `pgrep -x obsidian` 检查 Obsidian 是否正在运行。
   仅在已运行时触发 Remotely Save（RS）：

   ```bash
   HOME="$HOME" "$HOME/.local/bin/obsidian" command id=remotely-save:start-sync
   ```

   等待约 30 秒。若 CLI 不可用，继续拉取，但在报告中注明「未做 RS 前置同步」。
   若 Obsidian 未运行或同步命令失败，也如实说明未做前置同步；不要为此启动或
   重启 Obsidian，不要绕过 RS 直接上传 COS。

3. **增量拉取。** 运行：

   ```bash
   cd "$HOME/.zhihu-cli" && "$HOME/.local/share/uv/tools/pyzhihu-cli/bin/python" pull_collections_to_vault.py
   ```

   脚本依据状态文件增量拉取，只向
   `~/文档/Obsidian/Second_Brain/2Area/40 学习与阅读/知乎/<收藏夹名>/`
   写入新笔记，绝不删除已有笔记。日志为 `~/.zhihu-cli/collections_pull.log`。
   从本次运行输出和日志记录新笔记的准确路径、标题、所属收藏夹和新增数量，供
   后续核验及报告使用；不要将历史日志中的笔记算作本次新增。

4. **提交并推送。** 仅在本次写入新笔记时运行：

   ```bash
   bash "$HOME/.zhihu-cli/commit_collections.sh"
   git -C ~/文档/Obsidian/Second_Brain push origin main
   git -C ~/文档/Obsidian/Second_Brain log --oneline -1 main
   git -C ~/文档/Obsidian/Second_Brain log --oneline -1 origin/main
   ```

   确认最后两条命令输出相同，记录 commit/push 结果。Vault 可能含有与本次
   拉取无关的未提交改动；提交范围只能是 `2Area/40 学习与阅读/知乎/`。
   检查脚本的暂存范围，不得用 `git add .`、`git add -A` 或 `git commit -a`
   把其他路径的改动带入提交；已有无关暂存内容也不得带入。

5. **RS 后置同步及验证。** 若 Obsidian 仍在运行，再执行第 2 步的 RS 同步
   命令并等待约 60 秒。CLI 不可用或 Obsidian 未运行时如实记录，不启动或重启。
   对本次每一篇新笔记，用内联 Python/boto3 脚本只读核验 COS：

   - 读取 `<vault>/.obsidian/plugins/remotely-save/data.json` 的 `d` 字段，
     先将字符串反转，再 base64 解码并解析 JSON。例如：

     ```python
     import base64
     import json
     from pathlib import Path

     vault = Path.home() / "文档/Obsidian/Second_Brain"
     data = json.loads((vault / ".obsidian/plugins/remotely-save/data.json").read_text())
     config = json.loads(base64.b64decode(data["d"][::-1]).decode("utf-8"))
     ```

   - 在同一个内联脚本中，从解码后的实际 S3 配置读取 endpoint、region、
     bucket、凭证和远端目录前缀，创建 `boto3.client("s3", ...)`。不得将凭证
     或解码后的完整配置打印到报告、日志或写入仓库。
   - 将本次新笔记相对于 vault 的路径与配置的远端目录前缀组合成对象 key；
     对每篇笔记以该 key 为 `Prefix` 调用 `list_objects_v2`（处理分页），
     检查存在完全匹配的 `Key`，并比较对象的 `Size` 与本地文件的
     `Path.stat().st_size`。前缀下其他对象的存在不代表该笔记已同步。
   - 忽略已知历史缺口 `_debug_remotely_save/`、`印象笔记/_migration/`、
     `attachments/_orphan/`，它们不属于本次新笔记核验范围。
   - 新笔记仍缺失或大小不符时，报告「RS 同步未落地，需 feishu3 直传」，并
     列出未通过的笔记；本任务绝不直接上传。读取配置或查询失败时如实报告
     核验失败原因，不得声称已同步。

6. **报告。** 报告新增数量、涉及收藏夹、commit/push 结果、RS 核验结果，
   并且**按收藏夹分组列出本次每一篇新笔记的标题**。本次没有新增笔记且没有
   commit、也没有错误或需要报告的同步异常时，输出必须恰好为：

   ```text
   [SILENT]
   ```

   这是 PAP 抑制投递的静默标记，不要附加解释、空行内容或使用 `NO_REPLY`。
   登录失效、执行错误或同步异常仍须按相应步骤简要报告，不得用静默掩盖。

7. **错误处理。** 发生错误时简要报告原因；最多重试一次。重试前先检查
   增量状态、已有文件及提交结果，避免重复写入或重复提交。登录失效直接停止，
   不自行扫码；同步失败不改用 COS 直传。
