# pseudo-ai-chat

## MODIFIED Requirements

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