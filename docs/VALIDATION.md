# v0.1.0 发布验证记录

验证日期：2026-10-06。

| 环境 / 项目 | 实际结果 |
|---|---|
| Linux，Python 3.13.5，本地脚本与安装器 | 73/73 PASS |
| macOS arm64，Python 3.9.6，本地脚本与安装器 | 73/73 PASS |
| 源码传输 SHA-256 | 校验通过 |
| 无第三方 Python 依赖打包 | PASS |
| WorkBuddy 客户端技能发现、真实模型生成与跨对话行为 | NOT_RUN |
| GitHub Actions | 以仓库 Actions 实际记录为准 |

可复现命令：`python3 tools/package.py`，然后 `python3 -m unittest discover -s tests -v`。

上述 PASS 仅指已执行的确定性程序测试。新进程读盘测试不等同于 WorkBuddy 新会话验收；没有验证内容表现、收益、任意平台视频抓取或所有安全风险。人工步骤见 [TESTING.md](TESTING.md)。测试及演示资料为虚构数据。
