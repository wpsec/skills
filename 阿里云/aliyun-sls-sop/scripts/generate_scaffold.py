#!/usr/bin/env python3
"""根据日志样本生成一套模块文档骨架。"""

from __future__ import annotations

import argparse
import json
import shutil
import textwrap
from pathlib import Path

import profile_csv as profiler


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def yaml_list(items: list[str], indent: int = 2) -> str:
    prefix = " " * indent
    if not items:
        return f'{prefix}- "待补充"'
    return "\n".join(f"{prefix}- {yaml_quote(item)}" for item in items)


def env_display(code: str | None) -> str:
    if not code:
        return "COMMON"
    return profiler.ENV_DISPLAY.get(code, code.upper())


def default_source_alias(spec: dict, environment: str | None) -> str:
    return f"{env_display(environment)}-{spec['source_alias_suffix']}"


def field_desc(field_type: str) -> str:
    mapping = {
        "time": "时间字段，用于时间范围、趋势和事件顺序分析。",
        "ip": "IP 字段，用于来源、目标和访问关系归因。",
        "port": "端口字段，用于服务暴露面、协议行为和访问控制判断。",
        "status": "状态字段，用于判断成功、失败和异常类型。",
        "action": "动作字段，用于识别操作语义和事件结果。",
        "identifier": "标识字段，用于资源、账号、实例或请求归因。",
        "metric": "指标字段，用于体量、性能、影响面和趋势分析。",
        "integer": "数值字段，可用于体量、影响面或计数分析。",
        "number": "数值字段，可用于体量、性能或比例分析。",
        "string": "原始文本字段，需要结合具体业务语义进一步解读。",
    }
    return mapping.get(field_type, "原始字段，需要结合日志语义解读。")


def build_common_fields_block(summary: dict) -> str:
    lines = []
    for field in summary["fields"]:
        lines.append(f"  - name: {yaml_quote(field['name'])}")
        lines.append(f"    desc: {yaml_quote(field_desc(field['inferred_type']))}")
    return "\n".join(lines)


def build_core_fields_reference(summary: dict) -> list[str]:
    groups = summary["categories"]
    lines = []
    for key in (
        "time_fields",
        "ip_fields",
        "port_fields",
        "action_fields",
        "status_fields",
        "identifier_fields",
        "metric_fields",
    ):
        values = groups.get(key) or []
        if values:
            lines.append(" / ".join(values))
    return lines[:8]


def render_readme(module_dir: str, docs: dict[str, str], label: str, prompts: list[str]) -> str:
    return textwrap.dedent(
        f"""\
        # {label}子模块入口

        本目录是审计或分析中心下的 `{module_dir}/` 子模块，用于维护 {label}的数据源配置、分析 SOP 和报告模板；必要时也可结合临时导出的本地样本辅助建模。

        说明：

        - 当前 SOP 骨架是根据样本字段结构生成的通用模板。
        - 当前骨架默认采用可独立迁移的便携命名；如果目标仓库已有固定命名，应以目标仓库为准做重命名。
        - 本地样本只用于识别字段结构、分析维度和查询路径，不作为长期依赖文件。
        - 即使样本文件后续删除，只要线上日志字段结构一致，当前骨架仍然可以继续扩展使用。
        - 当前仓库里的其它日志目录只可作为写法和职责拆分参考，不属于本模块的固定组成部分。

        ## 目录文件

        - `overview.yaml`
          - 面向 AI 和人工分析者的子模块入口。
          - 负责任务识别、读取顺序和执行约束。
        - `{docs['datasource']}`
          - 数据源配置文件。
          - 负责账号、source_alias、运行时解析规则和 `project/logstore` 映射。
        - `{docs['analysis_sop']}`
          - 固定分析 SOP。
          - 负责字段认知、流程、分级响应、输出要求。
        - `{docs['report_template']}`
          - 标准报告模板。
          - 最终结论输出应严格套用该结构。
        - `README.md`
          - 当前说明文件，面向人工维护者阅读。

        ## 推荐阅读顺序

        1. 先读 `overview.yaml`，确认是否是当前日志家族。
        2. 再读 `{docs['datasource']}`，确认环境和数据源映射。
        3. 再读 `{docs['analysis_sop']}`，理解字段和分析流程。
        4. 出正式结论时，套用 `{docs['report_template']}`。

        ## 维护原则

        - 改任务识别、读取顺序、执行约束
          - 只修改 `overview.yaml`
        - 改账号、source_alias、`project/logstore` 和运行时解析规则
          - 只修改 `{docs['datasource']}`
        - 改字段说明、分析剧本、风险评级、输出规范
          - 只修改 `{docs['analysis_sop']}`
        - 改最终报告结构
          - 只修改 `{docs['report_template']}`
        - 原始日志文件
          - 只新增到当前目录
          - 不在原文件上做脱敏、删改、补列等二次加工

        ## 本地样本使用约束

        - 必须使用结构化方式解析 CSV 或 CSV.GZ，不能按普通文本逐行理解。
        - 样本里的热点值只用于字段建模和运行时观察，不自动写入永久规则。
        - 输出报告时默认最小披露，避免把样本里的对象名、设备名、IP 或资源 ID 直接暴露为稳定事实。

        ## 建议提问方式

        """
    ) + "\n".join(f"- `{prompt}`" for prompt in prompts) + "\n"


