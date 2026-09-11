# Design: 墨鱼 Moyu — 技术方案

## 技术栈
- **后端**：Python 3.11 + FastAPI + SQLAlchemy + SQLite + uvicorn
- **前端**：React 18 + Vite + TypeScript + 原生 fetch/SSE（不引入重量级状态库，用 hooks）
- **流式**：SSE（`text/event-stream`），`POST /api/chat` + 前端 `fetch` 读 `ReadableStream`（因为指令在请求体、`EventSource` 仅支持 GET，故不用 EventSource）
- **解析**：TXT 章节切分（正则识别「第 X 章/回/节/卷」标题），无分隔时按 3000 字/章兜底
- **部署**：单容器（后端托管前端构建产物）+ Docker Compose + 两个 volume（`/data` SQLite、`/novels` 原文备份）
- **测试**：pytest（后端）、vitest（前端）、Playwright（E2E 冒烟）

## 架构
```
Docker 单容器
├── FastAPI（托管 /api/* 路由 + 前端静态产物）
│   ├── readers/       TXT 解析（BaseReader 接口预留 EPUB）
│   ├── router/        books / progress / chat / search
│   └── services/
│       ├── chat_engine.py     指令解析 + 伪 AI 文案组装
│       └── typing_stream.py   分段推送 + 节流
└── SQLite 单文件（books/chapters/progress/settings）
```

## 数据模型
- `books(id, title, source_filename, total_chapters, created_at)`
- `chapters(id, book_id, index_no, title, content, char_count)`，`(book_id, index_no)` 唯一
- `progress(book_id PK, chapter_index, updated_at)`
- `settings(key, value)` — 打字速度、AI 文案模板、当前书（主题偏好存前端 localStorage，不落库）

## 对话引擎（指令解析，正则 + 中文关键词）
| 意图 | 触发示例 | 行为 |
|---|---|---|
| next | 下一章/继续/再来 | 当前书下一章 |
| prev | 上一章/返回 | 上一章 |
| goto | 第20章/跳到20 | 跳指定章 |
| list_books | 书单/有哪些书 | 列书单 |
| switch_book | 读《xx》/换书 xx | 切书并读进度章 |
| search | 搜xx/有xx吗 | 返回命中章节列表 |
| help | 帮助/你能干嘛 | 伪 AI 能力介绍 |
| fallback | 其他 | 伪 AI 兜底 + 引导回阅读 |

## 「伪 AI」三段式流式流程
1. **思考光标**：正文前停顿 1~2s，闪烁光标
2. **流式正文**：按句分批 SSE 推送，间隔 600ms~1.4s，前端逐字打字机渲染
3. **收尾**：结尾引导语「第 N 章完 · 回复『下一章』继续阅读」

### 真实感关键点
- 思考光标闪烁
- 异步节流（非一次性吐全章）
- SSE 期间输入框显示「AI 正在生成…」并禁止发送
- 可选「跳过生成」开关（默认开启流式）

## API
```
POST   /api/books/import       上传 TXT → 解析 → 落库
GET    /api/books              书单
GET    /api/books/{id}         详情
GET    /api/books/{id}/chapters 章节目录
DELETE /api/books/{id}         删除书
GET    /api/progress/{book_id} 进度
POST   /api/chat               SSE 对话流
GET    /api/search?q=&book_id= 搜索
```

## 错误处理
- 章末越界 → 伪 AI 提示「已经是最新章节了」
- 无书/进度空 → 引导「想读哪本书？回复『书单』」
- 跳章越界 → 提示「本书共 N 章，输入 1~N」
- 无分隔 TXT → 按字数兜底切分并提示
- SSE 中断 → 前端自动重连回到当前章
- 连续指令 → 串行排队防重复

## 配置（环境变量）
`PORT`、`DATA_DIR`、`NOVEL_DIR`、`TYPING_SPEED`（主题偏好由前端 localStorage 管理）

## 前端组件
`MessageList` / `ChatInput` / `BookSelector` / `ThemeToggle` + `useTypingEffect` hook

## 测试矩阵
- **txt_reader**：章节切分边界（标题识别、无分隔兜底、章节数统计）
- **chat_engine**：指令解析全覆盖（正常/越界/歧义/空命令）
- **api**：导入→列书→读章→进度闭环
- **useTypingEffect**：节流、状态机
- **Playwright**：传示例 TXT → 发「下一章」→ 断言正文出现