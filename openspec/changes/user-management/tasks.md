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
- [ ] `security.py`：Session 载荷改为携带 `user_id`（含签发/解析）
- [ ] `deps.py`：`get_current_user`（查库校验存在且启用）、`require_admin`
- [ ] `router/auth.py`：`login(username,password)` / `logout` / `me` / `status(setup_required)`
- [ ] 登录失败限速（同用户名 5 次 / 60 秒，内存计数）
- [ ] pytest：登录成功/失败、停用用户被拒、Cookie 无 user_id 被拒、限速生效

## 阶段 3：首次运行引导
- [ ] 启动时若无用户则生成一次性引导口令并打印到日志
- [ ] `POST /api/auth/setup`：校验引导口令 + 无用户 + 密码长度 ≥8 + 用户名格式
- [ ] 创建成功后：回填 `progress_legacy` 到该管理员、迁移 `settings.current_book`、作废口令、关闭接口
- [ ] pytest：口令错误被拒、成功后接口关闭、老数据归属管理员

## 阶段 4：用户管理 API
- [ ] `router/users.py`：列表 / 创建 / 改名（可选）/ 重置密码 / 切换管理员 / 停用 / 删除
- [ ] 保护规则：不能删除自己；不能移除最后一个管理员；用户名唯一（409）
- [ ] pytest：非管理员 403、重名 409、最后管理员保护、删除用户清进度

## 阶段 5：进度与书籍按用户隔离
- [ ] `services/store.py`：`get_current_book` / `write_progress` 全部带 `user_id`
- [ ] `router/progress.py`：读写当前用户进度
- [ ] `router/chat.py`：进度与当前书绑定当前用户
- [ ] `router/books.py`：书单共享 + 返回导入者名；删除书需管理员并清所有用户进度；select 只改本人
- [ ] `services/chat_engine.py`：当前书取本人
- [ ] pytest：两用户同书进度互不影响；A 的当前书不影响 B

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