---
name: aliyun-sls-sop
description: 根据仓库既有规范、同级目录文档、模板和阿里云 SLS project、本地抓取目录、CSV/CSV.GZ 等结构化日志工件生成或更新文档。可用于从 index/dashboard/alert/scheduled_sql/saved_search 抽取 SLS 资产，生成 overview.md 或 SKILL.md，也可继续沉淀成 README、overview.yaml、datasource 配置、analysis_sop、report_template、审计报告、巡检清单等仓库模块文档。
---

# 阿里云 SLS SOP

## 快速开始

1. 先读取目标目录的同级文档。如果用户要求“和现有目录对齐”，同级文件是第一约束。
2. 先按 [references/intake-patterns.md](references/intake-patterns.md) 识别输入模式和环境。
3. 如果输入是 SLS project、本地 project/logstore 目录、index/dashboard/alert/scheduled_sql/saved_search 资源，或用户说“继续上次生成”，先读 [references/sls-project-workflow.md](references/sls-project-workflow.md)。
4. 如果用户提供 CSV 或 CSV.GZ 日志样本，先执行 `python3 scripts/profile_csv.py <csv-path>`；需要快速起骨架时再执行 `python3 scripts/generate_scaffold.py <csv-path> --out-dir <目标目录>`。
5. 如果用户要“修改现有 SOP 仓库”“新增 workflow / module / datasource / correlation YAML”“把说明书式 YAML 收敛成可执行 schema / contract”，先读 [references/executable-contracts.md](references/executable-contracts.md)。
6. 在决定最终产物前，先读 [references/output-modes.md](references/output-modes.md) 和 [references/doc-types.md](references/doc-types.md)。
7. 在判断日志家族和默认命名之前，读 [references/log-families.md](references/log-families.md)。
8. 如果用户要沉淀 Prometheus、MetricStore、容器内存、CPU、资源使用率、request/limit、告警事件与 K8s 事件的联动能力，按本文“通用能力：指标告警与资源类 SOP”生成可复用模块和 contract。
9. 如果用户要沉淀 Pod 重启、BackOff、CrashLoopBackOff、OOMKilled、Killing、Unhealthy、发布后重启、镜像变更与 K8s audit 联动能力，按本文“通用能力：Kubernetes 重启与发布变更 SOP”生成可复用模块和 contract。
10. 收尾前按 [references/output-contracts.md](references/output-contracts.md) 对照检查。

## 通用规则：可执行联动优先

- SOP 中的 `handoff` 默认是可执行的下一步，而不是报告里的泛泛建议；能从当前证据确定目标模块和数据源时，必须写成“继续查询 / 必须补证”的执行要求。
- SLS `project`、`logstore`、`metric_store` 中的长哈希后缀不默认视为容器 ID、Pod ID 或一次性运行对象；必须先通过 SLS project / logstore / metricstore 元数据核实其资源类型和稳定性。
- 已确认稳定的 `project/logstore/metric_store` 只能沉淀到 `*_datasources.yaml`、`log-sources/overview.yaml` 或等价 datasource 配置层；`SOP.md`、`README.md`、模块 `overview.yaml`、workflow 和 analysis_sop 的导航/执行描述优先引用 `source_alias`、`datasource_config` 和运行时解析规则，避免把同一环境事实到处复制。
- 验证候选 logstore 存在性时，优先使用当前可用的 `aliyun sls ListLogStores` 或等价能力；不要臆造 `sls_list_logstores`、`ListSLSLogstores` 等未在可用工具列表中的工具名。
- 当工具不可用或权限不足时，报告写清 `source_alias/project/logstore/time_window`、验证状态和失败点；不能把“未验证 / 工具不可用”写成“无数据”。
- K8s `BackOff`、`CrashLoopBackOff`、`OOMKilled`、`Killing`、`Unhealthy`、Pod 频繁重启等运行事件只能先作为 `direct_trigger / symptom_evidence`；必须继续补 Kubernetes audit `pods/status`、Deployment `patch/update`、指标和工作负载日志，才能判断中间原因或最终根因。
- 对 `backend -> postgresql` 场景，若应用日志命中数据库连接池、HikariCP、`Connection is closed`、`datasource`、`connection pool`、`SQLTransientConnectionException`、SQL 或事务相关异常，backend 模块必须带着应用侧证据继续查询 PostgreSQL 模块；只有 PostgreSQL 查询失败、无权限、无数据源或工具不可用时，才允许输出 `root_cause_evidence_status=needs_handoff`。
- 跨模块报告必须压缩成一条可扫读的分析链，例如 `backend 症状 -> PostgreSQL 补证 -> 当前结论 / 缺失证据`，不要把入口模块和联动模块的完整报告简单拼接成超长输出。
- 自动联动后的报告优先保留结论、关键证据、已确认层级、缺失证据和下一步动作；聚合表、长日志片段和重复背景只保留能支撑判断的最小必要内容。

## 先路由任务

### 模式 A：仓库文档套件模式

