# 安装说明 · v0.2.0

## 推荐：工作区级安装

1. 新建一个独立知识库文件夹，不要选择桌面、用户主目录或整个磁盘。
2. 下载本项目 v0.2.0 源码到临时位置，先阅读 README、SKILL.md 和安装脚本。
3. 在源码目录执行：

`python3 tools/install.py --workspace "/你的路径/我的 AI 知识库" --init`

Windows 可按环境使用 `py -3 tools/install.py --workspace "D:\\我的AI知识库" --init`。

安装器把 Skill 放到当前工作区 `.codebuddy/skills/chao-knowledge/`，并调用初始化脚本。已有不同文件不会被静默覆盖。

## 可选：导入 ZIP

版本发布页提供 `chao-knowledge-v0.2.0.zip`。ZIP 内只有技能包，不包含你的私人知识库。WorkBuddy 是否能从 ZIP 自动识别，取决于当前客户端版本；如失败，使用工作区级安装。

## 从 v0.1.x 更新

从源码目录执行：

`python3 tools/install.py --workspace "/你的路径/我的 AI 知识库" --update --init`

`--update` 只会替换一个**清单完整、未被手工修改**的旧版 chao-knowledge，并把旧 Skill 备份到 `.codebuddy/skill-backups/`。如果检测到用户手工改过旧 Skill，会直接停止，不覆盖自定义内容。

随后 v0.2 会补齐新的可见目录和 Markdown 视图，但不会自动搬移旧的 `00-待整理`、`01-资料`、`02-作品`、`03-复盘`。先运行健康检查，确认迁移计划后再处理。

## 常见问题

- Python 不可用：按 `references/fallback.md` 的手动降级方式使用，不要让 Agent 擅自安装系统软件。
- 视频链接没有逐字稿：只保存链接不等于读取成功，请提供本地视频/逐字稿或使用宿主已有转写能力。
- WorkBuddy 没发现 Skill：检查工作区、`.codebuddy/skills/chao-knowledge/SKILL.md`、客户端权限和重新载入。
- 目录冲突：停止自动写入，先确认原目录用途，不删除现有文件。
