# pseudo-ai-chat Specification

## Purpose
TBD - created by archiving change mvp-moyu. Update Purpose after archive.

## Requirements

### Requirement: 聊天式小说阅读界面
**ID:** pseudo-ai-chat.chat-ui

提供一个外观对齐 ChatGPT 的聊天界面。用户输入指令后，系统以视觉上类似 LLM 的流式效果展示对应小说章节内容，全程不调用任何外部 AI 服务、不需要 API key。消息呈现上，助手正文为无背景的纯文本流，用户指令为浅灰圆角气泡。

#### Scenario: 用户输入「下一章」时流式展示下一章正文
- Given 我已导入《凡人修仙传》并读到第 12 章
- When 我在输入框输入「下一章」并回车
- Then 界面以打字机流式效果展示第 13 章（开场文案 → 正文分批流出 → 收尾引导语）
- Then 期间禁止再次发送

#### Scenario: 生成中指示的位置
- Given 正在流式生成章节
- Then 三点脉冲指示显示在消息流内、助手即将输出的位置
- Then 输入框区域的发送按钮同时变为「停止」，点击即中断本次流式输出

#### Scenario: 助手正文不带气泡
- Given 助手正在输出章节正文
- Then 助手消息不使用背景气泡，以无底色文本直接铺在阅读列上
- Then 用户消息使用浅灰圆角气泡并右对齐

#### Scenario: 聊天界面不暴露本地数据来源
- Given 正在阅读某章节
- When 流式输出正文
- Then 界面文案与外观保持「AI 生成」质感，不出现「来自本地文件/TXT 解析」等字样

#### Scenario: 不出现 ChatGPT 品牌元素
- Given 任意界面状态
- Then 不出现 OpenAI / ChatGPT 的名称、logo 或商标
- Then 品牌仍为本项目自身名称「墨鱼」，且不使用仿冒的图形标识

### Requirement: 指令集
**ID:** pseudo-ai-chat.commands

支持下一章、上一章、续读本章、跳章、书单、切书、搜索、帮助八类显式指令，以及未命中时的兜底指令。「当前书」定义为最近一次被切书指令选定或最后读过章节的那本书，按用户持久化于 `users.current_book_id`。

#### Scenario: 下一章/上一章
- Given 当前书进度在第 5 章
- When 输入「下一章」→ 展示第 6 章并推进进度
- When 输入「上一章」→ 展示第 5 章并推进进度

#### Scenario: 续读本章
- Given 当前书进度为第 5 章、章内偏移 1200
- When 输入「继续本章」（或「续读本章」「接着读」）
- Then 展示第 5 章正文**自偏移 1200 起**的剩余部分，已读部分不重放
- Then 章号不推进（仍是第 5 章），进度偏移保持在断点

#### Scenario: 已读完的章节不重放
- Given 第 5 章已读到末尾（偏移 ≥ 正文长度）
- When 输入「继续本章」
- Then 明确提示本章已读完并引导「下一章」，而不是无声重放整章

#### Scenario: 「继续」与「继续本章」不混淆
- When 输入「继续」或「继续读」
- Then 仍按「下一章」处理（推进到下一章），不得被「续读本章」抢占

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

#### Scenario: 流式期间零数据库访问
- Given 流式推送进行中
- Then 整章正文在推送开始前已读入内存，推送阶段不查库、不持有数据库连接

#### Scenario: 快速阅读开关
- Given 用户开启「快速阅读」
- When 下达阅读指令
- Then 流式只演开头三段，正文一次性渲染进 DOM
- Given 用户开启流式时点击「跳过」
- Then 前端用 AbortController 中断 fetch，服务端停止推送

#### Scenario: 超长输入截断
- Given 用户输入超过 500 字符的畸形文本
- Then 输入被截断，指令解析正则保持线性、不触发灾难性回溯

### Requirement: 伪 AI 文案
**ID:** pseudo-ai-chat.copywriting

所有回复由本地模板生成，可存储于 settings 表供未来定制。

#### Scenario: 开场与收尾模板
- Then 开场为「正在为你加载《{书名}》第 {N} 章…」
- Then 收尾为「第 {N} 章完 · 回复『下一章』继续阅读」

### Requirement: 生成节奏由用户设置驱动
**ID:** pseudo-ai-chat.pacing-setting

流式输出的节奏参数不再固定来自服务端环境变量，而是按**当前用户**的设置取值；环境变量退化为默认值。

#### Scenario: 读取当前用户的速度设置
- Given 用户设置里保存了思考强度对应的速度倍率
- When 该用户发起阅读请求
- Then 本次流式输出使用该倍率决定分批间隔
- Then 不影响其他用户的节奏

#### Scenario: 缺省回落
- Given 用户没有保存过速度设置
- Then 使用环境变量 `TYPING_SPEED` 的值

#### Scenario: 设置不影响进行中的流
- Given 一次流式输出正在进行
- When 用户在设置面板里改动思考强度
- Then 当前这次输出保持原有节奏不变，改动从下一次阅读开始生效

#### Scenario: 不破坏既有「不节流」语义
- Given 服务端默认速度被配置为 0（不节流）
- Then 未设置过的用户仍获得不节流的行为
- Then 用户手动设置的合法值（0.1~10）优先于该默认值
