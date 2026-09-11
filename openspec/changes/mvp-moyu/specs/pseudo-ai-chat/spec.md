# pseudo-ai-chat

## ADDED Requirements

### Requirement: 聊天式小说阅读界面
**ID:** pseudo-ai-chat.chat-ui

提供一个长得像通用大模型聊天的界面。用户输入指令后，系统以视觉上类似 LLM 的流式效果展示对应小说章节内容，全程不调用任何外部 AI 服务、不需要 API key。

#### Scenario: 用户输入「下一章」时流式展示下一章正文
- Given 我已导入《凡人修仙传》并读到第 12 章
- When 我在输入框输入「下一章」并回车
- Then 界面以打字机流式效果展示第 13 章（开场文案 → 正文分批流出 → 收尾引导语），期间输入框显示「AI 正在生成…」并禁止发送

#### Scenario: 聊天界面不暴露本地数据来源
- Given 正在阅读某章节
- When 流式输出正文
- Then 界面文案与外观保持「AI 生成」质感，不出现「来自本地文件/TXT 解析」等字样

### Requirement: 指令集
**ID:** pseudo-ai-chat.commands

支持下一章、上一章、跳章、书单、切书、搜索、帮助七类显式指令，以及未命中时的兜底指令。「当前书」定义为最近一次被切书指令选定或最后读过章节的那本书，持久化于 settings。

#### Scenario: 下一章/上一章
- Given 当前书进度在第 5 章
- When 输入「下一章」→ 展示第 6 章并推进进度
- When 输入「上一章」→ 展示第 5 章并推进进度

#### Scenario: 跳章
- Given 当前书共 N 章
- When 输入「第 20 章」且 20 ≤ N → 直接展示第 20 章
- When 输入「第 200 章」且 200 > N → 伪 AI 提示「本书共 N 章，输入 1~N」

#### Scenario: 书单与切书
- When 输入「书单」→ 列出所有已导入书籍
- When 输入「读《xx》」且该书存在 → 切换到该书并读取其进度章

#### Scenario: 搜索与帮助
- When 输入「搜 xx」→ 返回该书/当前书中标题命中的章节列表
- When 输入「帮助」→ 伪 AI 介绍可用的阅读指令

#### Scenario: 兜底指令
- When 输入其他任意无命中关键词的句子 → 伪 AI 温柔兜底回复并引导回阅读

### Requirement: 三段式流式渲染
**ID:** pseudo-ai-chat.sse-streaming

章节输出采用 SSE 三段式：思考光标、流式正文、收尾，节奏模拟真实 LLM 生成。

#### Scenario: 三段式节奏
- Given 用户下达阅读指令
- Then 先绘制 1~2s 闪烁思考光标
- Then 正文按句分批推送，间隔 600ms~1.4s
- Then 收尾出现「第 N 章完 · 回复『下一章』继续阅读」

#### Scenario: 支持跳过生成
- Given 正在流式输出长章节
- When 用户点击「跳过生成」
- Then 立即展示该章全文，中断剩余流式过程

### Requirement: 伪 AI 文案
**ID:** pseudo-ai-chat.copywriting

所有回复由本地模板生成，可存储于 settings 表供未来定制。

#### Scenario: 开场与收尾模板
- Then 开场为「正在为你加载《{书名}》第 {N} 章…」
- Then 收尾为「第 {N} 章完 · 回复『下一章』继续阅读」