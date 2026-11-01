# 数据源与业务配置

## 配置分层

- `config/example.yaml`：可提交的程序结构。
- `config/business-profile.example.yaml`：可提交的路线示例。
- `config/config.local.yaml`：真实Base、字段、Space路径、工作目录和控制器命令；被Git忽略。
- 密钥：只放环境变量或系统钥匙串，不写YAML。

## 飞书字段

必须配置分类、三个来源优先字段、成品、已发布、状态、备注和执行记录。程序按字段名读取，但写入前应通过元数据确认字段存在。附件写入必须保留已有有效附件，除非明确启用同名替换。

姜律师profile的分类映射为：`classification=二次分类型`是优先级一，`classification_fallback=类型`是优先级二，两者期望值都是`图文`。优先级二命中时不限制二次分类型是空还是其他值。

## 多电脑

每台电脑使用不同actor_id和独立runs_dir。没有跨机器租约字段时，只能运行一个生产写入者。另一个AI可执行离线测试、只读扫描或不同Base，不能同时清同一张表。

## 密钥后端

优先使用操作系统密钥库：macOS使用`macos_keychain`，Windows使用`windows_credential`。Windows目标名和账号写在配置中，App Secret由`scripts/setup_windows_feishu.ps1`安全写入Windows凭据管理器。环境变量只用于临时CI测试；不得把真实`.env`提交Git。

EGO已安装不代表飞书已就绪。还要单独验证应用scope、目标Base文档权限、附件上传、字段更新和实时回读。见`docs/FEISHU_PREPARATION.md`。