- 适用于“目录结构对齐”“补齐整套文档”“沉淀 SOP 模块”“生成 README、overview.yaml、datasource、analysis_sop、report_template”这类请求。
- 先抽取 `environment`、`system/product`、`time range`、`artifact type`、`document type`、`analysis direction`。
- 把 `分析 某某 环境 某某 最近的事件` 这类输入当成结构化入口，而不是普通自由文本。
- 如果用户说“继续做某类日志的 SOP”，默认补齐目标目录下同类型模块常见的整套文档，除非仓库已有更小的固定模式。
- 当前仓库里的 `waf`、`nat`、`slsaudit-center` 等目录只属于写法参考源，不属于固定输出结构。

### 模式 B：SLS 资源流水线模式

- 适用于用户直接给出 SLS project、本地抓取目录、单个 logstore 目录，或者明确要求“从 index/dashboard/alert/scheduled_sql/saved_search 生成 SOP / SKILL / overview”。
- 这个模式先走 project 级数据抓取、预处理、精选、模板归一化、可选验证、断点恢复和审计，再决定最终落成 overview.md、SKILL.md 或仓库文档套件。
- 详细步骤和命令都在 [references/sls-project-workflow.md](references/sls-project-workflow.md)；执行时按需读取 `rules/*.md`。

### 模式 C：SOP 可执行 Contract 模式

- 适用于“让 sop-chat / agent 能直接消费 YAML”“补 workflow / step / handoff”“把导航型 overview.yaml 升级成可执行 contract”“给联动分析补 schema”这类请求。
- 这个模式不是替代文档套件，而是在已有 `SOP.md`、`overview.yaml`、`workflows/overview.yaml`、模块 `overview.yaml`、`log-sources/overview.yaml`、`correlation-keys/overview.yaml` 之上补机器可执行字段。
- 默认同时维护两层内容：
  - 人类可读层：说明、路由、边界、维护提示。
  - 机器可执行层：`schema`、`schema_reference`、`workflow_id`、`module_id`、`entry_hints`、`execution`、`steps`、`depends_on`、`run_if_any`、`produces`。
- 详细规则读 [references/executable-contracts.md](references/executable-contracts.md)。

### 特殊组合：指标告警 + 资源根因分析

- 适用于用户提到 Prometheus、MetricStore、容器内存、CPU、资源使用率、request/limit、OOM、Evicted、Pod 重启、监控告警事件、“为什么内存高 / CPU 高 / 资源高”等请求。
- 默认不要把这类问题塞进 backend、database 或 alert-entry 单模块里。告警入口、指标事实、运行事件和工作负载日志必须分层。
- 如果仓库已有告警入口模块，告警入口只负责 `direct_trigger` 和入口分类；指标类事实必须由 `metrics`、`prometheus` 或等价模块承接。
- 如果仓库没有指标模块，但已有 MetricStore / Prometheus 数据源或资源类告警，应优先补出一个可复用指标模块五件套，再把根入口、workflow、log-sources、correlation-keys 接上。

### 特殊组合：Kubernetes 运行事件 + Pod 重启根因分析

- 适用于用户提到 Pod 重启、最近重启原因、BackOff、CrashLoopBackOff、OOMKilled、Killing、Unhealthy、Probe failed、发布后异常、镜像 tag 变化、Deployment 回滚或 K8s event / audit 联动分析。
- 默认不要把这类问题只写进 `k8s-event` 模块。运行事件只能确认触发事实，Pod `status`、Deployment 变更、指标和工作负载日志必须分层补证。
- 如果仓库已有 `k8s-event`、`k8s` / `k8s-audit`、`prometheus` / `metrics` 和工作负载模块，必须把 workflow 串成可执行链路；如果缺模块，应优先补齐缺失模块五件套或至少在 `log-sources`、`overview`、`analysis_sop` 中声明可执行 handoff。
- 默认 handoff 顺序：

```text
k8s-event
  -> k8s/k8s-audit
    -> prometheus/metrics
      -> workload-specific runtime logs
        -> summarize evidence state
```

- 若目标环境没有 Kubernetes audit 数据源，也必须在 SOP 中保留 `pods/status / deployment patch` 的补证步骤，并把查询状态写为 `unavailable / no_permission / not_configured`，不能直接省略。
- 若目标环境有 audit 数据源，Pod 重启类 workflow 必须查询 `pods/status` 子资源，提取 `lastState.terminated.reason`、`lastState.terminated.exitCode`、`lastState.terminated.finishedAt`、`restartCount`、`state.waiting.reason`。
- 若同窗口出现 Pod 创建、ReplicaSet 切换、镜像拉取、Deployment patch/update 或 revision 变化，必须查询 Deployment 变更，提取镜像 tag、revision、操作主体和状态码。
- Deployment 的 `requestObject / responseObject` 可能包含环境变量、Token、连接串或密码；报告和模板只允许输出字段摘要，不得粘贴完整对象。
- 如果应用日志或 stdout 没有命中，报告必须写清实际查询过的 `source_alias/project/logstore/time_window`、logstore 是否存在、是否可访问、查询语句或关键条件；未查询只能写“未查询”，查询失败写“查询失败”，不能写成“无数据”。
- 只有拿到应用崩溃日志、previous logs、配置差异、依赖异常、资源限制、发布内容差异或代码异常最底层证据，才能把最终根因状态写为 `confirmed`。`Error / exitCode=1` 只能确认进程异常退出这一中间层。

### 特殊组合：Project 索引 + 模块五件套

