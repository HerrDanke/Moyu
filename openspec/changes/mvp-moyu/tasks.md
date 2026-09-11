# Tasks: 墨鱼 Moyu MVP

## 阶段 0：项目脚手架
- [ ] 后端：Python 3.11 venv + requirements.txt（fastapi, uvicorn, sqlalchemy, pydantic, charset-normalizer, itsdangerous）
- [ ] 前端：Vite + React + TS 脚手架（npm create vite + 清理）
- [ ] 根目录 docker-compose.yml + 后端/前端 Dockerfile（非 root、pin python:3.11-slim）
- [ ] .gitignore（含 .superpowers/、.venv/、node_modules/、dist/、/data/、/novels/）
- [ ] 目录骨架：backend/app/{readers,router,services}、frontend/src/{components,api,hooks}

## 阶段 1：数据层（含并发配置）
- [ ] db.py：SQLite 连接（WAL + busy_timeout=5000 + check_same_thread=False + foreign_keys=ON）+ 建表
- [ ] models.py：SQLAlchemy 4 模型（books/chapters/progress/settings，progress 含 chapter_offset）
- [ ] pytest：WAL 下多线程并发读 + 写进度不报 `database is locked`

## 阶段 2：TXT 导入（含编码/安全/回滚）
- [ ] base.py：BaseReader 接口
- [ ] txt_reader.py：章节标题正则（线性）+ 正文切分 + 无分隔兜底（3000 字）+ 超大单章再拆
- [ ] 编码探测：charset-normalizer 处理 UTF-8/GBK/GB18030，失败给明确错误
- [ ] 上传安全：Content-Length 上限（100MB）、文件名取基名、写盘路径 resolve 校验
- [ ] 导入服务：multipart → 解析 → books+chapters 同一事务批量落库；失败整批回滚 + 清理 /novels
- [ ] pytest：章节切分边界（标题识别/无分隔/章节数/超大单章）
- [ ] pytest：GBK/GB18030 导入；上传超限/非法文件名被拒；导入失败回滚无孤儿

## 阶段 3：书籍与进度 API
- [ ] router/books.py：书单/详情/目录/删除（级联，foreign_keys=ON）
- [ ] router/progress.py：读写进度（含 chapter_offset）；写入用乐观锁 `WHERE chapter_index=旧值`
- [ ] router/search.py：参数化 LIKE 标题搜索；无命中返回空
- [ ] pytest：导入→列书→读章→进度闭环；搜索注入面与空结果

## 阶段 4：鉴权
- [ ] security.py：访问密码校验（ACCESS_PASSWORD）+ Session Cookie（itsdangerous）
- [ ] router/auth.py：`POST /api/auth/login`、`/api/auth/logout`
- [ ] 全局依赖：除 login 与静态资源外 `/api/*` 校验 Session，未登录 401
- [ ] pytest：未登录被拒；密码正确/错误

## 阶段 5：对话引擎与 SSE
- [ ] chat_engine.py：指令解析全覆盖（线性正则 + 关键词，8 意图）；输入截断 500 字符
- [ ] typing_stream.py：三段式推送 + 随机节流（600ms~1.4s）；推送前一次性取整章入内存，推送阶段零 DB 访问
- [ ] router/chat.py：POST /api/chat → text/event-stream；进度在流结束后写入
- [ ] 错误处理：章越界/无书/歧义/空命令/断线重连（半章清掉）
- [ ] pytest：指令解析全覆盖（正常/越界/歧义/空命令/超长输入）
- [ ] pytest：SSE 报文格式（Content-Type/data 行/结束符）

## 阶段 6：前端
- [ ] api/：REST + SSE 客户端（fetch ReadableStream + AbortController）
- [ ] hooks/useTypingEffect.ts：逐字打字机 + 节流
- [ ] components/：MessageList / ChatInput / BookSelector / ThemeToggle / ImportUpload / LoginPage / QuickReadToggle / ChapterProgress
- [ ] App.tsx：聊天主界面（布局 A ChatGPT 式 + 主题切换）+ 登录页路由
- [ ] SSE 期间输入框禁用 +「AI 正在生成…」；快速阅读开关；断句续读与进度百分比展示
- [ ] SPA 深层路由 history fallback
- [ ] vitest：useTypingEffect 节流/状态机；SSE 客户端状态机

## 阶段 7：部署
- [ ] 后端托管前端 dist 静态产物（/api 路由先注册，StaticFiles 后挂载；SPA fallback）
- [ ] docker-compose：/data（SQLite）+ /novels（原文备份）volume；默认绑 127.0.0.1 + public profile
- [ ] 环境变量：PORT/DATA_DIR/NOVEL_DIR/TYPING_SPEED/ACCESS_PASSWORD
- [ ] README：一键部署 + 访问密码 + 反代鉴权提示 + 示例小说导入
- [ ] Playwright 冒烟：登录 → 传示例 TXT → 发「下一章」→ 断言正文

## 阶段 8：收尾
- [ ] 全量测试通过（pytest + vitest + Playwright）
- [ ] openspec archive 归档变更
- [ ] 首次 commit + push