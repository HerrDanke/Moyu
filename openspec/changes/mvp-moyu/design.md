# Design: 墨鱼 Moyu — 技术方案

## 技术栈
- **后端**：Python 3.11 + FastAPI + SQLAlchemy + SQLite + uvicorn
- **前端**：React 18 + Vite + TypeScript + 原生 fetch/SSE（不引入重量级状态库，用 hooks）
- **流式**：SSE（`text/event-stream`），`POST /api/chat` + 前端 `fetch` 读 `ReadableStream`（因为指令在请求体、`EventSource` 仅支持 GET，故不用 EventSource）
- **解析**：TXT 章节切分（正则识别「第 X 章/回/节/卷」标题），无分隔时按 3000 字/章兜底；编码自动探测（`charset-normalizer`）
- **鉴权**：内置简单访问密码（环境变量 `ACCESS_PASSWORD` + Cookie Session）
- **部署**：单容器（后端托管前端构建产物，非 root 运行）+ Docker Compose + 两个 volume（`/data` SQLite、`/novels` 原文备份）
- **测试**：pytest（后端）、vitest（前端）、Playwright（E2E 冒烟）

## 架构
```
Docker 单容器（非 root 用户）
├── FastAPI（托管 /api/* 路由 + 前端静态产物）
│   ├── readers/       TXT 解析（BaseReader 接口预留 EPUB）
│   ├── router/        auth / books / progress / chat / search
│   ├── services/
│   │   ├── chat_engine.py     指令解析 + 伪 AI 文案组装
│   │   └── typing_stream.py   分段推送 + 节流（流式期间零 DB 访问）
│   └── security.py    访问密码校验 + Session
└── SQLite 单文件（WAL 模式）— books/chapters/progress/settings
```

**静态托管顺序（关键）**：先注册所有 `/api/*` 路由，最后 `app.mount("/", StaticFiles(html=True))`；SPA 深层路由刷新用 catch-all 返回 `index.html`（避免刷新 404）。静态目录与 `DATA_DIR`/`NOVEL_DIR` 分离，避免 volume 覆盖。

## SQLite 并发与流式模型（评审 blocker）
- 连接参数：`PRAGMA journal_mode=WAL`、`PRAGMA busy_timeout=5000`、`check_same_thread=False`、`PRAGMA foreign_keys=ON`（级联删除依赖）。
- **SSE 流式期间零 DB 访问**：流式开始前一次性把整章 `content` 读入内存，推送阶段只做内存分批 + `asyncio.sleep`，不查库、不持有连接。
- **进度写入放流式结束**：章节正文推完后才推进 `progress`（避免断线时进度错位）；写入用条件更新 `WHERE chapter_index = 旧值` 做乐观锁，防多 tab 竞态。
- 单进程 uvicorn 即可；若未来多 worker 再评估。

## 数据模型
- `books(id, title, source_filename, total_chapters, created_at)`
- `chapters(id, book_id, index_no, title, content, char_count)`，`(book_id, index_no)` 唯一
- `progress(book_id PK, chapter_index, chapter_offset, updated_at)` — `chapter_offset` 为章节内「断句续读」字符偏移
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

**正则安全**：所有指令正则保持线性（禁止嵌套重复量词），输入先截断到 500 字符，避免 ReDoS。

## 「伪 AI」三段式流式流程
1. **思考光标**：正文前停顿 1~2s，闪烁光标
2. **流式正文**：按句分批 SSE 推送，间隔 600ms~1.4s，前端逐字打字机渲染
3. **收尾**：结尾引导语「第 N 章完 · 回复『下一章』继续阅读」

### 真实感关键点
- 思考光标闪烁
- 异步节流（非一次性吐全章）
- SSE 期间输入框显示「AI 正在生成…」并禁止发送
- **快速阅读开关**：显式开关（替代原「跳过生成」），开启时流式只演开头三段、正文一次性入 DOM；关闭时全程流式。默认开启流式。
- 客户端「跳过」需 `AbortController` 中断 fetch，避免服务端继续推送。

