# 可执行 Contract

本文件约束 `aliyun-sls-sop` 在“修改现有 SOP 仓库”或“新增可执行联动分析能力”场景下的默认做法。

目标不是把说明文字删掉，而是让现有文档在保留可读性的前提下，补出 agent / `sop-chat` 可以稳定消费的结构化 contract。

## 1. 什么时候启用

出现这些信号时，默认启用可执行 Contract 覆盖层：

- 用户提到 `可执行 schema`、`contract`、`workflow`、`step`、`handoff`
- 用户要求“让 sop-chat / agent 直接按步骤执行”
- 用户要求把“先查 A，再看 B，再按条件联动 C”沉淀成仓库规则
- 用户要修改现有 `workflows/overview.yaml`、模块 `overview.yaml`、`log-sources/overview.yaml`、`correlation-keys/overview.yaml`

如果用户只是要单次分析报告或单文件说明，不要强行引入整套 contract。

## 2. 先识别仓库层级

默认按这几个层级检查现有文件：

- 根入口：`SOP.md`
- 工作流索引：`workflows/overview.yaml`
- 工作流定义：`workflows/<workflow>.yaml`
- 模块 contract：`<module>/overview.yaml`
- 数据源索引：`log-sources/overview.yaml`
- 关联键索引：`correlation-keys/overview.yaml`

规则：

- 已有说明性段落默认保留
- 已有旧字段默认兼容，除非用户明确要求重构
- 机器字段优先做增量补充，不用把整份文件推倒重写

## 3. Contract 类型

### 3.1 workflow 索引

推荐最小字段：

- `schema`
- `schema_reference`
- `workflow_files`
- `common_execution`
- `time_window_policies`

用途：

- 列出有哪些 workflow
- 指定入口模块和意图类型
- 定义通用执行策略，例如时间窗、证据输出、默认顺序

### 3.2 workflow 定义

推荐最小字段：

- `schema`
- `workflow_id`
- `title`
- `intent_types`
- `entry_modules`
- `required_context`
- `optional_context`
- `produces_facts`
- `steps`

每个 step 至少应包含：

- `step_id`
- `kind`
- `module` 或等价执行目标
- `description`
- `produces`

如果 step 依赖前置结论，还应包含：

- `depends_on`
- `run_if_any` 或 `run_if_all`

### 3.3 module contract

推荐最小字段：

- `schema`
- `schema_reference`
- `module_id`
- `entry_hints`
- `execution.required_inputs`
- `execution.optional_inputs`
- `execution.primary_source`
- `execution.alternate_sources`
- `execution.produces`
- `execution.evidence_requirements`
- `execution.handoff`

用途：

- 说明模块何时被选中
- 说明模块需要什么输入
- 说明模块会产出哪些事实
- 说明产出什么条件时应 handoff 到其它模块

### 3.4 datasource / correlation contract

推荐最小字段：

- `schema`
- `schema_reference`
- 可解析的索引主体

其中：

- `log-sources/overview.yaml` 负责数据源别名、主事实源 / 补证源和解析策略
- `correlation-keys/overview.yaml` 负责字段映射、别名、提取顺序和跨模块串联规则

## 4. Step 类型建议

当前默认优先使用这些 step 类型：

- `alert_query`
- `extract_keys`
- `resolve_datasource`
- `module_query`
- `conditional_module_query`
- `summarize`

如果用户没有要求更复杂的执行器，不要自造太多 step 类型。

## 5. 条件与事实

推荐条件字段：

- `depends_on`
- `run_if_any`
- `run_if_all`

推荐操作符：

- `equals`
- `not_equals`
- `contains`
- `exists`
- `in`

推荐事实写法：

- 先定义 step 会 `produces` 什么事实
- 再让后续 step 用条件引用这些事实
- 事实名应表达稳定语义，例如 `direct_trigger`、`suspect_dependency_type`、`needs_database_followup`

禁止：

- 前一步没有产出，后一步却直接假设这个结论存在
- 把“建议查数据库”写成总结散文，而不是结构化条件

## 6. 迁移规则

把说明书式 YAML 收敛成可执行 contract 时，按这个顺序做：

1. 先保留原有说明、导航和维护提示。
2. 抽出稳定入口对象，例如 workflow、module、datasource、correlation。
3. 把散落在段落里的步骤改写成 `steps`。
4. 把“如果发现 X，再去看 Y”改写成 `run_if_any` / `depends_on` / `handoff`。
5. 把“本步骤得到什么结论”改写成 `produces`。
6. 把“去哪查、查什么源”改写成 `primary_source`、`alternate_sources`、解析 contract。
7. 收尾时确认兼容旧字段，没有把说明层误删掉。

## 7. 防泄漏与去硬编码

在 contract、schema 示例和长期文档中，默认不要写死这些内容：

- 本机绝对路径
- 真实用户名
- 真实租户名
- 临时 Pod 名、容器 ID、集群后缀
- 样本中的热点值
- 一次性导出文件名

可替代表达：

- 使用占位符，如 `/path/to/...`
- 使用稳定别名，如 `primary_application_source`
- 使用抽象事实名，如 `target_namespace`、`application_pod_name`
- 如果必须保留观测值，标记为 `runtime observation` 或 `requires confirmation`

## 8. 最终自检

- 是否区分了人类可读层和机器可执行层
- 是否补齐了 `schema`、输入、条件、事实产出和 handoff
- 是否把步骤顺序写成结构化字段，而不是散文
- 是否保留了现有仓库可读性和兼容性
- 是否避免把真实环境和本机信息写进长期 contract
