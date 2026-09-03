# GitCode → GitHub 镜像同步

本仓库的主远端（唯一事实源）是 GitCode；GitHub 是只读镜像，由
GitHub Actions 每 3 小时自动从 GitCode 拉取同步。

## 配置

- Workflow：`.github/workflows/sync-gitcode.yml`（默认分支上生效）
- 触发：`schedule`（UTC `23 */3 * * *`，即北京时间每 3 小时的 23 分——错峰，GitHub Actions 整点 0 分是负载高峰，延迟/丢触发最严重）+ `workflow_dispatch`（手动）
- 依赖 Secret：GitHub 仓库 `GITCODE_TOKEN`（GitCode 访问令牌，私有仓库拉取用）
- 权限：workflow 内显式声明 `permissions: contents: write`（GITHUB_TOKEN 镜像推送需要）

## 约定

1. **日常提交只推 GitCode（origin）**。GitHub 由镜像自动跟进。
2. **不要在 GitHub 直接提交**——下次镜像同步（`--prune --force`）会覆盖 GitHub 侧的独立改动。
3. 镜像只同步 `refs/heads/*` 与 `refs/tags/*` 两个命名空间，刻意不用
   `git push --mirror`：mirror 模式会尝试更新 GitHub 的 `refs/pull/*` 等
   隐藏 ref，被服务端拒绝（"deny updating a hidden ref"）。
4. 两边分支/标签应始终一致；不一致时先看
   [Actions 运行日志](https://github.com/Xing-Shuchen/personal-agent-platform/actions)。

## 冷启动（bootstrap）注意

workflow 文件必须已在 GitHub 默认分支上存在，Actions 才会注册定时任务——
而镜像同步本身依赖这个 workflow。所以**首个含 workflow 的提交必须手动
`git push github` 两边都推**；之后的日常提交才走"只推 GitCode、镜像自动
跟进"的常态。本仓库的首推提交：`62cf2b2`（2026-09-03）。

## 排查

| 症状 | 原因 | 处理 |
|------|------|------|
| Actions 运行失败 `Authentication failed` | `GITCODE_TOKEN` 名字不一致或令牌过期 | Settings → Secrets and variables → Actions 核对 |
| 推送被拒 `refusing to allow ... token` | GITHUB_TOKEN 无写权限 | 本仓库已用 `permissions:` 声明；若仍失败查 Settings → Actions → General → Workflow permissions |
| 定时未触发 | GitHub 定时任务常有 5–30 分钟延迟；仓库 60 天无活动会被自动禁用 | 手动 workflow_dispatch 验证 |
