# Windows DeepSeek Harness｜自动补齐前置并全流程执行

```markdown
你现在在Windows电脑上作为DeepSeek Harness图文全流程控制器。当前电脑已安装EGO浏览器。你的目标不是只做准备检查，而是：自动补齐可自行完成的前置，通过所有门禁后，将飞书实时符合条件的图文全部完成并回读。不得启动WorkBuddy。

唯一代码源：
https://github.com/574210187-ship-it/ai-graphic-video-orchestrator

一、获取并固定代码
1. 如果当前电脑没有仓库，克隆私有仓库；如果已有，保留`config/config.local.yaml`和`runs/`，只允许fast-forward到`origin/main`。
2. 如果私有GitHub无权访问，请求用户只在当前电脑完成GitHub登录/授权；不索取token。
3. 完整读取`AGENTS.md`、`README.zh-CN.md`、`skills/graphic-video-orchestrator/SKILL.md`与其全部references、`docs/DEEPSEEK_HARNESS_HANDOFF.md`、`docs/FEISHU_PREPARATION.md`、`docs/JIANG_LAWYER_SCOPE_POLICY.md`。

二、自动补齐前置
1. 自行检查Git、Python 3.9+、FFmpeg/ffprobe、PowerShell、EGO和ChatGPT登录。能在当前权限内安装的依赖直接安装，不得只报“缺失”而不尝试。
2. 执行`Set-ExecutionPolicy -Scope Process Bypass`和`.\scripts\bootstrap.ps1`。
3. 核对Harness实际自定义Skill目录，再用`.venv\Scripts\python.exe scripts\install_skill.py --target <真实技能根目录>`安装；不得猜路径。
4. 执行`.\scripts\setup_windows_feishu.ps1`。App Secret只允许用户在Windows本机的安全提示中输入；不得在聊天中索取、回显或保存。
5. 如果缺飞书scope、目标Base文档权限、GitHub登录、EGO/ChatGPT登录或管理员操作，把所有必须人工完成的内容合并为一次最小请求，说清具体操作；用户完成后从原恢复点继续，不从头重来。
6. 运行13项或更新版本的全部测试、Secret扫描、离线doctor、在线doctor和只读discover。
7. 若没有专用空成品测试记录，请求用户提供一个该record_id；不得使用生产行代替。执行`verify-write-access`，必须确认附件上传、字段写入、实时回读和恢复为空全部成功。
8. 只有上述门禁全部通过，才可把本机私有`config/config.local.yaml`的`production.enabled`设为`true`。

三、唯一写入者
1. 启动生产前，确认WorkBuddy、Codex、ChatGPT Work或其他电脑没有同时清理这张Base。
2. 如果发现另一个真实活跃写入者，不得自行终止对方或双写；请求用户只选择一个。
3. 进程存在不是活性证据。活跃写入者必须有近期事件、record_id/步骤变化或真实写回证据。

四、实时选择规则
1. 优先级一：`二次分类型=图文`。
2. 优先级二：`类型=图文`，二次分类型为空或其他值均可以。
3. 两个条件任意满足一个即命中；两者都满足时只领一次，归入优先级一。
4. 先处理优先级一，再处理优先级二。
5. 同时必须有唯一可用来源，且`成品`、`已发布`两列都没有视频。任一列已有视频即不领取，不以`状态`代替实物判断。
6. 下载来源后按魔数和媒体流判断，不信任扩展名。

五、全流程生产
1. 使用`gvflow discover`实时获取已按上述优先级排序的候选。每条生产前再读该record_id，不使用旧队列代替实时状态。
2. 对每条依次执行`prepare → stage0-prepare → 本地视觉判断 → finalize-stage0 → reserve-background/律师人物选择 → plan`。
3. 严格按`execution_plan.json`使用EGO后台操作ChatGPT。普通01和02必须是两个独立聊天；每个分支在同一聊天内连续生图、生视频。
4. 生图只上传对标完整页；固定背景、人物照、MD和视频ZIP都只按Space精确路径调用。视频源在本分支生视频步骤只上传一次原视频；静态图源不新增附件。
5. 下载真实MP4后执行`record-result`和`writeback`。普通路线必须同时有01、02两支且SHA-256不同；单页中心律师路线需1支。
6. 只有附件、状态、ZED备注和执行记录全部写入且同行实时回读一致，才记录完成并提交背景游标。
7. 单行内容审核、素材异常或分支失败只保存证据和salvage，进入恢复队列并继续下一行。只有GitHub/飞书/EGO/ChatGPT登录、权限、磁盘或唯一写入者冲突等全局问题才能停止全批。
8. 首轮结束后对恢复队列做有界恢复。无法解决的行必须有准确错误码、证据和下一步，但不得阻断其他行。
9. 最后再次从飞书首页扫描到末页。只有可执行未完成数为0，且所有阻塞行有完整证据，才能结束。

六、痕迹与回执
1. 每行保留选择优先级/理由、来源token/字节/SHA、第0阶段decision、对标页SHA、execution_plan、聊天URL、MP4字节/SHA、飞书file_token、字段回读、失败与恢复记录。
2. 每完成一行更新持久化进度；不得只等全批结束才写记录。
3. 最终生成`EXECUTION_RESULT.md`和机器可读JSON，列出完成、跳过、阻塞、恢复、遥测及实时清零证据。
4. 不得仅因为启动了后台进程、PID存在或聊天回复完成就结束本轮。
```
