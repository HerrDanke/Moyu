# 交接文档 · 墨鱼 Moyu

> 面向：接手本项目的新 agent 或协作者。
> 原则：只写「去哪找」和「下一步做什么」，不重复已存在于规格、代码、提交中的细节。

## 一句话现状

一个可自托管的「伪装成 AI 聊天」的本地 TXT 小说阅读器，功能已完整（账号体系 / ChatGPT 式界面 / 章节目录 / 设置面板）、已多层测试、已推送到公开仓库并在真实 PVE 容器上运行。当前无进行中的 OpenSpec 变更（都已归档）。

## 产物索引（建议阅读顺序）

| 想了解 | 去哪里看 |
|---|---|
| 项目是什么、怎么部署、指令表与思考强度 | `README.md` |
| **系统当前事实源** | `openspec/specs/`（7 个能力：`pseudo-ai-chat` `novel-import` `books` `progress` `auth` `user-admin` `ui-shell`） |
| 某个功能为什么这么做、当时的取舍 | `openspec/changes/archive/<日期>-<名称>/`（proposal → design → tasks） |
| 后端结构 | `backend/app/`（`readers/` `router/` `services/`） |
| 前端结构 | `frontend/src/`（`api/` `hooks/` `utils/` `components/`） |
| 变更历史 | `git log`（不要在本文件重复提交内容） |
| 远程仓库 | https://github.com/HerrDanke/Moyu |

已归档变更（按时间）：`mvp-moyu` / `chatgpt-ui` / `user-management` / `chapter-navigation` / `settings-panel`。

## 不可破坏的约定

以下每条都有测试兜底。改动前先跑测试，改动后确认仍绿。

1. **SQLite 必须 WAL + `busy_timeout=5000` + `foreign_keys=ON`**（`backend/app/db.py`）。否则 SSE 长连接并发读会与进度写入互锁，报 `database is locked`，级联删除也会失效。
2. **SSE 流式推送期间零数据库访问**：整章正文在推送开始前一次性读入内存（查库发生在 `services/chat_engine.py` 的 `build_response`），`services/typing_stream.py` 只负责对已取出的字符串做内存分批 + `asyncio.sleep`，它开头就声明「正文进入本模块前已从 DB 取出」。
3. **进度推进绝不能被静默丢弃**（`services/store.py: write_progress`）。它会先试条件更新（`WHERE chapter_index = 旧值`）以减少多标签页重复推进，**但未命中时必须退化为无条件写入并记 warning**。同一行还会被前端的偏移上报并发 PATCH，这个"假设过期"的窗口是真实存在的——早期实现返回 False 什么都不写，导致「界面显示第 9 章、进度停在第 2 章，下一次『下一章』跳回第 3 章」。忘记这条会重演该 bug。
4. **「当前书」与阅读进度都是用户级**：存在 `users.current_book_id` 与 `progress(user_id, book_id)`，**不是**全局 `settings`。凡涉及进度的查询都必须带 `user_id`——特别注意 `store.get_current_book` 的**回退分支**（曾按 `updated_at` 全库排序，会让 B 继承 A 最近读的书）。
5. **书库共享、进度隔离**：所有登录用户看到同一批书；删除书籍需要管理员，且要清掉**所有**用户在该书上的进度，并用 `clear_current_book_reference` 清掉指向它的 `current_book_id`（该列无外键约束，见 `models.py` 模块说明）。
6. **会话可吊销**：Cookie 载荷是 `{uid, tv}`。`get_current_user` 每次请求都查库校验 用户存在 + 启用 + `token_version` 一致，因此改密/停用/删除后旧会话**下一次请求即失效**。旧版 `{ok:true}` 形态的 Cookie 一律视为无效。
7. **存在任意用户时，弱/空 `SECRET_KEY` 必须拒绝启动**（`main.py: assert_secure_secret`）。守卫条件已与账号体系绑定——**不要**再依赖 `ACCESS_PASSWORD`（该变量已退役，沿用旧条件会恒为假，从而允许用公开常量自签 Cookie 绕过鉴权）。
8. **未初始化期间不得暴露数据**：库中无任何用户时，除 `/api/auth/login|status|setup` 外全部 `/api/*` 返回 401（`deps.require_session` 自然满足，因为拿不到合法会话）。
9. **思考强度同时作用于两端**：服务端分批间隔（`typing_speed`）**与**前端打字机速率（`MessageList` 按倍率缩放 `charsPerTick`）。只调服务端没用——打字机本身有 125 字/秒的硬下限，长章节会被它拖住。档位定义是**服务端唯一事实源**（`services/user_settings.py`），前端从 `GET /api/settings` 读回，不要在前端再抄一份。
10. **不要把「会读 state 的处理函数」用 `useCallback(..., [])` 包起来**。`App.tsx` 的 `handleSend` 会读 `quickRead`；一旦某个入口（如目录点章）把它记忆化且依赖数组为空，那个入口就永久闭包住首帧的 `handleSend`，其中 `quickRead` 恒为 `false`——「快速阅读」在该路径上静默失效，且只在**点目录**时出现、点「下一章」正常，极难排查。`ChapterDrawer` 没有 `React.memo`，这类记忆化本来就零收益。已有 E2E 护栏（断言请求体 `quick_read`，见 `e2e/chapter-nav.spec.ts`）。
11. **续读偏移只按章节正文计**：服务端通过 `meta` 事件给出 `start_offset` / `char_count`，前端必须剔除标题与收尾文案后再计算偏移；且**只允许当前活跃消息上报**（旧章节滞留的打字机会污染新章节的偏移）。
12. **流式断句必须能原样拼回**：`typing_stream.split_sentences` 只丢弃真正的空串，**不能**用 `p.strip()` 过滤——`re.split` 会把「只含换行」的片段单独切出来，strip 后判空即被丢弃，段落分隔会在流式阶段被抹掉（长章节糊成一坨）。
13. **指令解析正则必须保持线性**（禁止嵌套量词）+ 输入截断 500 字符（防 ReDoS）；**SQL 必须参数化**，LIKE 关键词必须转义 `%` `_`（`services/chat_engine.py: escape_like`）。
14. **静态资源挂载必须晚于 `/api` 路由注册**；未注册的 `/api/*` 必须返回 404，不能回退成 `index.html`（`main.py: SPAStaticFiles`）。
15. TXT 编码探测顺序固定为 BOM → UTF-8 严格 → GB18030 严格 → charset-normalizer 兜底。许多 GBK 双字节序列恰好是合法 UTF-8，**不要改成 charset-normalizer 优先**。
16. **主题与阅读宽度必须留在 localStorage**：首屏防闪烁依赖 CSS 之前的内联脚本直接读 `localStorage`，改成等接口返回必然闪一下。这是有意取舍，不是遗漏。

