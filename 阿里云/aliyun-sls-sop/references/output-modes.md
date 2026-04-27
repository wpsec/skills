# 输出模式

`aliyun-sls-sop` 现在同时支持四类产物。先选最终产物，再决定是否先走 SLS 资源流水线。

## 1. 仓库模块文档套件

适用输入：

- 用户要求“和同级目录对齐”
- 用户要求“补齐 README、overview.yaml、datasource、analysis_sop、report_template”
- 用户要求沉淀成长期维护的模块文档

默认产物：

- `README.md`
- `overview.yaml`
- `*_datasources.yaml`
- `*_analysis_sop.yaml`
- `*_report_template.md`

约束：

- 以 [doc-types.md](doc-types.md) 和 [output-contracts.md](output-contracts.md) 为主。
- 如果输入来自 SLS project 或标准化抓取目录，可以先走 project 级流水线，再把结果折叠成五件套。
- 如果用户同时要求联动分析或 workflow 可执行化，可叠加 [executable-contracts.md](executable-contracts.md) 定义的 contract 字段。

## 2. Project 索引 + 模块五件套

适用输入：

- 用户既要 project 级索引，又要每个 logstore 落成模块五件套
- 用户给的是 SLS project 或标准化抓取目录，但最终仍要对齐当前仓库的模块文档
- 用户希望保留 project 级导航入口，同时避免 leaf 目录只剩 `overview.md`

默认产物结构：

```text
<输出根目录>/
├── SOP.md
└── <project>/
    ├── overview.md
    └── <module>/
        ├── README.md
        ├── overview.yaml
        ├── <name>_datasources.yaml
        ├── <name>_analysis_sop.yaml
        └── <name>_report_template.md
```

约束：

- 根目录仍保留 `SOP.md`，project 目录仍保留 `overview.md`。
- project 索引中的 leaf 链接默认指向 `<module>/README.md`，由 README 再路由到其余四个文件。
- 这类模式通常先跑 SLS 资源流水线，再把 leaf 的中间产物折叠成五件套。
- 如果用户还要求让系统自动串联模块，额外补 `workflows/overview.yaml`、workflow 文件、模块 contract 和关联键索引。

## 3. Project / Logstore SOP 文档

适用输入：

- 用户直接说“生成 SOP 文档”
- 用户更关心 overview 文档，而不是仓库五件套
- 用户给的是 SLS project、本地 project 目录或单个 logstore 目录

默认产物结构：

- 根目录：`SOP.md`
- project 目录：`<project>/overview.md`
- logstore 目录：`<project>/<logstore>/overview.md`
- 如果有补充查询：同目录 `queries_extra.md`

约束：

- 生成流程按 [sls-project-workflow.md](sls-project-workflow.md)。
- 输出路径、索引文件和全局更新遵循 `rules/naming_rules.md` 与 `rules/index_rules.md`。

## 4. Project / Logstore SKILL 文档

适用输入：

- 用户明确要求“生成 SKILL”
- 用户要把单个 logstore 或一组 logstore 沉淀成 agent skill 文档

默认产物结构：

- project 目录：`<project>/SKILL.md`
- logstore 目录：`<project>/<logstore>/SKILL.md`

约束：

- 仍然走同一条 SLS 资源流水线，只是 `output_format=SKILL`。
- 不额外生成根目录 `SKILL.md` 索引。

## 5. 选择规则

- 只要用户明确提到 `README.md`、`overview.yaml`、`datasource`、`analysis_sop`、`report_template`，优先走仓库模块文档套件模式。
- 只要用户同时明确提到“project 级索引 / 项目索引 / SOP.md / project overview”和“五件套”，优先走 Project 索引 + 模块五件套模式。
- 只要用户明确提到 `SOP 文档`、`overview.md`、`从 dashboard/index 生成文档`，优先走 Project / Logstore SOP 模式。
- 只要用户明确提到 `SKILL`、`技能文档`，优先走 Project / Logstore SKILL 模式。
- 如果用户同时要“从 SLS project 抽取能力”又要“和仓库目录对齐”，默认先判断是否还要 project 级索引：
  - 要 project 级索引：走 Project 索引 + 模块五件套模式
  - 不要 project 级索引：走仓库模块文档套件模式
- 如果用户明确提到 `可执行`、`schema`、`workflow`、`handoff`、`step`、`联动分析`、`step executor`，在上述模式基础上叠加可执行 Contract 覆盖层，而不是切到全新的产物模式。

## 6. 流水线结果到仓库五件套的映射

- `fragments/datasource.md`、`skill_options.json`、`selected_logstores.json` 主要喂给 `*_datasources.yaml` 和 `overview.yaml`。
- `parsed/fields.json`、`fragments/fields_table.md` 主要喂给 `overview.yaml` 的字段导航和 `*_analysis_sop.yaml` 的 `common_fields`。
- `parsed/query_pipeline.json`、`fragments/queries_selected.md`、`queries_extra.md` 主要喂给 `*_analysis_sop.yaml` 的流程查询和 `*_report_template.md` 的输出对齐。
- `project_summary.json`、`data_summary.md`、`parsed/query_report.md` 主要喂给 `README.md` 的范围说明、维护说明和阅读顺序。
- `_audit/` 主要喂给返修、质量标注和后续维护事项，不直接当成最终文档正文。

在 Project 索引 + 模块五件套模式下，再额外增加两条：

- `project_summary.json`、`selected_logstores.json` 还要喂给根索引 `SOP.md` 和 project 索引 `overview.md`
- 每个 module 的 `README.md` 是 leaf 入口文件，承担模块说明、文件清单、阅读顺序和返回 project 索引的职责

## 7. 可执行 Contract 覆盖层

这不是单独的产物模式，而是叠加在模式 1 或模式 2 上的增强层。

适用输入：

- 用户要修改现有 SOP 仓库，而不是只生成一次性文档
- 用户明确要求“让 agent / sop-chat 直接消费 YAML”
- 用户要 workflow step、条件跳转、handoff、facts、datasource 解析规则

默认补齐：

- `workflows/overview.yaml`
- `workflows/<workflow>.yaml`
- 模块 `overview.yaml` 的可执行字段
- `log-sources/overview.yaml`
- `correlation-keys/overview.yaml`

约束：

- 保留原有人类可读说明，默认做增量增强
- `workflow` 负责步骤编排，`module` 负责单模块 contract，`datasource` 和 `correlation` 负责运行时解析
- 不要把联动逻辑只散落在 README 或结论段落里
