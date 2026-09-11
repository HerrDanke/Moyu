# 墨鱼 Moyu · 伪装 AI 的聊天式小说阅读器

在一个长得像 ChatGPT 的聊天界面里「读小说」：你对它说「下一章」，它就像大模型一样逐字流式地"生成"出正文——其实内容全部来自你导入的本地 TXT 原著。**零 AI 依赖、零 API key、数据不出本机。**

## 特性

- **伪 AI 流式体验**：思考光标 → 逐句流式出字 → 收尾引导语，视觉上复刻大模型生成
- **聊天式指令**：下一章 / 上一章 / 跳章 / 书单 / 切书 / 搜索 / 帮助 + 任意输入兜底
- **TXT 导入**：自动探测 UTF-8 / GBK / GB18030 编码；无章节分隔时按字数兜底分段
- **断句续读 + 进度百分比**：重开从上次断点继续
- **快速阅读开关**：不想等流式时一次性展示正文
- **多本书 + 阅读进度**：切书各自记住进度
- **访问密码**：内置简单鉴权，防止公网裸奔
- **单容器自托管**：Docker Compose 一键部署，SQLite 单文件存储

## 快速开始（Docker）

```bash
cp .env.example .env
# 编辑 .env：至少改掉 ACCESS_PASSWORD 和 SECRET_KEY
docker compose up -d --build
```

浏览器打开 `http://localhost:8000`，输入访问密码，导入一个 TXT 小说，然后说「下一章」。

- 默认仅绑定 `127.0.0.1`（本机可访问）。要对外提供，在 `.env` 设 `BIND_HOST=0.0.0.0`，**并务必设置强密码**，建议再套一层反向代理鉴权。
- 数据持久化在 `./data`（SQLite）与 `./novels`（原文备份）。

## 本地开发

后端：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows；macOS/Linux 用 source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload     # http://127.0.0.1:8000
```

前端（Vite 已配置把 /api 代理到 8000）：

```bash
cd frontend
npm install
npm run dev                       # http://127.0.0.1:5173
```

## 测试

```bash
# 后端
cd backend && .venv\Scripts\python -m pytest -q

# 前端单元测试
cd frontend && npm run test

# 端到端冒烟（需先安装浏览器：npx playwright install chromium）
cd frontend && npm run test:e2e
```

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `ACCESS_PASSWORD` | 空 | 访问密码；为空则不校验（仅建议本地） |
| `SECRET_KEY` | dev 值 | 会话 Cookie 签名密钥，务必修改 |
| `PORT` | 8000 | 对外端口 |
| `BIND_HOST` | 127.0.0.1 | compose 绑定的宿主地址 |
| `DATA_DIR` | ./data | SQLite 存放目录 |
| `NOVEL_DIR` | ./novels | 导入原文备份目录 |
| `STATIC_DIR` | ./frontend/dist | 前端产物目录 |
| `TYPING_SPEED` | 1.0 | 打字机速度，越大越快 |

## 支持的聊天指令

| 你说 | 它做 |
|---|---|
| 下一章 / 继续 / 再来 | 读下一章 |
| 上一章 / 返回 | 读上一章 |
| 第 20 章 / 跳到 20 | 跳到指定章 |
| 书单 / 有哪些书 | 列书单 |
| 读《书名》/ 换书 书名 | 切换书并续读 |
| 搜 关键词 | 搜索章节标题 |
| 帮助 | 使用说明 |
| 其他任意话 | 温柔兜底并引导回阅读 |

## 项目结构

```
backend/                FastAPI + SQLAlchemy + SQLite
  app/readers/          TXT 解析（编码探测、章节切分）
  app/router/           auth / books / progress / chat / search
  app/services/         chat_engine（指令解析+伪 AI 文案）/ typing_stream（节流）
  tests/                pytest（含并发/编码/回滚/SSE 报文）
frontend/               React + Vite + TS
  src/api/client.ts     REST + SSE 客户端
  src/hooks/            useTypingEffect（打字机）
  src/components/       聊天界面组件
Dockerfile              multi-stage：构建前端 → 非 root Python 运行时
docker-compose.yml      单容器 + 两个数据卷
openspec/               规格驱动开发（proposal / specs / design / tasks）
```

## 设计说明

- **SSE 而非 WebSocket**：单向推送足够，实现更简单；用 `POST + fetch ReadableStream` 以便在请求体里携带指令。
- **SQLite WAL**：SSE 长连接并发读不阻塞进度写入。
- **流式期间零数据库访问**：整章在推送前读入内存，避免长章占用连接。
- **不调用任何 AI 服务**：所有"AI 感"由前端打字机 + 后端文案模板营造。