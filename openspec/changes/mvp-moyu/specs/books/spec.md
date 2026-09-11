# books

## ADDED Requirements

### Requirement: 书单与书目管理
**ID:** books.management

管理已导入的小说书目，包括书单、书籍详情、章节目录、删除书籍。

#### Scenario: 列出书单
- When 调用 `GET /api/books`
- Then 返回所有书籍的 id、title、total_chapters、source_filename、created_at

#### Scenario: 查看书籍详情与章节目录
- When 调用 `GET /api/books/{id}` 与 `GET /api/books/{id}/chapters`
- Then 返回单书详情与章节列表（index_no、title、char_count）

#### Scenario: 删除书籍并级联清理
- When 调用 `DELETE /api/books/{id}`
- Then 删除该书及其全部 `chapters` 与 `progress`，无孤儿数据
- Then 前端在删除前二次确认

### Requirement: 章节搜索
**ID:** books.search

按关键词在书籍章节标题中检索命中章节。

#### Scenario: 按标题关键词搜索
- Given 指定 `book_id`（或使用当前书）
- When 调用 `GET /api/search?q=关键词&book_id=`
- Then 返回标题命中的章节列表
- Then 使用 SQLite `LIKE` 匹配，个人库量级满足使用