def render_overview(summary: dict, docs: dict[str, str], spec: dict, datasource_path: str) -> str:
    core_fields = build_core_fields_reference(summary)
    dimensions = yaml_list(spec["dimensions"], indent=2)
    intent_blocks = [
        "\n".join(
            [
                f"  - user_says: {yaml_quote(prompt)}",
                "    mapped_action:",
                f"      - 读取 `{docs['datasource']}`",
                "      - 识别目标环境、主线索和时间范围",
                f"      - 读取 `{docs['analysis_sop']}`",
                f"      - 按 `{docs['report_template']}` 输出结果",
            ]
        )
        for prompt in spec["prompts"]
    ]
    intents_yaml = "\n".join(intent_blocks)
    core_fields_yaml = yaml_list(core_fields, indent=2)
    return (
        f"module: {spec['module_id']}\n"
        f"description: {yaml_quote(spec['label'] + '分析入口，基于 SLS project/logstore 数据源支持业务、运维、安全三个方向的排查和报告输出。')}\n\n"
        "quick_links:\n"
        "  readme: ./README.md\n"
        f"  datasource_config: ./{docs['datasource']}\n"
        f"  analysis_sop: ./{docs['analysis_sop']}\n"
        f"  report_template: ./{docs['report_template']}\n\n"
        "task_routing_rules:\n"
        f"  - condition: {yaml_quote('用户提到当前日志类型、SLS 导出样本、最近事件、异常排查或目录结构对齐')}\n"
        "    action:\n"
        f"      - 先读取 `{docs['datasource']}`\n"
        "      - 识别环境、source_alias、主线索和时间范围\n"
        f"      - 读取 `{docs['analysis_sop']}`\n"
        f"      - 按 `{docs['report_template']}` 输出结果\n\n"
        f"  - condition: {yaml_quote('用户显式提供本地 CSV 或 CSV.GZ 样本')}\n"
        "    action:\n"
        "      - 可将该文件作为辅助样本做字段和热点模式分析\n"
        f"      - 但正式数据源解析仍以 `{docs['datasource']}` 为准\n\n"
        "supported_intents:\n"
        f"{intents_yaml}\n\n"
        "important_notes:\n"
        f"  - {yaml_quote('主数据源应以 datasource 配置文件中的 project/logstore 为唯一事实源。')}\n"
        f"  - {yaml_quote('本地样本只用于字段建模和运行时观察，不作为正式配置依赖。')}\n"
        f"  - {yaml_quote('样本中的热点对象、设备名、IP、资源 ID 和文件名默认都属于动态事实。')}\n"
        f"  - {yaml_quote('若字段不足以支撑某个分析方向，应在结论中明确写出限制。')}\n\n"
        "core_fields_reference:\n"
        f"{core_fields_yaml}\n\n"
        "analysis_dimensions:\n"
        f"{dimensions}\n"
    )