- 如果用户同时要 project 级索引和 leaf 五件套，不要让他二选一。
- 默认结构是：
  - 根目录 `SOP.md`
  - project 目录 `overview.md`
  - 每个 module 目录下的 `README.md`、`overview.yaml`、`*_datasources.yaml`、`*_analysis_sop.yaml`、`*_report_template.md`
- 这种情况下，project `overview.md` 默认链接到各 module 的 `README.md`。

## 模式 A：仓库文档套件模式

### 1. 正确识别环境，不要写死

- 先用用户输入。
- 再用 datasource 元数据或文件元数据。
- 再用同级文档。
- 不要把当前仓库环境默认成通用事实。
- 如果仓库是 UAT，但用户要的是 PROD 或其它环境，文档结构要保持可复用，不能把 UAT 专有标识泄漏进新文档。

### 2. 从日志和工件里抽事实，不要硬编码

- 如果有 CSV，先用 `scripts/profile_csv.py` 做字段画像。
- 如果需要快速起一套骨架，再用 `scripts/generate_scaffold.py` 输出初稿。
- 区分稳定事实和运行时事实。
- 只有稳定事实才能写入 datasource 这类配置型文档。
- 样本里的对象名、设备名、bucket 名、IP、表名、request id 等，默认都当动态事实处理，除非用户明确确认它们是长期稳定值。
- 除非用户明确要求，否则不要把样例文件名写进永久 SOP。
- 如果没有现成目录风格可以对齐，优先生成可独立迁移的便携骨架，而不是复刻当前仓库里的模块名。

### 3. 同时覆盖业务、运维、安全三个方向

- 默认同时考虑 `business`、`ops`、`security`。
- 根据当前日志字段决定哪个方向是主线。
- 如果某个方向的结论缺少字段支撑，要直接说明，并指出还需要什么数据。
- 如果字段模式能稳定命中某个日志家族，就优先使用对应家族的默认文档套件和主线。

### 4. 生成正确的文档集合

- 如果是仓库级文档套件，按 [references/doc-types.md](references/doc-types.md) 的职责划分生成。
- 如果用户只要一个文件，只改那一个文件。
- 如果用户想做成可复用模块，优先补齐这一套：
  - `README.md`
  - `overview.yaml`
  - `*_datasources.yaml`
  - `*_analysis_sop.yaml`
  - `*_report_template.md`
- 只有当用户明确要求“和现有目录对齐”时，才借用目标仓库同级文件的命名和章节分工。
- 如果用户还要求联动分析、步骤编排或给 agent 直接消费，继续按 [references/executable-contracts.md](references/executable-contracts.md) 为 `overview.yaml`、工作流索引和关联键索引补机器可执行字段，而不是只停在说明文字。

### 5. 先解决同类日志冲突，再生成文档

- 在创建新模块或新增 logstore 子模块前，先检查仓库里是否已经存在同类日志家族的专项模块、审计中心子模块或其它入口。
- 如果同类日志只存在一个入口，直接把它定义为主事实源。
- 如果同类日志同时存在多个入口，先定义主事实源和补证源，再继续生成文档，不要让两个入口在职责上重叠。
- 默认规则：
  - 专项产品模块 = 主事实源
  - 审计中心 / 聚合入口中的同类子模块 = 补证源
  - 如果仓库中没有专项模块，则聚合入口子模块自动升级为主事实源
- 主事实源负责产品专属语义、资产别名、白名单治理、误报与绕过判断、最终定性。
- 补证源负责统一审计入口、横向审计、时间线补证和跨产品串联。
- 正式报告和模板必须显式记录 `source_alias`、`project/logstore`、`time_window`；如果存在多入口同类日志，还要记录 `source_role`。
- 如果用户的问题已经落在专项模块职责中，例如 WAF 告警、白名单、资产别名、误报或绕过，不要继续停留在聚合入口；应在 `overview.yaml` 里生成明确的 handoff 规则。
- 如果两个入口都保留，至少同步生成这些约束：
  - `README.md`：写清职责边界、主事实源 / 补证源关系
  - `overview.yaml`：写清任务路由和 handoff 条件
  - `*_datasources.yaml`：增加 `source_governance` 或等价稳定元数据，记录 `log_family`、`source_role`、主入口 / 补入口
  - `*_report_template.md`：要求最终输出显式记录 `source_role`

### 6. 收尾前做质量检查

