# Claude MCP 配置

## 还原步骤

将 `mcp.json` 中的 `mcpServers` 合并到 `~/.claude.json` 的 `mcpServers` 对象。Claude Code 启动时加载用户级 MCP 配置。

CodeGraph 设置了 `alwaysLoad`，让 `codegraph_explore` 在会话开始时可用。重启 Claude Code 后生效。

## 服务列表

| 服务 | 来源 | 安装方式 |
|------|------|----------|
| codegraph | [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | `npm install -g @colbymchenry/codegraph` |
| sequential-thinking | npm `@modelcontextprotocol/server-sequential-thinking` | Node.js 24+，`npx -y` 使用 2.1.1 |

> 本地调试工具 `burp-ai-agent` 不入库