def render_datasource(
    summary: dict,
    docs: dict[str, str],
    spec: dict,
    environment: str | None,
    source_alias: str,
    project: str,
    logstore: str,
    account_alias: str,
    aliuid: str,
    owner: str,
) -> str:
    label = spec["label"]
    env_name = env_display(environment)
    env_code = environment or "common"
    config_name = f"{env_name} {label}数据源配置"
    display_name = f"{env_name} {label}"
    datasource_name = docs["datasource"]
    analysis_name = docs["analysis_sop"]
    report_name = docs["report_template"]
    query_hints_yaml = yaml_list([field["name"] for field in summary["fields"]], indent=12)
    return (
        "# ==============================================================================\n"
        f"# {label}数据源配置文件\n"
        "# ==============================================================================\n\n"
        "metadata:\n"
        f"  name: {yaml_quote(config_name)}\n"
        '  version: "1.0"\n'
        '  last_updated: "<待填写>"\n'
        f"  owner: {yaml_quote(owner)}\n\n"
        "purpose: >\n"
        f"  为 {label}分析提供环境相关的数据源注册信息、运行时解析规则和 SLS project/logstore 路由规则。\n"
        f"  overview.yaml 只做导航，{docs['analysis_sop']} 只放固定分析规则，本文件是唯一配置事实源。\n\n"
        "editing_rules:\n"
        "  - 新增或修改账号、source_alias、region、project、logstore、topic 时，只修改本文件。\n"
        "  - 样本中的热点值、资源 ID、对象名和 IP 只作为运行时观察，不直接固化为长期配置。\n"
        "  - 若后续需要新增稳定别名或运行时解析规则，应优先修改本文件。\n\n"
        "datasource_registry:\n"
        "  defaults:\n"
        "    require_unique_match: true\n"
        "    fallback_to_user_confirmation_when_ambiguous: true\n"
        "    default_time_range_expand_minutes: 15\n"
        "    prefer_default_source: true\n\n"
        "  accounts:\n"
        f"    - account_alias: {yaml_quote(account_alias)}\n"
        f"      display_name: {yaml_quote(account_alias)}\n"
        f"      aliuid: {yaml_quote(aliuid)}\n"
        "      sls_sources:\n"
        f"        - source_alias: {yaml_quote(source_alias)}\n"
        f"          display_name: {yaml_quote(display_name)}\n"
        '          region: "<待填写>"\n'
        '          region_code: "<待填写>"\n'
        '          source_type: "sls_logstore"\n'
        f"          project: {yaml_quote(project)}\n"
        f"          logstore: {yaml_quote(logstore)}\n"
        '          topic: "<待填写>"\n'
        "          is_default: true\n"
        f"          log_type: {yaml_quote(spec['module_id'])}\n"
        "          query_hints:\n"
        f"{query_hints_yaml}\n\n"
        "runtime_resolution:\n"
        f"  environment_code: {yaml_quote(env_code)}\n"
        "  rules:\n"
        "    - 优先使用用户显式给出的环境、资源对象和主线索。\n"
        "    - 若样本路径、目录名或 datasource 命名能推断环境，可作为辅助，不覆盖用户输入。\n"
        "    - 若一次命中多个候选对象，应先聚合再收敛，不要盲判。\n\n"
        "usage_notes:\n"
        f"  - {yaml_quote(f'当前骨架默认按 {datasource_name} 维护环境映射和运行时解析规则。')}\n"
        f"  - {yaml_quote('project、logstore、账号和 source_alias 需要在接入真实环境时补齐或确认。')}\n"
        f"  - {yaml_quote('若用户显式提供本地样本，可将其作为辅助，但不能替代本文件中的正式配置。')}\n\n"
        "conversation_shortcuts:\n"
        f"  - user_says: {yaml_quote(f'分析 {env_name} {label} 最近的事件')}\n"
        "    resolved_actions:\n"
        f"      - {yaml_quote(f'读取 {datasource_name}，确认环境和数据源映射。')}\n"
        f"      - {yaml_quote(f'读取 {analysis_name}，按标准流程完成分析。')}\n"
        f"      - {yaml_quote(f'按 {report_name} 输出报告。')}\n"
        f"  - user_says: {yaml_quote(f'继续补齐 {label} 的 SOP')}\n"
        "    resolved_actions:\n"
        f"      - {yaml_quote('保持导航、配置、SOP、模板职责分离。')}\n"
        f"      - {yaml_quote('仅把样本作为字段结构参考，不把热点值写成永久规则。')}\n"
    )


