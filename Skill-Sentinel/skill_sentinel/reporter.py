# skill_sentinel/reporter.py
# 结果输出 — JSON 和终端格式

import json
import os
import sys
from typing import Dict, Optional


def format_result_json(scan_result: dict, indent: int = 2) -> str:
    """将扫描结果格式化为 JSON 字符串。

    适合写入文件或通过 API 返回。
    """
    return json.dumps(scan_result, ensure_ascii=False, indent=indent, default=str)


def format_result_terminal(scan_result: dict) -> str:
    """将扫描结果格式化为终端友好的彩色文本。

    使用 ANSI 颜色码输出风险等级。
    """
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    risk_level = scan_result.get("risk_level", "unknown")
    if risk_level == "block":
        level_color = RED
        level_icon = "🚫"
    elif risk_level == "review":
        level_color = YELLOW
        level_icon = "⚠️"
    else:
        level_color = GREEN
        level_icon = "✅"

    lines = []
    lines.append(f"{BOLD}{'='*60}{RESET}")
    lines.append(f"{BOLD}SkillSentinel 扫描报告{RESET}")
    lines.append(f"{BOLD}{'='*60}{RESET}")
    lines.append(f"")
    lines.append(f"Skill: {scan_result.get('skill_name', 'unknown')}")
    lines.append(f"路径: {scan_result.get('skill_path', 'unknown')}")
    lines.append(f"扫描时间: {scan_result.get('scan_time', 'unknown')}")
    lines.append(f"")
    lines.append(f"风险等级: {level_color}{BOLD}{level_icon} {risk_level.upper()}{RESET}")
    lines.append(f"风险评分: {scan_result.get('risk_score', 0)}")
    lines.append(f"")

    # 摘要
    summary = scan_result.get("summary", {})
    lines.append(f"{BOLD}--- 扫描摘要 ---{RESET}")
    lines.append(f"总文件数: {summary.get('total_files', 0)}")
    lines.append(f"已扫描: {summary.get('scanned_files', 0)}")
    lines.append(f"命中数: {summary.get('total_findings', 0)}")
    lines.append(f"")

    # 严重程度分布
    sev_counts = summary.get("severity_counts", {})
    if sev_counts:
        lines.append(f"{BOLD}--- 严重程度分布 ---{RESET}")
        parts = []
        for sev, count in sev_counts.items():
            if count > 0:
                if sev == "critical":
                    parts.append(f"{RED}严重:{count}{RESET}")
                elif sev == "high":
                    parts.append(f"{RED}高:{count}{RESET}")
                elif sev == "medium":
                    parts.append(f"{YELLOW}中:{count}{RESET}")
                else:
                    parts.append(f"低:{count}")
        lines.append(" | ".join(parts))
        lines.append(f"")

    # 风险分类分布
    cat_counts = summary.get("categories", {})
    if cat_counts:
        from skill_sentinel.rules import RISK_CATEGORIES
        lines.append(f"{BOLD}--- 风险分类分布 ---{RESET}")
        for cat_id, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            cat_name = RISK_CATEGORIES.get(cat_id, f"未知({cat_id})")
            lines.append(f"  {cat_id}. {cat_name}: {count} 次命中")
        lines.append(f"")

    # 资产图摘要
    graph = scan_result.get("asset_graph_summary", {})
    if graph:
        lines.append(f"{BOLD}--- 资产图 ---{RESET}")
        lines.append(f"入口文件: {graph.get('entry_file', '')}")
        lines.append(f"脚本: {graph.get('scripts_count', 0)}")
        lines.append(f"配置: {graph.get('configs_count', 0)}")
        lines.append(f"压缩包: {graph.get('archives_count', 0)}")
        lines.append(f"间接依赖: {graph.get('indirect_deps_count', 0)}")
        lines.append(f"")

    # 证据详情
    evidence = scan_result.get("evidence", [])
    if evidence:
        lines.append(f"{BOLD}--- 命中证据 (前 20 条) ---{RESET}")
        for i, ev in enumerate(evidence[:20]):
            if ev["severity"] == "critical":
                prefix = f"{RED}■{RESET}"
            elif ev["severity"] == "high":
                prefix = f"{RED}▲{RESET}"
            elif ev["severity"] == "medium":
                prefix = f"{YELLOW}●{RESET}"
            else:
                prefix = "○"
            lines.append(f"  {prefix} [{ev['category']}] {ev['rule']}")
            lines.append(f"    文件: {ev['file']}:{ev['line']}")
            lines.append(f"    建议: {ev['suggestion']}")
            lines.append(f"")

        if len(evidence) > 20:
            lines.append(f"  ... 还有 {len(evidence) - 20} 条命中，使用 --json 查看完整输出")
            lines.append(f"")

    # 决策建议
    lines.append(f"{BOLD}{'='*60}{RESET}")
    if risk_level == "block":
        lines.append(f"{RED}{BOLD}决策: 建议 BLOCK — 该 Skill 存在高危风险，不建议启用{RESET}")
    elif risk_level == "review":
        lines.append(f"{YELLOW}{BOLD}决策: 建议 REVIEW — 该 Skill 需要人工审查后决定是否启用{RESET}")
    else:
        lines.append(f"{GREEN}{BOLD}决策: ALLOW — 该 Skill 风险较低，可以启用{RESET}")
    lines.append(f"{BOLD}{'='*60}{RESET}")

    return "\n".join(lines)


def export_report(scan_result: dict, output_path: str, format: str = "json") -> str:
    """导出扫描报告到文件。

    Args:
        scan_result: 扫描结果字典
        output_path: 输出文件路径
        format: 输出格式 ("json" 或 "terminal")

    Returns:
        输出文件的绝对路径
    """
    if format == "terminal":
        content = format_result_terminal(scan_result)
    else:
        content = format_result_json(scan_result)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return os.path.abspath(output_path)