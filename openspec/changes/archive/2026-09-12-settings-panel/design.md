# Design: 设置面板与「思考强度」

## 数据模型

新增**每用户设置表** `user_settings(user_id, key, value)`，主键 `(user_id, key)`，`user_id` 外键级联删除。

选它而不是往 `users` 加列：设置项会持续增加，键值表不用为每一项改表结构。

- `key`: 设置名（当前只有 `typing_speed`）
- `value`: 字符串化的值（`typing_speed` 存倍率，如 `"1.0"`）

全局 `settings` 表保持原样（服务端默认值仍来自环境变量 `TYPING_SPEED`）。

## 思考强度：档位与映射

`typing_speed` 是「延迟除数」——`实际间隔 = 基准间隔 / typing_speed`。因此值越大越快。

| 档 | 名称 | typing_speed | 观感 |
|---|---|---|---|
| 1 | 迅捷 | `2.0` | 几乎不停顿，一口气往外走 |
| 2 | 标准 | `1.0` | 默认节奏 |
| 3 | 深入 | `0.6` | 一句一句慢慢斟酌 |
| 4 | 沉思 | `0.35` | 明显停顿，像在深思 |

- 面板主标签写「思考强度」，说明文案写「影响正文逐字出现的节奏」——既维持"伪装 AI"的叙事，又不至于让人调不明白。
- 未设置过的用户 → 回落到环境变量 `TYPING_SPEED`（保持既有部署行为不变）。
- 「快速阅读」与「思考强度」的正交关系：快速阅读是**绕过打字机**（一次性入 DOM），思考强度是**流式时的节奏**。开启快速阅读时节奏参数不影响观感，这是预期行为。

## API

| 接口 | 说明 |
|---|---|
| `GET /api/settings` | 返回当前用户的设置（含未设置项的服务端默认值） |
| `PATCH /api/settings` | 更新白名单内的键（当前仅 `typing_speed`），值做范围校验 |

字段白名单 + 取值校验（`0.1 ~ 10.0`），越界返回 400——避免有人塞个 `0` 或 `-1` 让服务端 `asyncio.sleep` 出怪行为。

## 服务端如何取到这个值

`router/chat.py` 构造 `Settings` 时，用当前用户的 `typing_speed` 覆盖环境变量带来的默认值：

```
有效设置 = dataclasses.replace(app_settings, typing_speed=用户值 or 环境默认)
```

`typing_stream` 无需改动——它本来就是读 `settings.typing_speed`。

`typing_speed <= 0` 的既有语义（不节流）保持不动，但用户输入不允许设成 ≤ 0（用白名单校验挡在接口层）。

## 前端

- 侧栏底部从「四个开关 + 退出」精简为：**进度文案 + 「设置」按钮 + 用户区**（用户名 + 管理员才有的「用户管理」）
- 新增 `SettingsDialog`，与「用户管理」保持同一套对话框模式：`role="dialog"` + `aria-modal`、Esc 关闭、焦点陷阱、关闭后焦点回到设置按钮
- 面板内容：
  - **思考强度**：`<input type="range" min=1 max=4 step=1>`，四档离散；显示当前档位名
  - 深色主题 / 宽松排版 / 快速阅读：沿用原有开关
  - 退出登录：危险色按钮，放在最下方
- 主题与阅读宽度仍写 localStorage（首屏防闪烁）；思考强度调 `PATCH /api/settings` 并即时用于下一次阅读

## 可测试性

新增 `data-testid`：`settings-button` · `settings-dialog` · `settings-close` · `thinking-slider` ·
`thinking-label` · `theme-toggle` · `reading-mode-toggle` · `quick-read-toggle` · `logout-button`

> 注意：`theme-toggle` / `reading-mode-toggle` / `quick-read-toggle` / `logout-button` 这些 id **保持不变**，只是从侧栏移进面板——既有 E2E 用例因此不需要改选择器，但**必须先打开设置面板**才能点到它们，需要更新对应步骤。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 既有 E2E 直接点侧栏里的开关 | 先开面板再点；选择器不变，仅补一步「打开设置」 |
| 非法速度值导致服务端异常 | 接口层白名单 + 范围校验（0.1~10） |
| 设置改动与流式中的请求竞争 | 设置在下一次阅读请求时读取，进行中的流不受影响（符合直觉） |
| 每用户设置表与全局表混淆 | 命名区分清楚：`user_settings`（每用户）vs `settings`（全局默认） |

## 不做的事

- 不做主题/阅读宽度的跨设备同步（见 proposal 的技术取舍说明）
- 不加「自定义曲线」「逐句间隔」等进阶项
- 不改 `typing_stream` 的分批算法与 SSE 协议