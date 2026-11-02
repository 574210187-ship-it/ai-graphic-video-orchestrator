# 网页版 ChatGPT Work｜准备检查指令

```markdown
你现在只做“图文全流程准备检查”，不生产、不批量领取、不修改业务记录。

唯一代码源：
https://github.com/574210187-ship-it/ai-graphic-video-orchestrator

一、完整读取
1. README.zh-CN.md
2. AGENTS.md
3. skills/graphic-video-orchestrator/SKILL.md及其references
4. docs/CHATGPT_WORK_HANDOFF.md
5. docs/FEISHU_PREPARATION.md

二、先列出你当前真实可用的能力，不得猜测
1. 是否能读取公开GitHub仓库；
2. 是否能读取本地task_manifest.json和execution_plan.json；
3. 是否能创建并持续控制普通Chat子聊天；
4. 是否能上传对标图片/视频并把MP4.zip下载到明确路径；
5. 飞书通道是什么：可写MCP，还是本地Bridge。

三、飞书通道必须逐项验证
- 分页读取记录和按record_id读单条；
- 下载来源附件；
- 上传MP4到目标Base；
- 更新附件、状态、备注和执行记录；
- 重新读取同一行核验写入。

如果当前飞书MCP只能读、不能上传或不能更新附件字段，必须判定为不合格。如果既没有合格MCP，也没有已就绪的本地Bridge，只回复：
FEISHU_WRITE_CHANNEL_NOT_CONNECTED
并列出缺少的最小能力，不得索取token或Secret。

四、只有用户明确提供专用空成品测试record_id后，才可对该专用行验证：
1. 上传一个小型测试MP4；
2. 写入成品字段；
3. 实时回读并取得file_token；
4. 恢复成品为空；
5. 再次回读证明已恢复。
禁止拿任意生产行做这个测试。

五、输出READINESS_RESULT.md，只能有以下结论之一：
- READY_FOR_DEDICATED_TEST
- READY_FOR_THREE_ROUTE_PILOT
- FEISHU_WRITE_CHANNEL_NOT_CONNECTED
- BLOCKED（必须带准确错误码和一个最小人工操作）

没有专用测试记录和真实回读证据时，不得宣布全流程已接通。
```