- 文件命名、语气和职责要和同级文档一致。
- 输出必须能跨环境复用。
- 样本推导值在未确认稳定前，不能进入永久规则。
- 输出结果必须满足 [references/output-contracts.md](references/output-contracts.md) 的最低要求。
- SOP 必须包含触发条件、执行步骤、判断标准、升级路径、记录要求。
- 报告模板必须覆盖 SOP 承诺的输出结果，并包含纯文本根本原因分析证据链图（使用 text 代码块，禁止 Mermaid）。
- 对所有告警、运行事件和异常分析 SOP，内部 contract 必须区分 `direct_trigger / symptom_evidence / intermediate_cause / root_cause_evidence / root_cause_evidence_status`；报告可见模板必须使用中文字段：直接触发器、触发证据、中间原因、中间证据、最终根因、根因证据、证据状态、已确认层级、下一跳补证。告警名称、阈值命中、状态码、事件 reason、错误数量、延迟指标等触发事实不能直接写成根因，必须要求能解释触发事实的补证日志、指标、配置、变更或依赖证据。
- 当用户问“原因 / 根因 / 为什么”时，SOP 的交付目标是解释告警，不是证明告警成立；生成的 workflow 必须沿 `direct_trigger -> symptom_evidence -> intermediate_cause -> final_root_cause` 继续下钻，直到取得可操作原因，或明确列出已穷尽的数据源、缺失证据和下一跳查询。
- `root_cause_evidence_status=confirmed` 只允许用于最终可操作原因，例如具体配置变更、缺失配置、依赖服务异常、资源限制、代码异常最底层 `Caused by`、权限/策略拒绝或容量瓶颈；应用启动失败、Probe 失败、BackOff、5xx、ERROR 聚合、`BeanCreationException` 等只能作为中间原因或症状，除非已补到更底层解释证据。
- 对已经具备明确目标模块和数据源的 handoff，不要只在处置建议里写“建议联动”；必须在 workflow / overview / analysis_sop 中声明执行器应继续查询。只有目标数据源无法查询、查询失败或缺少权限时，才输出 `needs_handoff`，并写清失败点。
- 报告模板必须把“已确认层级”和“最终根因状态”分开：内部 contract 可以写 `direct_trigger_confirmed / intermediate_cause_confirmed / final_root_cause_confirmed`，报告可见层写成“触发事实已确认 / 中间原因已确认 / 最终根因已确认”和“已确认 / 证据不足 / 需联动”，不能把中间原因包装成最终根因。
- 根因证据必须给足排障上下文：可用时列出 3-5 条关键日志 / 指标 / 配置 / 变更片段；应用异常至少保留异常类型、关键 message、最底层 `Caused by` 和对应时间 / 对象 / trace，避免只给一句摘要导致无法修复。
- 自动联动或多模块联动报告必须限制体量：优先输出“结论 / 分析链 / 关键证据 / 缺失证据 / 下一步动作”，避免重复整段粘贴上游模块报告；长表格只保留 Top 3-5 项。
- README 和 overview 必须把读者路由到下一个正确文件。

## 通用能力：指标告警与资源类 SOP

这部分能力用于任何需要沉淀“告警事件 -> 指标事实 -> 运行事件 -> 工作负载日志 -> 根因证据”的 SOP 仓库，不绑定具体环境、project、logstore、租户或 Pod。

### 1. 什么时候新增指标模块

满足任一条件时，优先新增或完善 `metrics` / `prometheus` / `observability-metrics` 等指标模块，而不是把规则写死在业务模块里：

- 仓库中存在 Prometheus、MetricStore、时序指标、CMS 告警中心或云监控告警数据源。
- 用户问题包含容器内存、CPU、资源使用率、request、limit、OOM、Evicted、重启计数、指标阈值。
- 现有告警入口只能证明规则触发，无法稳定给出 namespace、pod、container、metric_name、当前值、峰值或趋势。
- 同一个资源类问题需要同时联动告警事件、MetricStore、K8s event、应用日志或数据库日志。

### 2. 指标模块默认五件套

如果目标仓库使用模块五件套，指标模块默认输出：

- `README.md`：写清指标模块职责、文件清单、读取顺序和边界。
- `overview.yaml`：写清 `entry_hints`、`task_routing_rules`、`execution`、`handoff` 和证据要求。
- `*_datasources.yaml`：登记告警事件源、告警执行源、MetricStore / PromQL 源、K8s 事件源和工作负载补证源。
- `*_analysis_sop.yaml`：写清从告警触发、指标范围、趋势、request/limit、运行事件到根因判断的步骤。
- `*_report_template.md`：必须包含指标证据表、K8s 事件表、工作负载日志表、根因证据链和证据状态。

模块命名必须跟随目标仓库风格；没有先例时优先使用 `prometheus` 或 `metrics`，不要把当前仓库的模块名硬编码进 skill。

报告模板是输出排版文件，不是分析入口。若执行器先读取了 `*_report_template.md`，必须回读同模块 `overview.yaml`、`*_datasources.yaml` 和 `*_analysis_sop.yaml` 后才能查询或输出。

### 3. 分层职责

指标类 SOP 必须明确这些职责边界：

- 告警入口模块：只确认告警是否发生、持续或恢复，产出 `direct_trigger`、`alert_subject`、`severity`、`status`、`alert_time` 和 handoff 目标。
- 指标模块：确认指标事实，产出 `metric_evidence`、`affected_scope`、`metric_name`、`namespace`、`pod_name`、`container_name`、`value`、`limit_or_request`、`trend`。
- K8s 事件模块：确认 OOMKilled、Evicted、Killing、BackOff、Unhealthy、ProbeWarning、FailedScheduling 等运行事件。
- 工作负载模块：解释指标异常前后的业务、应用、数据库或中间件行为，只能作为辅助证据，不能替代指标事实。

默认 handoff 顺序：

```text
alert-entry
  -> metrics/prometheus
    -> k8s-event
      -> workload-specific module
        -> summarize evidence state
```

如果用户直接问资源使用率或“为什么内存高 / CPU 高”，可以直接进入指标模块；若问题来自告警标题，先经告警入口建立入口事实，再 handoff 到指标模块。

