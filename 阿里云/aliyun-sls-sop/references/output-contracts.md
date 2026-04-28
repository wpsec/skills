# 输出契约

本文件约束 `aliyun-sls-sop` 生成结果的最小质量标准，避免只输出“像文档”的文本，但缺少后续可维护性。

如果当前输出是 `overview.md` 或 `SKILL.md`，先按 `references/output-modes.md` 和 `rules/*.md` 执行，再回到这里检查可复用边界。

## 1. 模块文档套件的最低要求

当用户要求“目录结构对齐”“补齐整套文档”“沉淀 SOP 模块”时，默认至少输出：

- `README.md`
- `overview.yaml`
- `*_datasources.yaml`
- `*_analysis_sop.yaml`
- `*_report_template.md`

如果用户明确只要其中一个文件，才允许减少输出范围。

如果用户还明确要求保留 project 级索引，则在以上五件套之外，再额外输出：

- 根目录 `SOP.md`
- project 目录 `overview.md`

## 2. 每个文件必须承担单一职责

### `README.md`

必须包含：

- 模块用途
- 文件清单与职责
- 推荐阅读顺序
- 数据源 / 样本使用约束
- 建议提问方式

### `overview.yaml`

必须包含：

- `module`
- `description`
- `quick_links`
- `task_routing_rules`
- `supported_intents`
- `important_notes`

禁止：

- 把整套 SOP 细节复制进 `overview.yaml`

如果目标仓库采用可执行 contract，还必须额外包含：

- `schema`
- `schema_reference`
- `module_id`
- `entry_hints`
- `execution`

### `*_datasources.yaml`

必须包含：

- `metadata`
- `purpose`
- `editing_rules`
- `datasource_registry`
- 运行时解析规则
- `usage_notes`
- `conversation_shortcuts`

禁止：

- 把样本热点值当成稳定映射写死

### `*_analysis_sop.yaml`

必须包含：

- `metadata`
- `scope`
- `objectives`
- `required_inputs`
- `common_fields`
- `analysis_principles`
- 触发条件
- 执行步骤
- 判断标准
- 升级路径
- 记录要求
- `report_template_file`

### `*_report_template.md`

必须包含：

- 头部事实
- 事件概要
- 宏观总览
- 根本原因分析数据流图
- 关键发现
- 研判与影响评估
- 处置建议

