# skills

仓库用于存放可复用的本地 skill。Codex 与 Claude Code 共用本仓库:两边各自的 `skills/` 目录通过软链指向这里的 skill,改一处两边生效。

## 目录

### `阿里云/`
- `aliyun-sls-sop`:根据 CSV、CSV.GZ 与同级文档约束,生成或维护 SOP、README、overview、datasource、report template 等模块文档。

### `Skill-Sentinel/`
- `skill-sentinel`:Skill 安全扫描哨兵,在 Skill 安装/加载前进行安全审计,输出结构化风险结论。基于 839 条正则规则,覆盖 10 大风险分类和 14 个 APT 攻击技术领域。

### `java-audit/`
Java 安全审计套件,10 个 skill 协作完成从路由测绘到漏洞扫描的完整审计流水线:
- `java-route-mapper` / `java-route-tracer`:路由测绘与调用追踪
- `java-shared`:公共规则与工具
- `java-audit-pipeline`:编排整条审计流水线
- `java-auth-audit`:认证与鉴权审计
- `java-sql-audit`:SQL 注入审计
- `java-xxe-audit`:XXE 审计
- `java-file-read-audit`:任意文件读取审计
- `java-file-upload-audit`:任意文件上传审计
- `java-vuln-scanner`:综合漏洞扫描

### `code-review-skill/`
- `code-review-skill`:多语言 PR 审查指南(React 19 / Vue 3 / Angular 17+ / Svelte 5 / Rust / Java / Go / Python / C# / Kotlin / Swift / NestJS / C/C++ / PHP 等),含各语言专项 reference 和 pr-analyzer.py。

### `humanizer-zh/`
- `humanizer-zh`:去除中文文本的 AI 写作痕迹,翻译自 blader/humanizer。

## 同步到本地 Codex / Claude

两个 CLI 的 skills 目录都是固定路径(`~/.codex/skills`、`~/.claude/skills`),无法配置指向本仓库,因此用软链桥接:

```bash
bash sync-skills.sh
```

脚本扫描本仓库所有含 `SKILL.md` 的目录,在两边 `skills/` 目录建立同名软链(以 frontmatter `name` 为准),跳过各自专属(Codex 的 `.system`、Claude 的 `learned`),幂等可重复执行。

新增 skill 后跑一次脚本两边即生效;删除 skill 需手动删两边对应的旧软链(脚本不主动清理)。

## 通过 Claude Code 使用

- 对话里直接点名 skill,例如 `aliyun-sls-sop` 或 `skill-sentinel`。
- 斜杠命令 `/skill-sentinel` 初始化安全基线扫描。
- 同时给出任务目标、输入文件或目标目录路径。
- 详细使用说明、约束和示例写在对应 skill 的 `README.md` 与 `SKILL.md` 中。

示例:

- `使用 aliyun-sls-sop,根据这份 CSV 日志生成一套对齐现有目录的 SOP`
- `/skill-sentinel` 扫描所有已安装 Skill
- `扫描 ~/.claude/skills/ 下有没有恶意 Skill`
