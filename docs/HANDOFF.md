# 交接文档 · 墨鱼 Moyu

> 面向：接手本项目的新 agent 或协作者。
> 原则：只写「去哪找」和「下一步做什么」，不重复已存在于规格、代码、提交中的细节。

## 一句话现状

MVP 已完成、已通过多层测试、已推送到公开仓库：一个可自托管的「伪装成 AI 聊天」的本地 TXT 小说阅读器。当前无进行中的 OpenSpec 变更（都已归档）。

## 产物索引（建议阅读顺序）

| 想了解 | 去哪里看 |
|---|---|
| 项目是什么、如何部署、指令表 | `README.md` |
| 为什么做这件事、非目标 | `openspec/changes/archive/2026-09-11-mvp-moyu/proposal.md` |
| 技术方案与关键设计决策 | 同目录 `design.md` |
| **系统当前事实源**（已归档规格） | `openspec/specs/{pseudo-ai-chat,novel-import,books,progress,auth}/spec.md` |
| 实现清单与完成状态 | 同 archive 目录 `tasks.md` |
| 后端结构 | `backend/app/`（`readers/` `router/` `services/`） |
| 前端结构 | `frontend/src/`（`api/` `hooks/` `components/`） |
| 变更历史 | `git log`（不要在本文件重复提交内容） |
| 远程仓库 | https://github.com/HerrDanke/Moyu |

## 不可破坏的约定

以下每条都有测试兜底。改动前先跑测试，改动后确认仍绿。

1. **SQLite 必须 WAL + `busy_timeout=5000` + `foreign_keys=ON`**（`backend/app/db.py`）。否则 SSE 长连接并发读会与进度写入互锁，报 `database is locked`，级联删除也会失效。
2. **SSE 流式推送期间零数据库访问**：整章正文在推送开始前一次性读入内存（`services/typing_stream.py`），推送阶段只做内存分批 + `asyncio.sleep`。
3. **进度写入放在流式结束之后**（`router/chat.py`），客户端中途断开则不推进；推进用条件更新 `WHERE chapter_index = 旧值` 做原子 CAS。
4. **「当前书」唯一真相源在后端** `settings` 表。前端切换书目必须调用 `POST /api/books/{id}/select`，SSE 也会回发 `book` 事件让前端同步——不要只改前端 state。
5. **续读偏移只按章节正文计**：服务端通过 `meta` 事件给出 `start_offset` / `char_count`，前端必须剔除标题与收尾文案后再计算偏移。
6. **指令解析正则必须保持线性**（禁止嵌套量词）+ 输入截断 500 字符（防 ReDoS）；**SQL 必须参数化**，LIKE 关键词必须转义 `%` `_`（`services/chat_engine.py: escape_like`）。
7. **配置了 `ACCESS_PASSWORD` 却使用默认/空 `SECRET_KEY` 时，应用会拒绝启动**（`main.py: _assert_secure_config`）——这是有意的安全策略，不要移除。
8. **静态资源挂载必须晚于 `/api` 路由注册**；未注册的 `/api/*` 必须返回 404，不能回退成 `index.html`（`main.py: SPAStaticFiles`）。
9. TXT 编码探测顺序固定为 BOM → UTF-8 严格 → GB18030 严格 → charset-normalizer 兜底。许多 GBK 双字节序列恰好是合法 UTF-8，**不要改成 charset-normalizer 优先**。

## 快速验证

改动后至少跑前两组；涉及流式/前端交互时加跑 E2E。

```bash
# 后端（67 passed 为基线）
cd backend && .venv/Scripts/python.exe -m pytest -q

# 前端单元测试 + 生产构建（3 passed + 构建成功为基线）
cd frontend && npm run test && npm run build

# 真实浏览器端到端（需先启动后端；首次需 npx playwright install chromium）
cd frontend && npx playwright test
```

E2E 需要后端在运行，并通过环境变量指定地址与密码：
`E2E_BASE_URL=http://127.0.0.1:8000`、`E2E_PASSWORD=<你的访问密码>`。

历史基线：pytest 67 / vitest 3 / 临时 HTTP 冒烟脚本 13 / Playwright 1（冒烟脚本当时为临时文件，已删除，未入库）。

## 已知未完成与风险

1. **Docker 镜像未在本机实测**（开发机没有 Docker）。Dockerfile 与 compose 按最佳实践编写，但首次 `docker compose up -d --build` 需要人工确认。
2. **默认分支是 `master`**，GitHub 惯例为 `main`，尚未调整。
3. **git 提交显示名 `HerrrrDanke` 与账号 `HerrDanke` 不一致**（仅显示名，邮箱正确，提交仍会关联账号）。只影响未来提交，已推送的历史不追改。
4. **登录无速率限制**：单用户场景暂可接受，公网暴露前建议在反向代理层限制。
5. **超大文件导入内存峰值高**：接近上限（默认 100MB）时整体读入内存再解析。已移入线程池避免阻塞事件循环，但没有做流式解析。
6. **服务端无法真正中断进行中的流**：客户端 `AbortController` 只停止渲染与进度写入，服务端生成器仍会跑完（不影响数据正确性）。
7. **搜索引擎是标题 LIKE**，不支持正文检索。

## 下一步建议（按价值排序）

1. 划词批注 / 高亮（CEO 评审中列为延后项的增强）
2. EPUB 支持——`backend/app/readers/base.py` 的 `BaseReader` 接口已为扩展预留
3. 真实服务 HTTP 冒烟脚本入库（当前为临时脚本）或补充为 pytest 集成测试
4. 章节正文搜索升级到 SQLite FTS5
5. 阅读体验：字号/行距预设、读当前章时预取下一章
6. 部署体验：GitHub Actions 自动构建镜像；默认分支改为 `main`

## 建议调用的 skills

| 场景 | 建议 skill |
|---|---|
| 有新功能 / 需求变更想法 | `brainstorming`，随后 `openspec-propose` |
| 需要写实现计划 | `writing-plans` 或 `openspec-apply-change` |
| 实现完要评审 | `requesting-code-review` |
| 提交并开 PR | `commit-push-pr` |
| 排查 bug | `systematic-debugging` / `investigate` |
| 变更完成要归档 | `openspec-archive-change` |
| 更新项目文档 | `document-release` |
| 本轮复盘 | `retro` |

## 敏感信息

本文件不含任何密钥或个人信息。部署所需的 `ACCESS_PASSWORD` 与 `SECRET_KEY` 只应存在于使用者本机的 `.env`（已被 `.gitignore` 排除）。请勿把真实密码写入仓库任何文件——包括本文件。