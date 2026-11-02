# 给另一个 ChatGPT 账号的资产获取指令

复制下面整段到另一个 ChatGPT 账号的普通聊天窗口。它只负责下载和准备资产，不把未核验版本冒充最新版：

```text
你现在是“姜律师图文”另一个 ChatGPT 账号的资产准备窗口。不要依赖当前聊天历史，也不要先生产。

公开仓库：
https://github.com/574210187-ship-it/ai-graphic-video-orchestrator

先下载并读取：
1. https://raw.githubusercontent.com/574210187-ship-it/ai-graphic-video-orchestrator/main/assets/jiang-lawyer-graphic-v4.2/materials-verified-20261024/manifest.json
2. https://raw.githubusercontent.com/574210187-ship-it/ai-graphic-video-orchestrator/main/assets/jiang-lawyer-graphic-v4.2/materials-verified-20261024/MATERIAL_STATUS.md
3. https://raw.githubusercontent.com/574210187-ship-it/ai-graphic-video-orchestrator/main/assets/jiang-lawyer-graphic-v4.2/materials-verified-20261024/sha256sums.txt

逐个按 sha256 校验下载文件。当前公开资产包是“2026-10-24 本机已核验快照”，不是 2026-10-29 Authority 五份现行 MD 的替代品。Authority 仅确认五份现行版本号：单页01 v38、单页02 v30、多页01 v29、多页02 v27、单页姜律师 v9；如果本聊天无法获得这些版本的正文 bytes，必须明确记录 RULE_ASSET_UNAVAILABLE，不能把快照文件称为这些版本，也不能以降级文件宣称生产完成。

本轮只准备以下目录，不要一次性把全部材料上传到同一个聊天：
assets/jiang-lawyer-graphic-v4.2/materials-verified-20261024/md/
assets/jiang-lawyer-graphic-v4.2/materials-verified-20261024/video/
assets/jiang-lawyer-graphic-v4.2/materials-verified-20261024/fixed/

执行前输出：下载成功/失败、每个文件 SHA-256、当前版本是否可证明、当前账号能否把文件作为普通聊天附件上传、是否能把结果下载到本地。没有全部证据前不要写“已完成”。

若后续获得当前 Authority 五份 MD 的真实正文文件，再替换对应快照并重新计算 manifest 和 SHA-256；不允许改名掩盖版本差异。
```
