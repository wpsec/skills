---
name: skill-sentinel
description: Skill 安全扫描哨兵 — 在 Skill 安装/加载前进行安全审计，输出结构化风险结论。支持 --init 初始化扫描和单 Skill 扫描。
agent-type: security
---

# SkillSentinel — Skill 安全扫描哨兵

SkillSentinel 是 Skill 生态的入口门禁，在 Skill 安装、加载、启用之前执行安全把关。

## 安装

```bash
pip install -r requirements.txt
```

## 命令

> 所有命令需从 Skill 目录执行：`cd ~/.claude/skills/skill-sentinel`

### 初始化安全基线（扫描所有已安装 Skill）

```bash
cd ~/.claude/skills/skill-sentinel && python3 -m skill_sentinel --init
```

扫描系统中所有已安装的 Skill，输出汇总报告。
- 自动发现 `~/.claude/skills/`、`~/.cursor/skills/` 等常见路径
- 输出每个 Skill 的风险等级（BLOCK / REVIEW / ALLOW）
- 退出码 2 = 存在高危 Skill，0 = 全部安全

### 扫描单个 Skill

```bash
cd ~/.claude/skills/skill-sentinel && python3 -m skill_sentinel /path/to/skill
cd ~/.claude/skills/skill-sentinel && python3 -m skill_sentinel /path/to/skill --json
cd ~/.claude/skills/skill-sentinel && python3 -m skill_sentinel /path/to/skill -o report.json
```

### 扫描指定目录下所有 Skill

```bash
cd ~/.claude/skills/skill-sentinel && python3 -m skill_sentinel --scan-dir /path/to/skills
```

## 输出解读

| 风险等级 | 含义 | 建议动作 |
|---------|------|---------|
| BLOCK | 高危，检测到反弹Shell、后门、数据破坏等特征 | 禁止启用，人工审查 |
| REVIEW | 中危，存在需要确认的操作 | 人工审查后决定 |
| ALLOW | 低风险 | 可以启用 |

## 风险分类

| # | 分类 | 说明 |
|---|------|------|
| 1 | 提示注入 | 自然语言指令劫持、角色扮演注入 |
| 2 | 数据外发 | HTTP 请求、Webhook、邮件、FTP |
| 3 | 提权与越权 | sudo、setuid、capabilities |
| 4 | 持久化与自启动 | crontab、systemd、注册表、LaunchAgent |
| 5 | 文件破坏与目录篡改 | rm -rf、删除/覆写关键文件 |
| 6 | 供应链投毒 | curl\|bash、pip/npm 恶意安装、CI/CD 篡改 |
| 7 | 反弹Shell/后门 | socket+dup2、SSH 隧道、ngrok/frp |
| 8 | 隐蔽下载与远程执行 | eval/exec、base64 解码执行 |
| 9 | 敏感信息泄露 | 硬编码密钥、.env 读取、SSH 私钥 |
| 10 | 混淆与遮蔽行为 | chattr、nohup、screen/tmux 隐藏 |

## 规则文件

- `rules/total_rules.py`：全高危操作扫描（312 条）
- `rules/precise_rules.py`：恶意高危精确扫描（288 条）
- `rules/apt_rules.py`：APT 级高级威胁检测（239 条）

## 调用约定

当用户请求对 Skill 进行安全检查时，执行以下命令并解读结果：

```bash
cd ~/.claude/skills/skill-sentinel && python3 -m skill_sentinel --init
```

- 存在 BLOCK → 向用户展示高危 Skill 列表，建议禁用
- 全部 REVIEW → 列出中危 Skill，让用户决定
- 全部 ALLOW → 告知用户所有 Skill 通过检查