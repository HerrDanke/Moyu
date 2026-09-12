# Tasks: 阅读快捷工具条与章节目录

## 阶段 1：工具条骨架
- [ ] 新增 `components/ReadingToolbar.tsx`：下一章 / 上一章 / 目录 / 跳转章节
- [ ] 样式：小号次级按钮、`--r-pill`、悬停态；窄屏横向滚动不换行
- [ ] 放在 composer 上方，与阅读列同宽
- [ ] 生成中禁用「下一章 / 上一章」；「目录 / 跳转」保持可用

## 阶段 2：草稿状态提升
- [ ] `Composer` 改为受控：接收 `draft` 与 `onDraftChange`
- [ ] `App` 持有草稿状态，工具的「跳转」写入草稿并聚焦输入框、光标置尾
- [ ] 发送后清空草稿；确认手输与预填共用同一份状态

## 阶段 3：章节目录抽屉
- [ ] 新增 `components/ChapterDrawer.tsx`（`role="dialog"` + `aria-modal` + Esc + 焦点陷阱 + 焦点回归）
- [ ] 拉取 `GET /api/books/{id}/chapters`，失败与空列表给出明确提示
- [ ] 轻量窗口化：固定行高 32px + 占位撑高 + 只渲染可视窗口 ± 余量
- [ ] 打开时按当前章号定位并高亮（`aria-current`）
- [ ] 搜索框：按标题子串过滤，保留原始 `index_no`
- [ ] 点击章节 → 发送「第 N 章」并关闭抽屉
- [ ] 右侧滑出，宽 `min(360px, 88vw)`

## 阶段 4：空状态精简
- [ ] `EmptyState` 去掉全部 chip，改为书名 + 进度 + 一句引导

## 阶段 5：可测试性
- [ ] 补齐 `data-testid`：`reading-toolbar` / `toolbar-prev` / `toolbar-next` / `toolbar-toc` / `toolbar-jump` / `toc-drawer` / `toc-search` / `toc-close` / `toc-item-{index}`
- [ ] 更新既有 E2E：「空状态」用例改为点工具条的「下一章」

## 阶段 6：测试
- [ ] 新增 E2E：点「下一章」推进章节；生成中按钮禁用
- [ ] 新增 E2E：点「跳转」预填「第 」且不发请求
- [ ] 新增 E2E：目录打开、定位当前章、搜索过滤后跳转章号正确
- [ ] 新增 E2E：目录在 1807 章下 DOM 行数远小于总章数（窗口化生效）
- [ ] 全量通过（pytest / vitest / Playwright）

## 阶段 7：部署与验证
- [ ] 本地构建 + 全量测试
- [ ] 部署到 192.168.178.116，对线上跑全量 E2E
- [ ] 目视核对：工具条、目录抽屉、跳转预填、窄屏滚动
- [ ] 提交推送；`openspec archive chapter-navigation`