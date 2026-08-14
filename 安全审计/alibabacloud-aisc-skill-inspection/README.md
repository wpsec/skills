# alibabacloud-aisc-skill-inspection

对 Skill 文件下载链接执行阿里云 AISC 云端安全检测的 skill。

它面向的不是本地源码 SAST，而是把用户提供的 `download_url` 提交给 AISC，由 AISC 拉取并检测，再回收任务结果、子任务状态和风险报告。

来源：

- 上游仓库：[aliyun/alibabacloud-aiops-skills](https://github.com/aliyun/alibabacloud-aiops-skills/tree/master/skills/security/asc/alibabacloud-aisc-skill-inspection)

## 与官方版本同步

本目录是基于上游 skill 的本地维护副本，已经包含本仓库自己的 `README.md`、`generate_report.py` 以及对 `SKILL.md` / 调用脚本的适配。官方后续更新时不要直接覆盖整个目录，否则会丢失本地报告生成和翻译能力。

建议按以下流程同步：

```bash
git remote add aisc-upstream https://github.com/aliyun/alibabacloud-aiops-skills.git
git fetch aisc-upstream master
git show aisc-upstream/master:skills/security/asc/alibabacloud-aisc-skill-inspection/SKILL.md > /tmp/aisc-upstream-SKILL.md
git diff --no-index SKILL.md /tmp/aisc-upstream-SKILL.md || true
```

如果已经添加过 `aisc-upstream`，只需执行 `git fetch aisc-upstream master`。对比后，将上游新增的行为约束、API 参数和错误处理手工合并到本地 `SKILL.md` 与 `scripts/skill_file_check.py`，保留 `generate_report.py`、本 README 及本地报告文件；合并后重新执行脚本校验，不要把上游文件盲目复制过来。

## 适用场景

- 用户要判断某个 Skill 包或单个 Skill 文件是否安全。
- 用户提供一个或多个 Skill 下载链接，希望检测恶意代码、prompt injection、硬编码凭据、敏感信息或风险配置。
- 用户需要执行 AISC `CreateSkillFileCheck` / `ListSubTasks`。
- 用户已经拿到 `rootTaskId` 或 `check-report.json`，需要继续轮询或解读报告。
- 用户遇到权限、参数、限流、系统错误，需要定位失败原因。

## 最重要的约束

- 不要对用户提供的 `download_url` 做任何预拉取、预校验或可用性探测。
- 不要用 `curl`、`wget`、`HEAD`、`GET`、`requests`、浏览器访问等方式打开用户 URL。
- URL 必须原样传给 AISC，不能改 query string、签名、编码顺序或特殊字符。
- 真正允许触网的对象是 AISC，不是本地 agent。

## 核心能力

- 调用 `CreateSkillFileCheck` 提交 1 到 10 个 Skill 文件下载链接。
- 调用 `ListSubTasks` 轮询根任务下的子任务状态。
- 支持 `submit`、`poll`、`run` 三种模式。
- `run` 支持端到端提交和轮询，并输出 `check-report.json`。
- 超过 10 个文件时，由脚本自动分批并汇总结果。
- 支持对 `Virus`、`Sensitive`、`Guardrail`、`Config` 风险做结果解读。

## 目录结构

- `SKILL.md`：行为约束、执行流程、错误处理、结果解释。
- `scripts/skill_file_check.py`：AISC 官方调用包装脚本。
- `generate_report.py`：读取 AISC 原始 JSON，生成逐文件 Markdown 报告，并可选调用模型翻译风险描述。
- `scripts/requirements.txt`：Python 依赖。
- `references/ram-policies.md`：RAM 权限要求。
- `references/result-interpretation-guide.md`：风险类型解释。
- `references/verification-method.md`：结果校验方法。
- `check-report.json`：本地输出样例或最近一次扫描结果。

## 运行前提

依赖安装：

```bash
python3 -m pip install -r scripts/requirements.txt
```

认证要求：

- 使用 `alibabacloud_credentials` 默认凭证链。
- 不要在命令行、日志、文档或对话里暴露 AccessKey、STS Token 或密码。

RAM 权限：

- `aisc:CreateSkillFileCheck`
- `aisc:ListSubTasks`

## 常用命令

端到端扫描：

```bash
SKILL_SESSION_ID={session-id} python3 scripts/skill_file_check.py run \
  --files '[{"download_url":"https://example.com/path/to/SKILL.md","file_name":"example-SKILL.md"}]' \
  --output ./check-report.json
```

分步执行：

```bash
SKILL_SESSION_ID={session-id} python3 scripts/skill_file_check.py submit --files '[...]'
SKILL_SESSION_ID={session-id} python3 scripts/skill_file_check.py poll --root-task-id <rootTaskId>
```

说明：

- `file_name` 可选；未提供时脚本会从 URL 路径推断。
- `submit` 成功数为 0 时，不应继续 `poll`。
- 多于 10 个文件时，仍然把完整列表传给脚本，由脚本分批。

## 生成可读报告

是否访问翻译服务由同目录 `.env` 或命令行参数决定；设置为 `none` 时不访问翻译服务：

```bash
python3 generate_report.py ./check-report.json -o ./reports
```

如果输入的是不带 `submit.upload_results` 的纯 `poll` 报告，AISC 返回值可能没有原始文件名。脚本不会猜测或维护固定的 hash 映射；缺少名称时会使用 `skill-task-<task-id>`，并提示补充提交元数据。已知原始文件名时可以按任务顺序补充：

```bash
python3 generate_report.py ./check-report.json -o ./reports \
  --file-names '["first-skill.zip", "second-skill.zip"]'
```

也可以按任务 ID、`file_hash` 或 `target` 传 JSON 对象映射。包含 `submit.upload_results` 的 `run` 报告无需额外参数，脚本会优先使用其中的 `file_name`；纯 `poll` 报告本身没有文件名，无法仅凭 hash 反推出原始名称。

需要翻译英文风险描述时，编辑同目录 `.env` 配置 Provider、模型和 API Key。该文件已加入 `.gitignore`，脚本会自动加载；命令行参数可以覆盖 `.env` 配置。API 密钥不要写入 Python 脚本或报告：

```bash
python3 generate_report.py ./check-report.json -o ./reports
```

最少只需配置三个变量：

```dotenv
MODEL=qwen-plus
API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
API_KEY=在这里填写本地 Key
```

OpenAI 或 Anthropic 也只需要替换这三个值。脚本会根据 API 地址自动识别接口格式：

```dotenv
MODEL=claude-3-5-haiku-latest
API_URL=https://api.anthropic.com/v1/messages
API_KEY=在这里填写本地 Key
```

`.env.example` 提供了 OpenAI、Anthropic 和自定义 API 的模板。

如果使用阿里云 Model Studio 的 OpenAI-compatible 接口，可以这样配置：

```dotenv
AISCC_REPORT_TRANSLATOR=openai
AISCC_REPORT_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AISCC_REPORT_API_KEY_ENV=DASHSCOPE_API_KEY
AISCC_REPORT_MODEL=qwen-plus
DASHSCOPE_API_KEY=在这里填写本地 Key
```

这里的 `AISCC_REPORT_API_URL` 可以填写 Model Studio 的基础 URL，脚本会自动补上 `/chat/completions`；也可以直接填写完整接口地址。

自定义模型 API 默认按 OpenAI-compatible 的 `/chat/completions` 请求和响应格式调用；也可以切换为 Anthropic `messages` 格式，并自定义鉴权 Header：

```dotenv
AISCC_REPORT_TRANSLATOR=custom
AISCC_REPORT_API_URL=https://<your-model-host>/v1/chat/completions
AISCC_REPORT_API_KEY_ENV=MODEL_API_KEY
AISCC_REPORT_MODEL=your-model-name
AISCC_REPORT_API_FORMAT=openai
MODEL_API_KEY=在这里填写本地 Key
```

模型只会收到风险描述，不会收到命中的代码片段或敏感信息检测结果。翻译失败时默认保留原文并继续生成报告；如需失败即终止，可加 `--translation-error fail`。报告中的代码片段默认进行常见凭据脱敏，使用 `--hide-content` 可完全隐藏片段。

## 报告重点字段

- `root_task_id` / `rootTaskId`：根任务 ID。
- `root_task_ids`：多批次时的根任务 ID 列表。
- `success_count` / `fail_count`：提交阶段成功或失败文件数。
- `poll.status`：轮询状态，常见为 `completed` 或 `timeout`。
- `total_tasks`：子任务总数。
- `tasks`：子任务明细及对应风险信息。

## 常见错误

- 凭证缺失或过期：先在默认凭证链修复，再重试。
- 权限不足：补齐 `aisc:CreateSkillFileCheck` 和 `aisc:ListSubTasks`。
- 参数错误：检查 `--files` 是否是 JSON 数组，且每个对象都有 `download_url`。
- 限流：稍后重试，或增加轮询间隔。
- 系统错误：记录 `RequestId`，稍后重试或联系阿里云支持。

## 结果解读

- `risk_info` 为空：AISC 未返回风险发现，不等于绝对安全。
- `Virus`：优先阻断，通常需要删除或替换目标文件。
- `Sensitive`：删除敏感信息，轮换已暴露凭据或 Token，再重新扫描。
- `Guardrail`：通常意味着 prompt injection、执行边界绕过或高风险行为设计。
- `Config`：修复危险配置后再重新检测。

## 参考

- [SKILL.md](./SKILL.md)
- [scripts/skill_file_check.py](./scripts/skill_file_check.py)
- [references/ram-policies.md](./references/ram-policies.md)
- [references/result-interpretation-guide.md](./references/result-interpretation-guide.md)
- [references/verification-method.md](./references/verification-method.md)