### 4. 数据源登记规则

指标模块 datasource 必须区分：

- `alert_event_source`：告警发生、恢复、持续状态，只能证明规则触发。
- `alert_exec_source`：通知执行、重试、送达失败等链路补证。
- `metric_source`：MetricStore、PromQL 或其它时序指标源，是资源用量事实的主证据。
- `runtime_event_source`：K8s event 或等价运行事件源。
- `workload_log_source`：应用、数据库、中间件或 stdout 日志，只作解释性补证。

MetricStore / PromQL 源必须标记为指标源，不能当普通业务 Logstore 处理。普通日志 SQL 扫描为空，不能解释为指标不存在；必须在 SOP 中写清“查询能力不足 / 工具不支持指标查询”时的 `evidence_insufficient` 分支。

如果告警事件已经包含结构化对象标签、`current_value` 和 PromQL / 阈值表达式，即使暂时无法直接执行 PromQL，也必须把告警事件记录为“指标阈值快照证据”。此时缺失的是趋势、原始 working set、limit/request 明细或根因解释证据，不是“没有指标证据”。

### 5. 关联键规则

指标类 SOP 至少要把这些关联键写入 `correlation-keys` 或模块 `overview.yaml`：

- `namespace`
- `pod_name`
- `container_name`
- `workload_name`
- `metric_name`
- `alert_subject`
- `alert_time`
- `source_alias`
- `limit_or_request`
- `current_value`

Prometheus / 云监控告警事件的对象标签提取顺序默认是：

1. 优先解析结构化对象字段，例如 `resource.tags.namespace`、`resource.tags.pod`、`resource.tags.container` 或等价字段。
2. 再解析 labels、annotations、message、通知正文等展示字段。
3. 如果展示文本里出现 `Pod: null`、`Pod: <no value>` 或类似占位，但结构化对象字段有值，必须以结构化对象字段为准。

如果告警事件缺少 namespace、pod、container 或 instance 标签，不能声称已定位对象；必须回到 MetricStore 或要求补充告警详情。

### 6. 资源类分析步骤

资源类 `analysis_sop` 默认包含这些步骤：

1. 识别问题类型：内存、CPU、资源使用率、重启、OOM、Evicted 或其它指标异常。
2. 收集告警触发事实：subject、severity、status、rule_id、alert_time。
3. 抽取结构化对象：优先从 `resource.tags` 或等价结构化字段获取 namespace、pod、container，并抽取 current_value 和 PromQL。
4. 验证指标查询能力：确认 MetricStore / PromQL 可用，列出候选指标和标签。
5. 定位对象范围：按 namespace、pod、container、workload 聚合 TopN 和趋势。
6. 对比 request/limit 或历史基线：区分“用量高”“接近限制”“超过阈值”和“缺少基线”。
7. 关联运行事件：查询 OOMKilled、Evicted、Killing、BackOff、Unhealthy、ProbeWarning 等。
8. 查看工作负载日志：只在对象明确后进入 backend、database、middleware、stdout 等模块。
9. 生成候选原因研判：即使最终根因不能确认，也必须输出最可能解释、支持证据、反证、置信度和下一步一锤定音的证据。
10. 输出证据状态：`confirmed_root_cause`、`likely_cause`、`metric_threshold_confirmed`、`trigger_only`、`evidence_insufficient`。

### 7. 反误判规则

指标类 SOP 必须内置这些约束：

- 不能把“容器内存超过阈值”“CPU 超过阈值”等告警标题直接写成根因。
- 不能把没有 OOMKilled 写成没有内存问题；它只能说明未发现内存杀死证据。
- 不能把没有应用 OutOfMemoryError 写成没有容器内存高。
- 不能把告警事件中的规则元数据当成 pod/container 标签。
- 不能因为通知正文显示 Pod 为 null 或 `<no value>` 就放弃解析结构化 `resource.tags` 对象标签。
- 不能因为普通 SQL 无法查询 MetricStore，就丢弃告警事件中的 current_value、PromQL 和对象标签。
- 不能把 K8s 事件查询为空写成采集异常；只能说明当前窗口未发现匹配运行事件，除非另有采集失败证据。
- 不能把未实际查询的数据源写成“无数据”；报告必须记录实际命中的 source_alias、project、logstore 或明确写“未查询”。
- 工作负载日志可能包含密码、Token、连接串、租户密钥或完整 SQL 参数；报告只允许输出脱敏摘要和聚合结论，禁止粘贴原文。
- 不能只用“依据不足”结束原因类问题；必须给出候选原因排序、最可能解释、反证和下一步确认动作。
- 不能在没有 request/limit 或历史基线时输出明确使用率结论。
- 不能把 checkpoint、业务 ERROR、探针失败、BackOff 单独解释为内存或 CPU 根因。

## 通用能力：Kubernetes 重启与发布变更 SOP

这部分能力用于任何需要沉淀“运行事件 -> Pod status -> 发布变更 -> 指标 -> 工作负载日志 -> 根因证据”的 SOP 仓库，不绑定具体环境、project、logstore、namespace 或 Pod。

### 1. 推荐模块分层

