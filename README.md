# Chao Knowledge · 个人 AI 知识库

**让 AI 用你的资料做事，而不是每次都重新认识你。**

面向 AI 小白，WorkBuddy 桌面本地工作区优先。先完成一份真实草稿，再逐步积累资料和经过确认的要求。

**版本：v0.1.0 · MIT 开源 · Python 3.9+ · 无第三方 Python 依赖**

> 脚本负责文件、状态和校验，宿主 AI 负责理解与写作。不是自动训练模型，也不承诺内容表现或收益。WorkBuddy 实际自动发现、模型执行与跨对话效果须在你的客户端验证，不能用脚本测试替代。

## 它能帮你做什么

| 你说的话 | Skill 做的事 |
|---|---|
| 带我搭知识库，完成第一次使用 | 少量必要信息 → 导入一份资料 → 产出并核对第一份草稿 |
| 把这份资料放进来 | 保留原件和来源、去重、说明实际读取状态 |
| 用我的资料写一条口播 | 调用个人背景、适用要求和相关摘录，保留来源卡，不乱套用他人经历 |
| 这条要求以后只用于小白口播 | 提议带范围的规则，用户确认后生效，可撤销或移除 |
| 换个对话继续用 | 在同一工作区重新读取档案与规则；不依赖上一段聊天 |
| 把发布数据放回来复盘 | 记录实际窗口与计数，计算有分母的互动率，不把相关性当因果 |

## 给小白：复制这段到 WorkBuddy

先建一个独立文件夹，例如“我的 AI 知识库”，在 **WorkBuddy 桌面端**选中它作为本地工作区。不要选整个桌面或用户主目录。

```text
请从这个公开仓库安装 chao-knowledge 的 v0.1.0 版本：
https://github.com/up-10001/chao-knowledge

先读取 README 和安装脚本，检查必要权限与 Python 3.9+，不要关闭安全设置或安装付费服务。
只把 skills/chao-knowledge 安装到我选中工作区的 .codebuddy/skills/chao-knowledge；保留已有文件，冲突时停止覆盖。
按仓库 tools/install.py 的方法安装并初始化。下载和解压放临时目录，不要把源码仓库当作我的私人知识库。
完成后明确调用 chao-knowledge，带我做第一个真实任务。已有信息不要重复问；只补齐我在做什么、给谁看、今天想做什么，然后让我提供一份资料。
不要把演示人物或外部作者的经历写成我的经历。依赖或权限不满足时如实说明，不假装安装成功。
```

安装完建议新建对话、保持同一工作区，说：**“调用 chao-knowledge，带我完成第一次使用。”**

## 技能包与可复现安装

[下载 v0.1.0 技能包](https://github.com/up-10001/chao-knowledge/raw/refs/heads/main/dist/chao-knowledge-v0.1.0.zip) · [安装与故障处理](docs/INSTALL.md) · [录屏演示流程](docs/DEMO.md) · [测试边界](docs/TESTING.md)

WorkBuddy 官方支持导入本地技能包，也支持项目目录 `.codebuddy/skills/`。ZIP 导入后的实际识别需要客户端实测；需要可复现的文件安装时，用下述项目目录方式。

从本仓库下载并解压后，让 AI 执行（路径换成实际位置）：

```bash
python3 tools/install.py --workspace "/你的路径/我的 AI 知识库" --init
```

Windows 可按环境使用 `py -3 tools/install.py --workspace "D:\我的AI知识库" --init`。
安装器校验本地文件清单，不联网，不执行 pip；已有不同版本不覆盖。清单是完整性校验，不是签名或来源可信证明。

## 文件在哪里

```text
我的 AI 知识库/
├── AGENTS.md                 # 简短入口；保留已有内容
├── 开始使用.md               # 小白使用提示
├── 00-待整理/                # 用户提供的原始资料、临时稿
├── 01-资料/                  # 保留原件、可读文本、来源登记
├── 02-作品/                  # 草稿、版本、来源与验收卡
├── 03-复盘/                  # 每次数据快照
├── .chao/state.json          # 私人档案、规则、资料和作品登记
└── .codebuddy/skills/chao-knowledge/
```

不用手填这些文件。对 AI 说你要做什么即可。技能源码可以公开，**使用者的个人知识库不要一起上传**；初始化器会补充 `.gitignore`，但它不是数据泄露的绝对保障。

## 能力边界和费用

本包不要求新增付费 API。WorkBuddy/模型本身的额度或订阅费用以对应服务为准。

TXT、MD、CSV、JSON、SRT、VTT 可自动读取 UTF-8 文本；其他受支持的文档与媒体只先归档，正文提取依赖宿主已有能力。视频链接只存链接，不等于下载和转写。本包没有视频抓取器、自动发布器、收益计算器或后台定时任务。

单原件上限 32 MiB，自动文本上限 2 MiB；关键词检索有明确预算，不宣称向量/语义检索或企业级海量检索。转写、事实、权限和产出质量仍需人工核对。

本地脚本不主动联网或上传；但云端 AI 读取资料时可能发送给模型服务商。密钥模式检查并非全面隐私扫描；不得保存口令、客户秘密或未经授权的数据。

## 开发与测试

```bash
python3 tools/package.py
python3 -m unittest discover -s tests -v
```

测试包含初始化保护、去重、链接状态、来源登记、中文检索、规则确认/作用域/撤销、草稿版本、反馈分母、安装完整性与文件路径安全。**这些测试不验证模型会不会照做、不测真实 WorkBuddy GUI，也不认证作品质量。**详见 [TESTING](docs/TESTING.md)。

## 来源说明

本项目受“用个人资料让 Agent 更好地工作”的公开实践启发，包括 [shengjiang-knowledge](https://github.com/aslanyushengjiang-coder/shengjiang-skills) 的小白入门场景。本仓库的程序、测试、模板与指令为本项目重新编写，未直接复制上述项目代码，也不主张发明知识库、来源追踪或外部记忆等通用思想。参见 [设计与来源](docs/PROVENANCE.md)。

技术格式参考 [Agent Skills 规范](https://agentskills.io/specification)、[WorkBuddy 项目配置](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project) 与 [WorkBuddy 技能说明](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。

## 许可

[MIT](LICENSE)。允许按许可证使用、修改和再分发，请保留版权与许可声明。不隶属于、也未获腾讯 WorkBuddy 官方认证或背书。
