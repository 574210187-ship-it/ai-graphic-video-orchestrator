# 控制器合同

## 统一输入

控制器只接收`task_manifest.json`绝对路径。清单包含来源、路由、对标完整页、分支动作、Space规则路径、允许上传的附件和预期产物。

## 统一输出

控制器必须生成`controller_result.json`：

```json
{
  "ok": true,
  "engine": "deepseek-harness-ego",
  "record_id": "rec...",
  "artifacts": [
    {"branch": "01", "path": "/absolute/a.mp4", "chat_url": "https://..."},
    {"branch": "02", "path": "/absolute/b.mp4", "chat_url": "https://..."}
  ],
  "errors": []
}
```

路径必须绝对，文件必须真实存在。网页回复“完成”但没有可下载MP4时`ok=false`。

## 远程DeepSeek Harness/Honey＋EGO

该控制器运行在安装Harness的目标电脑，不要求与仓库制作电脑相同。AI负责第0阶段语义判断、人物匹配和定点纠错；EGO只负责后台页面动作。每个record_id一个TaskSpace，普通01/02为两个独立页面，单分支内部生图和生视频不换聊天。跨电脑只传GitHub代码和脱敏配置模板，密钥、登录态及本地路径由目标电脑单独配置。

## ChatGPT Work

先运行能力探测：创建子聊天、上传本轮附件、续写同聊天、下载MP4、返回URL、删除测试聊天。原生能力任一项不成立时，Work不能假装已执行，必须调用本地Work Bridge。Bridge继续使用相同任务清单和控制器输出合同。

## 失败处理

单分支失败只影响本记录。保留已合格分支，恢复时只补缺失分支，但最终写回负载必须合并salvage和新产物。登录、权限或全局浏览器不可用才允许停止全批。