- `k8s-event`：主事实源是 Kubernetes event，负责确认 `reason / message / object / count / firstTimestamp / lastTimestamp / component`，产出 `direct_trigger` 和 `symptom_evidence`。
- `k8s` 或 `k8s-audit`：主事实源是 Kubernetes audit，负责控制面补证和主体归因，重启类问题必须补 `pods/status` 与 Deployment `patch/update`。
- `prometheus` 或 `metrics`：负责重启计数、last terminated reason、CPU/memory、request/limit 和趋势补证。
- 工作负载模块：负责 previous logs、runtime stdout、应用结构化日志、依赖日志和配置证据。
- `log-sources/overview.yaml`：必须登记 K8s event、K8s audit、MetricStore/PromQL、工作负载日志之间的 `source_role` 和可解析别名。

### 2. Pod 重启 workflow 默认步骤

1. 提取 `namespace`、`pod_name`、`workload_name`、`deployment_name`、`container_name`、`alert_time / time_window`。
2. 查询 K8s event，确认 `BackOff / CrashLoopBackOff / OOMKilled / Killing / Unhealthy / FailedScheduling / FailedMount` 等直接触发器。
3. 对重启或退出类触发器，查询 K8s audit `pods/status`，提取 `lastState.terminated.reason`、`exitCode`、`finishedAt`、`restartCount`、`state.waiting.reason`。
4. 查询同窗口 Deployment `patch/update`，提取镜像 tag、revision、操作主体、状态码和必要字段摘要。
5. 查询 Prometheus / MetricStore，补 `kube_pod_container_status_restarts_total`、`kube_pod_container_status_last_terminated_reason`、CPU/memory、request/limit 和趋势。
6. 验证并查询工作负载日志源，包括结构化应用日志、stdout、previous logs 或平台可用的等价日志。
7. 汇总为 `direct_trigger -> pod_status_evidence -> deployment_change_evidence -> metric_evidence -> runtime_log_evidence -> final_root_cause`，并明确已确认层级和缺失证据。

### 3. 必须产出的 facts

- `direct_trigger`
- `symptom_evidence`
- `pod_status_last_state`
- `container_exit_reason`
- `container_exit_code`
- `restart_count`
- `waiting_reason`
- `deployment_change_evidence`
- `image_change_evidence`
- `restart_metric_evidence`
- `last_terminated_reason`
- `resource_trend_evidence`
- `runtime_logstore_query_status`
- `root_cause_evidence`
- `root_cause_evidence_status`
- `confirmed_cause_level`
- `next_evidence_action`

### 4. 判断边界

- `BackOff`、`CrashLoopBackOff` 和探针失败是触发事实，不是根因。
- `lastState.terminated.reason=Error` 与 `exitCode=1` 是容器进程异常退出的中间原因，不是最终应用根因。
- Deployment 镜像 tag 或 revision 变化是发布 / 变更证据；只有结合退出日志、配置差异、回滚恢复或依赖异常，才能继续定为最终根因。
- `OOMKilled` 可以作为较强中间原因，但仍要补 memory limit、working set、request/limit 和应用内存日志，判断是资源限制、内存泄漏还是突发流量。
- 没有应用日志不等于应用没有报错；必须区分“日志源不存在 / 未配置 / 无权限 / 查询失败 / 查询无匹配数据 / 采集延迟”。

### 5. 报告模板要求

K8s 重启类报告模板必须包含：

- 运行事件证据：`reason / message / count / firstTimestamp / lastTimestamp / object / component`
- Pod status 补证：`lastState.terminated.reason / exitCode / finishedAt / restartCount / waiting reason`
- 发布变更补证：Deployment `patch/update`、镜像 tag、revision、主体、状态码
- 指标补证：重启计数、last terminated reason、CPU/memory、request/limit、趋势
- 日志补证：实际查询过的应用日志 / stdout / previous logs source、时间窗、查询状态
- 根因证据链：已确认层级、证据状态、缺失证据和下一步一锤定音动作

### 6. 安全与脱敏

- 不输出完整 `requestObject`、`responseObject`、环境变量、Secret 引用值、Token、连接串、密码、JWT 或完整启动参数。
- 可输出镜像仓库和 tag、revision、资源名、响应状态码、字段路径和脱敏摘要。
- 如确需说明敏感字段存在，只写字段路径和风险类型，例如 `env contains datasource config`，不要输出值。

### 8. Root cause contract

指标类 workflow 必须产出：

- `direct_trigger`
- `trigger_condition`
- `metric_evidence`
- `affected_scope`
- `runtime_event_evidence`
- `workload_log_evidence`
- `intermediate_cause`
- `final_root_cause`
- `root_cause_evidence`
- `root_cause_evidence_status`
- `confirmed_cause_level`
- `next_evidence_action`
- `cause_hypotheses`
- `most_likely_explanation`
- `decisive_next_evidence`

判断标准：

- `confirmed_root_cause`：指标事实定位到具体对象，异常程度有 limit/request 或基线支撑，并且有配置、变更、运行事件、流量、连接数、依赖或工作负载日志解释异常。
- `likely_cause`：指标事实完整，但解释性证据不足。
- `metric_threshold_confirmed`：告警事件已包含对象标签、current_value 和 PromQL / 阈值表达式，但缺少完整趋势、原始指标明细或根因解释证据。
- `trigger_only`：只有告警触发记录或规则状态。
- `evidence_insufficient`：缺少对象标签、指标查询能力、时间范围或关键关联键。

