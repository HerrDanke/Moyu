# pseudo-ai-chat

## ADDED Requirements

### Requirement: 生成节奏由用户设置驱动
**ID:** pseudo-ai-chat.pacing-setting

流式输出的节奏参数不再固定来自服务端环境变量，而是按**当前用户**的设置取值；环境变量退化为默认值。

#### Scenario: 读取当前用户的速度设置
- Given 用户设置里保存了思考强度对应的速度倍率
- When 该用户发起阅读请求
- Then 本次流式输出使用该倍率决定分批间隔
- Then 不影响其他用户的节奏

#### Scenario: 缺省回落
- Given 用户没有保存过速度设置
- Then 使用环境变量 `TYPING_SPEED` 的值

#### Scenario: 设置不影响进行中的流
- Given 一次流式输出正在进行
- When 用户在设置面板里改动思考强度
- Then 当前这次输出保持原有节奏不变，改动从下一次阅读开始生效

#### Scenario: 不破坏既有「不节流」语义
- Given 服务端默认速度被配置为 0（不节流）
- Then 未设置过的用户仍获得不节流的行为
- Then 用户手动设置的合法值（0.1~10）优先于该默认值