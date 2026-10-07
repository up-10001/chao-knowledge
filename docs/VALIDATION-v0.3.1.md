# 验证范围 · v0.3.1

日期：2026-10-07。本次修复针对 WorkBuddy 5.7.6 / macOS 默认安全删除机制。实际 v0.3.0 的 GitHub 提示词安装成功发现 Skill，但 init 释放 LOCK 目录被拒绝，连续使用失败。不能沿用先前 5.5.3 客户端结果声明 5.7.6 通过。

## 本地与脚本

锁改为持久普通文件上的 OS 排他锁，正常释放只 unlock + close。成功提交后的 undo journal 重置为空闲文件；失败临时文件/目录保留，不自动删除。删除调用逐项说明见 [DELETE_AUDIT](DELETE_AUDIT.md)。

回归包含：init/profile/ingest/context/remember/confirm/save/health 每步结束立即取得锁；两个真实 Python 进程的超时拒绝、等待、退出后取得；os._exit 与进程终止后无永久 stale；安装和连续业务在 unlink/rmdir/rmtree 全部拒绝时成功；实际 v0.3.0 旧目录锁确认后保留改名迁移，不擅自删除；非空旧锁和链接/硬链接拒绝；旧事务恢复记录兼容。

macOS arm64 / Python 3.9.6：143 项测试全部通过。系统 Python 3.9 与 WorkBuddy 自带 Python 3.13.12 重建 ZIP 的 SHA256 相同。既有状态/来源/范围/升级/恢复保护测试保留；脚本测试与三套合成流程不能代替客户端结果。

## 三平台 CI 与发行门槛

Windows / macOS / Ubuntu 分别重建并核对 ZIP/manifest/SHA256，运行完整测试和三套合成流程。固定 LF、ZIP 成员平台/时间/顺序，检出完整历史 Git tags。三平台均成功后提供公开候选用于真实客户端，客户端通过后发布补丁正式版。

源码提交 `ddb9719d7415c4ff4e1926e0d84f2b2bf4309fc1` 的 [CI 37605853012](https://github.com/up-10001/chao-knowledge/actions/runs/37605853012) 三平台全部成功：

| 平台 / Python 3.12 | 完整测试 | 真实进程锁回归 | ZIP/manifest/SHA256 与源码 | 三套合成流程 |
|---|---|---|---|---|
| Windows | 143 PASS，60.127 秒 | PASS（非 mock，不跳过） | PASS | PASS |
| macOS | 143 PASS，9.436 秒 | PASS（非 mock，不跳过） | PASS | PASS |
| Ubuntu | 143 PASS，12.518 秒 | PASS（非 mock，不跳过） | PASS | PASS |

最终发行提交的 CI 另在发行说明链接核对。Skill ZIP SHA256：`6592673ce21f9766ba1035408f0c4b098a4392b98b993728866fae148fca46dd`。

## WorkBuddy 5.7.6 / macOS

2026-10-07，客户端界面版本 5.7.6，默认权限。本次先在 [公开候选 Release v0.3.1-rc.1](https://github.com/up-10001/chao-knowledge/releases/tag/v0.3.1-rc.1) 上验证正式包的相同 Skill 字节（manifest 0.3.1，SHA256 如上）。没有预装/手工下载；源码锁修复来自包自身，没有宿主安全豁免。

| 实际客户端路径 | 结果 |
|---|---|
| 原生技能面板卸载用户级旧 v0.3.0，列表只剩原有三个其他技能 | PASS |
| 保留失败空测试库，重新创建完全空白“我的知识库”，新任务选中 | PASS |
| 仅提供公开 GitHub 提示词，客户端发现候选 Release、下载附件、核验 ZIP/manifest/源码标签和 CI | PASS；附件域名一度超时，客户端正常重试后成功 |
| 安装用户级 0.3.1；安装文件逐个与 manifest/源码一致 | PASS |
| 初始化后立即 profile ×3、ingest 合成 UTF-8 demo 素材、context、remember、confirm、context、health | PASS |
| 三项范围匹配读取 active 规则，换平台排除 | PASS |
| 最终 health / journal | P0/P1/P2=0/0/0；status=idle、files=[] |
| 锁释放删除授权 / 手工清 LOCK / 安全豁免 | 无 / 无 / 无 |
| 下一命令正常取得锁，旧目录锁残留 | PASS / 无 |
| 设置文件与其他技能文件 | 32 个受保护文件 SHA256 不变，登录仍有效；没有修改全局模型/安全设置 |

没有生成或保存草稿；数据全部为合成软件回归设定。普通锁文件 `.chao/LOCK`、`.chao-init.lock` 留在原位是正常行为，不是 stale。判断依据是下一客户端命令实际成功取得 OS 锁。

**WORKBUDDY_5_7_6_REAL_TEST：PASS（发布前候选、正式包相同字节）。** 正式 Release 发布后还会额外从重新卸载/空白工作区复测“不指定候选版本的最新版 GitHub 提示词”；该补充结果记录在发行说明与后续验证记录，不沿用候选的 tag 假称正式 latest。

## 能力边界

没有实际发布到外部平台、抓取抖音、转写真实视频或读取受登录限制网页。合成数据不证明内容质量、业务效果或永久模型记忆。SHA256 校验一致性不是来源认证，锁是本机协作进程锁，不替代备份或抵抗恶意进程。
