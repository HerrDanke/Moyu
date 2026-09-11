# auth

## ADDED Requirements

### Requirement: 访问密码保护
**ID:** auth.password-gate

通过一个环境变量配置的访问密码保护整个应用，防止部署到公网后被陌生人访问；不做注册、角色与多用户体系。

#### Scenario: 未登录访问被拦截
- Given 服务已启动且配置了 `ACCESS_PASSWORD`
- When 未携带有效 Session 请求任意 `/api/*`（除 `/api/auth/login`）
- Then 返回 401，前端跳转到登录页

#### Scenario: 密码正确则放行
- When 在登录页输入正确密码调用 `POST /api/auth/login`
- Then 下发 Session Cookie，后续请求放行

#### Scenario: 密码错误被拒
- When 输入错误密码
- Then 返回 401 且不下发 Session，前端提示「密码错误」