## 快速验证

改动后至少跑前两组；涉及流式/前端交互时加跑 E2E。

```bash
# 后端（105 passed 为基线）
cd backend && .venv/Scripts/python.exe -m pytest -q

# 前端单元测试 + 生产构建（7 passed + 构建成功为基线）
cd frontend && npm run test && npm run build

# 真实浏览器端到端（30 passed 为基线；需先 npx playwright install chromium）
cd frontend && E2E_BASE_URL=http://<host>:8000 E2E_USERNAME=admin E2E_PASSWORD=<密码> npx playwright test
```

- **E2E 串行**（`playwright.config.ts: workers: 1`）：目标环境是单核容器，并行 worker 会把后端压到超时，产生与代码无关的偶发失败。
- `e2e/_*.spec.ts` 是**一次性工具/诊断脚本**的约定前缀（截图、探针、图标生成），已被 `testIgnore` 排除，不参与回归。需要重跑时临时改名或去掉该 ignore。
- E2E 需要一个**已初始化的实例**（库里有账号）。若服务尚未初始化，设置 `E2E_SETUP_CODE` 让它走首次引导。
- 本套 30 条已在**真实部署实例**（`192.168.178.116`）上跑通，单核约 1.1 分钟。这是发布前的最终口径。

### 别直接对线上实例跑全量 E2E

E2E 会**改动实例数据**。实测的污染范围：

| 影响 | 说明 |
|---|---|
| 新增书籍 | 本轮实测 **19 本**测试书留在库里（每个导入类用例 1~2 本，随跑的用例数变化） |
| 新增账号 | 本轮实测 **3 个** `reader*` 测试账号留在库里 |
| 改动用户设置 | `settings.spec.ts` 会把 admin 的「思考强度」设置成测试值 |
| 切走当前书 | 测试导入会 `select` 新书，admin 的「当前书」被改掉 |
| **不会**发生 | 删除既有书与进度、修改密码（唯一的 `delete` 是断言 403，不会真删） |

所以要么另起一个临时实例跑，要么「取快照 → 跑 → 还原」三步走完：

```bash
# 1) 取快照。直查容器内 SQLite 最准（不经 API，避免字段猜测）：
#    users.current_book_id、user_settings.typing_speed、books 的 id 列表、账号名列表
docker compose exec -T moyu python -c "...sqlite3 /data/moyu.sqlite3..."

# 2) 跑 E2E
E2E_BASE_URL=http://<host>:8000 E2E_USERNAME=admin E2E_PASSWORD=<密码> npx playwright test

# 3) 还原 —— 走 API 而不是直接改库，才能复用应用自身的级联删除与
#    clear_current_book_reference（见约定 5）
curl -X DELETE .../api/books/<快照外的 id>        # 级联清掉所有用户在该书上的进度
curl -X DELETE .../api/users/<非 admin 的 id>
curl -X POST   .../api/books/<原当前书>/select    # 还原「当前书」
curl -X PATCH  .../api/settings -d '{"typing_speed": <原值>}'
```

