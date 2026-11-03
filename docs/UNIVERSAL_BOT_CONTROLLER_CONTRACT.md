# 三类 Bot 通用控制器合同

本合同适用于 Muse、Grok Bot、ChatGPT Dot、网页版 ChatGPT Work 和 DeepSeek Harness。Bot 只是网页控制器；飞书候选、状态机、产物校验、写回和最终清零由 `gvflow` 及其确定性合同负责。

## 一、先说结论

三类 Bot 都可以执行完整流程，但必须满足同一组前置条件：

1. 能在自己的运行环境读取公开仓库并持久保存 `runs/`；
2. 能运行 `gvflow` 或调用一个等价的本地 Bridge；
3. 能真实控制 EGO/浏览器中的 ChatGPT 普通聊天；
4. 能把真实下载的 MP4 交回确定性核心；
5. 能通过 CLI、MCP 或 Bridge 上传附件、更新飞书并实时回读；
6. 有本机唯一 `actor_id`；
7. 同一 Base 同一时间只有一个生产写入者。

缺少任一能力时，Bot 必须输出准确错误码并停在准备阶段，不能用聊天中的“已完成”替代证据。

## 二、Bot 的唯一职责边界

Bot 可以做：

- 阅读 `task_manifest.json`、接触表和 `execution_plan.json`；
- 本地判断单页/多页、是否存在中心律师、选择人物照；
- 按计划控制 ChatGPT 普通聊天；
- 处理最多两次定点排版纠正；
- 下载并解包真实 MP4；
- 生成 `controller_result.json`。

Bot 不可以凭感觉做：

- 不自行猜候选行；
- 不以状态字段代替成品/已发布附件事实；
- 不把网页回复、PID、聊天标题或下载按钮当完成证据；
- 不直接把长聊天回复当作飞书写回；
- 不改 MD、Video ZIP、业务规则或其他分支的产物；
- 不因单行失败停掉全批；
- 不与其他 Bot 同时写同一个 Base。

## 三、统一循环

每一个 Bot 都必须执行同一个持久循环，而不是等待用户逐行发下一条指令：

```text
启动 → 读取仓库和状态 → doctor → 实时 discover → 获取一条 record_id
→ 再次回读该行和来源 → prepare → stage0-prepare → 本地决定路线
→ finalize-stage0 → reserve-background 或选择律师人物 → plan
→ 01/02 或 lawyer 分支网页执行 → 下载真实 MP4 → record-result
→ writeback → 同行回读 → 写入事件和检查点 → 下一条
→ 首轮结束后恢复队列 → 最终全表重新 discover → 可执行未完成=0 才结束
```

单行失败必须执行“记录错误 → 保存恢复点 → 进入恢复队列 → 继续下一行”。只有登录、权限、磁盘、全局网络、EGO整体失效或唯一写入者冲突才可以暂停全批。

## 四、统一能力探测

每个 Bot 首次接入只做一次能力探测，并保存 `capability_probe.json`：

```json
{
  "controller_id": "muse",
  "actor_id": "本机唯一值",
  "can_read_github": true,
  "can_run_commands": true,
  "can_persist_files": true,
  "can_control_ego": true,
  "can_upload_reference": true,
  "can_download_mp4": true,
  "can_read_feishu": true,
  "can_write_feishu_attachments": true,
  "can_readback_feishu": true,
  "checked_at": "2026-01-01T00:00:00+08:00"
}
```

字段必须是真实探测结果。任何一个写回能力为 `false`，结论只能是 `BOT_EXECUTION_CHANNEL_NOT_CONNECTED`，并列出最小缺口。

## 五、统一产物合同

每条记录的控制器必须写出绝对路径的 `controller_result.json`：

```json
{
  "ok": true,
  "controller_id": "muse",
  "actor_id": "本机唯一值",
  "engine": "muse-ego",
  "record_id": "rec...",
  "route": "single_no_lawyer",
  "artifacts": [
    {"branch": "01", "path": "绝对路径/branch01_final_animation.mp4", "chat_url": "https://..."},
    {"branch": "02", "path": "绝对路径/branch02_final_animation.mp4", "chat_url": "https://..."}
  ],
  "errors": []
}
```

`ok=true` 的最低条件是：文件真实存在、是有效 MP4、达到最小大小、普通路线两个分支 SHA-256 不同、路线所需分支齐全。没有这些证据，必须 `ok=false`。

## 六、三个 Bot 的分工方式

三者共享同一 `gvflow` 和同一飞书配置，只替换网页控制器：

| 控制器 | `controller_id` | `engine.name` | 网页职责 |
|---|---|---|---|
| Muse | `muse` | `muse-ego` | 通过云电脑和 EGO 控制 ChatGPT 普通聊天 |
| Grok Bot | `grok-bot` | `grok-bot-ego` | 通过其可用浏览器通道控制 ChatGPT 普通聊天 |
| ChatGPT Dot | `chatgpt-dot` | `chatgpt-dot-ego` | 通过 Dot 的浏览器通道控制 ChatGPT 普通聊天 |

如果某个 Bot 不能运行命令或不能写飞书，就必须调用本地 Bridge；Bridge 的输入仍是 `task_manifest.json`，输出仍是 `controller_result.json`，不能另造一套业务口径。

## 七、互斥和恢复

当前公开仓库的文件锁只覆盖同一台电脑。跨电脑生产时，最安全的默认方式是“三选一”：任意时刻只启用一个 Bot 的 `production.enabled=true`，其他两个只做只读检查或保持关闭。

若以后要并发，必须先增加共享租约服务或飞书“控制器租约”表，至少包含：`lease_id`、`actor_id`、`controller_id`、`scope`、`expires_at`、`heartbeat_at`、`status`。没有共享租约证据时，不得声称三者可以并发清同一张表。

## 八、停止条件

Bot 只能在以下两种情况结束：

1. 最终实时扫描显示可执行未完成数为 0，阻塞行都有错误码、证据和下一步；
2. 遇到全局人工阻塞，已写入错误事件和恢复点。

“已经启动”“正在输入”“网页说完成”“某个 PID 存在”“某一行完成”都不是全批结束条件。
