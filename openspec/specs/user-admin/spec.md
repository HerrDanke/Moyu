# user-admin Specification

## Purpose
管理员维护账号：创建用户、重置密码、启停账号，以及删除用户时一并清理其阅读进度。

## Requirements

### Requirement: 管理员用户管理
**ID:** user-admin.management

仅管理员可以管理账号；不提供开放注册。普通用户完全看不到也无法调用这些能力。

#### Scenario: 非管理员被拒
- Given 我是普通用户
- When 我请求任一 `/api/users` 接口
- Then 返回 403，且前端不显示用户管理入口

#### Scenario: 查看用户列表
- Given 我是管理员
- When 打开用户管理
- Then 返回全部用户（用户名、是否管理员、是否启用、创建时间），不含密码哈希

#### Scenario: 创建用户
- Given 我是管理员
- When 提交新用户名与密码
- Then 创建成功且该用户可立即登录
- When 提交已存在的用户名
- Then 返回 409 并提示用户名已被占用

#### Scenario: 重置密码
- Given 我是管理员
- When 为某用户设置新密码
- Then 该用户旧密码失效、新密码可登录

#### Scenario: 授予或取消管理员
- Given 我是管理员且系统中存在多名管理员
- When 取消某人的管理员身份
- Then 该用户不再是管理员

#### Scenario: 不能移除最后一个管理员
- Given 系统中只有一个启用的管理员
- When 尝试取消其管理员身份、停用它、或删除该账号
- Then 全部被拒绝，避免系统失去管理员

#### Scenario: 管理员不能自我锁死
- Given 我是当前唯一的管理员
- When 我尝试停用自己或取消自己的管理员身份
- Then 被拒绝；我仍然可以正常使用系统

#### Scenario: 字段白名单
- When 提交用户更新请求
- Then 只接受白名单字段（密码、管理员标记、启用状态），其余字段被忽略
- Then 普通用户无法通过任何接口修改自己的 `is_admin`

#### Scenario: 删除用户
- Given 我是管理员
- When 删除某普通用户
- Then 该用户被删除、其阅读进度一并清除；书籍库不受影响
- Then 我不能删除自己

#### Scenario: 用户名格式约束
- When 提交的用户名包含空格或特殊字符，或长度不在 3–32 之间
- Then 拒绝创建并给出格式说明
