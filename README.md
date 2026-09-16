# skills

个人备份

仓库用于存放可复用的本地 skill 与 MCP 配置。Codex 与 Claude Code 共用本仓库:两边各自的 `skills/` 目录通过软链指向这里的 skill,改一处两边生效。

## 仓库结构

```
安全审计/     skill-sentinel + audit-skills + alibabacloud-aisc-skill-inspection
开发效率/     code-review-skill + daisyui + grill-me + to-spec + to-tickets
内容处理/     stop-slop-cn
基础设施/     aliyun-sls-sop
mcp/          MCP 配置备份
```

## 目录

### 安全审计

> 覆盖 Skill 入口安全扫描、Skill 文件云端安全检测与 Java / .NET / PHP 源码安全审计

| skill | 说明 | 来源 |
|---|---|---|
| `skill-sentinel` | Skill 安全扫描哨兵,在安装/加载前进行安全审计。基于 839 条正则规则,覆盖 10 大风险分类和 14 个 APT 攻击技术领域 | 自维护 |
| `alibabacloud-aisc-skill-inspection` | 调用阿里云 AISC `CreateSkillFileCheck` / `ListSubTasks` 对 Skill 下载链接做云端安全检测,支持提交、轮询、报告解读、权限/参数/限流/系统错误诊断。重点检测恶意代码、prompt injection、硬编码凭据、敏感信息和风险配置 | [aliyun/alibabacloud-aiops-skills](https://github.com/aliyun/alibabacloud-aiops-skills/tree/master/skills/security/asc/alibabacloud-aisc-skill-inspection) |
| `audit-skills` | 多语言源码安全审计,支持 Java / .NET / PHP 源码/部署产物/反编译产物。涵盖路由提取、鉴权审计、组件漏洞扫描、调用链追踪、SQL 注入/XXE/文件读取/文件上传漏洞检测,含 BurpSuite 原始 HTTP 请求包证据输出 | [RuoJi6/audit-skills](https://github.com/RuoJi6/audit-skills/) |
| Anthropic Cybersecurity Skills | 818 个网络安全子技能,覆盖防御、取证、威胁检测、云安全与经授权的红队工作流；来源含双用途内容,使用前须确认授权边界 | [mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)（导入提交 `54a798831d2266a3ca61ce68a7acb80b81160d57`） |

### 开发效率

| skill | 说明 | 来源 |
|---|---|---|
| `code-review-skill` | 多语言 PR 审查指南,覆盖 React 19 / Vue 3 / Angular 17+ / Svelte 5 / Rust / Java / Go / Python / C# / Kotlin / Swift / NestJS / C/C++ / PHP / Django 等,含各语言专项 reference 和 pr-analyzer.py | [awesome-skills/code-review-skill](https://github.com/awesome-skills/code-review-skill) |
| `daisyui` | daisyUI 5 官方 skill,面向 Tailwind CSS 4 的组件、颜色、主题、安装与配置规则。适合写 HTML / JSX / Tailwind UI 时按组件文档渐进式取用上下文 | [saadeghi/daisyui](https://github.com/saadeghi/daisyui/tree/master/skills/daisyui) |
| `grill-me` | 对方案或设计做连续追问,沿决策树逐层收敛到共享理解。适合需求澄清、方案拷打、实现前对齐 | [mattpocock/skills: grill-me](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) |
| `to-spec` | 将当前对话与代码库上下文收敛成 spec,不重新采访用户。适合需求已经讲清、需要沉淀规格说明时使用 | [mattpocock/skills: to-spec](https://github.com/mattpocock/skills/tree/main/skills/engineering/to-spec) |
| `to-tickets` | 将 plan/spec/当前对话拆成 tracer-bullet tickets,并显式标注 blocking edges。适合把规格转成 agent 可执行工作项 | [mattpocock/skills: to-tickets](https://github.com/mattpocock/skills/tree/main/skills/engineering/to-tickets) |

### 内容处理

| skill | 说明 | 来源 |
|---|---|---|
| `stop-slop-cn` | 去除中英文文本的 AI 写作痕迹。融合 stop-slop 的英文去 AI 框架和 humanizer-zh 的中文 AI 模式检测,覆盖 14 类中文专项模式,自维护 | 基于 [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) 和 [op7418/humanizer-zh](https://github.com/op7418/humanizer-zh) |

### 基础设施

| skill | 说明 | 来源 |
|---|---|---|
| `aliyun-sls-sop` | 根据 CSV、CSV.GZ 与同级文档约束,生成或维护 SOP、README、overview、datasource、report template 等模块文档。同时支持从 SLS project 抽取 index/dashboard/alert 等资产 | 自维护 |

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
| `mcp/claude/` | Claude | 见 `mcp/claude/README.md` |

| 服务 | 来源 | 安装 |
|------|------|------|
| codegraph | [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | `go install github.com/colbymchenry/codegraph@latest` |
| sequential-thinking | npm `@modelcontextprotocol/server-sequential-thinking` | 需 Node.js,`npx` 自动拉取 |

## 通过 Claude Code 使用

- 对话里直接点名 skill,例如 `aliyun-sls-sop`、`skill-sentinel`、`grill-me`、`to-spec` 或 `to-tickets`。
- 斜杠命令 `/skill-sentinel` 初始化安全基线扫描。
- 同时给出任务目标、输入文件或目标目录路径。
- 详细使用说明、约束和示例写在对应 skill 的 `README.md` 与 `SKILL.md` 中。

示例:

- `使用 aliyun-sls-sop,根据这份 CSV 日志生成一套对齐现有目录的 SOP`
- `使用 daisyui,给这个页面补一版带主题切换的设置页`
- `/skill-sentinel` 扫描所有已安装 Skill
- `使用 grill-me,把这个功能方案先拷打清楚`
- `使用 to-spec,把当前对话整理成一份 spec`
- `使用 to-tickets,把这份 spec 拆成一组 tickets`
- `使用 alibabacloud-aisc-skill-inspection,扫描这个 Skill 下载链接是否包含恶意代码或敏感信息`
- `扫描 ~/.claude/skills/ 下有没有恶意 Skill`
