---
name: graphic-video-orchestrator
description: 从飞书或兼容表格实时领取尚无成品视频的图文记录，完成本地路由、AI网页生图/生视频、产物校验、附件写回和实时回读。适用于ChatGPT Work控制器、DeepSeek Harness/Honey＋EGO控制器及其恢复执行；不用于绕过测试门禁或并发写同一记录。
---

# 图文视频全流程编排

先读取项目的`config/config.local.yaml`。没有该文件、`production.enabled`未开启或唯一写入者不成立时，只能执行离线测试和只读发现。

## 必读资料

- 执行真实记录前读[references/workflow-contract.md](references/workflow-contract.md)。
- 使用DeepSeek Harness/Honey或ChatGPT Work时，读[references/controller-contract.md](references/controller-contract.md)。
- 配置另一台电脑、另一个Base或另一个业务项目时，读[references/provider-configuration.md](references/provider-configuration.md)。

## 执行入口

1. `gvflow doctor --config ...`检查配置、依赖、认证和写入门禁。
2. `gvflow discover --config ...`实时扫描。只领取分类匹配、来源唯一，且成品/已发布两列都没有视频的记录。
3. 对每个record_id执行`prepare`，检查第0阶段接触表并提交结构化decision。
4. 执行`finalize-stage0`。普通路线执行`reserve-background`，律师路线选择最匹配人物照但不占用蓝色背景游标；然后执行`plan`生成`execution_plan.json`。
5. 按计划逐项操作网页。普通路线的01、02使用不同聊天；每个分支在同一聊天连续生图、生视频。生图只上传对标完整页；其他固定素材和规则只按Space路径调用。视频源在各分支的视频步骤上传一次原视频，静态图片源不新增附件。
6. 下载真实MP4后用`record-result`登记。只有产物齐全且普通双分支SHA不同，才执行`writeback`。
7. 写回后必须实时读取同一record_id，核验附件名、大小、file_token、状态、备注和执行记录；只有此时才提交背景游标。
8. 单行失败保存事件与恢复点并继续下一行；全部处理后重新从表格实时扫描。可执行候选为0才结束。

不要把驱动退出、页面回复、聊天URL或本地文件存在当成完成证据。
