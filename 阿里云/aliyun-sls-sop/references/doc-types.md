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

## Project 索引 + 模块五件套

当用户既要 project 级导航，又要每个 logstore 落成模块五件套时，用这套混合结构。

目录关系：

- 根目录保留 `SOP.md`
- project 目录保留 `overview.md`
- 每个 leaf module 目录内放五件套

约束：

- `SOP.md` 负责 project 级入口，不承载 leaf 细节
- project `overview.md` 负责列出 module，并默认链接到各 module 的 `README.md`
- module `README.md` 是 leaf 入口页，负责把读者再路由到 `overview.yaml`、`*_datasources.yaml`、`*_analysis_sop.yaml`、`*_report_template.md`
- 不要求 leaf 再额外保留 `overview.md`，除非用户明确要求

可选共享文件：

- 当用户明确要求“共享白名单”“全局白名单”或仓库里已存在统一白名单约定时，可以在 project 根目录额外维护 `白名单.yaml`
- 这个文件不替代五件套，只作为跨模块共享的稳定事实源
- 推荐结构：

```yaml
nat:
  阿里云相关服务:
    - 47.102.2.89
waf:
  自定义白名单:
    - 127.0.0.1
```

- 一级键用模块名或日志家族名，二级键用分组名，值为该分组下的精确匹配项列表
- leaf `*_analysis_sop.yaml` 需要明确说明如何读取并解释自己对应的白名单段

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

## 索引型单文档输出

当用户明确要求 `overview.md`、`SOP.md` 或 `SKILL.md` 时，用这类结构，而不是仓库五件套。

### `SOP.md` / `overview.md`

应包含：

- frontmatter 或清晰标题
- 使用说明
- 数据源
- 字段参考
- 查询示例
- 必要时指向 `queries_extra.md`

### `SKILL.md`

应包含：

- frontmatter
- 使用说明
- 数据源
- 字段参考
- 查询示例
- 适合 agent 直接消费的简短定位说明

这类输出通常来自 SLS 资源流水线，详细步骤读 `references/sls-project-workflow.md`。

## 输出规则

- 如果仓库已有命名模式，优先复用同级文件名。
- 如果没有现成命名模式，优先使用可独立迁移的便携命名。
- 不要围绕文档套件再额外生成说明性质的杂项文件。
- 例外：如果用户明确要求共享白名单，允许在 project 根目录额外生成 `白名单.yaml`，但不要在 leaf 目录再散落多份白名单文件。
- 每个文件只负责一层：导航、配置、SOP、模板或人工说明。
- 如果仓库里没有先例，优先使用轻量的五件套，而不是铺开很多文件。
- 如果输入是 SLS project 或标准化抓取目录，允许先跑 project 级流水线，再把结果折叠成对应输出模式。
