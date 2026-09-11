# progress

## ADDED Requirements

### Requirement: 阅读进度持久化
**ID:** progress.persist

为每本书记录当前阅读章节，刷新或重新打开后不丢失阅读位置。

#### Scenario: 阅读指令推进进度
- Given 用户通过 next/prev/goto 或「读《xx》」读完某章
- Then 该书 `progress.chapter_index` 更新为最新章节 `index_no`

#### Scenario: 读取进度
- When 调用 `GET /api/progress/{book_id}`
- Then 返回该书最新进度 `{book_id, chapter_index, updated_at}`

#### Scenario: 首次阅读默认第一章
- Given 某书无进度记录
- When 用户请求阅读
- Then 默认从 `index_no = 1`（第一章）开始

#### Scenario: 空进度引导
- Given 用户请求阅读但当前书或进度不存在
- Then 伪 AI 引导「你好，想读哪本书？回复『书单』看看收藏」