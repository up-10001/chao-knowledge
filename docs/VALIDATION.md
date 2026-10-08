# 验证范围 · v0.4.0 开发候选（未发布）

2026-10-08 前半轮按用户要求只做后台源码审计与离线回归；随后用户授权 WorkBuddy 验收，本轮客户端证据见下方。录屏知识库与素材保留。详见 [源码与小白体验审计](AUDIT-2026-10-08.md)。

| 候选验收 | 状态与证据范围 |
|---|---|
| macOS / Python 3.9.6 本地完整回归 | PASS，193 项（含采集回归 30 项）；仅脚本证据 |
| 三个合成旅程：新用户、已有单份资料、v0.1.1 历史升级 | PASS；独立脚本进程，不是 GUI |
| 正式 v0.3.3 测试库入口与索引升级 | PASS；档案等事实保留，旧入口精确备份更新，手改入口保留 |
| 确定性 ZIP、manifest、SHA256 与源码匹配 | 本地打包及包完整性回归 PASS；不是正式发行 |
| 候选 Windows / Ubuntu / macOS GitHub CI | de4b6eb 的三平台各 193 项 + 三套合成旅程 PASS；见 [CI](https://github.com/up-10001/chao-knowledge/actions/runs/37700662048)。文档修正版以其提交 checks 为准 |
| WorkBuddy 5.7.6 / macOS 用户级更新、加载与连续业务 | PASS，独立工作区，默认权限；见本轮客户端记录 |
| WorkBuddy 三轮零缓存、direct 5xx fallback | NOT_RUN；本轮候选本地 ZIP 更新不能替代 GitHub 正式版本的三轮验收 |
| 发布到 main / tag / Release | NOT_PUBLISHED；官方仍为 v0.3.3 |

## TikHub 采集候选

- 9 个抖音/小红书标准适配器：端点/参数与官方 SDK 固定 OpenAPI 快照核对；所有请求、分页、超时、错误及返回字段测试使用合成响应。
- 通用读取接口目录：从官方快照提取 777 个 GET/POST 读取端点的参数元数据。目录覆盖不等于 777 个接口实测，也不等于全平台字段或分页均已自动映射。
- 已验证：计划去重、预算与请求上限、先采样后批量、计划/契约变化拒绝、并发锁、失败计数、结果不明不自动重发、响应落盘后的恢复、响应被手改时拒绝信任、分页去重与循环停止。
- 已验证：Key 配置不联网、已知凭据和查询签名脱敏、正确 GET/POST 请求形态、禁止凭据重定向、错误不回显 Key、CSV 公式防护、报告手改保护、禁止发行包携带常见 Key 文件。
- 已验证：缺少真实字幕时不把视频简介入为正文；类型不明笔记保持链接；字幕保留 external 和未核对提取状态；重复归档不重复生成资料。
- 真实 TikHub Key/付费接口：NOT_RUN。本轮未读取真实用户 Key、未发起付费采集请求。官方公开 OpenAPI 直连返回 403，随后从官方 GitHub 固定提交取得同版本快照；没有绕过登录或验证码。
- 通用 skill-creator 校验器：原版与候选都因既有 WorkBuddy frontmatter 扩展字段（version、author 等）被拒绝。保留原客户端使用的字段，不把该校验记为 PASS；基础字段与包内链接另由现有项目测试核验。
- 候选 CI 使用真实 Skills CLI 安装当前 checkout，并明确不是远端 GitHub main/WorkBuddy 证据；main 另保留远端 CLI 校验，避免用旧版 main 冒充新代码通过。
- WorkBuddy 客户端采集：离线 routes / check-config / plan / 缺价 run 拒绝 PASS；真实请求、样本语义、分页与账单 NOT_RUN。源码/模拟通过不能替代真实服务可用性、样本语义核对或账单验证。
- 当前未实现媒体文件下载、第三方 ASR 和自动发布；没有将这些能力标成完成。

正式 v0.3.3 的提交 `7c71908d7cd7589e158883a23548393fc69f3883` 已有 [三平台 CI 成功记录](https://github.com/up-10001/chao-knowledge/actions/runs/37637517181)，不可用作本候选 CI 或客户端证据。

## 2026-10-08 WorkBuddy 5.7.6 / macOS 实际客户端记录

通过原生客户端输入指令执行，模型 Hy4 preview，默认权限；未修改登录、模型、权限设置、其他 Skills 或桌面录屏知识库。使用独立 `client-acceptance/v040-20261008/我的知识库`，所有新增档案、资料与作品为明确授权的合成验收数据，不是用户真实业务数据。

- 包安装：WorkBuddy 安全审计 P2 后安装候选本地 ZIP，15 个内容文件 SHA256 匹配。此链路不是“只给 GitHub 地址安装正式最新版”，官方 Release 仍为 v0.3.3。
- 同名发现问题：项目 `.workbuddy/skills/chao-knowledge` 的 v0.4.0 落位后，当前对话及同工作区新对话的 Skill 工具均加载用户级 v0.3.3。没有把读项目文件或调用旧脚本算成新版加载；没有使用旧版初始化。本次不能据此确认该项目级路径优先级或普遍支持情况。
- 安全更新：WorkBuddy 将用户级 v0.3.3 完整备份并移动保留到验收目录外层，旧包 11 个内容文件哈希通过。候选安装到 `~/.workbuddy/skills/chao-knowledge`；新建对话实际 Skill 工具加载 v0.4.0，15 个内容文件核验通过。
- 连续业务：init → profile（3 次独立调用）→ ingest → context → remember → confirm → save → health --save → search 全部实际执行成功。最终档案 3 项、资料 1 份、作品 1 份、有效长期要求 1 条。外部作者归属保留，作品关联资料，规则范围只含用户授权的任务和受众。
- 锁：整个连续业务未出现锁释放删除授权或残留目录锁。`.chao/LOCK` 为持久普通文件；后续命令正常获得锁。额外只读核验后的非阻塞 OS 加锁也成功，未手动清锁。`pending-write.json` 为 idle / files=[]，客户端 recover 返回 nothing_to_recover。
- 投影：地图与完整资料/作品索引均实际打开；统计与 state 一致。health --save 后地图内显示严重 0 / 需核对 0 / 提示 1。提示为合成测试未填写本周重点，不是完整性错误。
- 采集离线保护：routes 显示 9 个标准适配器；check-config 如实返回未配置 Key（退出码 2）。建立抖音短链、未知单价、预算 0、请求上限 1 的离线计划。run 返回“尚无已核对单价；先查价并重新生成费用计划”（退出码 2），状态中 attempts=0、unit_price_usd=null、无响应导出。未发起 quote 或实际采集请求。
- 文档修正：客户端发现命令参考标题滞留 v0.3.1，现去除标题版本以避免误认；安装说明补充新对话复核及旧版遮蔽不能算成功。Python 脚本未变。本地重打包后 193 项回归通过，最终包安装完整性另行核对。

主业务验收包 SHA256：`b69e49c3be93e602b2a0d9bc668dfa66c108b81f89cb1fc42cd8cda8260ca864`。文档修正版 SHA256：`93deab3ca64b91082690e32b8e5bc10902156dce71d374c4137daf93d5655da7`。不能将前者的 UI 旅程冒称为后者重新执行了全套旅程；后者只修改两份文档及其打包元数据。

剩余：用户尚未配置 Key 或授权真实服务请求的次数与费用上限，因此真实 TikHub 采集仍为 NOT_RUN；GitHub 正式最新版零状态三轮及 direct 5xx fallback 同样没有在本轮执行。候选提交与正式发布分别记录。

## v0.3.3 原客户端计划（保留历史记录）

下列 PENDING 是当时的记录，后续按精确版本和实际证据补齐；不因录屏素材或本轮离线测试自动改为 PASS。

本轮只优化公开安装入口、scope/fallback 和缓存/版本核验，增加用户授权的导航投影优化与 health --save 后的状态摘要，state 结构和档案/资料/规则/作品/反馈/锁/迁移行为保留。v0.3.1 的锁与客户端连续业务证据见 [历史记录](VALIDATION-v0.3.1.md)。

当前状态：PENDING。不得据此声称“一句话安装”三轮验收通过。

| 验收 | 状态 |
|---|---|
| 最新标准 Skills CLI，远端仓库唯一 Skill 与完整包 | 安装入口提交 01f7c967 已在 Ubuntu CI 真实运行 PASS；最终包待复核 |
| WorkBuddy 5.7.6 / macOS：零缓存 ROUND_1 / ROUND_2 / ROUND_3 | PENDING |
| direct GitHub 5xx 后正常 fallback | PENDING |
| 已有旧版本的同一句话安全更新 | PENDING |
| 版本/SHA256/宿主发现/实际调用，旧缓存无错误复用 | PENDING |
| 原有完整测试、三套脚本流程、Windows/macOS/Ubuntu CI | PENDING |

三轮每次从新的空白工作区及无用户级/项目级 chao-knowledge 开始，只发送用户原始一句话；不补 npx、ZIP、版本号或安装路径，不预装。保留登录、其他 Skills、模型与系统配置，新测试对话使用默认权限。记录各轮第一请求、5xx、实际下载来源、路径/版本、发现/调用、缓存核对。合成/脚本结果不能替代实际客户端。

地图回归：空库、档案统计与隐私、资料/作品/版本、项目、规则/经验/反馈计数、只读 health、保存检查摘要、手改保护和健康记录恢复。health --save 只在地图未手改且存在时同步投影/其哈希元数据；不修复缺失地图或其他视图。普通 health 仍只读。

预验收记录：v0.3.2 在 WorkBuddy 5.7.6 默认权限、无旧安装的全空工作区，以原始一句话完成 FRESH_INSTALL、正式 Release ZIP/SHA256/manifest 核验、Skill 工具真实加载及脚本 init/context。网页内容曾返回旧 README 版本，客户端核对正式 Release 后没有安装旧版。最终三轮会另按 v0.3.3 记录，不把此预验收算作最终三轮。
