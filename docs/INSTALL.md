# 安装、更新与回滚 · v0.3.1

## WorkBuddy 桌面端

从 [Release](https://github.com/up-10001/chao-knowledge/releases/latest) 下载版本 ZIP。在 **专家·技能·连接器 → 技能 → 添加技能 → 上传技能** 中导入，然后确认启用状态。选择独立的本地知识库文件夹，发送“调用 chao-knowledge，带我完成第一次使用”。

不同版本菜单会变化，以 [官方技能说明](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market) 和实际界面为准。本包保留 `{skill-name}/SKILL.md`、references、scripts 结构与中英文描述、版本等元数据；参见 [官方包结构](https://open.workbuddy.cn/docs/skill)。ZIP 不包含个人知识库。已完成的客户端验证和未验证项见 [VALIDATION](VALIDATION.md)，官方能力说明不等于本包已通过实测。

完整模式需要 Python 3.9+，Agent 应先检查宿主已有运行时。无运行时不擅自安装 Python，按包内 fallback 说明降级。

## 项目级安装（可交给 WorkBuddy 执行）

不使用 ZIP 导入时，可以直接发送：

```text
请安装 https://github.com/up-10001/chao-knowledge 的 v0.3.1。
先获取该 tag 的源码并阅读 README、SKILL.md、安装脚本。
检查当前已选择的本地工作区、Python 3.9+ 和必要文件权限。
运行 tools/install.py --workspace 当前工作区绝对路径 --init。
保留已有文件；冲突或手工改动时停止覆盖并说明原因。
安装后调用 chao-knowledge，用我的背景和一份资料完成第一个任务。
```

安装器只把 Skill 放到 `.codebuddy/skills/chao-knowledge`，另建私人数据目录。不要把知识库创建在源码仓库、用户主目录或磁盘根目录。

开发者手动运行：

`python3 tools/install.py --workspace "/独立路径/我的 AI 知识库" --init`

Windows 使用可用的 `py -3` 或 `python` 替代 python3。包含空格的路径需引号。校验源码 manifest 与同版本 SHA256SUMS；它们检查一致性，不能替代对发布者的信任或提供数字签名。

[官方项目说明](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project) 确认 `.codebuddy/skills` 和 `AGENTS.md` 兼容。不能因此推断所有客户端模式都会自动触发：选本地工作区、启用 Skill，必要时新建对话并明确调用。

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
