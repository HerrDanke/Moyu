# ui-shell

## ADDED Requirements

### Requirement: 身份与账号界面
**ID:** ui-shell.identity

界面需要表达「当前是谁在用」，并提供账号相关入口。

#### Scenario: 登录页为用户名 + 密码
- Given 库中已存在用户且未登录
- Then 登录页包含用户名与密码两个输入框，以及明确的错误提示位

#### Scenario: 首次运行引导页
- Given 库中没有任何用户
- Then 展示「创建管理员」引导页，包含用户名、密码、引导口令三项
- Then 提示引导口令可在服务端启动日志中找到

#### Scenario: 侧栏用户区
- Given 已登录
- Then 侧栏底部显示当前用户名与其身份（管理员 / 普通用户）
- Then 提供「退出登录」入口

#### Scenario: 管理员专属入口
- Given 当前用户是管理员
- Then 侧栏显示「用户管理」入口
- Given 当前用户是普通用户
- Then 不显示该入口

#### Scenario: 用户管理对话框的可操作性
- Given 以管理员身份打开用户管理
- Then 可在弹窗内查看用户列表、创建用户、重置密码、切换管理员、删除用户
- Then 弹窗支持 Esc 关闭并把焦点收回到触发按钮
- Then 危险操作（删除用户）需要二次确认

### Requirement: 品牌标识
**ID:** ui-shell.branding

左上角展示项目自身的标识与名称，视觉语言保持克制。

#### Scenario: 显示自研标识
- Given 打开应用
- Then 左上角显示一个原创的极简几何标记，配项目自有名称「墨鱼」
- Then 标记为单色、无渐变，并随主题自动适配颜色

#### Scenario: 不出现第三方品牌元素
- Given 任意界面状态
- Then 不出现 OpenAI / ChatGPT 的名称、logo 或仿冒图形
- Then 不暗示本应用与 OpenAI 存在任何关联

#### Scenario: 窄屏下的标识表现
- Given 视口宽度小于 768px 且侧栏收起
- Then 标识不遮挡内容列，侧栏展开按钮仍然可点