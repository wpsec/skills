# SLS Project 流水线

当输入是 SLS project、本地抓取目录、单个 logstore 目录、SLS 资源文件，或者用户要求“继续上次生成”时，按这份流程执行。

## 1. 前置条件

- 必须在 workspace 根目录执行，不要 `cd` 到 skill 目录。
- 输入是 SLS project 名称时，需要 `aliyun` CLI >= `3.0.308`，并完成鉴权配置。
- 执行 `fetch_sls_data.py` 或 `validate_queries.py` 时，需要非沙箱网络环境。
- 默认串行执行每个 logstore；只有平台显式允许并行时，才并行处理多个 logstore。

## 2. 支持的输入形式

- SLS project 名称：从线上抓取 index、dashboard、alert、scheduled_sql、saved_search。
- 本地 project 目录：目录下有多个 logstore 子目录，每个目录至少有 `index.json`。
- 本地 logstore 目录：目录内含 `index.json`，并带 `dashboards/`、`alerts/`、`scheduled_sqls/`、`saved_searches/` 之一。
- 关键词搜索：在 workspace 中搜索包含 `index.json` 的目录，再回到本流程。

## 3. 工作文件

project 级关键文件：

- `<project_dir>/project_summary.json`
- `<project_dir>/selected_logstores.json`
- `<project_dir>/skill_options.json`
- `<project_dir>/data_summary.md`
- `<project_dir>/_audit/`

logstore 级关键文件：

- `<logstore_dir>/skill_options.json`
- `<logstore_dir>/step_progress.json`
- `<logstore_dir>/parsed/fields.json`
- `<logstore_dir>/parsed/queries.json`
- `<logstore_dir>/parsed/query_pipeline.json`
- `<logstore_dir>/parsed/query_report.md`
- `<logstore_dir>/fragments/datasource.md`
- `<logstore_dir>/fragments/fields_table.md`
- `<logstore_dir>/fragments/queries_selected.md`

## 4. 总流程

- Step 0：恢复检测
- Phase A / Step 1-3：定位数据源、预处理、确认输出路径
- Phase B / Step 4-11：逐 logstore 处理
- Phase C / Step 12：更新全局索引
- Phase D / Step 13：审计

## 5. Step 0：恢复检测

先推断 `<project_dir>`，然后执行：

```bash
python3 scripts/update_status.py <project_dir> --resume-check
```

根据返回值继续：

- `first_run`：从 Step 1 开始
- `resume_phase_b`：直接进入未完成的 logstore
- `all_completed`：进入 Step 12 或 Step 13

## 6. Phase A：Project 级准备

### Step 1：定位数据源

如果输入是 SLS project：

1. 检查版本：

```bash
aliyun version
aliyun configure list
```

2. 执行抓取：

```bash
python3 scripts/fetch_sls_data.py <project> .input/<project>/ [--logstores=<ls1,ls2,...>]
```

3. 持久化用户选项：

```bash
python3 scripts/save_options.py <project_dir> \
  [--output-format SOP|SKILL] \
  [--validate-queries] \
  [--reference-dir <path>] \
  [--reference <logstore>=<file>]
```

如果输入已经是本地 project/logstore 目录，跳过抓取，只执行 `save_options.py`。

### Step 2：批量预处理

```bash
python3 scripts/prepare_project.py <project_dir>
```

这一步会为每个有效 logstore 生成：

- `parsed/fields.json`
- `parsed/queries.json`
- `fragments/datasource.md`
- `parsed/prepare_summary.json`

### Step 3：名称简化与输出路径确认

先读 `rules/naming_rules.md`，再基于 `project_summary.json` 逐个确认 logstore 的输出路径。用户确认后，把选择写回：

```bash
python3 scripts/save_selections.py <project_dir> <<'SELECTIONS'
{
  "output_root": "<输出根目录>",
  "project_alias": "<project别名>",
  "output_format": "SOP",
  "selections": {
    "<logstore>": "<output_path>"
  }
}
SELECTIONS
```

写回后会得到：

- `<project_dir>/selected_logstores.json`
- 每个 logstore 的 `skill_options.json.output_path`

## 7. Phase B：逐 logstore 处理

开始一个 logstore 前先做两步：

```bash
python3 scripts/update_status.py <project_dir> --step-resume-check <logstore>
python3 scripts/update_status.py <project_dir> --mark-in-progress <logstore>
```

### Step 4：参考文档提取

- 条件步骤：只有 `skill_options.json` 含 `reference_source` 才执行。
- 先读 `rules/reference_extract.md`。
- 产物：`parsed/reference_queries.json`。

### Step 5：生成字段说明

1. 先读 `rules/field_desc.md`。
2. 由 LLM 生成 `parsed/field_annotations.json`。
3. 渲染字段表：

