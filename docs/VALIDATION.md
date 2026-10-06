# 验证记录

## v0.2.0

- macOS arm64 / Python 3.9.6：87/87 自动化测试通过。
- 本机临时工作区 smoke test：PASS。
  - 工作区级安装与初始化：PASS；
  - v0.2 可见目录与 Markdown 视图：PASS；
  - 身份、受众、当前目标同步：PASS；
  - 对标资料按分类入库：PASS；
  - 分场景规则确认后同步到可读规则文件：PASS；
  - `health --save` 生成 JSON 与 Markdown 报告：PASS；
  - smoke 结束健康状态：healthy，P0/P1/P2 均为 0。
- GitHub Actions Windows / macOS / Linux：发布后验证。
- WorkBuddy GUI 安装：NOT_RUN。
- WorkBuddy 真实模型第一次使用：NOT_RUN。
- WorkBuddy 同一工作区新对话规则复用：NOT_RUN。

脚本测试和本地 smoke test证明文件、状态、安装和命令行为，不等于真实 WorkBuddy 客户端、模型质量或跨会话行为已经验收。
