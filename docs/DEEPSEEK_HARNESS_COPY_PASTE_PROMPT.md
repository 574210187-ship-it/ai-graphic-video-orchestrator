# 第一轮｜复制到远程 DeepSeek Harness

```markdown
你现在负责在“当前这台安装了DeepSeek Harness的电脑”部署并验证图文视频全流程。不要引用其他电脑的进程、路径、登录态或本地配置；不要启动WorkBuddy。

唯一代码源：
https://github.com/574210187-ship-it/ai-graphic-video-orchestrator

本轮目标是“安装和测试门禁”，不是直接全量写生产表。你必须亲自执行命令、读取真实输出并留下文件证据，不得只回复计划。

一、取得代码
1. 在当前电脑选择一个独立目录克隆上述私有仓库；如果已经存在，只允许fast-forward到origin/main，不要覆盖本机私有配置和runs。
2. 若GitHub私有仓库访问失败，只报告“需要当前电脑完成GitHub登录/授权”，不要索取、展示或保存token。
3. 完整读取仓库根目录AGENTS.md、README.zh-CN.md、skills/graphic-video-orchestrator/SKILL.md、三个references，以及docs/DEEPSEEK_HARNESS_HANDOFF.md。

二、离线门禁
1. 运行./scripts/bootstrap.sh。
2. 运行python3、git和ffprobe版本检查；ffprobe缺失时只报告准确安装缺口，不得把它归因于网络。
3. 把skills/graphic-video-orchestrator安装到当前Harness真实使用的自定义Skill目录；先核对Harness配置，不得猜目录。可使用python3 scripts/install_skill.py --target <真实技能根目录>。
4. 运行：
   - .venv/bin/pytest -q
   - .venv/bin/python scripts/secret_scan.py
   - .venv/bin/gvflow doctor --config config/example.yaml --offline
5. 必须确认普通01/02双分支、律师单分支、失败后继续下一行、背景游标、半写回恢复这些测试全部通过。

三、本机私有配置
1. 复制config/jiang-lawyer-harness.example.yaml为config/config.local.yaml；该文件必须保持Git忽略。直接使用仓库内config/profiles/jiang-lawyer-v4.2.yaml，不要自行重写五份MD、视频包、背景和人物路径。
2. 根据当前电脑的飞书身份、运行目录、唯一ActorID和EGO实际情况调整，不得照抄其他电脑绝对路径。
3. 飞书密钥只用当前电脑环境变量或系统安全存储，不写进仓库、日志或回复。
4. 保持production.enabled=false。

四、飞书只读盘点
1. 运行在线doctor和discover，只读不写。
2. 未执行唯一口径：分类命中；来源优先字段中恰有一个可用附件；成品和已发布两列都没有视频。任一列已有视频即不领取，不以状态字段替代。
3. 对当前候选逐条执行prepare、stage0-prepare并分析接触表，生成decision草稿，但本轮不要finalize后生产，不要上传成品，不要改飞书字段。
4. 从只读候选中选择最多三条测试建议：普通单页、普通多页、单页中心律师各一条；如果某路线没有候选，如实写缺失。多页中心律师当前不执行。

五、EGO能力探测
1. 只在后台使用EGO，核对能否创建TaskSpace、打开ChatGPT、上传一个非敏感测试附件、保持同聊天续写、读取下载控件和返回聊天URL。
2. 不要在能力探测里生成或写回正式业务成品；测试页完成后按EGO规范清理临时页面，不关闭用户原有页面。
3. 若登录/扫码/权限需要人工，记录准确错误和用户只需做的一件事；不要把普通网页延迟当成全局网络故障。

六、结束条件和回执
本轮只有以下全部完成才能回复：代码版本、Harness Skill实际安装路径、离线测试结果、在线doctor结果、只读候选总数、三条建议测试record_id及其来源SHA/路线判断/EGO能力证据。所有证据写到runs/readiness-<日期时间>/READINESS_RESULT.md，并在回复中给出该文件绝对路径。

本轮禁止：production.enabled=true、飞书写入、正式生图/生视频、全量领取、启动后台无限驱动、只看到PID就报告运行。遇到单条来源问题继续盘点其他候选；只有GitHub登录、飞书权限或EGO整体登录等全局人工阻塞才允许提前停止。
```
