# Tasks: ChatGPT 风格界面改造

## 阶段 0：准备
- [ ] 确认后端零改动（不触碰 `backend/`）
- [ ] `index.html` 内联脚本：CSS 之前读取 localStorage 设置 `data-theme`（消除首屏闪烁）

## 阶段 1：设计令牌与样式骨架
- [ ] 重写 `frontend/src/styles.css` 为令牌体系（终稿见 design.md，含 `--text-body` / `--caret` / `--on-accent` / `--danger`）
- [ ] 落地半径刻度 `--r-sm/md/lg/pill`，替换随手写的圆角
- [ ] `.shell` 两栏布局 + 窄屏媒体查询（<768 抽屉；≤1024 可用收窄侧栏）
- [ ] 阅读列：宽松(680px + 2em 缩进) / 紧凑(768px) 两套变量
- [ ] 删除旧样式（顶部横条、book-bar、旧输入框）

## 阶段 2：组件新增与重组
- [ ] 新增 `components/Sidebar.tsx`：品牌区 / 导入新书 / 「我的书架」列表（含每书进度、当前高亮、悬停删除）/ 底部设置区
- [ ] 新增 `components/Composer.tsx`：auto-grow 输入 + 发送/停止按钮
- [ ] 新增 `components/EmptyState.tsx`：书名与进度 + 示例指令 chip
- [ ] 改造 `components/MessageList.tsx`：助手去气泡、用 `bodyStart` 把章节标题渲染成标题块、三点脉冲、滚动策略（instant + 底部吸附 + 「回到底部」）
- [ ] `components/ChapterProgress.tsx` 用于侧栏底部，文案改「第 N / M 章 · 本章 X%」（<1% 显示 `<1%`）
- [ ] 微调 `components/LoginPage.tsx` 对齐新令牌
- [ ] 删除 `BookSelector.tsx` / `Toolbar.tsx` / `ChatInput.tsx`
- [ ] 改造 `App.tsx`：布局重排、侧栏开合、**切书清空消息**、阅读模式状态

## 阶段 3：布局与交互行为
- [ ] 空状态：输入框垂直居中；发出首条消息后落底（snap，不做位置动画，宽度不变）
- [ ] 窄屏抽屉：遮罩 + Esc 关闭 + 焦点陷阱 + 关闭后焦点回到开关 + 选中后自动收起
- [ ] 生成中：三点脉冲在消息流内；输入框按钮变「停止」
- [ ] 用 `100dvh` 保证移动端输入框不被键盘遮挡
- [ ] 侧栏书架区独立滚动，设置区固定底部；长数字 `nowrap`

## 阶段 4：主题与阅读设置
- [ ] 默认浅色（无本地记录）
- [ ] 深色切换写入 localStorage 并即时生效
- [ ] 阅读宽度开关（宽松默认）持久化于 `moyu_reading_mode`
- [ ] 深色正文用 `--text-body`（`#d9d9d9`），光标用 `--caret`

## 阶段 5：无障碍
- [ ] 全部可聚焦元素 `:focus-visible` 描边
- [ ] `@media (prefers-reduced-motion: reduce)` 关闭光标闪烁/三点脉冲/平滑滚动/位置过渡
- [ ] 生成中加 `aria-live="polite"` 视觉隐藏播报
- [ ] 开关类控件 `aria-pressed`；侧栏开关 `aria-expanded`；抽屉 `role="dialog"` + `aria-modal`
- [ ] 对比度自查：正文/背景 ≥7:1，次级 ≥4.5:1，深色气泡可辨

## 阶段 6：可测试性迁移（与选择器改动同一提交）
- [ ] 为交互元素补齐 `data-testid`（sidebar / sidebar-toggle / import-button / book-item-{id} / composer-input / send-button / stop-button / message-user / empty-state / sidebar-progress / theme-toggle / quick-read-toggle / reading-mode-toggle / logout-button）
- [ ] 保留语义类名 `.msg` / `.msg.user` / `.msg.assistant`
- [ ] 同步更新既有 3 个 E2E（`.chapter-progress` 与 `/已完成\s*(\d+)%/` 正则、placeholder 仍含「下一章」）

## 阶段 7：测试
- [ ] 新增 E2E：空状态 → 发送后输入框落底
- [ ] 新增 E2E：切书清空消息并显示该书空状态
- [ ] 新增 E2E：窄屏抽屉可开合、Esc 关闭
- [ ] 新增 E2E：深浅主题切换 + 刷新保持
- [ ] 新增 E2E：阅读宽度切换 + 刷新保持
- [ ] 全量通过（pytest 67 / vitest / Playwright）

## 阶段 8：部署与验证
- [ ] 本地 `npm run build` 通过
- [ ] 部署到 192.168.178.116 并核对 bundle 变更
- [ ] 对线上跑全量 E2E
- [ ] 目视核对：首屏结构、空状态、消息样式、深色模式、窄屏抽屉
- [ ] 提交并推送；`openspec archive chatgpt-ui`