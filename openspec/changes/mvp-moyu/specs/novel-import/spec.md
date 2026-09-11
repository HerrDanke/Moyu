# novel-import

## ADDED Requirements

### Requirement: TXT 小说导入
**ID:** novel-import.import-txt

允许用户上传一个本地 TXT 小说文件，系统解析出章节结构并持久化，供聊天界面按章读取。

#### Scenario: 成功导入有章节分隔的 TXT
- Given 一个含「第 X 章」标题的 TXT 文件
- When 通过 `POST /api/books/import` 上传
- Then 解析出对应章节结构并写入 `chapters` 表，更新 `books.total_chapters`
- Then 返回 `{book_id, title, total_chapters}`

#### Scenario: 无章节分隔的 TXT 兜底分段
- Given 一个不含章节标题的 TXT 文件
- When 上传导入
- Then 按固定字数（默认 3000 字/章）切分
- Then 导入结果提示用户「未识别到章节分隔，已按字数分段」

### Requirement: 章节解析规则
**ID:** novel-import.parse-rules

解析器识别中文章节标题，记录章节正文与字符数。

#### Scenario: 识别常见章节命名
- Given 文件含「第 1 章 / 第 1 回 / 第 1 节 / 第 1 卷 / 第1话」等标题
- When 解析
- Then 每章正文为标题后到下一个标题前的内容，记录 `char_count`
- Then 无标题章节以「第 N 章」补齐

#### Scenario: 解析器可扩展
- Given `BaseReader` 接口已定义
- When 新增一种格式
- Then 实现新的 Reader 即可接入，无需修改调用方