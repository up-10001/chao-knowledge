# 验证范围 · v0.3.2

本轮只优化公开安装入口、scope/fallback 和缓存/版本核验，核心代码仅发行 VERSION 标识变化。v0.3.1 的锁与客户端连续业务证据见 [历史记录](VALIDATION-v0.3.1.md)。

当前状态：PENDING。不得据此声称“一句话安装”三轮验收通过。

| 验收 | 状态 |
|---|---|
| 最新标准 Skills CLI，远端仓库唯一 Skill 与完整包 | PENDING |
| WorkBuddy 5.7.6 / macOS：零缓存 ROUND_1 / ROUND_2 / ROUND_3 | PENDING |
| direct GitHub 5xx 后正常 fallback | PENDING |
| 已有旧版本的同一句话安全更新 | PENDING |
| 版本/SHA256/宿主发现/实际调用，旧缓存无错误复用 | PENDING |
| 原有完整测试、三套脚本流程、Windows/macOS/Ubuntu CI | PENDING |

三轮每次从新的空白工作区及无用户级/项目级 chao-knowledge 开始，只发送用户原始一句话；不补 npx、ZIP、版本号或安装路径，不预装。保留登录、其他 Skills、模型与系统配置，新测试对话使用默认权限。记录各轮第一请求、5xx、实际下载来源、路径/版本、发现/调用、缓存核对。合成/脚本结果不能替代实际客户端。
