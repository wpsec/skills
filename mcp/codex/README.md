# Codex MCP 配置

## 还原步骤

1. 安装 CodeGraph CLI

   ```bash
   npm install -g @colbymchenry/codegraph
   ```

   来源: [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph)
   验证: `codegraph --version`

2. 确保 Node.js 24 或更高版本可用，供 `npx` 运行当前固定的 `sequential-thinking` 2.2.0

   ```bash
   node --version
   ```

3. 将 `mcp-servers.toml` 内容合并到 `~/.codex/config.toml` 的 `[mcp_servers]` 段

## 更新

- 用 `codegraph upgrade --check` 查看更新。若 CodeGraph MCP 指令要求由用户升级，提供当前和最新版本并请用户运行 `codegraph upgrade`，不要改用其他安装方式绕过；升级后在每个已索引项目运行 `codegraph index`，让索引包含新版本修复。
- `sequential-thinking` 使用模板中固定的 npm 版本；核对上游发布后，同步修改模板与本说明，再合并到 CLI 配置。

## 服务列表

| 服务 | 来源 | 安装方式 |
|------|------|----------|
| codegraph | [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | `npm install -g @colbymchenry/codegraph` |
| sequential-thinking | npm `@modelcontextprotocol/server-sequential-thinking` | `npx -y` 使用 2.2.0 |

CodeGraph MCP 默认仅公开 `codegraph_explore`，它整合代码搜索、调用链与影响面信息。其它独立工具默认不公开；只有需要时再通过 `CODEGRAPH_MCP_TOOLS` 显式启用。