```bash
python3 scripts/render_fields.py <logstore_dir>
```

4. 可选校验：

```bash
python3 scripts/validate_step.py <logstore_dir> fields
```

### Step 6：精选查询

1. 先读 `rules/query_select.md`。
2. 由 LLM 生成 `parsed/query_selection.json`。
3. 组装完整 pipeline：

```bash
python3 scripts/build_pipeline.py <logstore_dir>
```

4. 可选校验：

```bash
python3 scripts/validate_step.py <logstore_dir> pipeline
```

### Step 7：归一化模板

```bash
python3 scripts/normalize_templates.py <logstore_dir>
python3 scripts/update_status.py <project_dir> --mark-step <logstore> --step 7
```

### Step 8：验证查询

- 条件步骤：只有 `skill_options.json.validate_queries=true` 才执行。
- 先读 `rules/query_verify.md`。

执行顺序：

```bash
python3 scripts/prepare_validation.py <logstore_dir>
python3 scripts/validate_queries.py --project <project> --logstore <logstore> <logstore_dir>
python3 scripts/apply_validation.py <logstore_dir>
python3 scripts/update_status.py <project_dir> --mark-step <logstore> --step 8
```

如果出现 `parsed/query_validation_LLM.json`，LLM 必须先修正其中各条 `executable_query`，再继续验证。

### Step 9：清理与标注

1. 先读 `rules/query_format.md`。
2. 由 LLM 生成 `parsed/query_annotations.json`。
3. 可选校验：

```bash
python3 scripts/validate_step.py <logstore_dir> annotations
```

### Step 10：渲染片段与报告

```bash
python3 scripts/render_queries.py <logstore_dir>
python3 scripts/update_status.py <project_dir> --mark-step <logstore> --step 10
```

关键输出：

- `fragments/queries_selected.md`
- `fragments/queries_extra.md`
- `parsed/query_report.md`
- `fragments/common_values.md`

### Step 11：组装输出

先根据 `fragments/queries_selected.md`、`fragments/fields_table.md` 和 logstore 语义，补出 `name` 与 `description`，再执行：

```bash
python3 scripts/assemble_overview.py <logstore_dir> \
  --name "..." \
  --description "..."
```

完成后记录状态：

```bash
python3 scripts/update_status.py <project_dir> --mark-step <logstore> --step 11
python3 scripts/update_status.py <project_dir> --mark-completed <logstore>
```

## 8. Phase C：更新全局索引

- 先读 `rules/index_rules.md`。
- 依据 `selected_logstores.json` 中的 `output_path`，从最深层目录向上更新索引。
- 如果输出格式是 `SOP`，维护 `SOP.md` / `overview.md`。
- 如果输出格式是 `SKILL`，维护 `project/SKILL.md` 与 `logstore/SKILL.md`。
- 如果最终模式是“Project 索引 + 模块五件套”，则仍按 `SOP` 维护根索引和 project 索引，但 leaf 链接目标改为 `<module>/README.md`。

## 9. Phase D：审计

- 先读 `rules/audit_rules.md`。
- 生成审计计划：

```bash
python3 scripts/prepare_audit.py <project_dir> [--mode full|sample|targeted] [--logstores <ls1,ls2>]
```

- 由 LLM 为每个 logstore 产出 `_audit/<logstore>/audit_issues.json`。
- 完成单项收尾：

```bash
python3 scripts/finalize_audit.py <project_dir> <logstore>
```

- 聚合项目级报告：

```bash
python3 scripts/aggregate_audit.py <project_dir>
python3 scripts/update_status.py <project_dir> --mark-audit-completed
```

## 10. 回接仓库文档套件

如果最终目标不是 overview.md / SKILL.md，而是当前仓库里的模块五件套，Phase B 的产物不要丢掉，直接把它们作为上游事实源：

- `fragments/datasource.md` 和 `selected_logstores.json` 进入 `overview.yaml` 与 `*_datasources.yaml`
- `fragments/fields_table.md` 和 `parsed/fields.json` 进入 `overview.yaml` 与 `*_analysis_sop.yaml`
- `parsed/query_pipeline.json`、`queries_selected.md`、`query_report.md` 进入 `*_analysis_sop.yaml` 和 `*_report_template.md`
- `project_summary.json`、`data_summary.md`、`_audit/` 进入 `README.md` 的维护说明和质量提示

如果最终目标是“Project 索引 + 模块五件套”，再追加两条：

- 根目录保留 `SOP.md`，project 目录保留 `overview.md`
- 每个 logstore 的最终 `output_path` 以 `<module>/README.md` 为入口文件，project 索引默认链接到这里

## 11. 故障排查

出错时直接读 `rules/troubleshooting.md`，不要重新发明排查路径。
