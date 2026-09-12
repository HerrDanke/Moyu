# AGENTS.md

面向在本仓库工作的编码 agent。只写「怎么跑」和「必须知道什么」，功能说明见 [README.md](README.md)，
踩坑记录与运维细节见 [docs/HANDOFF.md](docs/HANDOFF.md)。

## 项目概览

「墨鱼 Moyu」：一个伪装成大模型对话界面的本地 TXT 小说阅读器。**不调用任何 AI 服务**——
所有流式「生成感」由后端 SSE 分批节流 + 前端打字机共同伪造。

- 后端：FastAPI + SQLAlchemy 2.0 + SQLite（WAL），`backend/`
- 前端：React 18 + Vite + TypeScript（strict），`frontend/`
- 部署：单容器 multi-stage 镜像，`docker-compose.yml`
- 规格：`openspec/`（`specs/` 是系统当前事实源，`changes/archive/` 是历史变更）

## 常用命令

### 后端（`backend/`）

```bash
python -m venv .venv
.venv\Scripts\activate                      # Windows；macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload               # http://127.0.0.1:8000

.venv/Scripts/python.exe -m pytest -q                       # 全量（基线 105 passed）
.venv/Scripts/python.exe -m pytest tests/test_progress_advance.py -q   # 单个文件
.venv/Scripts/python.exe -m pytest -q -k write_progress     # 按名称筛选
```

后端**没有配置任何 linter/formatter**（无 ruff / flake8 / mypy / pre-commit）。测试即验证手段。

### 前端（`frontend/`）

```bash
npm install
npm run dev                                 # http://127.0.0.1:5173，/api 已代理到 8000

npm run test                                # vitest run（基线 7 passed）
npx vitest run src/hooks/useTypingEffect.test.ts   # 单个测试文件
npm run build                               # tsc -b && vite build —— 这也是唯一的类型检查入口
```

`npm run build` 里的 `tsc -b` 是前端唯一静态检查（tsconfig 开了 `strict` / `noUnusedLocals` /
`noUnusedParameters`）。改完 TS 至少跑一次 `npm run build`。

### 端到端（Playwright）

```bash
npx playwright install chromium             # 首次
E2E_BASE_URL=http://127.0.0.1:8000 E2E_USERNAME=admin E2E_PASSWORD=<密码> npx playwright test
npx playwright test e2e/chapter-nav.spec.ts # 单个 spec
```

- **串行是刻意的**（`playwright.config.ts: workers: 1`）：目标环境是单核容器，并行 worker 会把后端压到超时。
- `e2e/_*.spec.ts` 是「一次性工具/诊断脚本」约定前缀，已被 `testIgnore` 排除，跑它需临时改名或覆盖 `--testIgnore=''`。
- **别直接对线上实例跑全量 E2E**：它会导入测试书、建测试账号、改当前用户的设置与当前书。
  污染范围与「快照 → 跑 → 还原」步骤见 [docs/HANDOFF.md](docs/HANDOFF.md) 的「别直接对线上实例跑全量 E2E」。
- E2E 需要**已初始化**的实例；未初始化时用 `E2E_SETUP_CODE` 走首次引导。

### Docker / 部署

```bash
cp .env.example .env                        # 必须设置随机 SECRET_KEY（openssl rand -hex 32）
docker compose up -d --build
docker compose logs | grep 引导口令         # 首次启动打印一次性引导口令
```

部署目标是 `master` 分支**直接推送**的工作流（没有 PR 环节）。判定部署成功看远端 `/` 引用的
`assets/index-<hash>.js` 是否与本地 `npm run build` 的哈希一致——这是「部署的确实是验证过的那份代码」
最直接的证据。详见 [docs/HANDOFF.md](docs/HANDOFF.md) 的「部署与运维」。

## 架构

### 后端分层（`backend/app/`）

```
main.py        create_app：建 engine → init_db → 注册 /api 路由 → 最后挂载前端静态资源
config.py      Settings dataclass，from_env() 读环境变量；测试用 set_settings() 注入
db.py          engine/PRAGMA/WAL、建表、老库迁移（progress → progress_legacy 回填）
models.py      User / Book / Chapter / Progress / Setting / UserSetting
deps.py        get_db、require_session（= get_current_user）、require_admin
security.py    密码哈希、Cookie 会话签名（{uid, tv}）、引导口令
schemas.py     Pydantic 出入参
router/        auth / users / settings / books / progress / search / chat
services/      chat_engine、typing_stream、store、user_settings、ratelimit、importer
readers/       base.BaseReader + txt_reader（编码探测、章节切分）
```

