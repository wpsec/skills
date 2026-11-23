# Claude MCP 配置

## 还原步骤

将 `mcp.json` 中的 `mcpServers` 合并到 `~/.claude.json` 的 `mcpServers` 对象。Claude Code 启动时加载用户级 MCP 配置。

CodeGraph 设置了 `alwaysLoad`，让 `codegraph_explore` 在会话开始时可用。重启 Claude Code 后生效。

## 更新

- 用 `codegraph --check` 查看更新，用 `codegraph upgrade` 更新本机版本。升级后在每个已索引项目运行 `codegraph index`，让索引包含新版本修复。
- `sequential-thinking` 使用模板中固定的 npm 版本；核对上游发布后，同步修改模板与本说明，再合并到 CLI 配置。

## 服务列表

| 服务 | 来源 | 安装方式 |
|------|------|----------|
| codegraph | [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | `npm install -g @colbymchenry/codegraph` |
| sequential-thinking | npm `@modelcontextprotocol/server-sequential-thinking` | Node.js 24+，`npx -y` 使用 2.2.0 |

> 本地调试工具 `burp-ai-agent` 不入库
