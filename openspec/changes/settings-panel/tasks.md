# Tasks: 设置面板与「思考强度」

## 阶段 1：数据层与 API
- [ ] `models.py`：新增 `UserSetting(user_id, key, value)`，主键 `(user_id, key)`，FK 级联删除
- [ ] `services/store.py`：`get_user_setting` / `set_user_setting`
- [ ] `services/user_settings.py`：档位定义与映射（1..4 ↔ 速度倍率）、范围校验（0.1~10）
- [ ] `router/settings.py`：`GET /api/settings`、`PATCH /api/settings`（白名单 + 校验，越界 400）
- [ ] `main.py` 注册路由
- [ ] pytest：默认值回落、按用户隔离、非法值 400、档位映射

## 阶段 2：节奏接入
- [ ] `router/chat.py`：用当前用户的 `typing_speed` 覆盖 `settings.typing_speed`（`dataclasses.replace`）
- [ ] 保持 `typing_speed <= 0` 的既有「不节流」语义不变
- [ ] pytest：设置了速度后，chat 生效；未设置时回落环境变量；进行中的流不受后续改动影响

## 阶段 3：前端设置面板
- [ ] 新增 `components/SettingsDialog.tsx`（`role="dialog"` + `aria-modal` + Esc + 焦点陷阱 + 焦点回归）
- [ ] 内部包含：思考强度滑杆（4 档 + 档位名 + 说明）、深色主题、宽松排版、快速阅读、退出登录
- [ ] `Sidebar`：底部改为 进度 + 「设置」按钮 + 用户区；移除原来的四个开关与退出按钮
- [ ] `App.tsx`：`settingsOpen` 状态；拉取/保存用户设置；把思考强度传给后端
- [ ] 样式：面板与既有 `UserAdminDialog` 复用同一套 modal 样式

## 阶段 4：可测试性
- [ ] 新增 `data-testid`：`settings-button` / `settings-dialog` / `settings-close` / `thinking-slider` / `thinking-label`
- [ ] **保持不变**的 testid：`theme-toggle` / `reading-mode-toggle` / `quick-read-toggle` / `logout-button`（只是换了位置）
- [ ] 更新既有 E2E：先打开设置面板再点这些开关（`ui-shell.spec.ts` 的主题/阅读宽度用例、`accounts.spec.ts` 的退出登录用例）

## 阶段 5：测试
- [ ] 新增 E2E：打开/关闭设置面板、焦点回归
- [ ] 新增 E2E：侧栏已不含四个开关；设置面板内含它们
- [ ] 新增 E2E：思考强度切档后**刷新仍保持**（按用户保存）
- [ ] 新增 E2E：把强度调到「沉思」，断言出字节奏比「迅捷」慢（以「收尾出现所需时间」为可观测量）
- [ ] 全量通过（pytest / vitest / Playwright）

## 阶段 6：部署与验证
- [ ] 本地构建 + 全量测试
- [ ] 部署到 192.168.178.116，对线上跑全量 E2E
- [ ] 目视核对：侧栏精简后的样子、设置面板、滑杆手感
- [ ] 提交推送；`openspec archive settings-panel`