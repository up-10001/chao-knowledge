# 验证范围 · v0.3.2

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
