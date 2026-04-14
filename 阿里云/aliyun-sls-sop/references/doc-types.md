# 文档类型

## 仓库模块文档套件

当用户要的是一个可复用、且与同级目录对齐的子模块时，用这套结构。

### `README.md`

应包含：

- 模块用途
- 文件清单与职责
- 阅读顺序
- 维护规则
- 数据源/样本使用约束
- 建议提问方式

### `overview.yaml`

应包含：

- `module`
- `description`
- `quick_links`
- `task_routing_rules`
- `supported_intents`
- `important_notes`
- `core_fields_reference`
- `analysis_dimensions`

只做导航和路由，不要把详细 SOP 逻辑复制到这里。

### `*_datasources.yaml`

应包含：

- `metadata`
- `purpose`
- `editing_rules`
- `datasource_registry`
- 运行时解析规则
- `usage_notes`
- `conversation_shortcuts`

这里只放稳定的环境映射和解析规则。

### `*_analysis_sop.yaml`

应包含：

- `metadata`
- `scope`
- `objectives`
- `required_inputs`
- `common_fields`
- `analysis_principles`
- 场景化 workflow 或 playbook
- 阈值或评级规则
- 报告编写规则
- `report_template_file`

这个文件负责固定流程、判断规则和可复用查询。

### `*_report_template.md`

应包含：

- 报告头信息
- 事件摘要
- 宏观总览
- 关键发现
- 研判与评估
- 处置建议 / 后续动作

它必须和 SOP 承诺的输出保持一致。

## 其它常见文档

### Runbook / 事件处置手册

当用户要的是响应导向文档时使用。

应包含：

- 触发条件
- 分级
- 立即动作
- 证据保全
- 升级路径
- 闭环要求

### 审计报告模板

当用户要的是月度/季度可重复输出时使用。

应包含：

- 周期
- 范围
- 关键发现
- 影响评估
- 整改跟踪项

### 检查清单 / 巡检单

当用户要的是周期性执行文档时使用。

应包含：

- 检查项
- 阈值
- 证据
- 负责人
- 结果
- 跟进动作

## 输出规则

- 如果仓库已有命名模式，优先复用同级文件名。
- 如果没有现成命名模式，优先使用可独立迁移的便携命名。
- 不要围绕文档套件再额外生成说明性质的杂项文件。
- 每个文件只负责一层：导航、配置、SOP、模板或人工说明。
- 如果仓库里没有先例，优先使用轻量的五件套，而不是铺开很多文件。