根本原因分析数据流图必须使用纯文本 ASCII / 盒线图，并放在 ```text 代码块中；报告可见字段必须使用中文，图中必须展示直接触发器、触发证据、中间原因、中间证据、最终根因、根因证据、证据状态、已确认层级、下一跳补证和关键日志片段指引；内部 contract 可继续使用英文事实名。不得把一次性样本热点值画成长期固定链路。禁止使用 Mermaid、flowchart、graph、SVG 或依赖客户端渲染的图形语法。

若报告分析的是任何告警、运行事件、指标异常、错误率、超时、可用性、性能或数据库问题，根本原因分析 ASCII 数据流图还必须显式区分：

- 直接触发器：告警名称、Condition、阈值命中、状态码、事件 reason、错误数量、延迟指标、数据库延迟或其它触发事实。
- 根因证据：能解释直接触发器的日志、指标、配置、变更、运行事件、依赖侧日志或领域主事实源证据。
- 中间原因：已经被证据支持、但仍不是最终可操作根因的中间解释，例如应用未启动、端口未监听、Bean 创建失败、回源失败或连接池耗尽。
- 证据状态：报告可见层写“已确认 / 证据不足 / 需联动”，内部 contract 对应 `confirmed / evidence_insufficient / needs_handoff`。
- 已确认层级：报告可见层写“触发事实已确认 / 中间原因已确认 / 最终根因已确认”，内部 contract 对应 `direct_trigger_confirmed / intermediate_cause_confirmed / final_root_cause_confirmed`，用于避免把中间原因误写成最终根因。
- 下一跳补证：当最终根因未确认时，必须写清下一跳要查的日志、指标、配置、变更或依赖数据源。
- 根因证据日志片段：报告模板必须单独列出片段表格；可用时至少给 3-5 条关键日志 / 指标 / 配置 / 变更片段，应用异常至少保留异常类型、关键 message、最底层 `Caused by`、时间、对象和 trace / 类方法。

禁止把告警名称、阈值命中、状态码、事件 reason、错误数量、延迟指标、单条 message、应用启动失败、Probe 失败、BackOff、5xx、ERROR 聚合或 `BeanCreationException` 直接写成最终根本原因；证据不足时必须在报告中写“当前只解释到哪一层 / 根因待确认 / 下一跳补证”。当用户问“原因 / 根因 / 为什么”时，报告第一结论必须回答“目前能解释到哪一层、最终根因是否已确认、还缺什么证据”，不能只复述告警成立。

### `SOP.md`

必须包含：

- project 级目录表
- 每个 project 的简短描述
- 指向 project `overview.md` 的稳定链接

### project `overview.md`

必须包含：

- project 简述
- module 清单
- 指向各 module `README.md` 的稳定链接
- 不要把 leaf 级 SOP 全量复制进这个索引文件

## 3. 可执行 Contract 的最低要求

当用户要求“联动分析”“workflow 编排”“step executor”“把 YAML 收敛成可执行 schema”时，至少满足以下要求。

### workflow 索引

必须包含：

- `schema`
- `schema_reference`
- `workflow_files`
- `common_execution`
- `time_window_policies`

### workflow 定义

必须包含：

- `schema`
- `workflow_id`
- `title`
- `intent_types`
- `entry_modules`
- `required_context`
- `steps`

每个 step 至少要显式写出：

- `step_id`
- `kind`
- `module` 或等价执行目标
- `description`
- `produces`

如果 step 存在顺序或条件，还必须显式写出：

- `depends_on`
- `run_if_any` 或等价条件字段

### module contract

必须包含：

- `schema`
- `module_id`
- `entry_hints`
- `execution.required_inputs`
- `execution.primary_source`
- `execution.produces`
- `execution.handoff`

### datasource / correlation contract

必须包含：

- `schema`
- `schema_reference`
- 可解析的数据源定位或关联键提取规则

禁止：

- 只写“建议后续看 backend / postgresql”，但不写触发条件和 handoff 入口
- 只写“可能联动某模块”，但没有输入、条件和产出
- 在 contract 示例里直接写真实租户名、本机绝对路径、用户名、集群名后缀

## 4. 稳定事实与动态事实边界

### 可以进入永久文档的内容

- 已确认的 `project/logstore`
- 已确认的 `source_alias`
- 已确认的账号别名
- 稳定字段语义
- 经过确认的阈值、分级和升级路径

### 不能默认写死的内容

- bucket 名
- object 路径
- 设备名
- 主机名
- IP
- VM / ENI / VPC / 实例 ID
- request id
- SQL 原文
- 样本导出文件名
- 单个样本里的热点值

## 5. 查询与流程生成约束

- 只有字段存在时，才能生成依赖该字段的查询。
- 含连字符的字段名在 YAML 或 SQL 示例里要考虑引用方式，避免生成不可执行示例。
- 如果字段不足以支撑安全、运维或业务三个方向中的某一个，必须明确写出“当前字段不足”。
- 如果日志家族不明确，优先生成通用骨架，并提示后续补充。
- 如果 workflow 依赖前一步产出的事实，必须显式写在 `produces` 和下一步的条件里，不能靠读者脑补。
- 如果是多模块联动，至少要交代主事实源、补证源和 handoff 方向。
- 当用户问“原因 / 根因 / 为什么”时，输出必须优先追问并解释原因链：`direct_trigger -> symptom_evidence -> intermediate_cause -> final_root_cause`。如果最终原因未确认，必须说明已解释到哪一层、已查过哪些证据、缺失哪类证据和下一跳查询，不能只复述触发症状或告警成立。

## 6. 最终自检清单

- 是否与同级目录命名风格一致
- 如果没有同级目录，是否使用了可独立迁移的便携命名
- 是否避免硬编码样本事实
- 是否区分导航、配置、SOP、模板职责
- 是否给出可执行的触发 / 步骤 / 判断 / 升级 / 记录
- 是否能跨环境复用
- 是否在用户没确认前，把样本值误写成长期事实
- 是否把参考仓库误当成了 skill 的固定输出结构
- 如果补了 contract，是否补齐了 `schema`、step 输入、条件、事实产出和 handoff
- 是否避免把真实环境名、本机路径、用户名、Pod 名直接写进长期 schema
