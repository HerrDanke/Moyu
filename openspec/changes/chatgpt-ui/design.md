# Design: ChatGPT 风格界面改造

## 技术策略

纯前端改造，**后端与 API/SSE 契约零变更**。以 CSS 设计令牌 + 组件重组实现，不引入 UI 库。

## 设计令牌（终稿）

浅色为默认；深色通过 `:root[data-theme="dark"]` 覆盖。正文色单独立令牌，避免与主文字色混用。

| 令牌 | 浅色（默认） | 深色 | 用途 |
|---|---|---|---|
| `--bg-main` | `#ffffff` | `#212121` | 内容区背景 |
| `--bg-sidebar` | `#f9f9f9` | `#171717` | 侧栏背景 |
| `--bg-hover` | `#ececec` | `#2f2f2f` | 悬停 |
| `--bg-active` | `#e3e3e3` | `#383838` | 选中（当前书） |
| `--bg-bubble-user` | `#f4f4f4` | `#333333` | 用户气泡（深色提高对比） |
| `--bg-composer` | `#ffffff` | `#303030` | 输入框 |
| `--border` | `#e5e5e5` | `#383838` | 描边 |
| `--text-primary` | `#0d0d0d` | `#ececec` | 标题/UI 文字 |
| **`--text-body`** | `#1a1a1a` | `#d9d9d9` | **章节正文专用（深色不用纯白）** |
| `--text-secondary` | `#5d5d5d` | `#b0b0b0` | 次级文字 |
| `--accent` | `#0d0d0d` | `#ffffff` | 发送按钮底色 |
| `--on-accent` | `#ffffff` | `#0d0d0d` | 按钮上的文字 |
| **`--caret`** | `#0d0d0d` | `#d9d9d9` | 打字机光标（与正文同系，不用纯白） |
| `--danger` | `#b42318` | `#ff6b5e` | 错误（深色提升对比度） |

**半径刻度**（不再随手写）：`--r-sm: 6px`（按钮/侧栏项）· `--r-md: 10px`（卡片）· `--r-lg: 18px`（消息气泡）· `--r-pill: 28px`（输入框）

**排版**：字体栈 `system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif`；正文 `16px`；侧栏 `14px` / 次级 `12px`。

**对比度目标**：正文/背景 ≥ 7:1；次级文字 ≥ 4.5:1；气泡与背景需肉眼可辨（深色用户气泡由 `#303030` 提到 `#333333`）。

## 阅读列（可在界面上切换）

用户决定「两种都要，给开关」，默认宽松：

| 模式 | 列宽 | 正文 |
|---|---|---|
| **宽松（默认）** | `680px` | `text-indent: 2em`、段间距 `1.2em`、行高 `1.75` |
| 紧凑 | `768px` | 无缩进、段间距 `0.6em`、行高 `1.6` |

开关放侧栏底部设置区，持久化于 localStorage（键 `moyu_reading_mode`）。两种模式下列宽一致变化，避免切换时跳动。

## 组件结构

```
<div class="shell">
  ├── <Sidebar>              （新）
  │     ├── 品牌区「墨鱼」（纯文字 wordmark，不用图形 logo）
  │     ├── 「＋ 导入新书」按钮
  │     ├── 分区标题「我的书架」
  │     ├── 书架列表：书名 + 该书自身进度；当前书高亮；悬停显示删除
  │     └── 底部设置：本章进度 · 阅读宽度 · 快速阅读 · 主题 · 退出
  └── <main class="main">
        ├── 窄屏侧栏开关按钮
        ├── <MessageList>    （改）
        │     ├── 空状态：小标题 + 当前书与进度 + 示例指令 chip
        │     └── 消息：助手纯文本（章节标题单独成块）／用户灰气泡
        │           生成中：三点脉冲（消息流内，助手即将输出处）
        └── <Composer>       （新，替代 ChatInput）
              ├── auto-grow 输入
              ├── 空闲：发送按钮（内嵌右侧）
              └── 生成中：按钮变为「停止」
</div>
```

### 组件改动清单

