# skills

仓库用于存放可复用的本地 skill 与 MCP 配置。Codex 与 Claude Code 共用本仓库:两边各自的 `skills/` 目录通过软链指向这里的 skill,改一处两边生效。

## 仓库结构

```
安全审计/     skill-sentinel + audit-skills
开发效率/     code-review-skill
内容处理/     stop-slop-cn
基础设施/     aliyun-sls-sop
mcp/          MCP 配置备份
```

## 目录

### 安全审计

> 覆盖 Skill 入口安全扫描与 Java / .NET / PHP 源码安全审计

| skill | 说明 | 来源 |
|---|---|---|
| `skill-sentinel` | Skill 安全扫描哨兵,在安装/加载前进行安全审计。基于 839 条正则规则,覆盖 10 大风险分类和 14 个 APT 攻击技术领域 | 本仓库自研 |
| `audit-skills` | 多语言源码安全审计,支持 Java / .NET / PHP 源码/部署产物/反编译产物。涵盖路由提取、鉴权审计、组件漏洞扫描、调用链追踪、SQL 注入/XXE/文件读取/文件上传漏洞检测,含 BurpSuite 原始 HTTP 请求包证据输出 | [RuoJi6/audit-skills](https://github.com/RuoJi6/audit-skills/) |

### 开发效率

| skill | 说明 | 来源 |
|---|---|---|
| `code-review-skill` | 多语言 PR 审查指南,覆盖 React 19 / Vue 3 / Angular 17+ / Svelte 5 / Rust / Java / Go / Python / C# / Kotlin / Swift / NestJS / C/C++ / PHP / Django 等,含各语言专项 reference 和 pr-analyzer.py | [awesome-skills/code-review-skill](https://github.com/awesome-skills/code-review-skill) |

### 内容处理

| skill | 说明 | 来源 |
|---|---|---|
| `stop-slop-cn` | 去除中英文文本的 AI 写作痕迹。融合 stop-slop 的英文去 AI 框架和 humanizer-zh 的中文 AI 模式检测,覆盖 14 类中文专项模式,自维护 | 基于 [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) 和 [op7418/humanizer-zh](https://github.com/op7418/humanizer-zh) |

### 基础设施

| skill | 说明 | 来源 |
|---|---|---|
| `aliyun-sls-sop` | 根据 CSV、CSV.GZ 与同级文档约束,生成或维护 SOP、README、overview、datasource、report template 等模块文档。同时支持从 SLS project 抽取 index/dashboard/alert 等资产 | 本仓库自研 |

## 同步到本地 Codex / Claude

两个 CLI 的 skills 目录都是固定路径(`~/.codex/skills`、`~/.claude/skills`),无法配置指向本仓库,因此用软链桥接:

```bash
bash sync-skills.sh
```

脚本扫描本仓库所有含 `SKILL.md` 的目录,在两边 `skills/` 目录建立同名软链(以 frontmatter `name` 为准),跳过各自专属(Codex 的 `.system`、Claude 的 `learned`),幂等可重复执行。

新增 skill 后跑一次脚本两边即生效;删除 skill 需手动删两边对应的旧软链(脚本不主动清理)。

## MCP 配置

`mcp/` 目录存放 MCP 服务器配置备份与安装说明,用于跨机还原。与 skill 不同,MCP 配置无法用软链同步,需手动复制到对应 CLI 的配置位置,并安装依赖工具。

| 目录 | 对应 CLI | 还原方式 |
|---|---|---|
| `mcp/codex/` | Codex | 见 `mcp/codex/README.md` |
| `mcp/claude/` | Claude | 见 `mcp/claude/README.md`(当前仅有 burp-ai-agent 本地调试,不入库) |

| 服务 | 来源 | 安装 |
|------|------|------|
| codegraph | [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | `go install github.com/colbymchenry/codegraph@latest` |
| sequential-thinking | npm `@modelcontextprotocol/server-sequential-thinking` | 需 Node.js,`npx` 自动拉取 |
| prompt-optimizer | [linshenkx/prompt-optimizer](https://github.com/linshenkx/prompt-optimizer) | Docker 部署,见 `mcp/prompt-optimizer/README.md` |

## 通过 Claude Code 使用

- 对话里直接点名 skill,例如 `aliyun-sls-sop` 或 `skill-sentinel`。
- 斜杠命令 `/skill-sentinel` 初始化安全基线扫描。
- 同时给出任务目标、输入文件或目标目录路径。
- 详细使用说明、约束和示例写在对应 skill 的 `README.md` 与 `SKILL.md` 中。

示例:

- `使用 aliyun-sls-sop,根据这份 CSV 日志生成一套对齐现有目录的 SOP`
- `/skill-sentinel` 扫描所有已安装 Skill
- `扫描 ~/.claude/skills/ 下有没有恶意 Skill`