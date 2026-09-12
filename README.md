# 墨鱼 Moyu · 伪装 AI 的聊天式小说阅读器

在一个长得像 ChatGPT 的聊天界面里「读小说」：你对它说「下一章」，它就像大模型一样逐字流式地"生成"出正文——其实内容全部来自你导入的本地 TXT 原著。**零 AI 依赖、零 API key、数据不出本机。**

## 特性

- **伪 AI 流式体验**：思考光标 → 逐句流式出字 → 收尾引导语，视觉上复刻大模型生成
- **对话式指令**：下一章 / 上一章 / 跳章 / 书单 / 切书 / 搜索 / 帮助 + 任意输入兜底
- **阅读快捷工具条**：输入框上方常驻 上一章 / 下一章 / 继续本章 / 目录（跳章走目录搜索，或直接手输「第 N 章」）
- **断点续读**：读到一半离开后，点「继续本章」从断点接着读，不必重头再来
- **章节目录抽屉**：搜索章节、自动定位并高亮当前章、点章节即跳转；**上千章也不卡**（只渲染可视区域）
- **设置面板**：一个「思考强度」滑杆控制出字快慢（5 档，从「极速」到「沉思」），并收纳主题 / 阅读宽度 / 快速阅读 / 退出登录
- **账号体系**：首次运行引导创建管理员，管理员可建号、重置密码、启停；**书库全体共享、阅读进度按人独立**
- **TXT 导入**：自动探测 UTF-8 / GBK / GB18030 编码；无章节分隔时按字数兜底分段
- **断句续读 + 进度百分比**：重开从上次断点继续
- **深浅主题 + 宽松/紧凑排版**：首屏无闪烁
- **单容器自托管**：Docker Compose 一键部署，SQLite 单文件存储

## 快速开始（Docker）

```bash
cp .env.example .env
# 编辑 .env：设置一个随机的 SECRET_KEY（openssl rand -hex 32）
docker compose up -d --build
docker compose logs | grep 引导口令     # 首次启动会打印一次性引导口令
```

浏览器打开 `http://localhost:8000`，按引导页创建**第一个管理员**（需要上面那串引导口令），
然后登录、导入 TXT 小说并开始阅读。

- 账号由管理员在界面的「用户管理」里创建，**不开放自助注册**。
- **书库全体用户共享，阅读进度按用户独立**：两个人可以读同一本书而互不干扰。
- 引导口令只出现在**服务端日志**里——这是有意设计，等于把「创建第一个管理员」的权限限定给拥有服务器访问权的人。
- 默认仅绑定 `127.0.0.1`（本机可访问）。要对外提供，在 `.env` 设 `BIND_HOST=0.0.0.0`，**并务必走 HTTPS**。
- 数据存在 Docker 命名卷 `moyu-data`（SQLite）与 `moyu-novels`（原文备份）中：
  `docker volume inspect moyu_moyu-data` 查看位置，`docker compose down` 不会删除它们。
- 若想改用宿主目录绑定挂载，把 compose 里的 `moyu-data:/data` 换成 `./data:/data`，
  并先确保目录属主为容器用户：`mkdir -p data novels && sudo chown -R 10001:10001 data novels`
  （否则非 root 容器无法写入，会启动失败）。
- 从旧版本（共享访问密码）升级：无需手工迁移。老的书与进度会自动归属到第一个管理员。

## 使用

界面是「左侧栏书架 + 居中阅读列 + 底部输入框」，与 ChatGPT 同构：

- **左侧栏**：导入新书、书架（每本书显示自己读到哪）、当前书进度、设置入口、用户区
- **输入框上方**：上一章 / 下一章 / 继续本章 / 目录
- **下方输入框**：既能点按钮，也能直接打字下指令（跳章可手输「第 20 章」）

### 支持的聊天指令

| 你说 | 它做 |
|---|---|
| 下一章 / 继续 / 再来 | 读下一章 |
| 上一章 / 返回 | 读上一章 |
| 继续本章 / 接着读 | **从断点续读本章**，已读部分不重放 |
| 第 20 章 / 跳到 20 | 跳到指定章 |
| 书单 / 有哪些书 | 列书单 |
| 读《书名》/ 换书 书名 | 切换书并续读（等于开新会话） |
| 搜 关键词 | 搜索章节标题 |
| 帮助 | 使用说明 |
| 其他任意话 | 温柔兜底并引导回阅读 |

### 思考强度

设置面板里的滑杆，控制正文逐字出现的节奏，**同时作用于服务端推送间隔与前端打字机速率**：

| 档位 | 观感 |
|---|---|
| 极速 | 几乎瞬间铺满，像在快速扫读 |
| 迅捷 | 几乎不停顿，一口气往外走 |
| 标准 | 默认节奏 |
| 深入 | 一句一句慢慢斟酌 |
| 沉思 | 明显停顿，像是在深思 |

该设置**按账号保存**。实测同一章（2075 字）：极速约 12 秒，深入约 78 秒。

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

