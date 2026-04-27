# 输入模式

## 1. 提问入口解析

### 模式 A

`分析 <环境> <系统/产品> 最近的事件`

拆成这些结构化字段：

- `environment`
- `system_or_product`
- `time_intent`
- `event_scope`
- `artifact_family`
- `output_type`

如果用户没有明确说 `output_type`，按上下文推断：

- 提到沉淀、规范、SOP、流程 -> SOP / runbook
- 提到目录结构对齐 -> 模块化文档套件
- 提到报告、总结 -> 报告模板或分析报告

### 模式 B

`继续做 <日志类型> 的 sop，目录结构和同目录其它日志对齐`

把它理解成：

- 以仓库现有结构为准生成
- 同级文档是最强模板
- 文件命名必须和相邻模块一致
- 样本文件只是字段/schema 参考，不是永久依赖
- 如果这些目录只是参考样例，而不是目标产物本身，就只提炼它们的职责分工和写法，不直接复刻目录名

### 模式 C

`我给你一个 csv，帮我生成文档`

把 CSV 当作：

- 字段模型来源
- 业务/运维/安全方向的信号来源
- 动态维度的证据来源
- 不是把样本值硬编码进正式文档的许可

### 模式 D

`帮我生成 <project-name> 的 SOP` / `帮我从 .input/<project>/ 生成 SKILL`

把它理解成：

- 输入源优先是 SLS project 或标准化抓取目录
- 默认要走 project 级流水线，而不是只看单个样本
- 需要从 index、dashboard、alert、scheduled_sql、saved_search 中抽取稳定事实
- 输出可能是 `overview.md`、`SOP.md`、`SKILL.md`，也可能继续折叠成仓库五件套

### 模式 E

`继续上次的 SOP 生成` / `继续上次的 SKILL 生成`

把它理解成：

- 优先寻找已有 `<project_dir>`
- 先跑恢复检测，不要从头重做
- 已完成的 logstore 不重复生成
- 先判断是继续 Phase B、Phase C 还是 Phase D

### 模式 F

`把现有 SOP 仓库的 YAML 收敛成可执行 schema` / `给这个模块补联动分析的 workflow 和 handoff`

把它理解成：

- 目标通常不是新起一套文档，而是在现有仓库结构上补机器可执行 contract
- 先识别当前仓库是否已有 `SOP.md`、`workflows/overview.yaml`、模块 `overview.yaml`、`log-sources/overview.yaml`、`correlation-keys/overview.yaml`
- 默认保留现有说明性段落、兼容老字段，不要粗暴重写成只剩 schema
- 需要明确 `workflow_id`、`module_id`、步骤输入、条件跳转、产出事实、handoff 目标
- 如果用户提到 `k8s`、`backend`、`postgresql` 等联动模块，把它们当作 workflow step 和 module handoff 的候选，而不是只写成“建议后续排查”

## 2. 环境识别顺序

优先级如下：

1. 用户明确输入
2. datasource 元数据或日志元数据
3. 同级文档
4. 仓库命名

规则：

- 如果仓库是 `uat`，但用户问的是其它环境，以用户指定环境为准。
- 如果只有 UAT 样本，但用户要的是通用文档或跨环境文档，就把环境相关值做成参数化。
- 如果环境无法确认，文档要写成运行时解析，而不是硬编码。
- 如果目标目录不存在现成模块样式，优先生成便携命名骨架，不偷带当前仓库里的模块名。

### 环境归一化建议

优先把用户输入归一化到以下标准环境键：

- `prod`
  - 常见别名：`prod`、`prd`、`production`、`online`
- `pre`
  - 常见别名：`pre`、`staging`、`stage`、`gray`
- `uat`
  - 常见别名：`uat`
- `sit`
  - 常见别名：`sit`
- `test`
  - 常见别名：`test`、`qa`
- `dev`
  - 常见别名：`dev`、`daily`、`local`

如果用户只说“最近的事件”但没说环境：

1. 先从 prompt 里找环境词。
2. 再从样本路径、目录名、datasource 命名里推断。
3. 还无法确认时，用 `common` 生成通用骨架，不要偷带 UAT/PROD 假设。

## 3. 稳定事实和动态事实

### 稳定事实

适合进入永久文档的内容：

- 已确认的 `project/logstore`
- 已确认的 `source_alias`
- 已确认的账号别名
- 固定的文件职责划分
- 标准工作流阶段
- 稳定字段含义
- 已批准的阈值或升级规则

### 动态事实

除非用户确认稳定，否则不要固化进永久规则：

- bucket 名
- object 路径
- 设备名
- 单个样本里的主机名
- 源/目的 IP
- 单个样本里的 VM/ENI/资源 ID
- request id
- 单个样本里的热点值
- 某一份导出文件名
- 本机绝对路径
- 真实用户名
- 临时 Pod 名、容器 ID、集群实例后缀

## 4. 业务 / 运维 / 安全三个视角

默认三个方向都看，再根据字段决定主次。

### 业务

关注：

- 受影响对象
- 过程是否正确
- 预期正常路径
- 业务影响和业务确认点

### 运维

关注：

- 错误与失败
- 时延、体量、稳定性
- 发布窗口
- 重试、漂移、噪声、可观测性缺口

### 安全

关注：

- 未授权访问
- 暴露面
- 异常与滥用模式
- 升级与遏制

## 5. 硬编码边界

- 不要把样本观察值升级成配置事实。
- 如果必须提到观察值，要明确标注为运行时观察、示例值或样本提示。
- 优先使用 `dynamic_from_user_input_or_logs`、`runtime observation`、`candidate`、`observed in sample`、`requires confirmation` 这类表述。
- 如果字段缺失，不要发明依赖该字段的查询或流程。
- 如果是在补可执行 contract，不要把真实环境名、本机路径、租户标识写进 schema 示例；优先用参数化键、别名或占位符。

## 6. 推荐联动文件

- 需要按日志家族选择模板时，读 `references/log-families.md`
- 需要判断最终产物时，读 `references/output-modes.md`
- 需要把说明性 YAML 升级成可执行 workflow / module / datasource / correlation contract 时，读 `references/executable-contracts.md`
- 需要从 SLS project 或本地目录走完整流水线时，读 `references/sls-project-workflow.md`
- 需要检查输出是否合格时，读 `references/output-contracts.md`