| 文件 | 动作 |
|---|---|
| `components/Sidebar.tsx` | 新增 |
| `components/Composer.tsx` | 新增（替代 `ChatInput.tsx`） |
| `components/MessageList.tsx` | 修改：去气泡、章节标题层次、三点脉冲、滚动策略 |
| `components/EmptyState.tsx` | 新增：书感知空状态 + 示例指令 chip |
| `components/ChapterProgress.tsx` | 保留，用于侧栏底部 |
| `components/BookSelector.tsx` | 删除（并入 Sidebar） |
| `components/Toolbar.tsx` | 删除（并入 Sidebar） |
| `components/ChatInput.tsx` | 删除（由 Composer 取代） |
| `components/LoginPage.tsx` | 微调对齐令牌 |
| `App.tsx` | 布局重排、侧栏开合、切书清空、阅读模式状态 |
| `styles.css` | 重写为令牌体系 + 新布局 |

## 已确认的交互决策

1. **切书 = 新会话**：点击侧栏另一本书时清空消息区，显示该书的空状态（含进度）。与 ChatGPT「切换历史」语义一致，也顺带让空状态在主路径上可达。
2. **生成中指示**：三点脉冲显示在**消息流内**（助手即将输出的位置）；输入框按钮同时变为「停止」。
3. **阅读列宽度**：界面开关，默认宽松。

## 无障碍（评审补齐的缺口）

- 所有交互元素 `:focus-visible` 明显描边（`2px solid var(--accent)`，`outline-offset: 2px`）
- `@media (prefers-reduced-motion: reduce)`：关闭光标闪烁、三点脉冲、平滑滚动、输入框位移过渡
- 生成中通过视觉隐藏的 `aria-live="polite"` 文案播报「正在生成第 N 章」
- 窄屏抽屉：`role="dialog"` + `aria-modal` + Esc 关闭 + 焦点陷阱，关闭后焦点回到开关按钮
- 开关类控件使用 `aria-pressed`；侧栏开关使用 `aria-expanded`

## 其他落地细节

- **章节标题层次**：利用前端已有的 `bodyStart` 把章节标题渲染为独立块（19px / 600 / 上下留白），正文才有段落感。
- **滚动策略**：流式期间用 `behavior: "auto"`（不用 smooth，避免持续平滑滚动致晕）；仅当用户已在底部时自动跟随，上滚后暂停并显示「回到底部」。
- **打字机光标**：改为 2px 竖条 + `--caret`，去掉原来的 8×15 实心方块。
- **空状态不写空话**：不出现「你好，我是你的阅读助手」这类文案，改为当前书名 + 进度 + 可点击的示例指令 chip（`下一章` / `上一章` / `跳到第 12 章`）。
- **侧栏长数字**：`第 N / 1807 章` 用 `white-space: nowrap` + 次级字号，避免折行。
- **进度文案**：改为「第 N / M 章 · 本章 X%」，避免与整书进度混淆；`<1%` 显示为 `<1%` 而非 `0%`。

## 可测试性

新增稳定 `data-testid`，并**保留语义类名**（`.msg` / `.msg.user` / `.msg.assistant`）：

`sidebar` · `sidebar-toggle` · `import-button` · `book-list` · `book-item-{id}` ·
`composer-input` · `send-button` · `stop-button` · `message-user` · `message-assistant` ·
`empty-state` · `sidebar-progress` · `theme-toggle` · `quick-read-toggle` · `reading-mode-toggle` · `logout-button`

> 注意：既有 E2E 依赖 `.chapter-progress` 类与正则 `/已完成\s*(\d+)%/`、以及输入框 placeholder 含「下一章」。文案调整必须**同一提交内**同步更新这些断言。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 改造打断既有 E2E 选择器 | 迁移到 `data-testid`，与选择器改动同一提交完成 |
| 去气泡后长文糊成一片 | 章节标题用 `bodyStart` 分块 + 宽松模式 2em 缩进 + 段间距 > 行距 |
| 深色下用户气泡看不见 | 气泡提到 `#333333`，必要时加发丝描边 |
| 主题切换首屏闪烁 | `index.html` 内联脚本在 CSS 前设置 `data-theme` |
| 移动端键盘遮挡输入框 | 用 `100dvh`，输入框始终在可视区 |
| 18 本书以上的侧栏滚动 | 书架区独立滚动（`overflow-y:auto`），设置区固定在底部 |

## 不做的事

- 不引入 Tailwind/Radix 等依赖，不做动画库（三点脉冲纯 CSS）
- 不加头像（助手无头像、用户无字母圈），这正是 ChatGPT 的做法
- 不使用任何渐变、光晕、AI 星芒等装饰
- 不出现 OpenAI/ChatGPT 的品牌名与 logo，品牌仍为「墨鱼」
- 不改后端与 SSE 协议