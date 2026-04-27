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
8. 收尾前按 [references/output-contracts.md](references/output-contracts.md) 对照检查。

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
- 报告模板必须覆盖 SOP 承诺的输出结果。
- README 和 overview 必须把读者路由到下一个正确文件。

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
- 只有字段足够支撑时，才补具体查询示例。
- 阈值和升级规则必须来自字段模型或用户明确要求，不能凭空捏造。

### 针对仓库配套文档

- `README.md` 面向人工维护者。
- `overview.yaml` 默认负责导航和路由；如果用户要求可执行 contract，可在保留可读内容的前提下叠加机器可执行字段。
- datasource 文件是稳定环境映射的唯一事实源。
- SOP 文件只放固定流程和判断规则。
- report template 必须和 SOP 输出对齐。
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
- `保留 project 级索引，同时每个 logstore 输出 README、overview.yaml、datasource、analysis_sop、report_template`
- `把这份日志样本抽象成通用文档，不要硬编码样本里的对象`
- `帮我生成 <project-name> 的 SOP 文档`
- `帮我从 .input/my-project/ 生成 SOP`
- `帮我从某个 logstore 目录生成 overview`
- `帮我生成 <project-name> 的 SKILL 文档`
- `继续上次的 SOP 生成`
- `帮我生成 SOP，并验证 query 语法`
- `对已生成的 SOP 做质量审计`
