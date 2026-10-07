# v0.3.0 删除调用审计与 v0.3.1 处理

审计范围：实际 v0.3.0 tag 的 `skills/chao-knowledge/scripts/kb.py` 与 `tools/install.py`，包括正常路径和失败路径。Python 运行时与安装器不主动删除用户原件。

| 原调用位置（v0.3.0） | 类型与触发 | v0.3.1 |
|---|---|---|
| kb.py:365、655；install.py:143 rmdir | 正常结束释放业务/初始化/安装目录锁；临时实现细节 | 持久普通文件，POSIX flock / Windows msvcrt 排他锁；unlock + close |
| kb.py:212、214 pending.unlink | 正常提交或成功回滚后清理 undo journal；临时实现细节 | 重置持久 journal 为 idle、files=[]，清空个人 before-images |
| kb.py:140 os.unlink(temp) | 原子写入失败清理临时文件 | 保留现场供核对 |
| kb.py:208 path.unlink | 失败事务回滚新建受管理文件 | 校验身份/哈希后改名保留到 .chao/recovery-retained |
| kb.py:257、258、259 unlink/rmtree | 明确 recover 后移除新建受管理文件、恢复记录与旧 journal 目录 | 确认/哈希检查保留；新文件改名归档，journal 清空空闲，旧目录保留 |
| install.py:72、132、137 rmtree | 失败 stage、失败安装目标与剩余 stage 清理 | 失败 stage 保留；失败目标改名保留，恢复原 Skill 备份；成功 stage 已移动成目标 |

正常业务操作没有必须通过以上调用删除原件的路径。forget 仅在用户确认后移除规则的当前逻辑记录，revoke、验收、发布和恢复的确认门槛保留。不会删除宿主聊天、旧作品或备份，也不会放宽 WorkBuddy 的真正删除保护。失败保留文件可能需要用户日后明确整理；不自动清理。

## 旧目录锁升级

检测到 `.chao/LOCK`、`.chao-init-lock`、`.chao-install-lock` 的旧目录锁时停止写入，不能把目录存在自行判断成 stale。用户先停止全部旧版任务，再运行 `migrate-locks` 看计划；明确确认后 `migrate-locks --apply --quote "确认所有旧版任务已停止并保留迁移空目录锁"`。只移动空目录到 `.chao-legacy-locks`，原路径留普通文件，阻止旧版 mkdir 协议继续写入；迁移收据保留在 `.chao-lock-migration.json`。非空目录、链接、未知文件停止。没有 unlink/rmdir、强制删除、安全关闭或环境变量豁免。

持久锁文件存在不表示被占用。并发由 OS 排他锁判断，默认等待 2 秒，`--lock-timeout` 可设 0–60 秒。正常退出、异常退出和进程终止由 OS 自动释放，不需清 LOCK。被杀时的未完成业务写入仍须单独 recover，不因锁已释放而忽略事务问题。

AST 回归拒绝运行脚本/安装器重新引入 unlink、rmdir、rmtree；连续业务测试同时将三种删除 API 设为 PermissionError。测试框架清理自己创建的隔离临时目录不属于业务运行路径。
