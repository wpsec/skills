# 日志家族映射

本文件是给 `aliyun-sls-sop` skill 和维护者使用的内部参考，不是给最终使用者单独阅读的操作手册。

它的作用只有一个：当 skill 拿到一份日志样本时，帮助它快速判断“这更像哪一类日志”，然后选择更合适的模块目录、文件命名、分析主线和文档骨架。

说明：

- 普通使用者即使不知道这个文件存在，也不影响使用 skill。
- 只有在维护 skill、扩展新日志类型、或排查为什么命中了某个模板时，才需要看这个文件。
- 如果你觉得“日志家族映射”这个名字太抽象，可以把它理解成“日志类型到文档模板的路由表”。
- skill 单独迁移到别的仓库时，应优先使用“便携默认命名”；只有当用户明确要求对齐现有目录时，才参考下表里的仓库示例命名。

## 1. 使用方式

- 先根据字段特征判断最接近的日志家族。
- 再按该家族的便携默认命名或目标仓库现有命名生成文档骨架。
- 如果样本和任何现有家族都不完全匹配，回退到 `通用结构化日志`，不要强行套错模板。

## 2. 家族总览

| 家族键 | 中文名称 | 典型字段特征 | 便携默认目录 | 仓库示例目录 | 默认主线 |
| --- | --- | --- | --- | --- | --- |
| `network_flow` | 网络流日志 | `srcaddr/dstaddr/action` | `network_flow_log` | `vpc_log` | 基线 -> 异常流量 -> 分级响应 -> 根因排查 -> 闭环 |
| `object_storage_access` | 对象存储访问日志 | `bucket/object/operation` | `object_storage_access_log` | `oss_log` | 基线访问 -> 异常读写 -> 分级响应 -> 归因 -> 闭环 |
| `database_audit` | 数据库审计日志 | `db/sql/user` | `database_audit_log` | `rds_log` | 基线 SQL -> 异常操作 -> 分级响应 -> 根因排查 -> 闭环 |
| `waf_or_edge_security` | WAF 或边界安全日志 | `client_ip/domain/rule_id/attack_type` | `waf_security_log` | `waf_log` | 攻击趋势 -> 高危命中 -> 处置 -> 溯源 -> 规则优化 |
| `network_device_or_firewall` | 网络设备或防火墙日志 | `srcip/dstip/device/policy` | `network_device_log` | `net_log` | 访问策略 -> 异常命中 -> 处置 -> 策略核查 -> 闭环 |
| `generic_structured_log` | 通用结构化日志 | 以上都不稳定命中 | `structured_log` | `sls_log` | 字段建模 -> 异常识别 -> 处置建议 -> 后续补充 |

## 3. 各家族细化规则

### `network_flow`

- 典型字段：
  - `srcaddr`、`dstaddr`、`srcport`、`dstport`
  - `action`、`direction`、`protocol`
  - `bytes`、`packets`
  - `vpc-id`、`eni-id`、`vm-id`
- 默认文档集合：
  - `README.md`
  - `overview.yaml`
  - 便携默认：`network_flow_<env>_datasources.yaml`、`network_flow_analysis_sop.yaml`、`network_flow_report_template.md`
  - 仓库示例：`vpc_<env>_datasources.yaml`、`vpc_flow_analysis_sop.yaml`、`vpc_flow_report_template.md`
- 常见分析方向：
  - 安全：暴露面、异常来源、敏感端口、横向移动
  - 运维：REJECT 比率、流量波动、连通性异常
  - 治理：拓扑、访问关系、白名单沉淀
- 默认不要硬编码：
  - IP、端口热点值、VPC/ENI/VM ID、样本文件名

### `object_storage_access`

- 典型字段：
  - `bucket`、`object`、`host`
  - `operation`、`http_status`、`error_code`
  - `client_ip`、`requester_id`
  - `response_time`、`response_body_length`
- 默认文档集合：
  - `README.md`
  - `overview.yaml`
  - 便携默认：`object_storage_access_<env>_datasources.yaml`、`object_storage_access_analysis_sop.yaml`、`object_storage_access_report_template.md`
  - 仓库示例：`oss_<env>_datasources.yaml`、`oss_access_analysis_sop.yaml`、`oss_access_report_template.md`
