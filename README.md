# skills

仓库用于存放可复用的本地 skill 与 MCP 配置。Codex 与 Claude Code 共用本仓库:两边各自的 `skills/` 目录通过软链指向这里的 skill,改一处两边生效。

## 目录

### 安全审计

> 覆盖 Skill 入口安全扫描与 Java Web 全链路漏洞审计

| skill | 说明 | 来源 |
|---|---|---|
| `skill-sentinel` | Skill 安全扫描哨兵,在安装/加载前进行安全审计。基于 839 条正则规则,覆盖 10 大风险分类和 14 个 APT 攻击技术领域 | 本仓库自研 |
| `java-route-mapper` | 从源码提取所有 HTTP 路由与参数结构,支持 Spring MVC / Servlet / JAX-RS / Struts 2 / CXF | [RuoJi6/audit-skills](https://github.com/RuoJi6/audit-skills/) |
| `java-route-tracer` | 追踪从 Controller 到 DAO 的完整调用链,输出每层文件位置、方法签名和可传入参数 | 同上 |
| `java-audit-pipeline` | 编排整条审计流水线,调度路由提取、鉴权审计、组件漏洞、调用链追踪等子 skill | 同上 |
| `java-auth-audit` | 识别鉴权实现,检测鉴权绕过漏洞和越权访问缺陷。支持 Shiro / Spring Security / JWT / Filter | 同上 |
| `java-sql-audit` | SQL 注入审计,追踪参数到 SQL 拼接点。支持 JDBC / MyBatis / Hibernate | 同上 |
| `java-xxe-audit` | XXE 漏洞审计,检测 XML 解析器配置与外部实体引用 | 同上 |
| `java-file-read-audit` | 任意文件读取审计,追踪路径参数到 File 操作 | 同上 |
| `java-file-upload-audit` | 任意文件上传审计,检测上传点与文件类型校验逻辑 | 同上 |
| `java-vuln-scanner` | 扫描 pom.xml / build.gradle / jar 中的第三方依赖,匹配已知 CVE 漏洞规则 | 同上 |

> `java-shared` 为公共规则与工具库(无 SKILL.md,非独立 skill),不列入。

### 开发效率

| skill | 说明 | 来源 |
|---|---|---|
| `code-review-skill` | 多语言 PR 审查指南,覆盖 React 19 / Vue 3 / Angular 17+ / Svelte 5 / Rust / Java / Go / Python / C# / Kotlin / Swift / NestJS / C/C++ / PHP / Django 等,含各语言专项 reference 和 pr-analyzer.py | [awesome-skills/code-review-skill](https://github.com/awesome-skills/code-review-skill) |

### 内容处理

| skill | 说明 | 来源 |
|---|---|---|
| `humanizer-zh` | 去除中文文本的 AI 写作痕迹,翻译自 blader/humanizer | [op7418/humanizer-zh](https://github.com/op7418/humanizer-zh) |

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

`mcp/` 目录存放 MCP 服务器配置备份,用于跨机还原或参考。与 skill 不同,MCP 配置无法用软链同步,需手动复制到对应 CLI 的配置位置。

| 目录 | 对应 CLI | 还原路径 |
|---|---|---|
| `mcp/codex/mcp-servers.toml` | Codex | 合并到 `~/.codex/config.toml` 的 `[mcp_servers]` 段 |
| `mcp/claude/` | Claude | 复制到 `~/.claude/mcp.json`(当前仅有 burp-ai-agent 本地调试,不入库) |

当前纳入仓库的 MCP 服务:

- **codegraph**:代码知识图谱索引,为 Codex 提供符号级代码搜索
- **sequential-thinking**:结构化思考工具

## 通过 Claude Code 使用

- 对话里直接点名 skill,例如 `aliyun-sls-sop` 或 `skill-sentinel`。
- 斜杠命令 `/skill-sentinel` 初始化安全基线扫描。
- 同时给出任务目标、输入文件或目标目录路径。
- 详细使用说明、约束和示例写在对应 skill 的 `README.md` 与 `SKILL.md` 中。

示例:

- `使用 aliyun-sls-sop,根据这份 CSV 日志生成一套对齐现有目录的 SOP`
- `/skill-sentinel` 扫描所有已安装 Skill
- `扫描 ~/.claude/skills/ 下有没有恶意 Skill`