> 本地跑后端时若库中还没有账号，控制台会打印一次性引导口令，打开前端按引导页建号即可。

## 测试

```bash
# 后端（117 passed 为基线）
cd backend && .venv\Scripts\python -m pytest -q

# 前端单元测试 + 生产构建（7 passed 为基线）
cd frontend && npm run test && npm run build

# 真实浏览器端到端（31 passed 为基线；需先 npx playwright install chromium）
E2E_BASE_URL=http://127.0.0.1:8000 E2E_USERNAME=admin E2E_PASSWORD=<密码> \
  npx playwright test
```

- E2E **串行执行**（`workers: 1`）：目标环境常是单核自托管机器，并行 worker 会把后端压到超时，产生与代码无关的偶发失败。
- `e2e/_*.spec.ts` 是**一次性工具/诊断脚本**的约定前缀，已被 `testIgnore` 排除，不参与正式回归。
- **别直接对已在用的实例跑全量 E2E**：它会导入测试书、创建测试账号并改动当前用户的设置。先取快照、跑完再还原，步骤见 [docs/HANDOFF.md](docs/HANDOFF.md) 的「快速验证」。

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `SECRET_KEY` | dev 值 | 会话签名密钥，**必改**；存在账号却用默认弱值会拒绝启动 |
| `COOKIE_SECURE` | false | 经 HTTPS 反代访问时设为 true |
| `PORT` | 8000 | 对外端口 |
| `BIND_HOST` | 127.0.0.1 | compose 绑定的宿主地址 |
| `DATA_DIR` | ./data | SQLite 存放目录 |
| `NOVEL_DIR` | ./novels | 导入原文备份目录 |
| `STATIC_DIR` | ./frontend/dist | 前端产物目录 |
| `TYPING_SPEED` | 1.0 | 生成节奏的**服务端默认值**；用户在设置面板里调过之后以用户设置为准 |
| `MAX_UPLOAD_BYTES` | 104857600 | 单次导入的 TXT 体积上限（100 MB），超出即拒绝 |

**账号不从环境变量配置**：首次启动时若库中无任何用户，服务端日志会打印一次性**引导口令**，
用它在网页上创建第一个管理员。此后账号由管理员在「用户管理」里维护。

## 项目结构

```
backend/                FastAPI + SQLAlchemy + SQLite
  app/readers/          TXT 解析（编码探测、章节切分）
  app/router/           auth / users / settings / books / progress / search / chat
  app/services/         chat_engine（指令解析+伪 AI 文案）
                        typing_stream（分批与服务端节流）
                        user_settings（思考强度档位定义与校验）
                        ratelimit（登录限速）
  tests/                pytest（117 项：并发/编码/回滚/SSE/账号/隔离/迁移/设置/断点续读）
frontend/               React + Vite + TS
  public/               favicon.svg / favicon-32x32.png / apple-touch-icon.png
  src/api/client.ts     REST + SSE 客户端
  src/hooks/            useTypingEffect（打字机，速率随思考强度缩放）
  src/components/       Sidebar / MessageList / Composer / ReadingToolbar
                        ChapterDrawer（章节列表，窗口化）/ SettingsDialog
                        UserAdminDialog / EmptyState / LoginPage / SetupPage / Logo
  e2e/                  Playwright 用例（_ 前缀为一次性脚本，不参与回归）
Dockerfile              multi-stage：构建前端 → 非 root Python 运行时
docker-compose.yml      单容器 + 两个数据卷
openspec/               规格驱动开发（specs 为当前事实源，changes/archive 为历史变更）
docs/HANDOFF.md         交接文档：产物索引、不可破坏的约定、下一步建议
```

> 打算改这个项目？先读 **[docs/HANDOFF.md](docs/HANDOFF.md)** —— 里面记着 16 条「不可破坏的约定」
> （每条都对应一个踩过的坑）、已知风险与下一步建议。

## 设计说明

- **SSE 而非 WebSocket**：单向推送足够，实现更简单；用 `POST + fetch ReadableStream` 以便在请求体里携带指令。
- **SQLite WAL**：SSE 长连接并发读不阻塞进度写入。
- **流式期间零数据库访问**：整章在推送前读入内存，避免长章占用连接。
- **不调用任何 AI 服务**：所有"AI 感"由前端打字机 + 后端文案模板营造。
- **会话可吊销**：Cookie 载荷含 `token_version`，改密/停用后旧会话立即失效（不必等过期）。
- **进度推进不会被静默丢弃**：并发写入冲突时退化为直接写入并记日志——用户已经看到新章节，进度就必须跟上。
- **续读时进度归前端所有**：「继续本章」不改章号，章内偏移由前端实时上报，服务端**不**把自己在请求时刻读到的旧偏移写回去——否则会把用户真正读到的位置回滚。
- **首屏无主题闪烁**：主题与阅读宽度存在 localStorage，由 CSS 之前的内联脚本直接应用；因此它们**按浏览器保存**，而思考强度**按账号保存**。
