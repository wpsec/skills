# Claude MCP 配置

## 还原步骤

将 `mcp.json` 复制到 `~/.claude/mcp.json`。Claude Code 启动时自动加载。

如需合并到已有配置,手动将 `mcpServers` 下的条目合并。

## 当前配置

- `prompt-optimizer`:HTTP MCP,需先 Docker 部署(见 `mcp/prompt-optimizer/README.md`)

> 本地调试工具 `burp-ai-agent` 不入库