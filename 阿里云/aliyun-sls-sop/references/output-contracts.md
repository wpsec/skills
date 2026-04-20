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
- 关键发现
- 研判与影响评估
- 处置建议

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

## 3. 稳定事实与动态事实边界

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

## 4. 查询与流程生成约束

- 只有字段存在时，才能生成依赖该字段的查询。
- 含连字符的字段名在 YAML 或 SQL 示例里要考虑引用方式，避免生成不可执行示例。
- 如果字段不足以支撑安全、运维或业务三个方向中的某一个，必须明确写出“当前字段不足”。
- 如果日志家族不明确，优先生成通用骨架，并提示后续补充。

## 5. 最终自检清单

- 是否与同级目录命名风格一致
- 如果没有同级目录，是否使用了可独立迁移的便携命名
- 是否避免硬编码样本事实
- 是否区分导航、配置、SOP、模板职责
- 是否给出可执行的触发 / 步骤 / 判断 / 升级 / 记录
- 是否能跨环境复用
- 是否在用户没确认前，把样本值误写成长期事实
- 是否把参考仓库误当成了 skill 的固定输出结构
