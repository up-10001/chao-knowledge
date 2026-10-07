# 安装与更新入口

仅用于当前用户明确要求安装/更新；普通知识库任务不自动联网或升级。
仓库：`up-10001/chao-knowledge`；唯一 Skill：`chao-knowledge`。

1. 核实最新**正式** Release（排除 draft/prerelease）及其 tag、ZIP、SHA256SUMS。检查当前工作区和已安装用户级/项目级的实际路径、SKILL.md version、manifest version、文件完整性。目录存在或一次 HTTP 5xx 都不是成功/失败结论。
2. 正常安全审计后优先标准 Skills CLI：

   ```bash
   npx -y skills@latest add up-10001/chao-knowledge --skill chao-knowledge -y
   ```

   先检查当前 CLI 的 `--help`、支持的 agent 与 WorkBuddy 发现路径，再补 scope；不要猜 `--agent workbuddy`。WorkBuddy 本地项目确认支持 `.codebuddy/skills` 时，可在选中工作区执行同一命令加 `--agent codebuddy --copy`。`--copy` 保留独立完整包，避免链接影响发现/完整性检查。CodeBuddy CLI 的 `-g` 目标不等于 WorkBuddy 的用户目录；需要用户级时按 WorkBuddy 实际支持的导入方式落位，不给其他宿主顺带安装。`-y` 只处理 CLI 自身选项，不跳过宿主安全确认。
3. 页面/API/direct fetch 遇到 502、503、timeout 或抓取失败：尝试仍可用的官方 raw/API 读取本说明，继续 CLI；不能改用本地旧副本声称新安装。CLI 因 Node/npx/git/网络/路径兼容不可用时，转正式 Release ZIP（`chao-knowledge-v<tag版本>.zip`），按 WorkBuddy 支持的 Skill 导入安装。只用 GitHub 官方发布渠道，不用未知镜像。若 main 与正式 tag 不同，CLI 改用同仓库 tag 的 tree URL，或用正式 ZIP，不把开发版当正式版。两条正常路径都失败才 INSTALL_FAILED，给出各自真实原因。
4. 已有最新版须与官方同版 manifest/文件对照后才 ALREADY_INSTALLED。旧版或不完整副本先说明，再将未手改的完整旧包**备份改名保留**后安装；不触发 CLI 覆盖旧目录的删除。自定义/未知文件停止覆盖。失败保留现场与旧包，不擦除知识库。用户级与项目级重名遮蔽必须指出，并核实实际加载路径。
5. 安装后读取实际安装的 SKILL.md 和 manifest，核对版本、全部 references/scripts/assets 与正式包。确认 WorkBuddy 发现/启用（技能面板、当前工作区可用技能或实际 Skill 调用），**实际调用一次 chao-knowledge**；可运行安装脚本的 `--help` 验证入口，必要时在空测试工作区 init/context，不能仅“读了文件”就宣称宿主识别。没有填写档案/导入资料授权时不替用户造数据。
6. 只在版本、完整性、宿主发现和调用均通过后报告：`FRESH_INSTALL` / `UPDATED` / `ALREADY_INSTALLED`，附实际路径与版本；否则 `INSTALL_FAILED`，明确哪一项未过。无法联网核验最新版时保留旧副本并说明未验证，不能冒充成功。

不关闭安全设置，不 sudo、不绕过权限、不自动批准危险授权。没有可用正常渠道时如实失败；用户只需给名称 + GitHub 地址，不应被要求复制更长提示词或自己开 Terminal。