def render_analysis_sop(summary: dict, docs: dict[str, str], spec: dict, owner: str) -> str:
    common_fields = build_common_fields_block(summary)
    scope_applies = yaml_list(spec["dimensions"], indent=4)
    analysis_dimensions = yaml_list(spec["dimensions"], indent=2)
    label = spec["label"]
    report_name = docs["report_template"]
    return (
        "# ==============================================================================\n"
        f"# {label}通用分析 SOP (Standard Operating Procedure)\n"
        "# ==============================================================================\n\n"
        "metadata:\n"
        f"  name: {yaml_quote('通用' + label + '分析 SOP')}\n"
        '  version: "1.0"\n'
        '  last_updated: "<待填写>"\n'
        f"  owner: {yaml_quote(owner)}\n\n"
        "scope:\n"
        "  description: |\n"
        f"    本 SOP 用于标准化分析 {label}。\n"
        "    当前骨架根据样本字段结构自动生成，目标是先建立可复用的分析框架，再按真实环境补齐细节。\n"
        "    样本文件只用于识别字段结构、分析维度和典型问题，不作为长期依赖文件。\n"
        "  applies_to:\n"
        f"{scope_applies}\n"
        "  outputs:\n"
        f"    - {yaml_quote('问题分类结果')}\n"
        f"    - {yaml_quote('异常对象与时间范围')}\n"
        f"    - {yaml_quote('根因结论与处置建议')}\n"
        f"    - {yaml_quote('标准化 Markdown 分析报告')}\n\n"
        "objectives:\n"
        f"  - {yaml_quote(f'建立 {label}的统一分析口径。')}\n"
        f"  - {yaml_quote('区分稳定事实与动态事实，避免把样本热点值写成永久规则。')}\n"
        f"  - {yaml_quote('形成可复用、可扩展、可追踪的 SOP 骨架。')}\n\n"
        "required_inputs:\n"
        f"  - name: {yaml_quote('raw_logs')}\n"
        "    required: true\n"
        f"    desc: {yaml_quote('来自 SLS project/logstore 或同结构导出样本的日志结果。')}\n"
        f"  - name: {yaml_quote('time_window')}\n"
        "    required: false\n"
        f"    desc: {yaml_quote('已知异常发生时间；若未提供，先从时间字段建立分析窗口。')}\n"
        f"  - name: {yaml_quote('primary_clue')}\n"
        "    required: false\n"
        f"    desc: {yaml_quote('用户给出的主线索，如对象、来源、资源 ID、端口、状态、错误码等。')}\n\n"
        "common_fields:\n"
        f"{common_fields}\n\n"
        "analysis_principles:\n"
        f"  - {yaml_quote('先建立字段模型，再决定查询、流程和结论。')}\n"
        f"  - {yaml_quote('先区分稳定事实和动态事实，再决定哪些内容可以写入永久文档。')}\n"
        f"  - {yaml_quote('同时考虑业务、运维、安全三个方向，根据字段支持度确定主次。')}\n"
        f"  - {yaml_quote('样本中的热点值、IP、对象名、资源 ID 和文件名默认都属于运行时事实。')}\n"
        f"  - {yaml_quote('只有字段存在时，才生成依赖该字段的查询或判断。')}\n\n"
        "trigger_conditions:\n"
        f"  - {yaml_quote('用户要求分析最近事件、异常排查、生成 SOP，或补齐模块文档套件。')}\n"
        f"  - {yaml_quote('监控、审计或告警发现异常，需要统一的分析和响应流程。')}\n"
        f"  - {yaml_quote('需要把一次性排查经验沉淀成可复用的标准文档。')}\n\n"
        "analysis_dimensions:\n"
        f"{analysis_dimensions}\n\n"
        "workflow:\n"
        f"  - step: {yaml_quote('0. 锁定分析对象与时间范围')}\n"
        f"    goal: {yaml_quote('识别环境、主线索、目标对象和时间窗口。')}\n"
        "    checks:\n"
        f"      - {yaml_quote('明确 source_alias、project、logstore 和目标对象。')}\n"
        f"      - {yaml_quote('若用户未给时间范围，先根据时间字段建立分析窗口。')}\n"
        f"  - step: {yaml_quote('1. 做宏观分布')}\n"
        f"    goal: {yaml_quote('从整体上识别热点字段、异常方向和主问题类型。')}\n"
        "    checks:\n"
        f"      - {yaml_quote('统计动作、状态、来源、目标、资源和体量字段的整体分布。')}\n"
        f"      - {yaml_quote('判断当前更偏业务、运维还是安全。')}\n"
        f"  - step: {yaml_quote('2. 锁定异常信号')}\n"
        f"    goal: {yaml_quote('从结果、热点值和关键对象中收敛异常。')}\n"
        "    checks:\n"
        f"      - {yaml_quote('关注失败、拒绝、异常来源、高频对象和异常热点。')}\n"
        f"      - {yaml_quote('对比是否符合正常基线或已知白名单。')}\n"
        f"  - step: {yaml_quote('3. 做根因排查')}\n"
        f"    goal: {yaml_quote('把异常映射到资源、调用链或策略层。')}\n"
        "    checks:\n"
        f"      - {yaml_quote('结合资源标识、状态、动作和上下文做归因。')}\n"
        f"      - {yaml_quote('区分配置问题、业务异常、运维抖动和安全风险。')}\n"
        f"  - step: {yaml_quote('4. 做分级响应')}\n"
        f"    goal: {yaml_quote('按影响面和风险等级确定响应动作。')}\n"
        "    checks:\n"
        f"      - {yaml_quote('明确通知对象、升级路径和处置时限。')}\n"
        f"      - {yaml_quote('记录证据和已执行动作。')}\n"
        f"  - step: {yaml_quote('5. 输出结论与闭环项')}\n"
        f"    goal: {yaml_quote('形成结构化报告，并沉淀规则优化项。')}\n"
        "    checks:\n"
        f"      - {yaml_quote('明确异常是否成立、影响范围和根因状态。')}\n"
        f"      - {yaml_quote('给出立即动作、后续核查和规则沉淀建议。')}\n"
        f"      - {yaml_quote(f'严格按 {report_name} 输出结果。')}\n\n"
        "judgement_rules:\n"
        f"  - condition: {yaml_quote('出现明显失败、拒绝、异常状态或高频热点值。')}\n"
        f"    standard: {yaml_quote('判定为候选异常，进入根因排查。')}\n"
        f"  - condition: {yaml_quote('异常对象能和资源、身份、策略或业务动作形成稳定关联。')}\n"
        f"    standard: {yaml_quote('可输出高置信度归因结论，并进入分级响应。')}\n"
        f"  - condition: {yaml_quote('字段不足或证据冲突。')}\n"
        f"    standard: {yaml_quote('只能给出待确认结论，并补充需要的字段或数据源。')}\n\n"
        "escalation_path:\n"
        f"  - level: {yaml_quote('高危')}\n"
        f"    trigger: {yaml_quote('存在明确未授权访问、敏感对象暴露、或高影响异常。')}\n"
        f"    notify: {yaml_quote('立即通知安全、运维和相关业务负责人。')}\n"
        f"    expectation: {yaml_quote('默认 15 分钟内响应，1 小时内给出初步处置结论。')}\n"
        f"  - level: {yaml_quote('中危')}\n"
        f"    trigger: {yaml_quote('异常持续扩大、影响多个对象，或存在明显业务/运维风险。')}\n"
        f"    notify: {yaml_quote('通知值班人员和模块负责人，必要时拉群协同排查。')}\n"
        f"    expectation: {yaml_quote('默认 30 分钟内响应，4 小时内给出阶段性结论。')}\n"
        f"  - level: {yaml_quote('低危')}\n"
        f"    trigger: {yaml_quote('轻微异常、单点波动或待确认问题。')}\n"
        f"    notify: {yaml_quote('记录到巡检或工单体系，纳入后续跟踪。')}\n"
        f"    expectation: {yaml_quote('默认一个工作日内完成核查和记录。')}\n\n"
        "record_requirements:\n"
        f"  - {yaml_quote('必须记录分析时间范围、source_alias、project、logstore 和主线索。')}\n"
        f"  - {yaml_quote('必须记录关键证据、判断依据、升级动作和处置结果。')}\n"
        f"  - {yaml_quote('必须区分已证实结论、推测结论和待确认项。')}\n"
        f"  - {yaml_quote('若引用样本热点值，必须明确标注为运行时观察，不得误写成长期规则。')}\n\n"
        "report_writing_rules:\n"
        f"  - {yaml_quote('必须明确问题类型、时间范围、关键对象和关键证据。')}\n"
        f"  - {yaml_quote('必须明确哪些结论已证实、哪些仍待确认。')}\n"
        f"  - {yaml_quote('若字段不足以支撑某个判断，必须在报告中显式说明。')}\n"
        f"  - {yaml_quote('必须包含根本原因分析数据流图，串联触发事实、主事实源、候选根因、补证、定性和处置闭环。')}\n\n"
        f"report_template_file: {yaml_quote(docs['report_template'])}\n"
    )


