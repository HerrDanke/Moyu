# books Specification

## Purpose
书库：列出与选择书籍、按章节标题搜索，以及（仅管理员）删除书籍并清理其连带数据。

## Requirements

### Requirement: 书单与书目管理
**ID:** books.management

书库为**全体登录用户共享**：任何用户导入的书，其他用户都能看到并阅读。书不按用户隔离，只有阅读进度按用户隔离。删除书籍需要管理员权限。

#### Scenario: 列出书单
- When 调用 `GET /api/books`
- Then 返回全部书籍（不区分导入者）：id、title、total_chapters、source_filename、created_at、导入者显示名
- Then 任一登录用户看到的是同一份书单

#### Scenario: 查看书籍详情与章节目录
- When 调用 `GET /api/books/{id}` 与 `GET /api/books/{id}/chapters`
- Then 返回单书详情与章节列表（index_no、title、char_count）

#### Scenario: 记录导入者
- Given 用户 A 导入了一本书
- Then 该书记录的导入者为 A（仅作展示，不影响其他用户能否阅读）

#### Scenario: 删除书籍并级联清理
- Given 我是普通用户
- When 调用 `DELETE /api/books/{id}`
- Then 返回 403；前端不提供删除入口
- Given 我是管理员
- When 调用 `DELETE /api/books/{id}`
- Then 删除该书及其全部章节
- Then 所有用户在该书上的进度一并清除（含其他用户）

#### Scenario: 选定当前书是用户级操作
- When 用户调用 `POST /api/books/{id}/select`
- Then 只改变**该用户自己**的当前书，不影响其他用户

### Requirement: 章节搜索
**ID:** books.search

按关键词在书籍章节标题中检索命中章节。

#### Scenario: 按标题关键词搜索
- Given 指定 `book_id`（或使用当前用户自己的当前书）
- When 调用 `GET /api/search?q=关键词&book_id=`
- Then 返回标题命中的章节列表
- Then 使用 SQLite `LIKE` 匹配，个人库量级满足使用

#### Scenario: 关键词必须参数化绑定
- Given 用户输入任意关键词（含 `%`、`_`、引号等）
- When 执行搜索
- Then 关键词仅以绑定参数传入（禁止 f-string 拼接 SQL），无注入面
- Then 无命中时返回空列表而非报错

#### Scenario: 未指定 book_id 时使用本人当前书
- Given 未传 `book_id`
- Then 使用当前登录用户自己的「当前书」作为搜索范围
