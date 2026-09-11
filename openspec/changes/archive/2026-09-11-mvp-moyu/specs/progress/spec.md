# progress

## ADDED Requirements

### Requirement: 阅读进度持久化
**ID:** progress.persist

为每本书记录当前阅读章节与章节内断点，刷新或重新打开后不丢失阅读位置。

#### Scenario: 阅读指令推进进度
- Given 用户通过 next/prev/goto 或「读《xx》」读完某章
- Then 该书 `progress.chapter_index` 更新为最新章节 `index_no`（在流式推送结束后写入）

#### Scenario: 断句续读
- Given 用户在章节内读到某一句后离开
- Then 记录 `chapter_offset`（章节内字符偏移）
- When 再次打开该书
- Then 从该断点继续渲染，并展示进度百分比

#### Scenario: 多标签页并发写进度
- Given 两个标签页同时对同一本书推进章节
- Then 使用条件更新（`WHERE chapter_index = 旧值`）避免丢失推进

#### Scenario: 读取进度
- When 调用 `GET /api/progress/{book_id}`
- Then 返回该书最新进度 `{book_id, chapter_index, chapter_offset, updated_at}`

#### Scenario: 首次阅读默认第一章
- Given 某书无进度记录
- When 用户请求阅读
- Then 默认从 `index_no = 1`（第一章）开始

#### Scenario: 空进度引导
- Given 用户请求阅读但当前书或进度不存在
- Then 伪 AI 引导「你好，想读哪本书？回复『书单』看看收藏」