def render_report_template(spec: dict) -> str:
    return textwrap.dedent(
        f"""\
        # {spec['label']}分析报告

        > 分析时间范围:
        > 源文件:
        > 主线索:

        ## 1. 事件对象概要

        | 字段 | 内容 |
        | --- | --- |
        | 问题类型 | <安全 / 运维 / 业务 / 治理 / 混合> |
        | 分析原因/对象 | <填写> |
        | 主线索 | <填写> |
        | 初判级别 | <填写> |

        ## 2. 宏观总览

        | 维度 | 结果 | 说明 |
        | --- | --- | --- |
        | 时间范围 | <填写> | <填写> |
        | 主要对象 | <填写> | <填写> |
        | 主要动作 / 状态 | <填写> | <填写> |
        | 主要来源 / 目标 | <填写> | <填写> |
        | 主要体量 / 指标 | <填写> | <填写> |

        ## 3. 根本原因分析数据流图

        ```mermaid
        flowchart LR
          trigger["触发事实 / 告警 / 样本线索"] --> source["主事实源"]
          source --> symptom["症状确认"]
          symptom --> cause_a["候选根因 A"]
          symptom --> cause_b["候选根因 B"]
          symptom --> cause_c["候选根因 C"]
          cause_a --> evidence["补证：字段聚合 / 时间线 / 关联对象"]
          cause_b --> evidence
          cause_c --> evidence
          evidence --> conclusion["根本原因定性与影响评估"]
          conclusion --> closure["处置闭环 / 规则沉淀"]
        ```

        ## 4. 关键发现

        ### 4.1 异常对象 / 可疑行为

        | 时间 | 对象 | 动作/状态 | 关键字段 | 说明 |
        | --- | --- | --- | --- | --- |
        | <填写> | <填写> | <填写> | <填写> | <填写> |

        ### 4.2 根因排查

        - 关键证据：<填写>
        - 归因判断：<填写>
        - 根因状态：<已证实 / 高概率 / 待确认>

        ### 4.3 影响面

        - 影响范围：<填写>
        - 业务影响：<填写>
        - 运维影响：<填写>
        - 安全影响：<填写>

        ## 5. 研判与评估

        - **问题归类**：<填写>
        - **风险等级**：< Critical / High / Medium / Low / Safe >
        - **影响等级**：< Critical / High / Medium / Low / Safe >
        - **核心结论**：<填写>

        ## 6. 处置建议

        - **立即动作**：<填写>
        - **后续核查**：<填写>
        - **规则沉淀**：<填写>
        """
    )