还原后再**直查一次 SQLite** 核对行数与进度值——API 的成功响应不等于落盘状态正确。
两个附带提醒：测试会消耗书籍自增 id（下次导入的 id 会往后跳，无功能影响）；临时快照可能含小说正文，**不要**留在服务器或提交进仓库。

## 部署与运维

目标环境 `192.168.178.116`（主机名 `Moyu`，PVE 上的**单核 LXC**），应用目录 `/opt/moyu`，对外 `http://192.168.178.116:8000`。
本机已配置免密登录（密钥 `~/.ssh/moyu_pve_ed25519`），无需输密码。

```bash
# 拉取 + 重建 + 重启
ssh root@192.168.178.116 'cd /opt/moyu && git pull --ff-only && docker compose up -d --build'
```

- **先确认能快进**：远端 HEAD 必须是本地 HEAD 的祖先（`git merge-base --is-ancestor <远端HEAD> HEAD`）。本仓库是**直接推 `master`** 的工作流，没有 PR 环节。
- 单核上增量构建约 15~30 秒（前端与依赖层有缓存），首次全量构建要几分钟。
- **判定部署是否成功，看前端产物哈希**：远端 `/` 引用的 `assets/index-<hash>.js` 必须与本地 `npm run build` 的产出哈希一致。这是「部署的确实是我验证过的那份代码」最直接的证据——曾靠它区分修复版与注入 bug 的版本。
- `docker compose up -d --build` 的退出码**不**代表服务已就绪，部署脚本应轮询 `/api/auth/status` 返回 200 再判定成功。
- 数据库在命名卷 `moyu_moyu-data`（容器内 `/data`），原文备份在 `moyu-novels`。`up -d --build` 不重建卷，`down` 也不删卷，所以**账号与阅读进度跨部署持续**。
- 远端 `.env` 权限 `600`，`SECRET_KEY` 为随机值（沿用默认弱值且库中有账号时会拒绝启动，见约定 7）。
- 容器以非 root（uid 10001）运行；若改用宿主目录绑定挂载，必须先 `chown -R 10001:10001`，否则因无权写入而启动失败。

## 已知未完成与风险

1. **默认分支是 `master`**，GitHub 惯例为 `main`，尚未调整。
2. **git 提交显示名 `HerrrrDanke` 与账号 `HerrDanke` 不一致**（仅显示名，邮箱正确，提交仍会关联账号）。只影响未来提交，已推送的历史不追改。
3. **超大文件导入内存峰值高**：接近上限（默认 100MB）时整体读入内存再解析。已移入线程池避免阻塞事件循环，但没有做流式解析。
4. **服务端无法真正中断进行中的流**：客户端 `AbortController` 只停止渲染与进度写入，服务端生成器仍会跑完（不影响数据正确性）。
5. **搜索引擎是标题 LIKE**，不支持正文检索。
6. **登录限速与引导口令是内存实现**（`services/ratelimit.py`、`security.py`）：**一旦改为多 worker 或水平扩容即失效**，届时需换成共享存储。这是扩容的前置条件。
7. **删除书籍不清理 `/novels` 里的原文备份**，会留孤儿文件（导入失败时会清理，删除时不会）。
8. **没有审计日志 / 登录失败留痕**：排查入侵时无据可查。
9. **密码强度下限只有 4 位**（为了照顾短口令的使用习惯），公网部署前应配合 HTTPS 与强口令。

## 下一步建议（按价值排序）

1. **划词批注 / 高亮**（CEO 评审中列为延后项）
2. **EPUB 支持**——`backend/app/readers/base.py` 的 `BaseReader` 接口已为扩展预留
3. **把删除书籍时的原文备份一并清理**（当前会留孤儿，见风险 7）
4. **章节正文搜索升级到 SQLite FTS5**（当前只有标题 LIKE）
5. **阅读体验**：字号/行距预设、读当前章时预取下一章、目录里的已读标记
6. **部署体验**：GitHub Actions 自动构建镜像、配 HTTPS（Caddy）、默认分支改 `main`
7. **多 worker 前的改造**：限速与引导口令改为共享存储（见风险 6）

## 建议调用的 skills

| 场景 | 建议 skill |
|---|---|
| 有新功能 / 需求变更想法 | `brainstorming`，随后 `openspec-propose` |
| 需要写实现计划 | `writing-plans` 或 `openspec-apply-change` |
| 实现完要评审 | `requesting-code-review` |
| 提交并开 PR | `commit-push-pr` |
| 排查 bug | `systematic-debugging` / `investigate` |
| 变更完成要归档 | `openspec-archive-change` |
| 更新项目文档 | `document-release`（本文件的更新就走它） |
| 本轮复盘 | `retro` |

## 敏感信息

本文件不含任何密钥或个人信息。部署所需的 `SECRET_KEY`（以及管理员密码）只应存在于服务器本机的 `.env` / 数据库里（`.env` 已被 `.gitignore` 排除）。**`ACCESS_PASSWORD` 已退役**——账号体系取代了它。请勿把真实密码写入仓库任何文件——包括本文件。
