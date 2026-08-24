# daisyui

> 来源: [saadeghi/daisyui - skills/daisyui](https://github.com/saadeghi/daisyui/tree/master/skills/daisyui)

## 作用

给 Codex / Claude 提供 daisyUI 5 与 Tailwind CSS 4 的组件、颜色、主题、安装和配置规则,按需读取组件文档后生成 UI 代码。

## 适用时机

- 需要写 HTML / JSX / Tailwind CSS UI
- 需要基于现成组件库而不是手写原子类拼装页面
- 需要处理主题切换、语义颜色、组件结构和 class 约束

## 上游约束

- 使用 daisyUI class 前先读 `usage/SKILL.md`
- 使用 daisyUI 颜色或主题前先读 `colors/SKILL.md`
- 安装或修改插件配置时再读 `install/SKILL.md` 和 `config/SKILL.md`
- 具体组件落地前先读对应的 `components/*.md`

## 本地维护

- 本目录为上游官方 skill 的本地镜像,保留原始 `SKILL.md` 结构
- 新增或更新后执行 `bash sync-skills.sh`,同步到 `~/.codex/skills` 和 `~/.claude/skills`
- 由于上游把 `install`、`config`、`usage`、`colors` 也拆成了独立 `SKILL.md`,`sync-skills.sh` 会额外挂出 `daisyui-*` 软链,属于预期行为
- 上游文档同时推荐使用 daisyUI MCP;当前仓库先维护免费 skill 版本
