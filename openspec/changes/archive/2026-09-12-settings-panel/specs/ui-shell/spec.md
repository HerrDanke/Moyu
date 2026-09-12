# ui-shell

## ADDED Requirements

### Requirement: 设置面板
**ID:** ui-shell.settings-panel

侧栏底部提供统一的设置入口；原先散落在侧栏的开关收纳进面板，侧栏恢复简洁。

#### Scenario: 打开与关闭设置
- Given 已登录
- Then 侧栏底部显示「设置」按钮
- When 点击它
- Then 打开设置面板（对话框语义）
- Then 按 Esc 或点击遮罩可关闭，关闭后焦点回到「设置」按钮

#### Scenario: 侧栏精简
- Given 打开应用
- Then 侧栏底部不再直接出现 主题 / 阅读宽度 / 快速阅读 / 退出登录 这些开关
- Then 侧栏保留：书架、导入新书、当前书进度、设置入口、用户区
- Then 管理员仍能从侧栏进入「用户管理」

#### Scenario: 面板内可完成原有操作
- Given 设置面板已打开
- Then 面板内包含 深色主题、宽松排版、快速阅读 三个开关，行为与之前完全一致
- Then 面板内包含「退出登录」，点击后回到登录页

#### Scenario: 窄屏下可用
- Given 视口宽度小于 768px
- Then 设置入口位于抽屉式侧栏内，打开面板后内容不溢出、可滚动

### Requirement: 思考强度控制
**ID:** ui-shell.thinking-intensity

以「AI 思考强度」的叙事提供文字生成速度控制，贴合产品「伪装成大模型」的定位。

#### Scenario: 四档滑杆
- Given 设置面板已打开
- Then 显示一个四档的「思考强度」滑杆，并标注当前档位名称
- Then 档位为：迅捷 / 标准 / 深入 / 沉思
- Then 说明文案表明它影响正文逐字出现的节奏

#### Scenario: 调整即时生效
- Given 我把思考强度从「标准」调到「沉思」
- When 我发起下一次阅读
- Then 正文逐字出现的节奏明显变慢
- When 我调到「迅捷」
- Then 节奏明显变快

#### Scenario: 按用户保存
- Given 我把思考强度设为「深入」
- When 刷新页面或换一个浏览器登录同一账号
- Then 设置面板中的档位仍为「深入」，且阅读节奏随之生效

#### Scenario: 未设置时回落到服务端默认
- Given 我从未调整过思考强度
- Then 使用服务端环境变量 `TYPING_SPEED` 作为默认节奏

#### Scenario: 非法值被拒绝
- Given 有人直接调用设置接口
- When 提交超出允许范围的速度值（如 0、负数或极大值）
- Then 返回 400 且不写入