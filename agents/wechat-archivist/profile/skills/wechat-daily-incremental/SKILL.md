---
name: wechat-daily-incremental
description: 每日从已验证的 Ubuntu 微信 4.1.1.7 数据库副本增量归档消息。
---

# 每日增量归档

只执行以下本地命令，并将最终响应严格设为 `NO_REPLY`：

```bash
python3 "$PAP_ROOT/agents/wechat-archivist/runtime/export_incremental.py"
```

该脚本使用已缓存、已验证的密钥文件和只读数据库连接；它会把新消息追加到
`$PAP_AGENT_STATE_DIR/messages.jsonl`，并原子更新 checkpoint。不要读取、打印或发送
消息正文，不要访问网络，不要运行 GDB，不要修改微信原始数据库。

如果命令失败，最终响应以 `NO_REPLY` 结束，并在 `$PAP_AGENT_STATE_DIR/run-log.jsonl`
记录错误；不得把密钥、解密数据库或聊天正文写入 PAP 全局日志。
