# 设计与来源

## 设计依据

本项目围绕一个具体需求编写：面向 AI 小白，在桌面 Agent 的本地工作区完成“个人背景 → 资料 → 第一份草稿 → 明确确认的规则 → 新会话复用 → 结果反馈”。

该场景受到公开的个人知识库实践与 shengjiang-knowledge 入门演示启发。知识库、资料索引、来源追踪、用户档案和外部记忆属于已有广泛实践，本项目不声称发明这些概念，也不对其他作者作原创性或抄袭定性。

## 本仓库新增实现

程序、测试、模板与指令在本项目中重新编写。重点为小白首次任务引导、本地状态与文件校验、资料读取状态区分、带作用域且需确认的规则、可撤销/移除记忆、草稿来源登记、反馈窗口与缺失值处理。

没有直接复制 shengjiang-skills 或 dbskill 的源码；因此没有将其他项目代码改名后重新许可。未来引入第三方代码或素材时，贡献者应记录具体文件、版本和原始许可，并保留相应声明。当前代码和自编示例按 MIT 许可发布。

实现中使用 AI 辅助生成与人工式审查流程，自动化测试不等于零缺陷或业务效果保证。

## 技术参考

- Agent Skills 格式：https://agentskills.io/specification
- WorkBuddy 项目目录：https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project
- WorkBuddy 技能安装与权限：https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market
- 场景启发：https://github.com/aslanyushengjiang-coder/shengjiang-skills

文档核对日期：2026-10-06。平台能力可能更新，以当前官方文档和实际版本为准。
