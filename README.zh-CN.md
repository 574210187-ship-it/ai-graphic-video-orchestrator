# AI 图文视频全流程编排器

本仓库把“从多维表领取未执行图文记录，到生成视频、上传成品、写入状态并实时回读”的流程拆成一个确定性核心和多个 AI 控制器适配器。

当前目标控制器：

- 网页版 ChatGPT Work：负责任务判断、子聊天调度和异常修复；原生子聊天能力不足时使用本地 Work Bridge。
- DeepSeek Harness/Honey：负责全流程调度，通过 EGO 浏览器操作 ChatGPT 普通聊天完成生图和生视频。
- Muse：通过云电脑和 EGO 操作 ChatGPT 普通聊天；必须使用统一控制器合同，不能绕过 Muse 直接操作浏览器。
- Grok Bot：使用其可用的浏览器/命令通道或本地 Bridge，调用同一 `gvflow` 核心。
- ChatGPT Dot：使用 Dot 可用的浏览器/命令通道或本地 Bridge，调用同一 `gvflow` 核心。

所有方向必须共用同一份业务配置、任务清单、状态机、产物校验和飞书写回器；只能替换网页控制器，不能各自发明业务规则。

现行候选口径取两个条件的并集：先处理`二次分类型=图文`，再处理`类型=图文`且二次分类型为空或其他值的记录；两项同时满足只领取一次。分类命中后还必须有唯一来源，并且`成品`、`已发布`两列都没有视频。

## 安全边界

- 仓库不包含飞书密钥、访问令牌、cookie、真实视频、真实运行目录或聊天记录。
- 默认配置为`production.enabled: false`，没有显式启用时禁止写生产表。
- 飞书写入必须完成同记录实时回读；回读不一致不得标记完成。
- 同一个 Base 同一时间只允许一个生产写入者，除非配置了跨机器租约字段。
- 测试先使用夹具或专用测试记录，不覆盖真实业务数据。

## 安装

前置环境：Python 3.9以上、Git、FFmpeg（命令行可找到`ffprobe`）。EGO和ChatGPT登录只在真实网页测试时需要。

```bash
git clone https://github.com/574210187-ship-it/ai-graphic-video-orchestrator.git
cd ai-graphic-video-orchestrator
./scripts/bootstrap.sh
cp config/example.yaml config/config.local.yaml
```

编辑`config/config.local.yaml`，填写本机工作目录、飞书 Base/Table、字段映射、Space 规则路径和控制器命令。密钥只通过环境变量或系统钥匙串读取，不写入配置。

姜律师项目优先复制`config/jiang-lawyer-harness.example.yaml`或`config/jiang-lawyer-work.example.yaml`；现行Space业务profile已在`config/profiles/jiang-lawyer-v4.2.yaml`，目标电脑无需重复填写固定素材路径。

Windows DeepSeek Harness请不要照抄macOS命令，使用：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\bootstrap.ps1
.\scripts\setup_windows_feishu.ps1
```

仓库为公开仓库，无需GitHub登录即可克隆。脚本会要求在目标Windows本机填写App ID、Base App Token、Table ID，并把App Secret只保存在Windows凭据管理器；写权限还必须用专用测试记录验证。完整前置见[docs/FEISHU_PREPARATION.md](docs/FEISHU_PREPARATION.md)。

## 最小验证

```bash
.venv/bin/gvflow doctor --config config/config.local.yaml --offline
.venv/bin/pytest -q
```

## AI原生执行顺序

```bash
# 只读扫描
.venv/bin/gvflow discover --config config/config.local.yaml

# 为一条记录下载来源并建立任务清单
.venv/bin/gvflow prepare --config config/config.local.yaml --record-id REC_ID

# 提取第0阶段候选帧/接触表
.venv/bin/gvflow stage0-prepare --config config/config.local.yaml --record-id REC_ID

# AI检查接触表，写入decision.json后固化路由和对标完整页
.venv/bin/gvflow finalize-stage0 --config config/config.local.yaml \
  --record-id REC_ID --decision-file /absolute/path/decision.json

