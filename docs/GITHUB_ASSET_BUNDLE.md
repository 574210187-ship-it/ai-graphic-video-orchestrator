# GitHub 资产包使用说明

公开仓库：`https://github.com/574210187-ship-it/ai-graphic-video-orchestrator`

资产目录：`assets/jiang-lawyer-graphic-v4.2/materials-verified-20261024/`

对应原始文件地址格式：

```text
https://raw.githubusercontent.com/574210187-ship-it/ai-graphic-video-orchestrator/main/assets/jiang-lawyer-graphic-v4.2/materials-verified-20261024/manifest.json
https://raw.githubusercontent.com/574210187-ship-it/ai-graphic-video-orchestrator/main/assets/jiang-lawyer-graphic-v4.2/materials-verified-20261024/sha256sums.txt
```

先下载 `manifest.json`、`MATERIAL_STATUS.md` 和 `sha256sums.txt`，再按本轮路线只下载需要的文件。不要把所有 MD、两个视频 ZIP、背景 ZIP 和形象 ZIP 一次性上传到同一个 ChatGPT 聊天；这样会增加误选旧路线的风险。

## 普通 ChatGPT 账号的最小准备

1. 下载并校验清单。
2. 生图聊天只上传本轮需要的 MD 和对标图片；固定蓝色背景图或姜律师形象图按路线上传。
3. 生视频聊天只上传本轮需要的原始对标视频及生成结果图层；在指令中明确使用哪个视频包及其包内《执行说明.txt》。
4. 不要把 `materials-verified-20261024` 目录中的文件标成 Authority 的 v38/v30/v29/v27/v9；当前 Authority 版本正文尚未被本包物化。
5. 业务写回必须由具备飞书写权限的本机执行器完成，并对同一 record_id 做附件、状态、备注、执行记录的实时回读。

## 版本边界

`MATERIAL_STATUS.md` 已明确：本目录是 2026-10-24 的本机快照。2026-10-29 Authority 只确认了五份 MD 的版本号，未提供正文 bytes；Space 根页里的旧文件也不能作为替代。任何执行器都必须把这个差异记录为 `RULE_ASSET_UNAVAILABLE`，不能静默降级后写“已按最新版完成”。