**一次「下一章」的完整链路**（理解本项目最关键的一条线）：

1. `POST /api/chat`（`router/chat.py`）→ `chat_engine.parse_intent` 解析指令
2. `chat_engine.build_response` **在这里完成全部数据库访问**：定位「当前书」、取章节、更新进度，
   并把整章正文读入内存
3. `typing_stream.stream_response` 只对已取出的字符串做内存分批 + `asyncio.sleep` 节流，输出 SSE
4. 前端 `api/client.ts: streamChat` 解析 `data:` 行 → `App.tsx: handleSend` 派发事件
5. `hooks/useTypingEffect` 打字机按速率渲染 → `App.tsx: handleProgressReport` 节流上报 `chapter_offset`

### 前端分层（`frontend/src/`）

- `App.tsx` 是**唯一的状态容器**（auth / books / currentId / progressMap / messages / 设置开关 / draft）。
  组件基本是受控的展示层，没有状态管理库。
- `api/client.ts` 承担全部 REST + SSE，含全局 401 回调 `onUnauthorized`。
- `components/ChapterDrawer.tsx` 对章节列表做窗口化渲染（上千章不卡）。
- `hooks/useTypingEffect.ts` 打字机：默认 2 字 / 16ms（约 **125 字/秒**）；`MessageList.tsx`
  按 `typing_speed` 缩放 `charsPerTick` 来突破这个下限。因此「思考强度」必须同时调服务端间隔与前端速率。
- **`MessageList.tsx` 通过 `animate={!quickRead}` 决定是否走打字机**；`quickRead` 是「快速阅读」开关。

### 状态存放位置（有意为之，改动前先看 HANDOFF 的第 9、16 条约定）

| 状态 | 存在哪 | 原因 |
|---|---|---|
| 思考强度档位定义 | 服务端 `services/user_settings.py` | 唯一事实源，前端从 `GET /api/settings` 读回 |
| 用户思考强度值 | 服务端 `user_settings` 表（按账号） | 跨设备一致 |
| 主题、阅读宽度 | `localStorage` | 首屏防闪烁靠 CSS 之前的内联脚本直读，**不能**改成等接口 |
| 当前书 | 服务端 `users.current_book_id` + `localStorage` 镜像 | 对话引擎需要，前端用于首屏选择 |

### 数据模型要点

- **书库共享、进度按人隔离**：`progress` 主键是 `(user_id, book_id)`；凡涉及进度的查询都必须带 `user_id`。
- `users.current_book_id` **有意不加外键**（users↔books 会构成循环外键，SQLite 无法 ALTER 加约束）。
  删除书籍时必须在业务代码里 `clear_current_book_reference`。
- 老库（无账号体系）通过 `db.py: _rename_legacy_progress` + `backfill_legacy_data` 迁移到首个管理员名下。

### 鉴权

- Cookie 载荷 `{uid, tv}`（tv = `token_version`）。`deps.require_session` **每次请求都查库**，
  校验「用户存在 + 启用 + token_version 一致」→ 改密/停用/删除后旧会话下一次请求即失效。
- 库中无任何用户时，除 `/api/auth/login|status|setup` 外全部 `/api/*` 返回 401。
- **存在用户时用弱 `SECRET_KEY` 必须拒绝启动**（`main.py: assert_secure_secret`）。

## 必须遵守的高风险约束

以下几条是踩过坑、且有测试兜底的。完整 16 条见 [docs/HANDOFF.md](docs/HANDOFF.md) 的「不可破坏的约定」，
改动相关模块前请先读一遍。

1. **SSE 推送期间零数据库访问**：`typing_stream.py` 不得查库；查库只发生在 `chat_engine.build_response`。
2. **进度推进不能被静默丢弃**（`services/store.py: write_progress`）：条件更新未命中时**必须退化为无条件写入**
   并记 warning。早期版本直接返回 False，导致「界面显示第 9 章、进度停在第 2 章」。