# 普通路线先预留本行蓝色背景；律师路线不执行本命令
.venv/bin/gvflow reserve-background --config config/config.local.yaml --record-id REC_ID

# 生成网页控制器要逐步执行的精确动作清单和提示词
.venv/bin/gvflow plan --config config/config.local.yaml --record-id REC_ID

# AI按execution_plan.json用网页完成各分支后，登记真实本地MP4
.venv/bin/gvflow record-result --config config/config.local.yaml --record-id REC_ID \
  --route single_no_lawyer \
  --artifact 01:/absolute/branch01_final_animation.mp4 \
  --artifact 02:/absolute/branch02_final_animation.mp4 \
  --chat-url 01:https://chatgpt.com/c/... \
  --chat-url 02:https://chatgpt.com/c/...

# 校验、上传、写状态、执行记录并实时回读
.venv/bin/gvflow writeback --config config/config.local.yaml --record-id REC_ID

# AI按Skill循环上述流程，单行失败留证并跳过，最终必须重新实时扫描为0
```

完整部署与测试门禁见[docs/IMPLEMENTATION_ROADMAP.md](docs/IMPLEMENTATION_ROADMAP.md)。

- 远程DeepSeek Harness交接：[docs/DEEPSEEK_HARNESS_HANDOFF.md](docs/DEEPSEEK_HARNESS_HANDOFF.md)
- 第一轮远程Harness复制指令：[docs/DEEPSEEK_HARNESS_COPY_PASTE_PROMPT.md](docs/DEEPSEEK_HARNESS_COPY_PASTE_PROMPT.md)
- Windows Harness自动补齐前置并执行全流程：[docs/DEEPSEEK_HARNESS_FULL_EXECUTION_PROMPT.md](docs/DEEPSEEK_HARNESS_FULL_EXECUTION_PROMPT.md)
- ChatGPT Work交接：[docs/CHATGPT_WORK_HANDOFF.md](docs/CHATGPT_WORK_HANDOFF.md)
- ChatGPT Work准备检查复制指令：[docs/CHATGPT_WORK_READINESS_PROMPT.md](docs/CHATGPT_WORK_READINESS_PROMPT.md)
- ChatGPT Work自动补齐通道并执行全流程：[docs/CHATGPT_WORK_FULL_EXECUTION_PROMPT.md](docs/CHATGPT_WORK_FULL_EXECUTION_PROMPT.md)
- 三类Bot统一控制器合同：[docs/UNIVERSAL_BOT_CONTROLLER_CONTRACT.md](docs/UNIVERSAL_BOT_CONTROLLER_CONTRACT.md)
- Muse全流程指令：[docs/MUSE_FULL_EXECUTION_PROMPT.md](docs/MUSE_FULL_EXECUTION_PROMPT.md)
- Grok Bot全流程指令：[docs/GROK_BOT_FULL_EXECUTION_PROMPT.md](docs/GROK_BOT_FULL_EXECUTION_PROMPT.md)
- ChatGPT Dot全流程指令：[docs/CHATGPT_DOT_FULL_EXECUTION_PROMPT.md](docs/CHATGPT_DOT_FULL_EXECUTION_PROMPT.md)
- 控制器缺口审计：[docs/CONTROLLER_GAP_AUDIT_20261104.md](docs/CONTROLLER_GAP_AUDIT_20261104.md)
- 飞书认证、权限与写入测试：[docs/FEISHU_PREPARATION.md](docs/FEISHU_PREPARATION.md)
- 姜律师候选行筛选口径：[docs/JIANG_LAWYER_SCOPE_POLICY.md](docs/JIANG_LAWYER_SCOPE_POLICY.md)
- 原图文接手窗口的公开长期记忆：[docs/WINDOW_MEMORY_GRAPHIC_TAKEOVER.md](docs/WINDOW_MEMORY_GRAPHIC_TAKEOVER.md)
