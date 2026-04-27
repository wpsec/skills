# aliyun-sls-sop

统一处理阿里云 SLS 文档生成的 skill。

它已经同时覆盖两类能力：

- 仓库文档模式：根据 CSV、CSV.GZ、现有目录规范和固定话术，生成或维护 `README.md`、`overview.yaml`、`*_datasources.yaml`、`*_analysis_sop.yaml`、`*_report_template.md`。
- SLS 资源流水线模式：根据 SLS project、本地抓取目录或单个 logstore 目录，抽取 index、dashboard、alert、scheduled_sql、saved_search，生成 `overview.md` / `SKILL.md`，并支持断点续跑、查询验证、审计。
- SOP 可执行 Contract 模式：在现有 SOP 仓库上补 `workflow`、`module`、`datasource`、`correlation` 的机器可执行 schema，让 `sop-chat` 或其它 agent 能按步骤联动分析，而不只停在说明文字。

两者也可以组合：

- 保留根目录 `SOP.md` 和 project `overview.md`
- 同时把每个 leaf logstore 落成五件套模块目录

## 适用场景

- 用户提供 CSV 或 CSV.GZ 样本，希望快速起一套可复用模块骨架。
- 用户要求“和同目录其它文档对齐”，需要补齐 README、overview、datasource、analysis_sop、report_template。
- 用户直接给 SLS project 名称，希望从线上资源生成 SOP 或 SKILL。
- 用户提供 `.input/<project>/` 这类标准化输入目录，希望从本地数据生成 SOP 或 SKILL。
- 用户既要 project 级索引，又要每个 logstore 输出五件套模块文档。
- 用户需要恢复上次中断的生成任务，或者对已生成结果做质量审计。
- 用户要把说明书式 YAML 收敛成可执行 contract，给联动分析或 step executor 直接消费。

## 目录结构

- `SKILL.md`：统一入口，负责模式路由、输出选择和收尾约束。
- `references/intake-patterns.md`：输入解析、环境识别、硬编码边界。
- `references/output-modes.md`：四种输出模式的路由规则和相互映射。
- `references/executable-contracts.md`：SOP 仓库可执行 schema、workflow step、handoff 和事实 contract。
- `references/sls-project-workflow.md`：SLS project / 本地输入目录的完整流水线。
- `references/log-families.md`：日志家族识别与默认模板路由。
- `references/doc-types.md`：仓库五件套与索引型单文档的职责定义。
- `references/output-contracts.md`：最低质量标准。
- `rules/`：字段说明、查询精选、查询验证、索引更新、审计、排障等细则。
- `scripts/profile_csv.py`、`scripts/generate_scaffold.py`：CSV 模式下的画像和骨架生成。
- `scripts/fetch_sls_data.py` 到 `scripts/aggregate_audit.py`：吸收自 `generate-sls-sop` 的 project 级流水线能力。
- `scripts/tests/`：流水线脚本单测。
- `evals/`：评测清单和 fixtures。
- `agents/openai.yaml`：agent UI 元数据。

## 推荐阅读顺序

1. 先读 `SKILL.md`，确定当前请求属于哪种模式。
2. 读 `references/intake-patterns.md`，确认输入类型和环境。
3. 读 `references/output-modes.md`，确认最终产物是五件套、SOP 还是 SKILL。
4. 如果目标是修改现有 SOP 仓库或补 workflow / handoff，继续读 `references/executable-contracts.md`。
5. 如果输入是 SLS project 或本地抓取目录，继续读 `references/sls-project-workflow.md`。
6. 如果输入是 CSV，执行 `scripts/profile_csv.py`；需要骨架时执行 `scripts/generate_scaffold.py`。
7. 生成前按需读 `references/log-families.md`、`references/doc-types.md` 和 `rules/*.md`。
8. 收尾时对照 `references/output-contracts.md` 自检。

## 常用命令

```bash
python3 scripts/profile_csv.py /path/to/sample.csv
python3 scripts/profile_csv.py /path/to/sample.csv.gz
python3 scripts/generate_scaffold.py /path/to/sample.csv --out-dir /path/to/module
python3 scripts/prepare_project.py .input/my-project
python3 scripts/update_status.py .input/my-project --resume-check
python3 scripts/prepare_audit.py .input/my-project --mode sample
```

## 输出原则

- 默认区分稳定事实和动态事实，不把样本热点值直接写死进永久文档。
- 如果用户要仓库模块文档，优先交付五件套，不用 overview.md 代替全部产物。
- 如果用户既要 project 级索引又要模块文档，保留 `SOP.md` 与 project `overview.md`，leaf 默认以 `README.md` 作为入口。
- 如果用户明确要 `overview.md` 或 `SKILL.md`，可以直接按索引型单文档结构交付。
- 如果输入来自 SLS project，但用户最终要仓库文档，先走 project 级流水线，再把产物折叠成五件套。
- 如果用户要联动分析能力，默认保留可读文档，再叠加可执行 contract，不把两者对立起来。

## 建议提问方式

- `根据这份 CSV 日志生成一套对齐现有目录的 SOP`
- `补齐 README、overview、datasource、analysis_sop、report_template`
- `帮我生成 <project-name> 的 SOP 文档`
- `保留 project 级索引，同时每个 logstore 输出 README、overview.yaml、datasource、analysis_sop、report_template`
- `帮我从 .input/my-project/ 生成 SKILL`
- `继续上次的 SOP 生成`
- `帮我生成 SOP，并验证 query 语法`
- `对已生成的 SOP 做质量审计`
- `把现有 SOP 仓库的 YAML 收敛成可执行 schema，保留现有说明文字`
- `给这个模块补 workflow steps、handoff 和 datasource/correlation contract`
