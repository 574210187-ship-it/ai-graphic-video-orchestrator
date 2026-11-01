# 远程 DeepSeek Harness＋EGO 交接

本文件用于另一台电脑上的DeepSeek Harness。Harness不在仓库制作电脑上；不得引用制作电脑的进程、路径或登录态。

## 一、一次性安装

1. 在目标电脑克隆本仓库的私有GitHub地址。
2. 确认Python 3.9以上、Git和FFmpeg可用，尤其`ffprobe -version`可正常执行；再运行`scripts/bootstrap.sh`。
3. 把`skills/graphic-video-orchestrator`加入Harness的自定义Skill目录；若Harness只能读取固定目录，运行：

```bash
python3 scripts/install_skill.py --target /目标电脑/Harness技能根目录
```

4. 复制`config/example.yaml`为`config/config.local.yaml`，复制`config/business-profile.example.yaml`为`config/business-profile.local.yaml`。
5. 只在目标电脑私有配置中填写飞书Base/Table、字段、Space路径、规则版本、运行目录与唯一ActorID。密钥只放环境变量或系统钥匙串，禁止提交Git。
6. 确认目标电脑已经安装并登录EGO浏览器和ChatGPT网页；使用后台TaskSpace，不抢占用户前台浏览器。

## 二、强制测试门禁

必须按顺序通过，任何一步失败都不得直接开启全量生产：

1. `gvflow doctor --offline`和`pytest -q`。
2. fixture端到端：普通双分支、律师单分支、单行失败后继续下一行、半写回恢复。
3. 飞书只读`doctor`和`discover`，核对候选数量和字段，不写表。
4. 三条专用测试记录：普通单页、普通多页、单页中心律师。逐条完成网页生成、真实MP4、飞书写回和实时回读。
5. 重启Harness后重新`discover`，已完成测试记录不得再次领取。

## 三、每条记录的固定动作

1. `prepare`：下载唯一来源，生成`task_manifest.json`并固化来源SHA。
2. `stage0-prepare`：生成候选帧和接触表。
3. Harness自行看接触表并生成`decision.json`：
   - 正文完整重启才算新页；像素小差异不算新页。
   - 中心律师只在人物是叙事核心时成立，路人或小配角忽略。
   - 允许路线只有`single_no_lawyer`、`multi_no_lawyer`、`single_lawyer`。
   - `multi_lawyer`当前阻塞并跳过，不能自行降级。
   - 视频选每页最后稳定完整帧；静态图只有一页。
4. `finalize-stage0`：固化路由和`对标完整页_XX.png`。
5. 普通路线执行`reserve-background`；律师路线根据对标人物姿势选择最接近的人物Space路径，写入decision，不占用背景游标。
6. `plan`：只执行生成的`execution_plan.json`，不要凭记忆拼提示词。
7. EGO后台网页执行：
   - 普通01和02各开独立聊天；律师路线开一个lawyer聊天。
   - 每个分支先生图，再在同一聊天生视频，不跨分支复用生成图。
   - 生图步骤只上传本轮对标完整页；固定蓝底、人物照、MD由提示词中的Space路径读取，不上传ZIP或MD。
   - 视频步骤不新开聊天；视频源只在该分支上传一次原视频，静态图片源不新增附件；视频规则包由Space路径调用，不上传ZIP。
   - 多页视频只用共用背景和全部透明文字层，不用多页成品图；单页使用该路线规定的背景、透明文字和成品图。
   - 网页声称完成但没有可下载MP4.zip，不算完成。
8. 下载并解包最终MP4，运行`record-result`。普通路线必须同时登记01和02，且SHA不同；律师路线登记lawyer。
9. `writeback`：程序上传成品、更新状态/备注/执行记录并实时回读。回读通过后才提交背景游标并按配置删除本地MP4。
10. 重新读取该行确认终态，再处理下一行。

## 四、全量排空规则

- 每次循环都从飞书实时`discover`，不要使用历史候选清单替代实时状态。
- 单行失败写`last_error.json`和事件，保存已合格分支，加入恢复队列，然后立即继续下一行。
- 内容审核、单页错误或某个网页失败都不是全局停止理由。
- 只有登录/扫码、飞书权限、磁盘不可写、EGO整体不可用等全局人工阻塞才暂停全批。
- 首轮遍历完后，再对恢复队列做有界恢复；无法执行的行写准确错误码和下一步，但不能阻断其他行。
- 最后必须重新全表扫描。可执行候选为0才可报告清零；PID存在、聊天回复完成、驱动退出都不是清零证据。

## 五、必须保留的痕迹

每行至少保留：来源token/字节/SHA、第0阶段decision、参考页SHA、execution_plan、聊天URL、最终MP4字节/SHA、飞书远端file_token、字段回读、事件JSONL、失败与恢复记录。不得删除云端聊天，除非用户另行明确要求。
