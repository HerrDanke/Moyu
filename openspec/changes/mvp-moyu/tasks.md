# Tasks: 墨鱼 Moyu MVP

## 阶段 0：项目脚手架
- [ ] 后端：Python 3.11 venv + requirements.txt（fastapi, uvicorn, sqlalchemy, pydantic）
- [ ] 前端：Vite + React + TS 脚手架（npm create vite + 清理）
- [ ] 根目录 docker-compose.yml + 后端/前端 Dockerfile
- [ ] .gitignore（含 .superpowers/、.venv/、node_modules/、dist/）
- [ ] 目录骨架：backend/app/{readers,router,services}、frontend/src/{components,api,hooks}

## 阶段 1：数据层
- [ ] db.py：SQLite 连接 + 建表（books/chapters/progress/settings）
- [ ] models.py：SQLAlchemy 4 模型
- [ ] 迁移/初始化策略（启动时 create_all 足够 v1）

## 阶段 2：TXT 导入
- [ ] base.py：BaseReader 接口
- [ ] txt_reader.py：章节标题正则 + 正文切分 + 无分隔兜底（3000 字）
- [ ] 导入服务：multipart 上传 → 解析 → 批量落库 → 返回结果
- [ ] pytest：章节切分边界测试（标题识别/无分隔/章节数）

## 阶段 3：书籍与进度 API
- [ ] router/books.py：书单/详情/目录/删除（级联）
- [ ] router/progress.py：读写进度
- [ ] router/search.py：LIKE 标题搜索
- [ ] pytest：导入→列书→读章→进度闭环

## 阶段 4：对话引擎与 SSE
- [ ] chat_engine.py：指令解析全覆盖（正则+关键词，8 意图）
- [ ] typing_stream.py：三段式分段推送 + 随机节流（600ms~1.4s）
- [ ] router/chat.py：POST /api/chat → text/event-stream
- [ ] 错误处理：章越界/无书/歧义/空命令/断线重连
- [ ] pytest：指令解析全覆盖（正常/越界/歧义/空命令）

## 阶段 5：前端
- [ ] api/：REST + SSE 客户端（fetch ReadableStream）
- [ ] hooks/useTypingEffect.ts：逐字打字机 + 节流
- [ ] components/：MessageList / ChatInput / BookSelector / ThemeToggle / ImportUpload
- [ ] App.tsx：聊天主界面（布局 A ChatGPT 式 + 主题切换）
- [ ] SSE 期间输入框禁用 +「AI 正在生成…」+ 跳过生成开关
- [ ] vitest：useTypingEffect 节流/状态机

## 阶段 6：部署
- [ ] 后端托管前端 dist 静态产物（同源，免 CORS）
- [ ] docker-compose：/data（SQLite）+ /novels（原文备份）volume
- [ ] 环境变量：PORT/DATA_DIR/NOVEL_DIR/TYPING_SPEED/THEME
- [ ] README：一键部署 + 使用说明 + 示例小说导入
- [ ] Playwright 冒烟：传示例 TXT → 发「下一章」→ 断言正文

## 阶段 7：收尾
- [ ] 全量测试通过（pytest + vitest + Playwright）
- [ ] openspec archive 归档变更
- [ ] 首次 commit + push