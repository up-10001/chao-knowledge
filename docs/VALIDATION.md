# 验证范围 · v0.3.4 开发候选（未发布）

2026-10-08 按用户要求只做后台源码审计与离线回归，没有操作正在录屏的 WorkBuddy 客户端、已安装 Skill 或演示工作区。详见 [源码与小白体验审计](AUDIT-2026-10-08.md)。

| 候选验收 | 状态与证据范围 |
|---|---|
| macOS / Python 3.9.6 本地完整回归 | PASS，162 项（含新增 9 项）；仅脚本证据 |
| 三个合成旅程：新用户、已有单份资料、v0.1.1 历史升级 | PASS；独立脚本进程，不是 GUI |
| 正式 v0.3.3 测试库入口与索引升级 | PASS；档案等事实保留，旧入口精确备份更新，手改入口保留 |
| 确定性 ZIP、manifest、SHA256 与源码匹配 | 本地打包及包完整性回归 PASS；不是正式发行 |
| 候选 Windows / Ubuntu / macOS GitHub CI | NOT_RUN；候选未推送 |
| WorkBuddy 三轮零缓存、旧版更新、direct 5xx fallback | DEFERRED；用户要求本轮不要操作客户端 |
| 发布到 main / tag / Release | NOT_PUBLISHED；官方仍为 v0.3.3 |

正式 v0.3.3 的提交 `7c71908d7cd7589e158883a23548393fc69f3883` 已有 [三平台 CI 成功记录](https://github.com/up-10001/chao-knowledge/actions/runs/37637517181)，不可用作本候选 CI 或客户端证据。

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
