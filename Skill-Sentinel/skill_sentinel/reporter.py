# skill_sentinel/reporter.py
# 结果输出 — JSON 和终端格式

import json
import os


def format_result_json(scan_result: dict, indent: int = 2) -> str:
    """将扫描结果格式化为 JSON 字符串。"""
    return json.dumps(scan_result, ensure_ascii=False, indent=indent, default=str)


def format_result_terminal(scan_result: dict) -> str:
    """将扫描结果格式化为终端友好的文本。"""
    red = "\033[91m"
    yellow = "\033[93m"
    green = "\033[92m"
    bold = "\033[1m"
    reset = "\033[0m"

    risk_level = scan_result.get("risk_level", "unknown")
    if risk_level == "block":
        level_color = red
        level_label = "BLOCK"
    elif risk_level == "review":
        level_color = yellow
        level_label = "REVIEW"
    else:
        level_color = green
        level_label = "ALLOW"

    lines = [
        f"{bold}{'=' * 68}{reset}",
        f"{bold}SkillSentinel 扫描报告{reset}",
        f"{bold}{'=' * 68}{reset}",
        "",
        f"Skill: {scan_result.get('skill_name', 'unknown')}",
        f"路径: {scan_result.get('skill_path', 'unknown')}",
        f"扫描时间: {scan_result.get('scan_time', 'unknown')}",
        f"风险等级: {level_color}{bold}{level_label}{reset}",
        f"风险评分: {scan_result.get('risk_score', 0)}",
        "",
    ]

    summary = scan_result.get("summary", {})
    lines.extend([
        f"{bold}--- 扫描摘要 ---{reset}",
        f"发现文件: {summary.get('discovered_files', summary.get('total_files', 0))}",
        f"已扫描目标: {summary.get('scanned_targets', summary.get('scanned_files', 0))}",
        f"跳过目标: {summary.get('skipped_targets', 0)}",
        f"异常目标: {summary.get('errored_targets', 0)}",
        f"结构化发现: {summary.get('total_findings', 0)}",
        f"原始命中: {summary.get('raw_findings_count', 0)}",
        "",
    ])

    severity_counts = summary.get("severity_counts", {})
    if severity_counts:
        lines.append(f"{bold}--- 严重程度分布 ---{reset}")
        lines.append(_format_counts(severity_counts))
        lines.append("")

    confidence_counts = summary.get("confidence_counts", {})
    if confidence_counts:
        lines.append(f"{bold}--- 置信度分布 ---{reset}")
        lines.append(_format_counts(confidence_counts))
        lines.append("")

    impact_scope_counts = summary.get("impact_scope_counts", {})
    if impact_scope_counts:
        lines.append(f"{bold}--- 影响范围分布 ---{reset}")
        lines.append(_format_counts(impact_scope_counts))
        lines.append("")

    graph = scan_result.get("asset_graph_summary", {})
    if graph:
        lines.extend([
            f"{bold}--- 资产图摘要 ---{reset}",
            f"入口文件: {graph.get('entry_file', '')}",
            f"节点数: {graph.get('nodes_count', 0)} | 边数: {graph.get('edges_count', 0)}",
            f"脚本: {graph.get('scripts_count', 0)} | 配置: {graph.get('configs_count', 0)} | 压缩包: {graph.get('archives_count', 0)}",
            f"间接依赖: {graph.get('indirect_deps_count', 0)}",
            "",
        ])

    evidence = scan_result.get("evidence", [])
    if evidence:
        lines.append(f"{bold}--- 结构化证据 (前 15 条) ---{reset}")
        for item in evidence[:15]:
            severity = item.get("severity", "medium")
            marker = _severity_marker(severity, red, yellow, reset)
            lines.append(
                f"  {marker} [{item.get('category', '未知')}] {item.get('rule', '')} "
                f"(confidence={item.get('confidence', 'medium')}, scope={item.get('impact_scope', 'single_file')})"
            )
            lines.append(f"    文件: {item.get('file', 'unknown')}:{item.get('line', 0)}")
            if item.get("related_files"):
                lines.append(f"    关联文件: {', '.join(item['related_files'][:4])}")
            if item.get("chain"):
                lines.append(f"    链路: {_format_chain(item['chain'])}")
            lines.append(f"    原因: {item.get('reason', '')}")
            lines.append(f"    建议: {item.get('suggestion', '')}")
            lines.append("")

        if len(evidence) > 15:
            lines.append(f"  ... 还有 {len(evidence) - 15} 条结构化证据，使用 --json 查看完整输出")
            lines.append("")

    decision_factors = scan_result.get("decision_factors", {})
    if decision_factors.get("top_contributors"):
        lines.append(f"{bold}--- 评分贡献 Top 5 ---{reset}")
        for item in decision_factors["top_contributors"][:5]:
            lines.append(
                f"  {item['score']:.2f} | {item['severity']} | {item['confidence']} | "
                f"{item['impact_scope']} | {item['file']}:{item['line']}"
            )
        lines.append("")

    lines.append(f"{bold}{'=' * 68}{reset}")
    if risk_level == "block":
        lines.append(f"{red}{bold}决策: 建议 BLOCK，存在高风险链路，不建议启用{reset}")
    elif risk_level == "review":
        lines.append(f"{yellow}{bold}决策: 建议 REVIEW，需要人工确认关键链路后再决定{reset}")
    else:
        lines.append(f"{green}{bold}决策: ALLOW，未发现足以阻断启用的高置信度风险{reset}")
    lines.append(f"{bold}{'=' * 68}{reset}")
    return "\n".join(lines)


def _format_counts(counts: dict) -> str:
    """格式化计数字典。"""
    parts = []
    for key, value in counts.items():
        if value:
            parts.append(f"{key}:{value}")
    return " | ".join(parts) if parts else "-"


def _severity_marker(severity: str, red: str, yellow: str, reset: str) -> str:
    """按严重程度生成文本标记。"""
    if severity == "critical":
        return f"{red}CRIT{reset}"
    if severity == "high":
        return f"{red}HIGH{reset}"
    if severity == "medium":
        return f"{yellow}MED{reset}"
    return "LOW"


def _format_chain(chain: list) -> str:
    """压缩链路显示。"""
    formatted = []
    for step in chain[:5]:
        step_type = step.get("type", "step")
        detail = step.get("detail", "")
        line = step.get("line")
        suffix = f"@{line}" if line else ""
        if detail:
            formatted.append(f"{step_type}:{detail}{suffix}")
        else:
            formatted.append(f"{step_type}:{step.get('path', '')}{suffix}")
    return " -> ".join(formatted)


def export_report(scan_result: dict, output_path: str, format: str = "json") -> str:
    """导出扫描报告到文件。"""
    if format == "terminal":
        content = format_result_terminal(scan_result)
    else:
        content = format_result_json(scan_result)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return os.path.abspath(output_path)
