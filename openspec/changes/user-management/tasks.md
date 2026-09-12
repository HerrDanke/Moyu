# Tasks: 用户管理

## 阶段 0：准备与迁移设计
- [ ] 确认 `ACCESS_PASSWORD` 退役路径（compose / .env.example / README）
- [ ] 写迁移探测：`progress` 是否已有 `user_id` 列；无则重命名为 `progress_legacy`

## 阶段 1：数据层
- [ ] `models.py`：新增 `User`；`progress` 改为主键 `(user_id, book_id)`；`books` 加 `uploaded_by`；`settings` 移除 current_book 语义
- [ ] `db.py`：启动迁移函数（重命名 legacy 表 + create_all + 幂等）
- [ ] `security.py`：`hash_password` / `verify_password`（scrypt 优先，pbkdf2 回退；`hmac.compare_digest`）
- [ ] pytest：哈希往返、错误密码、盐唯一性、迁移幂等

## 阶段 2：鉴权与会话
- [ ] `security.py`：Session 载荷改为携带 `user_id` **与 `token_version`**（含签发/解析）
- [ ] `security.py`：`hash_password` 外层加**全局并发信号量**（最多 2 个 KDF 并行）；用户不存在时跑 dummy 哈希，抹平计时差
- [ ] `deps.py`：`get_current_user`（查库校验存在、启用、`token_version` 一致）、`require_admin`
- [ ] `deps.py`：无用户（`setup_required`）时除 login/status/setup 外全部 401
- [ ] `router/auth.py`：`login(username,password)` / `logout` / `me` / `status(setup_required)`
- [ ] 登录限速：键为 `(IP, username)` 的退避节流 + 全局令牌桶；不硬锁
- [ ] 密码字段加 `max_length`
- [ ] **修正启动守卫**：`_assert_secure_config` 改为「存在任意用户 + 空/弱 SECRET_KEY → 拒绝启动」（原条件依赖 ACCESS_PASSWORD，退役后会恒为假，导致可用默认密钥自签 Cookie 绕过鉴权）
- [ ] pytest：登录成功/失败、停用用户被拒、旧版无 user_id Cookie 被拒、改密后旧会话失效、限速生效、无用户时全站 401、弱密钥拒绝启动

## 阶段 3：首次运行引导
- [ ] 启动时若无用户则用 `secrets` 生成一次性引导口令并打印到日志
- [ ] `POST /api/auth/setup`：**先校验口令（`compare_digest`）再执行 KDF**；无用户 + 密码长度 ≥8 + 用户名格式
- [ ] 引导接口同样受限速约束；`/api/auth/status` 不返回口令
- [ ] 创建成功后：回填 `progress_legacy` 到该管理员、迁移 `settings.current_book`、作废口令、关闭接口
- [ ] pytest：口令错误被拒（且未触发 KDF）、成功后接口关闭、老数据归属管理员

## 阶段 4：用户管理 API
- [ ] `router/users.py`：列表 / 创建 / 重置密码 / 切换管理员 / 停用 / 删除
- [ ] 保护规则：不能删除或停用自己；不能删除/降级/停用**最后一个启用的管理员**；用户名唯一（409）
- [ ] 重置密码 / 停用 / 删除时自增 `token_version`（吊销其会话）
- [ ] 更新接口使用字段白名单，防越权改 `is_admin`
- [ ] pytest：非管理员 403、重名 409、最后管理员保护、自我锁死保护、删除用户清进度、改密吊销会话

## 阶段 5：进度与书籍按用户隔离
- [ ] `services/store.py`：`get_current_book`（**含按 `updated_at` 全库排序的回退分支**）与 `write_progress` 全部带 `user_id`
- [ ] `router/progress.py`：读写当前用户进度（`session.get(Progress, (user_id, book_id))`）
- [ ] `router/chat.py` + `services/chat_engine.py`：进度与当前书绑定当前用户
- [ ] `router/books.py`：书单共享 + 返回导入者名；删除书需管理员并清所有用户进度；select 只改本人
- [ ] pytest：两用户同书进度互不影响；A 不能读到/写到 B 的进度；B 的当前书不继承 A 的最近阅读

## 阶段 6：前端
- [ ] `LoginPage`：用户名 + 密码 + 错误提示
- [ ] `SetupPage`（新增）：用户名 + 密码 + 引导口令
- [ ] `App.tsx`：`setup_required` 分支、当前用户状态、`/api/auth/me` 拉取
- [ ] `Sidebar`：用户区（用户名 + 身份 + 退出）、管理员「用户管理」入口
- [ ] `UserAdminDialog`（新增）：列表 / 新建 / 重置密码 / 切换管理员 / 删除（二次确认）、Esc 关闭 + 焦点回归
- [ ] 品牌：新增 `Logo.tsx`（原创 SVG 标记）+ 侧栏 wordmark「墨鱼」
- [ ] 全部交互元素补 `data-testid`

## 阶段 7：测试
- [ ] 更新既有 E2E：登录辅助函数改为「首次引导建号 / 已建号则登录」
- [ ] 新增 E2E：首次引导页出现且错误口令被拒
- [ ] 新增 E2E：管理员创建用户 → 新用户登录 → 两人读同一本书进度互不干扰
- [ ] 新增 E2E：普通用户看不到「用户管理」入口
- [ ] 新增 E2E：品牌标识区不包含 ChatGPT/OpenAI 文案
- [ ] 全量通过（pytest / vitest / Playwright）

## 阶段 8：部署与验证
- [ ] `docker-compose.yml`：去掉 `ACCESS_PASSWORD` 强制项；`.env.example` / README 更新升级说明
- [ ] 本地构建 + 全量测试
- [ ] 部署到 192.168.178.116：验证存量《宠魅》与进度迁移到首个管理员
- [ ] 线上跑全量 E2E；目视核对登录页 / 自动引导 / 用户管理 / 品牌标识
- [ ] 提交推送；`openspec archive user-management`