def write_text(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"文件已存在，且未指定 --force: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="根据日志样本生成一套模块文档骨架。")
    parser.add_argument("csv_path", help="CSV 或 CSV.GZ 文件路径")
    parser.add_argument("--out-dir", required=True, help="输出根目录，脚本会在其下创建模块目录")
    parser.add_argument("--module-name", help="手工指定模块目录名，默认按日志家族推断")
    parser.add_argument(
        "--family",
        choices=sorted(profiler.FAMILY_SPECS.keys()),
        help="手工指定日志家族，覆盖自动识别",
    )
    parser.add_argument("--environment", help="手工指定环境，如 uat/prod/sit/pre/test/dev")
    parser.add_argument(
        "--naming-style",
        choices=sorted(profiler.NAMING_STYLE_LABELS.keys()),
        default="portable",
        help="骨架命名策略，默认使用可独立迁移的便携命名",
    )
    parser.add_argument("--source-alias", help="手工指定 source_alias")
    parser.add_argument("--project", default="<待填写>", help="SLS project，默认占位符")
    parser.add_argument("--logstore", default="<待填写>", help="SLS logstore，默认占位符")
    parser.add_argument("--account-alias", default="待确认账号", help="账号别名")
    parser.add_argument("--aliuid", default="<待填写>", help="阿里云账号 aliuid")
    parser.add_argument("--owner", default="安全运营 / 日志审计", help="文档 owner")
    parser.add_argument("--force", action="store_true", help="覆盖已存在文件")
    parser.add_argument("--dry-run", action="store_true", help="只输出计划，不落文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv_path)
    if not csv_path.is_file():
        print(f"样本文件不存在: {csv_path}")
        return 1

    summary = profiler.profile_csv_file(
        csv_path,
        family_override=args.family,
        environment_override=args.environment,
        naming_style=args.naming_style,
    )
    spec = profiler.FAMILY_SPECS[summary["family_key"]]
    environment = summary["environment_hint"]["code"] or profiler.normalize_environment(args.environment) or "common"
    docs = profiler.build_recommended_doc_set(
        summary["family_key"],
        environment,
        naming_style=args.naming_style,
    )
    module_name = args.module_name or docs["module_dir"]
    module_dir = Path(args.out_dir) / module_name
    source_alias = args.source_alias or default_source_alias(spec, environment)

    plan = {
        "family_key": summary["family_key"],
        "label": spec["label"],
        "environment": environment,
        "naming_style": args.naming_style,
        "module_dir": str(module_dir),
        "files": docs,
    }
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if module_dir.exists() and args.force:
        shutil.rmtree(module_dir)

    readme = render_readme(module_name, docs, spec["label"], spec["prompts"])
    overview = render_overview(summary, docs, spec, docs["datasource"])
    datasource = render_datasource(
        summary,
        docs,
        spec,
        environment,
        source_alias,
        args.project,
        args.logstore,
        args.account_alias,
        args.aliuid,
        args.owner,
    )
    analysis_sop = render_analysis_sop(summary, docs, spec, args.owner)
    report_template = render_report_template(spec)

    write_text(module_dir / "README.md", readme, args.force)
    write_text(module_dir / "overview.yaml", overview, args.force)
    write_text(module_dir / docs["datasource"], datasource, args.force)
    write_text(module_dir / docs["analysis_sop"], analysis_sop, args.force)
    write_text(module_dir / docs["report_template"], report_template, args.force)

    print(f"已生成模块骨架: {module_dir}")
    for file_name in ("README.md", "overview.yaml", docs["datasource"], docs["analysis_sop"], docs["report_template"]):
        print(f"- {module_dir / file_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
