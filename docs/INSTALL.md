# 安装说明

## 推荐：工作区级安装

1. 在 WorkBuddy 桌面端选定一个专门的本地工作区，不选择整个用户主目录。
2. 下载本项目 v0.1.1 源码并解压到临时位置，先读 README、SKILL.md 和脚本。
3. 检查 Python 3.9+。从源码目录运行 `python3 tools/install.py --workspace "实际知识库路径" --init`；Windows 检测 `py -3`。
4. 回到同一工作区新建对话，明确调用 chao-knowledge，完成一份真实草稿。

安装器只复制清单内的技能文件，不复制 tests/docs 或任何个人资料。它不会关闭权限控制，不修改 WorkBuddy 全局配置，不安装第三方依赖。不同版本/用户修改过的安装会停止，不能一键覆盖。

## 可选：导入 ZIP

技能面板支持导入本地包；使用 `dist/chao-knowledge-v0.1.1.zip`，不是整个源码压缩包。包内为一个 chao-knowledge 目录，含 SKILL.md、scripts、references、assets、LICENSE 和 manifest。

客户端对包格式和界面的处理以实际版本为准，本项目尚未用 WorkBuddy GUI 验证。识别失败可解压，将完整 chao-knowledge 目录放入工作区 `.codebuddy/skills/`，避免同名目录嵌套。目录方式也需新建任务测试技能是否加载。

## 安全更新与卸载

更新前备份当前 Skill 文件夹，确认是否有自己修改过的指令；新版本先放到新的测试工作区。不要以升级为由删除 `.chao/` 或业务资料。

卸载只移除技能文件夹；知识库业务资料保留。若要移除 AGENTS.md 入口，仅删除 `chao-knowledge:begin/end` 标记包围的块，保留其他内容。彻底删除业务资料与系统备份须用户另外明确授权。

## 常见问题

Python 缺失：详见 Skill 内 `references/fallback.md`，先用手动简化模式或由用户决定安装依赖。

已有目录冲突：停止覆盖，在新工作区试用；不自动迁移用户成熟的知识库。

权限不足：由用户授予最小必要文件权限，不以关闭沙箱或无限制目录访问解决。

网络无法访问 GitHub：使用已经获取并校验过的本地包；不能把下载失败描述成安装成功。

新对话“不记得”：检查是否选择同一工作区、技能是否启用、AGENTS.md 是否被宿主读取；明确调用 context 并核对规则 ID，不能只凭生成语气相近认定记忆成功。
