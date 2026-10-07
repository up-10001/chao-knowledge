# 安装、更新与回滚 · v0.3.3

## Agent / WorkBuddy 一句话安装（首选）

在 WorkBuddy 选定本地工作区后发送：

> 帮我安装 chao-knowledge 这个 skill，地址是https://github.com/up-10001/chao-knowledge，装好以后告诉我装在哪里，并确认你能调用它。

不需要用户下载 ZIP、打开终端或解释 scope。安装 Agent 先读 [AGENT_INSTALL](../AGENT_INSTALL.md)：标准 Skills CLI → 环境不支持时正式 Release ZIP；502/503/timeout 不等于仓库不存在。安全审计与宿主权限确认保持正常，禁止缓存冒充安装。最终核对最新正式版本、实际路径、全包完整性、WorkBuddy 识别和真实调用。

标准命令为 `npx -y skills@latest add up-10001/chao-knowledge --skill chao-knowledge -y`。当前 CLI 支持的 agent/scope 必须核实。已确认支持 `.codebuddy/skills` 的 WorkBuddy 本地工作区可追加 `--agent codebuddy --copy`；这不意味着 CLI 的 CodeBuddy 用户级目录就是 WorkBuddy 用户级目录。仅有 CLI 成功还不算 WorkBuddy 成功。

安装结果区分：FRESH_INSTALL 新安装；UPDATED 旧版安全更新；ALREADY_INSTALLED 已核实最新完整包；INSTALL_FAILED 正常渠道/最终核验失败。无法核实最新版时不能用本地副本宣布成功。旧包先备份改名保留，手改/新增内容停止覆盖，知识库不擦除。

## 手动 ZIP 安装

从 [最新正式 Release](https://github.com/up-10001/chao-knowledge/releases/latest) 获取 `chao-knowledge-v0.3.3.zip` 和 SHA256SUMS；核对同版清单并审阅后，在 **专家·技能·连接器 → 技能 → 添加技能 → 上传技能** 导入，确认启用，再调用 chao-knowledge。普通用户可让 Agent 完成此 fallback。

不同客户端菜单/用户目录可能变化，以 [官方技能说明](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)、[项目说明](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project) 和实际发现结果为准。包仍使用 `{skill-name}/SKILL.md`、references、scripts、assets 结构，ZIP 不包含个人知识库。SHA256 只检查一致性，不是数字签名或来源认证。

## 开发者项目级安装

审阅固定正式 tag 的源码和安装器后执行：

`python3 tools/install.py --workspace "/独立路径/我的 AI 知识库" --init`

安装器目标为该工作区 `.codebuddy/skills/chao-knowledge`。Windows 可用 `py -3` 或 `python`。不要把知识库建在源码仓库、主目录或磁盘根目录。宿主发现仍要实测，读取 SKILL.md 不算自动发现。

运行脚本需已有 Python 3.9+；缺运行时按包内 fallback 说明解释，不擅自安装系统软件或放宽安全设置。

## 旧知识库升级

下载并审阅新版本源码，在**同一个知识库**运行：

`python3 tools/install.py --workspace "/独立路径/我的 AI 知识库" --update --init`

- 仅替换 manifest 完整且未经手改的旧 Skill；新增自定义文件也会停止覆盖。
- 旧 Skill 完整保存在 `.codebuddy/skill-backups/chao-knowledge-v旧版本-唯一编号/`。
- v0.1.x/v0.2.x 的 schema 1 自动迁到 schema 2。迁移前状态与可读入口保存在 `.chao/backups/pre-v0.3-唯一编号/`。
- 原资料、规则、作品版本、反馈和用户自定义文件保留；旧目录不自动搬移，记录仍指向原路径并可检索。
- 检测到手改可读入口时停止升级；若安装后初始化失败，会还原旧 Skill。先展示差异，用新包脚本的 sync 计划决定如何保留与采纳修改，再重新升级。
- 重复 init 幂等；重复更新同一完整包不会重新复制个人数据。

未来 schema 2 版本继续通过同一更新命令检查版本和完整性；遇到未知 schema 停写，不要求删库重建。

## 回滚

更新后还没有新增数据修改时，先保留整个知识库副本，再由 Agent 展示回滚范围。使用新版本源码里的安装器：

`python3 tools/install.py --workspace "/独立路径/我的 AI 知识库" --rollback ".codebuddy/skill-backups/实际旧包目录" --restore-migration --quote "确认恢复升级前版本，尚未新增数据"`

安装器核对旧 Skill 支持的 schema，并检查迁移后的数据及配置是否改动。条件满足才恢复升级前状态/入口和旧 Skill；原件、作品和新增文件不删除。

**升级后已有新资料、档案或规则时，禁止用旧状态覆盖当前库。** 应保留当前完整库，用升级前可信的整库备份另建工作区恢复；再把确认需要的数据导入。迁移备份只保存状态/入口，不能重建后来删除或变化的资料原件。

同 schema 的完整旧包可以只回滚 Skill；`--rollback` 不接受工作区外目录，不覆盖手改 Skill。单独 `rollback-migration` 也有只读计划，不能用它绕过数据保护。

## 常见问题

- **没发现技能**：确认桌面本地工作区、技能启用状态和 `.codebuddy/skills/chao-knowledge/SKILL.md`；新建对话明确调用。显式读取 SKILL.md 的降级方式需要注明，不算自动发现通过。
- **只有链接/视频没正文**：提供正文/逐字稿，或使用宿主实际可用的读取工具。保存 URL/原件不等于读取或转写。
- **文件冲突/手工改动**：保留文件，先用 sync 看差异；应用同步要明确范围，改动会备份。不要删除原库重试。
- **正在写入/LOCK**：v0.3.1 普通锁文件始终存在，文件存在不代表占用；进程退出由 OS 自动释放。超时等待另一任务结束，不手工清锁。旧 v0.3.0 目录锁须先停止旧任务，再用 migrate-locks 查看保留迁移计划；确认后只改名保留空目录，绝不自动删除。pending-write.json 的 status=idle 是正常状态，只有未完成记录才用 recover 查看范围。
- **权限提示**：检查命令与路径是否仅指向当前库，按宿主正常权限流程处理。不要切换完全访问来绕过提示。
- **状态损坏**：停写，保留现场，从可信备份恢复。没有备份就从原材料重新登记，不能伪造旧 ID 或确认历史。