当最终根因未确认时，报告仍必须给出“最可能解释”，但要明确标注为候选而不是最终根因。对 PostgreSQL / middleware postgres 容器，默认候选包括：正常缓存或 shared_buffers 高水位、查询负载或连接数导致工作集升高、容器 memory limit 偏小、内存泄漏或未受控增长。每个候选都要写支持证据和反向证据。

### 9. 根入口和工作流必须同步

新增指标模块时，至少同步这些位置：

- 根入口 `SOP.md`：增加资源类问题路由规则和模块导航。
- `alert-entry/overview.yaml` 或等价入口：资源类告警 handoff 到指标模块。
- `workflows/overview.yaml`：给 Prometheus / metrics workflow 增加指标模块为 entry module。
- `workflows/<metrics-workflow>.yaml`：把告警查询、指标查询、运行事件、工作负载日志和 summary 写成结构化 steps。
- `log-sources/overview.yaml`：标记 MetricStore / PromQL 是指标源，不是普通 Logstore。
- `correlation-keys/overview.yaml`：补 namespace、pod_name、container_name、metric_name、source_alias。
- `alert-types/overview.yaml`：补资源类告警识别模式。

所有这些更新都必须使用目标仓库自己的命名和目录结构，不要把某个项目的真实 project、logstore、租户、Pod 或本机路径写入 skill 模板。

## 模式 B：SLS 资源流水线模式

- 这个模式已经吸收 `generate-sls-sop` 的 fetch、prepare、select、normalize、validate、resume、audit 能力。
- 入口判断、Phase A/B/C/D、状态恢复、输出路径确认、质量审计，统一按 [references/sls-project-workflow.md](references/sls-project-workflow.md) 执行。
- 运行期主要脚本包括：
  - `scripts/fetch_sls_data.py`
  - `scripts/save_options.py`
  - `scripts/prepare_project.py`
  - `scripts/save_selections.py`
  - `scripts/update_status.py`
  - `scripts/build_pipeline.py`
  - `scripts/normalize_templates.py`
  - `scripts/prepare_validation.py`
  - `scripts/validate_queries.py`
  - `scripts/apply_validation.py`
  - `scripts/render_fields.py`
  - `scripts/render_queries.py`
  - `scripts/assemble_overview.py`
  - `scripts/prepare_audit.py`
  - `scripts/finalize_audit.py`
  - `scripts/aggregate_audit.py`

## 让流水线结果服务仓库文档

- 如果用户明确要 `overview.md`、`SOP.md` 或 `SKILL.md`，按流水线的原始输出方式交付即可。
- 如果用户同时要求“对齐当前仓库”或“补齐五件套”，不要停在 overview.md。先跑完流水线的抽取和整理步骤，再把产物折叠成仓库模块文档。
- 如果用户还明确要求 project 级索引，则采用“Project 索引 + 模块五件套”混合模式，而不是纯五件套模式。
- 生成仓库文档时，优先使用这些流水线产物做事实源：
  - `project_summary.json`、`data_summary.md`：项目级范围、候选 logstore、来源分布、处理摘要。
  - `parsed/fields.json`、`fragments/fields_table.md`：字段语义、字段别名、嵌套字段约束。
  - `fragments/datasource.md`、`skill_options.json`：数据源定位、输出路径、运行方式。
  - `parsed/query_pipeline.json`、`fragments/queries_selected.md`、`parsed/query_report.md`：可复用查询、分类、保底查询、来源覆盖和验证结果。
  - `_audit/`：质量问题、风险分布和后续修正线索。
- 在仓库模式下，`overview.md` 或 `SKILL.md` 可以作为中间成果或参考，不要求它们成为最终唯一交付物。
- 无论来自 CSV 还是 SLS project，都继续遵守稳定事实 / 动态事实边界。
- 如果 `project_summary.json`、`data_summary.md`、`fragments/datasource.md` 或 live 查询结果显示同类日志在多个入口同时存在，先做去重和 `source_role` 判定，再决定是否生成新的子模块。
- 对这类双入口场景，优先把冲突处理规则返写到根入口、聚合入口和具体模块，不要只在单个 leaf 文档里临时说明。
- 如果用户明确要求“让系统能顺序执行查询、按条件跳转模块、沉淀 handoff 规则”，除了常规文档外，还要把这些事实返写到 workflow / module / datasource / correlation contract，而不是只写在 README 或总结里。

## 使用 CSV 画像脚本

执行：

```bash
python3 scripts/profile_csv.py <csv-path>
python3 scripts/profile_csv.py <csv-path>.gz
```

根据脚本输出识别：

- 候选日志类型
- 时间字段和时间范围
- 身份/资源字段
- 动作/状态/结果字段
- IP/端口/对象/实体字段
- 数值类字段
- 更偏业务、运维还是安全

除非用户明确确认稳定，否则不要把画像脚本输出的热点值直接写成永久文档事实。

## 使用脚手架生成器

执行：

```bash
python3 scripts/generate_scaffold.py <csv-path> --out-dir <目标目录>
```

这个脚本会自动给出：

- 候选日志家族
- 环境提示
- 推荐模块目录
- 推荐文件集合
- 一套可继续细化的模块文档骨架

