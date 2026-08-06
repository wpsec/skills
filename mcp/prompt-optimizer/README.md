# Prompt Optimizer MCP Server

> 来源: [linshenkx/prompt-optimizer](https://github.com/linshenkx/prompt-optimizer) (32k stars)

AI 提示词优化工具,支持系统提示词 / 用户提示词优化、多轮迭代、分析与对比评估。通过 MCP 协议集成到 Claude Code / Codex 等客户端。

## 部署

```bash
docker run -d -p 8081:80 \
  -e VITE_OPENAI_API_KEY=your-openai-key \
  -e MCP_DEFAULT_MODEL_PROVIDER=openai \
  --name prompt-optimizer \
  linshen/prompt-optimizer
```

- Web 界面: `http://localhost:8081`
- MCP 服务器: `http://localhost:8081/mcp`

## 客户端配置

### Claude Code

在 `~/.claude/mcp.json` 的 `mcpServers` 中添加:

```json
"prompt-optimizer": {
  "type": "url",
  "url": "http://localhost:8081/mcp"
}
```

### Codex

在 `~/.codex/config.toml` 的 `[mcp_servers]` 段中添加:

```toml
[mcp_servers.prompt-optimizer]
type = "url"
url = "http://localhost:8081/mcp"
```

## MCP 工具

- `optimize-user-prompt`: 优化用户提示词
- `optimize-system-prompt`: 优化系统提示词
- `iterate-prompt`: 基于特定需求迭代改进提示词