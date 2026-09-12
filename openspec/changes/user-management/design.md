# Design: 用户管理

## 数据模型

### 新增 `users`

| 列 | 说明 |
|---|---|
| `id` | 主键 |
| `username` | 唯一，3–32 字符，仅字母数字下划线连字符 |
| `password_hash` | `算法$盐hex$派生密钥hex` |
| `is_admin` | 布尔 |
| `is_active` | 布尔（停用后不可登录，但保留其进度数据） |
| `current_book_id` | 该用户当前的「当前书」（可空，FK → books，删除书时置空） |
| `created_at` | 时间戳 |

### 改造 `progress`（由「每书一行」变为「每用户每书一行」）

新的主键为 `(user_id, book_id)`，并新增 `user_id` 外键（级联删除）。
`chapter_index` / `chapter_offset` / `updated_at` 语义不变。

### `books`

新增 `uploaded_by`（可空 FK → users，删除用户时置空）——只作信息展示，**不做可见性隔离**。

### `settings`

保留为全局配置（打字速度、文案模板）。「当前书」从 `settings` 迁到 `users.current_book_id`。

## 密码存储

不引入第三方密码库，使用标准库：

- 首选 `hashlib.scrypt(n=2**14, r=8, p=1, dklen=32)`（内存困难，抗 GPU）
- 若运行环境不支持 scrypt（`ValueError`），回退 `hashlib.pbkdf2_hmac("sha256", ..., 600_000)`
- 每用户独立 16 字节随机盐；校验用 `hmac.compare_digest`
- 存储格式自带算法前缀，未来可平滑升级参数

## 鉴权与会话

- `POST /api/auth/login`：`{username, password}` → 校验通过后写入签名 Cookie
- **Cookie 内容包含 `user_id`**（itsdangerous 签名），每次请求解析出当前用户
- `require_session` → `get_current_user`：解析 Cookie、确认用户存在且 `is_active`
- `require_admin`：在 `get_current_user` 基础上校验 `is_admin`，否则 403
- 用户被删除或停用后，其旧 Cookie 立即失效（每次请求都查库确认用户状态）

## 首次运行引导（防抢注）

问题：若直接开放「创建首个管理员」接口，先访问到的人即可抢占管理员。

方案：**服务启动时若 `users` 表为空，生成一次性引导口令并打印到容器日志**。

- 启动日志形如：`[setup] 未检测到任何用户，请访问 <url>/setup 并使用引导口令：XXXX-XXXX-XXXX`
- `GET /api/auth/status` 返回 `{setup_required: true}`
- `POST /api/auth/setup {username, password, setup_code}`：仅当无用户时可用，且 `setup_code` 必须匹配
- 成功创建首个管理员后，内存中的引导口令作废、接口永久关闭
- 这条口令只出现在服务器日志里，等价于「拥有服务器访问权」这一前提

## 数据迁移（老库升级）

`Base.metadata.create_all` 只能建新表，无法改主键。采用**重命名 + 回填**：

1. 启动时探测 `progress` 表是否已有 `user_id` 列
2. 若无：`ALTER TABLE progress RENAME TO progress_legacy`，随后 `create_all` 建出新结构
3. 首个管理员创建成功后：把 `progress_legacy` 的行回填给该管理员，然后 `DROP TABLE progress_legacy`
4. 把 `settings.current_book` 的值写入该管理员的 `current_book_id`

迁移是幂等的：`progress_legacy` 不存在时跳过。

## API 变更

| 接口 | 变化 |
|---|---|
| `POST /api/auth/login` | 由「密码」改为「用户名 + 密码」 |
| `POST /api/auth/setup` | **新增**：首次创建管理员（需引导口令） |
| `GET /api/auth/status` | 返回 `{setup_required, authenticated, user}` |
| `GET /api/auth/me` | **新增**：当前用户信息 |
| `POST /api/auth/logout` | 不变 |
| `GET /api/users` | **新增**（管理员）：用户列表 |
| `POST /api/users` | **新增**（管理员）：创建用户 |
| `PATCH /api/users/{id}` | **新增**（管理员）：重置密码 / 改管理员 / 停用 |
| `DELETE /api/users/{id}` | **新增**（管理员）：删除用户（保留其进度？→ 级联删除其进度） |
| `GET/PATCH /api/progress/{book_id}` | 改为操作**当前用户**的进度 |
| `POST /api/chat` | 进度读写绑定当前用户；「当前书」取当前用户的 |
| `GET /api/books` | 共享书库，额外返回 `uploaded_by_name` |

环境变量：`ACCESS_PASSWORD` 退役；`docker-compose.yml` 不再强制它，只保留 `SECRET_KEY`。

## 登录防暴力破解

单机自托管场景，做一个轻量防护即可：

- 同一 `username` 连续失败计数（内存字典），失败 5 次后锁定 60 秒
- 不引入 Redis 或额外依赖
- 失败响应统一为「用户名或密码错误」，不区分「用户不存在」与「密码错误」，避免用户名枚举

## 前端

- **登录页**：用户名 + 密码两个字段；错误提示
- **首次引导页**（`setup_required` 时）：用户名 + 密码 + 引导口令
- **侧栏底部用户区**：显示当前用户名与身份；管理员多一个「用户管理」入口；退出登录
- **用户管理对话框**（仅管理员）：用户列表（用户名 / 角色 / 创建时间）、新建用户、重置密码、删除、切换管理员；用原生 `role="dialog"` + Esc 关闭 + 焦点陷阱（复用侧栏抽屉已有的键盘处理模式）
- 非管理员看不到入口；后端同样强制校验（前端隐藏不算安全措施）

## 品牌标识（自研）

左上角替换为：

- **原创几何标记**：单色、无渐变的极简「墨滴 + 鱼尾」造型，用 `currentColor` 描边，随主题自适应
- **wordmark**：项目自有名称「墨鱼」
- 明确**不使用** OpenAI / ChatGPT 的名称、logo 或任何仿冒图形；视觉语言（克制、单色、无衬线）可以对齐

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 迁移把老进度弄丢 | 先重命名再回填、回填成功才删旧表；迁移逻辑幂等；有单测覆盖 |
| 首个管理员被抢注 | 引导口令只出现在服务器日志 |
| 用户误删自己导致无管理员 | 禁止删除最后一个管理员；禁止取消最后一个管理员的管理员身份 |
| 旧 Cookie 在用户删除后仍可用 | 每次请求查库校验用户存在且启用 |
| 破坏既有部署 | compose 去掉 ACCESS_PASSWORD 强制项；README 更新升级步骤 |
| E2E 全部依赖登录流程 | 提供测试辅助：每个用例通过 `/api/auth/setup` 或管理员建号完成登录 |

## 不做的事

- 不做会话持久化列表与「登出其他设备」
- 不做密码复杂度校验之外的强度策略（长度下限 8 位）
- 不做用户头像与个人资料页