3. **SQLite PRAGMA 三项固定**：WAL + `busy_timeout=5000` + `foreign_keys=ON`（`db.py`）。去掉会互锁或级联删除失效。
4. **静态资源挂载必须晚于 `/api` 路由注册**，且未注册的 `/api/*` 必须 404（不能回退 `index.html`）。
5. **不要把读 state 的处理函数用 `useCallback(..., [])` 包起来**：`App.tsx: handleSend` 会读 `quickRead`，
   一旦被空依赖记忆化，某条路径（如目录点章）会永久闭包首帧值，「快速阅读」静默失效。
   `ChapterDrawer` 没有 `React.memo`，这类记忆化本来就零收益。
6. **流式断句必须能原样拼回**：`typing_stream.split_sentences` 只丢弃真正的空串，
   **不能**用 `p.strip()` 过滤（会把「只含换行」的段落分隔吃掉，长章节糊成一坨）。
7. **指令解析正则必须线性**（禁嵌套量词）+ 输入截断 500 字符防 ReDoS；SQL 必须参数化，
   LIKE 关键词必须转义 `%` `_`（`chat_engine.escape_like`）。
8. **续读偏移只按章节正文计**，且只允许当前活跃消息上报（旧章节滞留的打字机会污染新章节偏移）。
9. **TXT 编码探测顺序固定**：BOM → UTF-8 严格 → GB18030 严格 → charset-normalizer 兜底。
   很多 GBK 双字节序列恰好是合法 UTF-8，**不要**改成 charset-normalizer 优先。

## 测试约定（`backend/tests/`）

- `conftest.py` 的夹具：`client` = **已登录的管理员**（多数用例直接用）、`anon_client` = 未登录、
  `other_client` = 第二个普通用户（验证数据隔离）。
- 测试通过 `create_app(make_settings(tmp_path))` 注入独立实例与临时目录，**不读环境变量**。
  新增可配置项时请在 `make_settings` 里给出测试默认值。
- `_reset_rate_limits` 是 autouse 夹具：限速是全局内存状态，必须逐用例重置。
- `make_settings` 的 `secret_key` 必须是「非弱值」，否则存在用户时会拒绝启动。
- 涉及并发/迁移/SSE 的用例见 `test_db_concurrency.py` / `test_migration.py` / `test_chat_sse.py`。

## 规格驱动工作流（OpenSpec）

仓库已初始化 `openspec`，根目录存在 `openspec/`：

- **动手前**读 `openspec/specs/`（7 个能力：`pseudo-ai-chat` `novel-import` `books` `progress` `auth`
  `user-admin` `ui-shell`）与 `openspec/changes/`（进行中的变更）。
- **新需求/行为变更**：建 `changes/<kebab-case-名称>/`，产出 `proposal.md` → `specs/`（ADDED/MODIFIED/REMOVED
  增量）→ `design.md` → `tasks.md`（带 checkbox），**待用户确认后再写实现代码**，然后按清单逐项实现并勾选。
- **完成**：`openspec archive <名称> --yes`，把增量合并进主 `specs/`。
- 小改动、bug 修复、一次性脚本不强制走流程。

常用检查：`openspec list` / `openspec status --change <名>` / `openspec validate <名>`。

## 其他约定

- **默认分支是 `master`**，工作流是直接推 `master`（无 PR 环节）；GitHub 惯例的 `main` 尚未调整。
- 一次性诊断/工具脚本放 `frontend/e2e/_*.spec.ts`，利用既有 `testIgnore` 排除。
- 根目录下成片的 `.claude/`、`.cursor/`、`.github/`、`.agents/` 等目录是 superpowers 框架生成的
  工具适配产物（内容只有 OpenSpec 的 skills/commands 副本），**已整体 gitignore，不属于项目代码**，
  不要在其中做修改。`.bitfun/screens/` 仅为界面截图。
- `.gitignore` 已排除运行时数据（`data/`、`novels/`、`.env`、`*.sqlite3`、`dist/`）。
- 不要把真实密码或 `SECRET_KEY` 写进仓库任何文件（含文档）。`ACCESS_PASSWORD` 已退役，账号体系取代了它。
