#!/usr/bin/env bash
# sync-skills.sh — 把主仓库里的 skill 同步为 Claude / Codex 两边 skills 目录的软链
#
# 用法:新增或删除 skill 后,在主仓库跑一次 `bash sync-skills.sh`,两边自动更新软链。
# 跳过各自专属目录:Claude 的 learned、Codex 的 .system。
# 幂等:已是正确软链则跳过;存在非软链同名条目则备份为 .bak.<时间戳> 后重建。

set -euo pipefail

REPO="$HOME/Documents/Github/skills"
TARGETS=(
  "$HOME/.claude/skills"
  "$HOME/.codex/skills"
)
SKIP_NAMES=(.system learned)   # 两边各自专属,不覆盖

# 读取 SKILL.md frontmatter 的 name 字段;缺失则用目录名兜底
read_name() {
  local skillmd="$1"
  awk '
    NR==1 && /^---[[:space:]]*$/ { in_fm=1; next }
    in_fm && /^---[[:space:]]*$/ { exit }
    in_fm && /^name:/ {
      sub(/^name:[[:space:]]*/, "")
      sub(/[[:space:]]*$/, "")
      print
      exit
    }
  ' "$skillmd"
}

is_skip() {
  local n="$1" s
  for s in "${SKIP_NAMES[@]}"; do [[ "$n" == "$s" ]] && return 0; done
  return 1
}

while IFS= read -r skillmd; do
  src_dir="$(dirname "$skillmd")"
  name="$(read_name "$skillmd")"
  name="${name:-$(basename "$src_dir")}"
  if is_skip "$name"; then
    echo "skip (reserved): $name"
    continue
  fi
  for tgt in "${TARGETS[@]}"; do
    mkdir -p "$tgt"
    link="$tgt/$name"
    if [ -L "$link" ] && [ "$(readlink "$link")" = "$src_dir" ]; then
      continue
    fi
    if [ -e "$link" ] && [ ! -L "$link" ]; then
      mv "$link" "$link.bak.$(date +%s)"
    fi
    ln -sfn "$src_dir" "$link"
    echo "linked $name -> $src_dir  [$tgt]"
  done
done < <(find "$REPO" -name SKILL.md -not -path '*/.git/*' -not -path '*skill_sandbox*')

# ── MCP 配置检查 ──────────────────────────────────────────────
# MCP 无法像 skill 一样用软链同步,这里只做状态检查并给出操作提示。

check_mcp() {
  local changed=0
  echo
  echo ">>> MCP 配置检查"

  if ! command -v codegraph &>/dev/null; then
    echo "[!] codegraph 未安装"
    echo "    npm install -g @colbymchenry/codegraph"
    echo "    来源 https://github.com/colbymchenry/codegraph"
    changed=1
  fi

  if ! command -v node &>/dev/null; then
    echo "[!] Node.js 未安装,sequential-thinking MCP 需要 Node.js 24+"
    changed=1
  fi

  if [ -f "$REPO/mcp/codex/mcp-servers.toml" ]; then
    echo "[!] Codex MCP 需手动合并"
    echo "    将 mcp/codex/mcp-servers.toml 合并到 ~/.codex/config.toml 的 [mcp_servers] 段"
    changed=1
  fi

  if [ -f "$REPO/mcp/claude/mcp.json" ]; then
    echo "[!] Claude MCP 配置需合并到 ~/.claude.json 的 mcpServers 段"
    changed=1
  fi

  if [ "$changed" -eq 0 ]; then
    echo "[OK] MCP 配置无变化"
  fi
}

check_mcp
