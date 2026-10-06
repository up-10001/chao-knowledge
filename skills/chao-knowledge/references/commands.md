# 命令参考

所有命令在本地执行，输出 JSON。退出码 0 成功、2 失败；失败时不得声称完成。
要求 Python 3.9+。macOS 常用 `python3`；Windows 检测 `py -3` 或 `python`。
以下 `SCRIPT` 和 `ROOT` 都必须替换为实际绝对路径。普通用户用自然语言，Agent 负责选择命令，不要求小白自己填 ID。

## 初始化与个人档案

```text
PYTHON SCRIPT --root ROOT init
PYTHON SCRIPT --root ROOT profile --field 身份 --value "做办公效率内容" --quote "我是做办公效率内容的"
PYTHON SCRIPT --root ROOT profile --field 受众 --value "AI小白" --quote "我的内容主要给AI小白看"
```

其他档案字段：称呼、当前目标、表达风格、真实经历、不能替我说的话。`profile` 会更新一个字段，其余字段保留。只接收当前用户明确自述；保存前确认推断未被写成事实。

## 导入与提取

```text
PYTHON SCRIPT --root ROOT ingest --file "00-待整理/资料.md" --title "我的选题笔记" --provenance user_original --tag 口播
PYTHON SCRIPT --root ROOT ingest --url "https://example.com/article" --title "待阅读文章"
PYTHON SCRIPT --root ROOT extract --id m-真实ID --file "00-待整理/正文.txt" --method "宿主实际读取网页正文" --complete
```

`extract` 需要宿主先真正取得正文。本脚本不会下载 URL。省略 `--complete` 表示提取可能不完整。所有提取结果仍待人工核对。

显式提供的工作区外附件可以追加 `--allow-external`；不得用它扩大扫描范围。
单文件原件最多 32 MiB；自动读取文本最多 2 MiB，仅 UTF-8。大视频请保留在自己的存储中，并导入较小逐字稿；不能承诺已下载原视频。

## 检索与跨对话上下文

```text
PYTHON SCRIPT --root ROOT search --query "知识库 口播" --limit 5
PYTHON SCRIPT --root ROOT context --task "写一条给AI小白的知识库口播" --scope task=口播 --scope audience=AI小白 --scope platform=抖音
```

检索返回原文件路径、行号和摘录，不代表读过全部内容。每次最多遍历前 1000 条材料、读取正文总预算 20 MiB，每个匹配摘录最多 1200 字符；命令会报告跳过或预算限制。规则与个人档案也有显式预算与遗漏计数。容量大时先按项目拆分，不夸大成大规模语义检索。

## 规则：先提议，再确认

```text
PYTHON SCRIPT --root ROOT remember --key 表达难度 --text "少用术语，必要术语配一个生活例子" --scope task=口播 --scope audience=AI小白
PYTHON SCRIPT --root ROOT confirm --id r-真实ID --quote "确认，只用于给AI小白看的口播"
PYTHON SCRIPT --root ROOT rules
PYTHON SCRIPT --root ROOT revoke --id r-真实ID --quote "撤销这条要求"
PYTHON SCRIPT --root ROOT forget --id r-真实ID --quote "从规则库删除这条记录"
```

`remember --expires YYYY-MM-DD` 可设置到期日（UTC 日历日结束后不再调用）。全局规则不传 `--scope`；每个 scope 只能出现一次。
相同主题、相同范围存在活跃规则时必须确认替换，再给 `confirm` 加 `--replaces r-旧ID`。不会通过纠正次数自动确认。`revoke` 保留历史，`forget` 移除当前规则内容；二者都不会擦除聊天、备份或旧作品。

## 草稿、版本和验收

```text
PYTHON SCRIPT --root ROOT save --title "知识库入门口播" --file "00-待整理/初稿.md" --source m-真实ID --unverified "用户经历和工具功能需核对"
PYTHON SCRIPT --root ROOT save --title "知识库入门口播二稿" --file "00-待整理/二稿.md" --parent o-上一版ID --source m-真实ID
PYTHON SCRIPT --root ROOT approve --id o-真实ID --quote "我已核对来源、个人经历和表达，同意作为定稿"
```

`--source` 可多次指定。仅存链接、待提取资料、正文被篡改的资料不能被登记为已读依据。
`save` 创建 Markdown 与 `.sources.json` 来源卡，状态永远先是 draft。脚本不做语义事实核验；Agent 须在正文之外注明支撑关键主张的原文位置。草稿被直接修改后，必须保存新版本才能验收。approved 不等于已发布。

## 数据回流与自查

```text
PYTHON SCRIPT --root ROOT feedback --id o-真实ID --file "00-待整理/数据.json"
PYTHON SCRIPT --root ROOT health
```

数据按 `assets/feedback-template.json` 提供，填写真实窗口和带时区的观察时间；未知计数为 null，非负整数有效。没有播放量或播放量为零时，互动率保持 null，不自动推断成绩。每次反馈是独立快照，不覆盖历史；复盘不会改变长期规则。

文件锁 `.chao/LOCK` 防止脚本并发改写，原子替换避免状态文件写到一半。异常退出可能留锁：先确认没有正在执行的任务再人工清理锁目录，不提供强制并发选项。外部编辑器不受此锁约束，因此用 health 检查文件变化。
