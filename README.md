# skills

仓库用于存放可复用的本地 skill

## 目录

### `阿里云/`

- `aliyun-sls-sop/`：根据 CSV、CSV.GZ 与同级文档约束，生成或维护 SOP、README、overview、datasource、report template 等模块文档。

### `Skill-Sentinel/`

- `skill-sentinel`：Skill 安全扫描哨兵，在 Skill 安装/加载前进行安全审计，输出结构化风险结论。基于 839 条正则规则，覆盖 10 大风险分类和 14 个 APT 攻击技术领域。

## 通过 Claude Code 使用

- 在对话里直接点名 skill，例如 `aliyun-sls-sop` 或 `skill-sentinel`。
- 斜杠命令 `/skill-sentinel` 初始化安全基线扫描。
- 同时给出任务目标、输入文件或目标目录路径。
- 详细使用说明、约束和示例写在对应 skill 的 `README.md` 与 `SKILL.md` 中。

示例：

- `使用 aliyun-sls-sop，根据这份 CSV 日志生成一套对齐现有目录的 SOP`
- `/skill-sentinel` 扫描所有已安装 Skill
- `扫描 ~/.claude/skills/ 下有没有恶意 Skill`