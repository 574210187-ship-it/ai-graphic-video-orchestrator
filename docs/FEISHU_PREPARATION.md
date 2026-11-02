# 飞书准备｜Windows Harness、DSH与ChatGPT Work

## 共同前提

任何AI开始生产前，必须同时证明三层已经接通：

1. **应用认证**：有正确的App ID和App Secret，应用已发布；Secret只进入目标电脑安全存储，不进入聊天、Git、Markdown或日志。
2. **开放平台权限**：至少启用“查看、评论、编辑和管理多维表格”（`bitable:app`）。只读模式可用只读scope，但本项目要上传附件和写状态，最终必须有编辑权限。
3. **目标Base权限**：不能只在开放平台勾scope；还要在目标多维表格中把该应用添加为文档应用/协作者，并给予可编辑或可管理权限。否则会出现403、1254304或附件权限错误。

官方接口要求调用身份本身具有目标Base编辑权限；附件必须先上传到当前Base，再把返回的`file_token`写入附件字段。

## Windows DeepSeek Harness/DSH

Harness不必额外安装飞书MCP。本仓库自带`gvflow` CLI，直接调用飞书官方API：

```powershell
git clone https://github.com/574210187-ship-it/ai-graphic-video-orchestrator.git
cd ai-graphic-video-orchestrator
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\bootstrap.ps1
.\scripts\setup_windows_feishu.ps1
```

第二个脚本会：

- 要求在本机填写飞书App ID、目标Base App Token和业务Table ID，并使用仓库中的字段模板；
- 要求输入这台电脑唯一ActorID；
- 在Windows凭据管理器中保存App Secret；
- 保持`production.enabled=false`；
- 执行在线doctor和只读discover。

不要把App Secret粘贴给Harness。脚本会在Windows本机安全输入框中读取。App ID、Base App Token和Table ID是资源标识，不是App Secret；它们写入被Git忽略的`config/config.local.yaml`。

### 写权限验证

只读通过不等于能上传和写表。必须先准备一条专用测试记录，并保证它的“成品”为空，然后执行：

```powershell
.venv\Scripts\gvflow.exe verify-write-access `
  --config config\config.local.yaml `
  --record-id <专用测试record_id> `
  --confirm-dedicated-test-record
```

该命令会上传一个小型测试MP4、写入成品字段、实时回读，然后把成品字段恢复为空。成功标准：`attachment_upload_verified=true`、`field_write_verified=true`、`restored_to_original=true`。平台自动更新时间可能变化，因此禁止拿生产记录做此测试。

完成专用写测试后，才能开始三路线业务试点；三路线验收通过后才可把`production.enabled`改为`true`。

## ChatGPT Work网页模式

网页版Work不能因为“看得到GitHub”就自动获得飞书和本机文件权限。它必须二选一：

### 方案A：飞书MCP

MCP至少要真实提供并通过以下动作：

- 列出数据表和字段；
- 分页读取记录、按record_id读取单条；
- 下载来源附件；
- 上传MP4到目标Base；
- 更新附件、状态、备注和执行记录；
- 再次读取同一record_id做回读核验。

只支持“读表”的MCP不合格。Work必须用专用测试记录做一次附件上传、字段写入和恢复测试。

### 方案B：Windows本地桥接

Work只负责决策和调度，把`record_id/task_manifest`交给一台已经通过上述Windows CLI门禁的本地执行主机；本地主机负责文件、EGO和飞书。桥接器必须返回真实MP4路径、SHA、聊天URL、飞书file_token和回读结果。没有这些证据，Work不能报告完成。

当前仓库已经提供本地CLI和统一JSON合同，但不会自动替用户在ChatGPT账号中安装或授权飞书MCP。Work能力探测时如果没有飞书工具或本地桥接，必须明确报告`FEISHU_WRITE_CHANNEL_NOT_CONNECTED`，不得直接开始业务。

## 最终放行门

无论Harness、DSH还是Work，开始生产前都必须同时通过：

- `doctor`在线认证与字段检查；
- `discover`实时分页读取；
- `prepare`真实来源附件下载；
- 专用记录附件上传/字段写入/恢复；
- 唯一写入者确认；
- EGO/ChatGPT登录与下载能力检查。

任何一项缺失，只能停在准备阶段，不能把“已安装Skill”称为“全流程接通”。

## 飞书官方参考

- [新增多维表格记录](https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/create)
- [多维表格开发与权限指南](https://open.feishu.cn/document/base-extensions/base-table-view-extension-development-guide)
- [多维表格开放接口常见问题](https://open.feishu.cn/document/docs/bitable-v1/faq?lang=zh-CN)
