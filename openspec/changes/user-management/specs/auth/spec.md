# auth

## REMOVED Requirements

### Requirement: 访问密码保护
**ID:** auth.password-gate

（移除原因：单一共享访问密码无法区分身份，已由「账号登录」取代。环境变量 `ACCESS_PASSWORD` 随之退役。）

## ADDED Requirements

### Requirement: 账号登录
**ID:** auth.account-login

使用用户名 + 密码的账号体系取代共享访问密码。密码以标准 KDF 加盐哈希存储，绝不保存明文。

#### Scenario: 未登录访问被拦截
- Given 服务已启动且已存在用户
- When 未携带有效 Session 请求任意 `/api/*`（`/api/auth/login`、`/api/auth/status`、`/api/auth/setup` 除外）
- Then 返回 401，前端跳转到登录页

#### Scenario: 凭据正确则放行
- When 在登录页提交正确的用户名与密码
- Then 下发签名 Session Cookie（内含 user_id），后续请求以该用户身份放行

#### Scenario: 凭据错误被拒且不泄露账号是否存在
- When 提交不存在的用户名，或存在但密码错误
- Then 一律返回 401 且提示「用户名或密码错误」，两种情况响应无差异

#### Scenario: 停用或删除的用户立即失效
- Given 某用户已登录
- When 管理员将其停用或删除
- Then 该用户携带原 Cookie 的后续请求返回 401

#### Scenario: 会话可被吊销
- Given 用户 U 已登录并持有有效 Cookie
- When 管理员重置 U 的密码，或 U 自己修改密码
- Then U 原有的 Cookie 在下一次请求即返回 401，必须重新登录

#### Scenario: 旧版 Cookie 一律无效
- Given 存在升级前下发的、不携带 user_id 的旧 Cookie
- When 携带它请求任意 `/api/*`
- Then 返回 401

#### Scenario: 不安全密钥拒绝启动
- Given 系统中存在任意用户
- When `SECRET_KEY` 为空或属于已知弱值/默认值
- Then 应用拒绝启动并给出明确原因
（说明：`ACCESS_PASSWORD` 退役后，原有的密钥守卫条件会失效，必须改为与账号体系绑定，否则可用默认密钥自签 Cookie 绕过鉴权。）

#### Scenario: 未初始化期间不暴露任何数据
- Given 数据库中还没有任何用户（`setup_required` 为真）
- When 请求除 `/api/auth/login`、`/api/auth/status`、`/api/auth/setup` 之外的任意 `/api/*`
- Then 返回 401，不得返回书库、章节、进度或搜索内容

#### Scenario: 密码不以明文存储
- Given 任意用户
- Then 数据库中只保存「算法$盐$派生密钥」形式的哈希，不存在明文或可逆编码

#### Scenario: 哈希计算有并发上限
- Given 同时发起大量登录/建号/改密请求
- When 并发超过设定阈值
- Then 超出部分排队而非并行执行 KDF，服务不因内存或 CPU 被占满而不可用
- Then 长度超过上限的密码在请求校验阶段即被拒绝

#### Scenario: 登录失败限速且不锁定真实用户
- Given 同一来源对同一用户名连续失败多次
- Then 该键进入退避（递增延迟）而非硬锁，不影响其他用户名的正常登录

### Requirement: 首次运行引导
**ID:** auth.first-run-setup

全新部署且库中无任何用户时，引导创建第一个管理员；该引导必须只能被拥有服务器访问权的人完成，避免被抢先注册。

#### Scenario: 无用户时进入引导
- Given 数据库中没有任何用户
- When 访问应用
- Then 前端展示「创建管理员」引导页，而不是普通登录页

#### Scenario: 引导需要一次性口令
- Given 服务启动时库中无用户
- Then 启动日志中打印一次性引导口令，且该口令由密码学安全随机源生成、有足够长度
- When 提交引导表单但口令不匹配
- Then 返回 401，且**先校验口令再执行任何密码哈希计算**
- Then `/api/auth/status` 的响应体中不包含该口令

#### Scenario: 引导接口受限速约束
- Given 库中无用户
- When 对引导接口短时间内连续提交错误口令
- Then 触发与登录一致的限速/退避，避免口令被暴力枚举

#### Scenario: 引导成功后永久关闭
- Given 已通过引导创建了首个管理员
- When 再次调用创建引导接口
- Then 返回 400/409，不再允许创建

#### Scenario: 首个管理员继承既有数据
- Given 升级前已存在书籍与阅读进度
- When 首个管理员创建成功
- Then 既有书籍与其阅读进度归属该管理员，原「当前书」成为该用户的当前书

#### Scenario: 密码强度下限
- When 提交的新密码短于 8 位
- Then 拒绝创建并提示密码长度要求