默认行为：

- 样本中的热点值不会被自动写死成永久规则
- 如果无法稳定识别环境，会按 `common` 生成通用骨架
- 如果无法稳定识别日志家族，会回退到通用结构化日志骨架
- 如果没有同级目录样式约束，默认使用便携命名；如需复刻某个仓库风格，应以目标目录实际文件为准再调整

## 生成可复用文档，不要写成一次性说明

### 应该做

- 从工件里抽象出可复用字段模型。
- datasource 规则尽量做成动态解析。
- 对环境敏感的值要参数化或运行时解析。
- 尽量复用目标仓库现有的文档风格和分工。
- 如果仓库需要联动分析，把步骤顺序、条件判断、输入输出事实写成结构化字段，而不是散落在段落叙述里。

### 不应该做

- 不要把样本里的 bucket/object 名、设备名、IP、主机名、表名、request id 硬编码进 SOP 规则。
- 不要把单个样本的热点值当成永久白名单。
- 不要把样例文件名当成稳定依赖写进正式 SOP。
- 不要把所有日志都强行解释成安全问题。
- 不要把真实租户名、本机绝对路径、用户名、Pod 名、集群名直接写进 skill 模板、schema 示例或长期 contract。

## 默认输出策略

### 针对 SOP 请求

- 主线优先按 `baseline -> anomaly -> response -> root cause -> closure` 组织。
- 指标类问题优先按 `alert trigger -> metric evidence -> affected scope -> runtime event -> workload evidence -> root cause status` 组织。
- 只有字段足够支撑时，才补具体查询示例。
- 阈值和升级规则必须来自字段模型或用户明确要求，不能凭空捏造。

### 针对仓库配套文档

- `README.md` 面向人工维护者。
- `overview.yaml` 默认负责导航和路由；如果用户要求可执行 contract，可在保留可读内容的前提下叠加机器可执行字段。
- datasource 文件是稳定环境映射的唯一事实源。
- SOP 文件只放固定流程和判断规则。
- report template 必须和 SOP 输出对齐，并包含纯文本根本原因分析证据链图（使用 text 代码块，禁止 Mermaid）。
- workflow / module / datasource / correlation contract 负责让 agent 能稳定执行步骤、判断跳转和串联数据源。

### 针对其它文档类型

- 继续沿用“稳定事实 / 动态事实”这条边界。
- 优先复用仓库已有模板、章节和标题习惯。
- 如果仓库里没有先例，就生成一份轻量但结构清晰的文档，不要写成长篇散文。

## 配套参考文件

- 在判断环境、提炼话术模式、约束硬编码边界时，读 [references/intake-patterns.md](references/intake-patterns.md)。
- 在补 workflow、module、datasource、correlation 的机器可执行结构时，读 [references/executable-contracts.md](references/executable-contracts.md)。
- 在选择最终产物是 overview、SKILL 还是仓库五件套时，读 [references/output-modes.md](references/output-modes.md)。
- 在输入是 SLS project、本地抓取目录或需要断点续跑时，读 [references/sls-project-workflow.md](references/sls-project-workflow.md)。
- 在选择日志家族、模块目录、默认命名时，读 [references/log-families.md](references/log-families.md)。
- 在决定生成哪些文件、每个文件写什么时，读 [references/doc-types.md](references/doc-types.md)。
- 在检查输出是否达标时，读 [references/output-contracts.md](references/output-contracts.md)。
- 在执行流水线细节时，按需读取 `rules/naming_rules.md`、`rules/field_desc.md`、`rules/query_select.md`、`rules/query_verify.md`、`rules/query_format.md`、`rules/index_rules.md`、`rules/audit_rules.md`、`rules/troubleshooting.md`。

## 典型触发语句

- `根据这份 CSV 日志生成一套对齐现有目录的 SOP`
- `根据这份 CSV.GZ 日志样本生成一套模块骨架`
- `继续做某个日志类型的 sop，目录结构和同目录其它日志对齐`
- `分析 PROD 某系统 最近的事件，并沉淀成 SOP`
- `补齐 README、overview、datasource、analysis_sop、report_template`
- `把现有 SOP 仓库的 YAML 收敛成可执行 schema，保留现有说明文字`
- `给这个模块补 workflow steps、handoff 和 datasource/correlation contract`
- `让这个 SOP 能支持先查 k8s-event，再看 backend，再按条件联动 postgresql`
- `让这个 SOP 支持 Prometheus 告警先查告警事件，再查 MetricStore，再联动 k8s-event 和应用日志`
- `把容器内存 / CPU / 资源使用率的通用排查能力沉淀到 skill`
- `给其它 SOP 仓库补一个可复用的 metrics / prometheus 模块`
- `保留 project 级索引，同时每个 logstore 输出 README、overview.yaml、datasource、analysis_sop、report_template`
- `把这份日志样本抽象成通用文档，不要硬编码样本里的对象`
- `帮我生成 <project-name> 的 SOP 文档`
- `帮我从 .input/my-project/ 生成 SOP`
- `帮我从某个 logstore 目录生成 overview`
- `帮我生成 <project-name> 的 SKILL 文档`
- `继续上次的 SOP 生成`
- `帮我生成 SOP，并验证 query 语法`
- `对已生成的 SOP 做质量审计`