### 阅读体验（MVP 纳入）
- **断句续读**：按句分段时记录 `chapter_offset`，重开从断点继续
- **进度百分比**：顶部显示「《书名》第 N 章 · 已完成 62%」

## API
```
POST   /api/auth/login          校验访问密码 → 下发 Session Cookie
POST   /api/auth/logout         登出
POST   /api/books/import        上传 TXT → 解析 → 落库
GET    /api/books               书单
GET    /api/books/{id}          详情
GET    /api/books/{id}/chapters 章节目录
DELETE /api/books/{id}          删除书
GET    /api/progress/{book_id}  进度（含 chapter_offset）
POST   /api/chat                SSE 对话流
GET    /api/search?q=&book_id=  搜索
```
- 除 `/api/auth/login` 与静态资源外，所有 `/api/*` 需有效 Session。

## 导入安全与健壮性（评审 blocker）
- **上传限制**：`Content-Length` 上限（默认 100MB），超限拒绝。
- **文件名 sanitize**：仅取 `Path(filename).name`；正文备份以服务端生成的 UUID/书 id 命名。
- **路径安全**：写盘路径 `.resolve()` 后校验仍在 `NOVEL_DIR` 内。
- **编码探测**：用 `charset-normalizer` 探测 UTF-8/GBK/GB18030，探测失败或解码失败给出明确报错。
- **事务原子性**：解析 + `books` + `chapters` 批量写入同一事务；失败整批回滚，并清理已写的 `/novels` 备份，避免孤儿。
- **单章上限**：单章正文超上限（如 10 万字）时按更大 chunk 再拆，避免一次流式过久。

## 错误处理
- 章末越界 → 伪 AI 提示「已经是最新章节了」
- 无书/进度空 → 引导「想读哪本书？回复『书单』」
- 跳章越界 → 提示「本书共 N 章，输入 1~N」
- 无分隔 TXT → 按字数兜底切分并提示
- 未登录 → 前端跳转登录页
- SSE 中断 → 前端清掉半章渲染并提示重试；进度未推进
- 连续指令 → 串行排队防重复

## 配置（环境变量）
`PORT`、`DATA_DIR`、`NOVEL_DIR`、`TYPING_SPEED`、`ACCESS_PASSWORD`（主题偏好由前端 localStorage 管理）

## 部署安全（评审建议）
- Dockerfile：非 root `USER`、`COPY --chown`、pin `python:3.11-slim` 精确 tag、锁依赖版本。
- docker-compose：默认绑 `127.0.0.1:$PORT`（安全默认）；提供 `public` profile 绑 `0.0.0.0` 并在 README 提示反代加鉴权；仅 `/data`、`/novels` 卷可写。

## 前端组件
`MessageList` / `ChatInput` / `BookSelector` / `ThemeToggle` / `ImportUpload` / `LoginPage` / `QuickReadToggle` / `ChapterProgress` + `useTypingEffect` hook

## 测试矩阵
- **txt_reader**：章节切分边界（标题识别、无分隔兜底、章节数统计、GBK/GB18030 编码、超大单章拆分）
- **chat_engine**：指令解析全覆盖（正常/越界/歧义/空命令/超长输入）
- **api**：导入→列书→读章→进度闭环；导入失败回滚断言（无孤儿 books/chapters + `/novels` 清理）；搜索无命中返回空
- **db 并发**：WAL 下多线程并发读 + 写进度不报 `database is locked`
- **sse**：报文格式（`Content-Type: text/event-stream`、`data:` 行、结束符）；断流后前端恢复
- **progress**：续读 `chapter_offset` 读写；乐观锁防竞态
- **auth**：未登录访问被拒、密码正确/错误
- **useTypingEffect**：节流、状态机
- **Playwright**：登录 → 传示例 TXT → 发「下一章」→ 断言正文出现