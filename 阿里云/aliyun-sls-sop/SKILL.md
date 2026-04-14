---
name: aliyun-sls-sop
description: 根据仓库既有规范、同级目录文档、模板和阿里云 SLS/CSV/CSV.GZ 等结构化日志生成或更新文档。用于创建或维护 SOP、runbook、README、overview.yaml、datasource 配置、报告模板、审计报告、巡检清单等业务/运维/安全文档；尤其适用于用户提供日志样本、要求与同目录文档对齐、使用“分析 某某 环境 某某 最近的事件”这类固定话术，或需要从日志动态抽取事实而不是硬编码样例对象，并希望自动生成一套模块文档骨架的场景。
---

# 阿里云 SLS SOP

## 快速开始

1. 先读取目标目录的同级文档。
   如果没有同级先例，默认采用脚本输出的便携命名，不偷带当前仓库里的目录名。
2. 如果用户提供了 CSV 或 CSV.GZ 日志样本，先执行 `python3 scripts/profile_csv.py <csv-path>`。
3. 如果用户要快速落一套模块骨架，执行 `python3 scripts/generate_scaffold.py <csv-path> --out-dir <目标目录>`。
4. 在判断环境、范围和哪些事实可固化之前，先读 [references/intake-patterns.md](references/intake-patterns.md)。
5. 在决定日志家族和默认命名之前，读 [references/log-families.md](references/log-families.md)。
   这是 skill 内部用的“日志类型到文档模板的路由表”，不是给最终使用者单独阅读的手册。
6. 在决定生成哪些文件、每个文件写什么之前，先读 [references/doc-types.md](references/doc-types.md)。
7. 在收尾自检前，按 [references/output-contracts.md](references/output-contracts.md) 对照检查。

## 按这个流程执行

### 1. 先把请求解析成“文档任务”

- 抽取 `environment`、`system/product`、`time range`、`artifact type`、`document type`、`analysis direction`。
- 把 `分析 某某 环境 某某 最近的事件` 这类输入当作结构化入口，而不是普通自由文本。
- 如果用户要求“目录结构和同目录其它文档对齐”，先看同级文件，再镜像它们的文件集合和命名方式。
- 如果用户说“继续做某类日志的 SOP”，默认补齐该目录下同类型模块常见的整套文档，除非仓库已有更小的固定模式。
- 当前仓库里的 `waf`、`nat`、`slsaudit-center` 等目录只属于写法参考源，不属于 skill 的固定输出结构。

### 2. 正确识别环境，不要写死

- 先用用户输入。
- 再用 datasource 元数据或文件元数据。
- 再用同级文档。
- 不要把当前仓库环境默认成通用事实。
- 如果仓库是 UAT，但用户要的是 PROD 或其它环境，文档结构要保持可复用，不能把 UAT 专有标识泄漏进新文档。

### 3. 从日志和工件里抽事实，不要硬编码

- 如果有 CSV，先用 `scripts/profile_csv.py` 做字段画像。
- 如果需要快速起一套骨架，再用 `scripts/generate_scaffold.py` 输出初稿。
- 区分**稳定事实**和**运行时事实**。
- 只有稳定事实才能写入 datasource 这类配置型文档。
- 样本里的对象名、设备名、bucket 名、IP、表名、request id 等，默认都当动态事实处理，除非用户明确确认它们是长期稳定值。
- 除非用户明确要求，否则不要把样例文件名写进永久 SOP。
- 如果没有现成目录风格可以对齐，优先生成可独立迁移的便携骨架，而不是复刻当前仓库里的模块名。

### 4. 同时覆盖业务、运维、安全三个方向

- 默认同时考虑 `business`、`ops`、`security`。
- 根据当前日志字段决定哪个方向是主线。
- 如果某个方向的结论缺少字段支撑，要直接说明，并指出还需要什么数据。
- 如果字段模式能稳定命中某个日志家族，就优先使用对应家族的默认文档套件和主线。

### 5. 生成正确的文档集合

- 如果是仓库级文档套件，按 [references/doc-types.md](references/doc-types.md) 的职责划分生成。
- 如果用户只要一个文件，只改那一个文件。
- 如果用户想做成可复用模块，优先补齐这一套：
  - `README.md`
  - `overview.yaml`
  - `*_datasources.yaml`
  - `*_analysis_sop.yaml`
  - `*_report_template.md`
- 只有当用户明确要求“和现有目录对齐”时，才借用目标仓库同级文件的命名和章节分工。

### 6. 收尾前做质量检查

- 文件命名、语气和职责要和同级文档一致。
- 输出必须能跨环境复用。
- 样本推导值在未确认稳定前，不能进入永久规则。
- 输出结果必须满足 [references/output-contracts.md](references/output-contracts.md) 的最低要求。
- SOP 必须包含触发条件、执行步骤、判断标准、升级路径、记录要求。
- 报告模板必须覆盖 SOP 承诺的输出结果。
- README 和 overview 必须把读者路由到下一个正确文件。

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

### 不应该做

- 不要把样本里的 bucket/object 名、设备名、IP、主机名、表名、request id 硬编码进 SOP 规则。
- 不要把单个样本的热点值当成永久白名单。
- 不要把样例文件名当成稳定依赖写进正式 SOP。
- 不要把所有日志都强行解释成安全问题。

## 默认输出策略

### 针对 SOP 请求

- 主线优先按 `baseline -> anomaly -> response -> root cause -> closure` 组织。
- 只有字段足够支撑时，才补具体查询示例。
- 阈值和升级规则必须来自字段模型或用户明确要求，不能凭空捏造。

### 针对仓库配套文档

- `README.md` 面向人工维护者。
- `overview.yaml` 只做导航和路由。
- datasource 文件是稳定环境映射的唯一事实源。
- SOP 文件只放固定流程和判断规则。
- report template 必须和 SOP 输出对齐。

### 针对其它文档类型

- 继续沿用“稳定事实 / 动态事实”这条边界。
- 优先复用仓库已有模板、章节和标题习惯。
- 如果仓库里没有先例，就生成一份轻量但结构清晰的文档，不要写成长篇散文。

## 配套参考文件

- 在判断环境、提炼话术模式、约束硬编码边界时，读 [references/intake-patterns.md](references/intake-patterns.md)。
- 在选择日志家族、模块目录、默认命名时，读 [references/log-families.md](references/log-families.md)。
- 在决定生成哪些文件、每个文件写什么时，读 [references/doc-types.md](references/doc-types.md)。
- 在检查输出是否达标时，读 [references/output-contracts.md](references/output-contracts.md)。

## 典型触发语句

- `根据这份 CSV 日志生成一套对齐现有目录的 SOP`
- `根据这份 CSV.GZ 日志样本生成一套模块骨架`
- `继续做某个日志类型的 sop，目录结构和同目录其它日志对齐`
- `分析 PROD 某系统 最近的事件，并沉淀成 SOP`
- `补齐 README、overview、datasource、analysis_sop、report_template`
- `把这份日志样本抽象成通用文档，不要硬编码样本里的对象`