- 常见分析方向：
  - 安全：异常下载、越权访问、可疑导出、配置变更
  - 运维：失败高峰、链路抖动、延迟异常
  - 业务：对象覆盖、目录错写、上传异常
- 默认不要硬编码：
  - bucket 名、对象路径、request id、访问身份、样本文件名

### `database_audit`

- 典型字段：
  - `db`、`user`、`sql`
  - `client_ip`、`thread_id`
  - `fail`、`latency`
  - `return_rows`、`update_rows`
- 默认文档集合：
  - `README.md`
  - `overview.yaml`
  - 便携默认：`database_audit_<env>_datasources.yaml`、`database_audit_analysis_sop.yaml`、`database_audit_report_template.md`
  - 仓库示例：`rds_<env>_datasources.yaml`、`rds_audit_analysis_sop.yaml`、`rds_audit_report_template.md`
- 常见分析方向：
  - 安全：越权、脱库、敏感 SQL、破坏性操作
  - 运维：慢 SQL、失败重试、发布回归
  - 业务：事务异常、批量写入异常、链路回溯
- 默认不要硬编码：
  - 库名、用户名、SQL 文本片段、thread id、来源 IP

### `waf_or_edge_security`

- 典型字段：
  - `client_ip`、`domain`
  - `rule_id`、`attack_type`
  - `http_method`、`request_uri`
  - `action`、`status`
- 默认文档集合：
  - `README.md`
  - `overview.yaml`
  - 便携默认：`waf_security_<env>_datasources.yaml`、`waf_security_analysis_sop.yaml`、`waf_security_report_template.md`
  - 仓库示例：`waf_<env>_datasources.yaml`、`waf_attack_analysis_sop.yaml`、`waf_attack_report_template.md`
- 常见分析方向：
  - 安全：攻击类型、来源 IP、误报与真实拦截
  - 运维：规则漂移、拦截激增、日志完整性
  - 业务：误拦截、业务入口影响
- 默认不要硬编码：
  - 域名、来源 IP、URI 片段、规则命中热点

### `network_device_or_firewall`

- 典型字段：
  - `srcip`、`dstip`
  - `device_name`、`policy_name`
  - `protocol`、`action`
  - `srcport`、`dstport`
- 默认文档集合：
  - `README.md`
  - `overview.yaml`
  - 便携默认：`network_device_<env>_datasources.yaml`、`network_device_analysis_sop.yaml`、`network_device_report_template.md`
  - 仓库示例：`net_<env>_datasources.yaml`、`net_device_analysis_sop.yaml`、`net_device_report_template.md`
- 常见分析方向：
  - 安全：策略命中、异常访问、暴露面
  - 运维：设备抖动、策略漂移、链路异常
  - 治理：策略优化、白名单和例外梳理
- 默认不要硬编码：
  - 设备名、策略名、源/目的 IP、热点端口

### `generic_structured_log`

- 适用条件：
  - 当前字段无法稳定归类到以上家族
  - 或者用户先要一份通用 SOP 骨架
- 默认文档集合：
  - `README.md`
  - `overview.yaml`
  - 便携默认：`structured_<env>_datasources.yaml`、`structured_analysis_sop.yaml`、`structured_report_template.md`
  - 仓库示例：`sls_<env>_datasources.yaml`、`sls_generic_analysis_sop.yaml`、`sls_generic_report_template.md`
- 策略：
  - 强调字段建模和运行时解析
  - 不预设过多业务语义
  - 只输出当前字段能支撑的查询、流程和结论

## 4. 家族选择守则

- 同时命中多个家族时，优先选择字段语义更明确的家族。
- 如果只是目录名像某个家族，但字段不匹配，以字段为准。
- 如果用户明确指定日志类型，以用户输入为准；但如果样本字段明显矛盾，要在结果里指出。
- 任何家族下，样本里的热点对象、资源 ID、IP、设备名都默认属于动态事实，不进入永久规则。
