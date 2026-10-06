# 命令参考

下文 `PYTHON` 为可用的 Python 3.9+ 命令，`SCRIPT` 为 `skills/chao-knowledge/scripts/kb.py` 的绝对路径，`ROOT` 为知识库绝对路径。

## 初始化与个人档案

`PYTHON SCRIPT --root ROOT init`

保存档案字段：

`PYTHON SCRIPT --root ROOT profile --field 身份 --value "AI内容创作者" --quote "我现在主要做AI内容"`

可用字段：称呼、身份、业务、产品、受众、当前目标、表达风格、真实经历、不能替我说的话。

## 导入与提取

把资料放进收件箱后导入：

`PYTHON SCRIPT --root ROOT ingest --file "00-收件箱/资料.md" --title "我的选题笔记" --collection "素材" --provenance user_original --tag 口播`

对标逐字稿：

`PYTHON SCRIPT --root ROOT ingest --file "00-收件箱/transcript.md" --title "对标视频逐字稿" --collection "对标内容" --provenance external --tag 抖音`

URL 只保存链接：

`PYTHON SCRIPT --root ROOT ingest --url "https://example.com/video" --title "待读取链接" --collection "对标内容" --provenance external`

宿主真正读取/转写后，把正文保存为 UTF-8 文件，再执行：

`PYTHON SCRIPT --root ROOT extract --id m-真实ID --file "00-收件箱/正文.txt" --method "宿主实际读取网页正文" --complete`

## 检索与跨对话上下文

`PYTHON SCRIPT --root ROOT search --query "AI知识库 口播" --limit 5`

`PYTHON SCRIPT --root ROOT context --task "写一条AI知识库口播" --scope task=口播 --scope platform=抖音 --scope audience=AI初学者 --limit 4`

## 规则：先提议，再确认

提议：

`PYTHON SCRIPT --root ROOT remember --key "表达难度" --text "句子短一些，少用术语" --scope task=口播 --scope audience=AI初学者`

确认：

`PYTHON SCRIPT --root ROOT confirm --id r-真实ID --quote "确认以后AI初学者口播都按这个要求"`

替换已有同主题同范围规则：

`PYTHON SCRIPT --root ROOT confirm --id r-新规则ID --quote "确认替换旧要求" --replaces r-旧规则ID`

查看、撤销、移除：

`PYTHON SCRIPT --root ROOT rules`
`PYTHON SCRIPT --root ROOT revoke --id r-真实ID --quote "这条以后不要用了"`
`PYTHON SCRIPT --root ROOT forget --id r-真实ID --quote "从当前规则库移除"`

## 草稿、版本和验收

`PYTHON SCRIPT --root ROOT save --title "知识库入门口播" --file "00-收件箱/初稿.md" --stage "草稿" --source m-真实ID --unverified "用户经历和工具功能需核对"`

`PYTHON SCRIPT --root ROOT save --title "知识库入门口播二稿" --file "00-收件箱/二稿.md" --stage "待确认" --parent o-上一版ID --source m-真实ID`

用户明确验收后：

`PYTHON SCRIPT --root ROOT approve --id o-真实ID --quote "我已核对，可以作为完成稿"`

## 数据回流与自查

反馈 JSON 见 `assets/feedback-template.json`：

`PYTHON SCRIPT --root ROOT feedback --id o-真实ID --file "00-收件箱/数据.json"`

默认健康检查只读：

`PYTHON SCRIPT --root ROOT health`

明确需要保存报告时：

`PYTHON SCRIPT --root ROOT health --save`
