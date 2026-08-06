# Codex MCP 配置

## 还原步骤

1. 安装 codegraph CLI

   ```bash
   go install github.com/colbymchenry/codegraph@latest
   ```

   来源: [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph)
   验证: `codegraph --version`

2. 确保 Node.js 可用(npx 拉取 sequential-thinking)

   ```bash
   node --version
   ```

3. 将 `mcp-servers.toml` 内容合并到 `~/.codex/config.toml` 的 `[mcp_servers]` 段

## 服务列表

| 服务 | 来源 | 安装方式 |
|------|------|----------|
| codegraph | [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | `go install` |
| sequential-thinking | npm `@modelcontextprotocol/server-sequential-thinking` | `npx` 自动拉取 |