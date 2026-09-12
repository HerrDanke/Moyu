# progress Specification

## Purpose
按用户、按书记录阅读位置（章节号 + 章内字符偏移），并保证刷新、切书、断点续读、多标签页与多用户之间互不干扰。

## Requirements

### Requirement: 阅读进度持久化
**ID:** progress.persist

为**每个用户、每本书**分别记录当前阅读章节与章节内断点。进度以 `(user_id, book_id)` 为主键，互不干扰；刷新或重新打开后不丢失阅读位置。

#### Scenario: 阅读指令推进进度
- Given 用户通过 next/prev/goto 或「读《xx》」读完某章
- Then 该用户在该书上的 `progress.chapter_index` 更新为最新章节 `index_no`（在流式推送结束后写入）

#### Scenario: 断句续读
- Given 用户在章节内读到某一句后离开
- Then 记录 `chapter_offset`（章节内字符偏移）
- When 再次打开该书
- Then 从该断点继续渲染，并展示进度百分比

#### Scenario: 偏移上报必须与章号一起提交
- Given 前端打字机在逐字渲染时按秒节流上报阅读位置
- When 调用 `PATCH /api/progress/{book_id}`
- Then 请求体必须**同时**携带 `chapter_index` 与 `chapter_offset`
- Then 只给偏移时，服务端会沿用库里的旧章号（服务端只在本章流正常结束后才写新章号），
  于是中途「停止」会留下「旧章号 + 新偏移」的不一致行，之后按断点续读会跳到错误位置

#### Scenario: 续读本章不推进进度
- Given 用户在第 5 章读到章内偏移 1200
- When 下达「继续本章」
- Then 章号仍为第 5 章，且服务端**不**写回它在请求时刻读到的旧偏移
- Then 章内偏移由前端的实时上报负责更新，避免把用户真正读到的位置回滚

#### Scenario: 多标签页并发写进度
- Given 两个标签页同时对同一本书推进章节
- Then 使用条件更新（`WHERE chapter_index = 旧值`）避免丢失推进

#### Scenario: 读取进度
- When 调用 `GET /api/progress/{book_id}`
- Then 返回**当前登录用户**在该书的进度 `{book_id, chapter_index, chapter_offset, updated_at}`

#### Scenario: 首次阅读默认第一章
- Given 某用户在某书上无进度记录
- When 该用户请求阅读该书
- Then 默认从 `index_no = 1`（第一章）开始

#### Scenario: 不同用户读同一本书互不影响
- Given 用户 A 与用户 B 都能看到同一本书
- When A 读到第 3 章、B 读到第 10 章
- Then 两人的进度各自保存，各自读到自己的章节，互不覆盖

#### Scenario: 当前书按用户隔离
- Given 用户 A 的当前书是《宠魅》，用户 B 的当前书是《凡人修仙传》
- When A 输入「下一章」
- Then 推进的是《宠魅》第 N+1 章，与 B 的当前书无关

#### Scenario: 不得越权读写他人进度
- Given 用户 A 已读《宠魅》到第 5 章，用户 B 从未读过该书
- When B 请求 `GET /api/progress/{宠魅}`、带 `book_id` 的搜索、或不带 `book_id` 的搜索
- Then 只返回 B 自己的进度（该书对 B 表现为未开始），不得返回 A 的第 5 章
- When B 触发一次阅读
- Then 只写入 B 自己的进度行，不覆盖 A 的记录
- Then B 的「当前书」解析不会回退到 A 最近读过的书

#### Scenario: 删除用户清理其进度
- Given 管理员删除了某用户
- Then 该用户的所有进度记录被一并清除，书籍与原文保留

#### Scenario: 空进度引导
- Given 用户请求阅读但当前书或进度不存在
- Then 伪 AI 引导「你好，想读哪本书？回复『书单』看看收藏」
