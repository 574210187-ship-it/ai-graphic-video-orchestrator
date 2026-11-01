# 全流程合同

## 未执行口径

记录先按两级或条件命中分类：

1. 优先级一：`classification`字段等于`classification_value`；
2. 优先级二：`classification_fallback`字段等于`classification_fallback_value`，不限制优先级一字段为空或其他值。

两者任意满足一个即命中；两者都命中时只领一次并归入优先级一。然后还必须同时满足：

1. 来源优先级中第一个非空字段恰有一个可用附件；
2. 成品字段不存在视频附件；
3. 已发布字段不存在视频附件；
4. record_id不在denylist中。

任一输出列已有视频都不属于全新未执行。不能只看状态字段或历史队列。

## 状态机

`DISCOVERED → LEASED → SOURCE_DOWNLOADED → STAGE0_READY → PLANNED → EXECUTING → ARTIFACTS_READY → WRITTEN → READBACK_VERIFIED → COMPLETED`

每次状态变化写`events.jsonl`，至少包含run_id、record_id、actor_id、状态、时间和证据路径。错误必须包含error_code、summary、next_action和dedupe_key。

## 产物门禁

- 普通单页/多页：必须有01和02两个MP4，文件SHA-256不得相同。
- 单页中心人物：必须有一个lawyer MP4。
- 多页中心人物或业务profile禁用的路线：阻塞并跳过，不得降级。
- MP4必须有有效ISO BMFF魔数，大小超过配置下限。
- 部分产物可以进入salvage，但不能写完成状态。

## 写回门禁

先上传附件并实时回读附件名、大小和file_token，再更新状态、备注和执行记录，最后再次回读。只有全部一致才完成。背景游标等共享状态只能在完整回读后提交。

## 全量清零

单行错误不得中断全批。保存salvage并进入恢复队列，继续执行后续记录。首轮结束后有界恢复，仍无法执行的记录进入阻塞清单。最终重新实时扫描整表：可执行未完成数为0才可结束。
