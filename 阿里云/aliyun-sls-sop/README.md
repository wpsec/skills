# aliyun-sls-sop

用于把阿里云 SLS 结构化日志样本和现有目录规范沉淀成可复用文档，而不是一次性分析说明。适合生成或维护 SOP、README、`overview.yaml`、datasource 配置、报告模板以及相关运维或安全文档。

## 适用场景

- 用户提供 CSV 或 CSV.GZ 日志样本，希望快速生成一套模块骨架。
- 用户要求“和同目录其它文档对齐”，需要补齐 README、SOP、datasource、report template。
- 用户希望基于“分析某环境最近事件”这类固定话术，将结果沉淀为后续可复用文档。
- 用户明确要求避免把样本中的对象名、IP、实例 ID 等动态值写死进永久文档。

## 文件清单

- `SKILL.md`：执行入口，定义判断流程、生成策略和收尾检查。
- `references/intake-patterns.md`：约束请求解析、环境识别和硬编码边界。
- `references/log-families.md`：日志家族识别与默认文档路由规则。
- `references/doc-types.md`：文档套件职责划分与最小输出集合。
- `references/output-contracts.md`：最终结果的最低质量标准。
- `scripts/profile_csv.py`：对 CSV 或 CSV.GZ 做字段画像，帮助识别时间、身份、动作、状态和对象字段。
- `scripts/generate_scaffold.py`：根据日志样本输出一套可继续细化的模块文档骨架。
- `agents/openai.yaml`：相关 agent 配置。

## 推荐阅读顺序

1. 先读 `SKILL.md`，明确这个 skill 处理什么问题。
2. 如果输入是日志样本，执行 `scripts/profile_csv.py` 做字段画像。
3. 如果要快速起骨架，执行 `scripts/generate_scaffold.py`。
4. 生成前分别参考 `intake-patterns.md`、`log-families.md`、`doc-types.md`。
5. 收尾时对照 `output-contracts.md` 自检。

## 使用示例

```bash
python3 scripts/profile_csv.py /path/to/sample.csv
python3 scripts/profile_csv.py /path/to/sample.csv.gz
python3 scripts/generate_scaffold.py /path/to/sample.csv --out-dir /path/to/module
```

## 输出约束

- README 负责人工导航，不承载详细 SOP 流程。
- `overview.yaml` 只做导航和任务路由，不复制整套 SOP。
- datasource 文件只保留稳定环境映射与运行时解析规则。
- SOP 文件必须包含触发条件、执行步骤、判断标准、升级路径、记录要求。
- report template 必须覆盖 SOP 承诺的输出结果。

## 样本使用约束

- 默认区分稳定事实和动态事实。
- 样本中的 bucket、object、设备名、主机名、IP、实例 ID、request id、导出文件名等，不应直接写成永久规则。
- 如果环境无法稳定识别，应输出可迁移的通用骨架，而不是借用当前仓库的偶然命名。

## 建议提问方式

- `根据这份 CSV 日志生成一套对齐现有目录的 SOP`
- `根据这份 CSV.GZ 日志样本生成一套模块骨架`
- `补齐 README、overview、datasource、analysis_sop、report_template`
- `分析 PROD 某系统 最近的事件，并沉淀成 SOP`
