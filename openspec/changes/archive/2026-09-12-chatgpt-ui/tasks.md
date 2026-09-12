# Tasks: ChatGPT 风格界面改造

## 阶段 0：准备
- [x] 确认后端零改动（除流式段落 bug 修复外未触碰业务逻辑）
- [x] `index.html` 内联脚本：CSS 之前读取 localStorage 设置 `data-theme` / `data-reading`（消除首屏闪烁）

## 阶段 1：设计令牌与样式骨架
- [x] 重写 `frontend/src/styles.css` 为令牌体系（含 `--text-body` / `--caret` / `--on-accent` / `--danger`）
- [x] 落地半径刻度 `--r-sm/md/lg/pill`
- [x] `.shell` 两栏布局 + 窄屏媒体查询（<768 抽屉）
- [x] 阅读列：宽松(680px + 2em 缩进) / 紧凑(768px) 两套变量
- [x] 删除旧样式（顶部横条、book-bar、旧输入框）

## 阶段 2：组件新增与重组
- [x] 新增 `components/Sidebar.tsx`（品牌 / 导入 / 我的书架（含每书进度）/ 底部设置区）
- [x] 新增 `components/Composer.tsx`（auto-grow + 发送/停止）
- [x] 新增 `components/EmptyState.tsx`（书名与进度 + 示例指令 chip）
- [x] 改造 `components/MessageList.tsx`（去气泡、章节标题成块、三点脉冲、滚动策略）
- [x] 进度文案改为「第 N / M 章 · 本章 X%」（<1% 特殊显示），迁移至 `utils/progress.ts`
- [x] 微调 `components/LoginPage.tsx` 对齐新令牌
- [x] 删除 `BookSelector.tsx` / `Toolbar.tsx` / `ChatInput.tsx` / `ChapterProgress.tsx`
- [x] 改造 `App.tsx`（两栏布局、侧栏开合、切书清空、阅读模式状态）

## 阶段 3：布局与交互行为
- [x] 空状态输入框垂直居中；发出首条消息后落底（无位置动画、宽度不变）
- [x] 窄屏抽屉：遮罩 + Esc 关闭 + 焦点陷阱 + 选中后自动收起
- [x] 生成中：三点脉冲在消息流内；输入框按钮变「停止」
- [x] `100dvh` 保证移动端输入框不被键盘遮挡
- [x] 侧栏书架区独立滚动、设置区固定底部、长数字 nowrap

## 阶段 4：主题与阅读设置
- [x] 默认浅色（无本地记录）
- [x] 深色切换写入 localStorage 并即时生效
- [x] 阅读宽度开关（宽松默认）持久化于 `moyu_reading_mode`
- [x] 深色正文用 `--text-body`（`#d9d9d9`），光标用 `--caret`

## 阶段 5：无障碍
- [x] 全部可聚焦元素 `:focus-visible` 描边
- [x] `prefers-reduced-motion` 关闭光标闪烁/三点脉冲/过渡
- [x] 生成中加 `aria-live="polite"` 视觉隐藏播报
- [x] 开关类控件 `aria-pressed`；侧栏开关 `aria-expanded`；抽屉 `role="dialog"` + `aria-modal`
- [x] 对比度：正文/背景 ≥7:1，深色用户气泡提高到 `#333333`

## 阶段 6：可测试性迁移（与选择器改动同一提交）
- [x] 为交互元素补齐 `data-testid`
- [x] 保留语义类名 `.msg` / `.msg.user` / `.msg.assistant`
- [x] 同步更新既有 E2E（进度正则改为「本章 X%」、选择器改 testid）

## 阶段 7：测试
- [x] 新增 E2E：空状态 → 点示例指令 → 输入框落底
- [x] 新增 E2E：切书清空消息并显示该书空状态
- [x] 新增 E2E：窄屏抽屉可开合、Esc 关闭
- [x] 新增 E2E：深浅主题切换 + 刷新保持
- [x] 新增 E2E：阅读宽度切换 + 刷新保持
- [x] 新增 E2E：助手无气泡 / 用户有气泡
- [x] 全量通过（pytest 69 / vitest 7 / Playwright 9）

## 阶段 8：部署与验证
- [x] 本地 `npm run build` 通过
- [x] 部署到 192.168.178.116 并核对 bundle 变更
- [x] 对线上跑全量 E2E（9/9）
- [x] 目视核对：首屏结构、空状态、消息样式、深色模式、窄屏抽屉
- [x] 提交并推送；`openspec archive chatgpt-ui`

## 过程中额外发现并修复的缺陷
- [x] 导入新书后未同步服务端「当前书」→ 「下一章」读到上一本（E2E 捕获）
- [x] 流式断句用 `strip()` 过滤空片段，吞掉段落换行 → 长章节被糊成一整段（后端，长期存在；由真实浏览器核对发现）