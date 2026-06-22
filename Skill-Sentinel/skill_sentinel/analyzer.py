# skill_sentinel/analyzer.py
# 风险分析与评分

from typing import Dict, List, Optional
from datetime import datetime

from skill_sentinel.rules import Rule, RISK_CATEGORIES, SEVERITY_LEVELS
from skill_sentinel.scanner import scan_skill_assets


def analyze_skill(asset_graph: dict, rules: Dict[str, Rule]) -> dict:
    """对 Skill 执行完整的安全分析。

    综合扫描结果、资产图结构，输出风险等级和证据。

    Returns:
        {
            "skill_name": str,
            "skill_path": str,
            "scan_time": str,
            "risk_level": "allow" | "review" | "block",
            "risk_score": int,
            "summary": {
                "total_files": int,
                "scanned_files": int,
                "total_findings": int,
                "categories": {category_id: count},
                "severity_counts": {severity: count},
            },
            "findings": [...],
            "evidence": [...],
            "asset_graph_summary": {
                "entry_file": str,
                "scripts_count": int,
                "configs_count": int,
                "archives_count": int,
                "indirect_deps_count": int,
            },
        }
    """
    # 扫描所有资产
    scan_results = scan_skill_assets(asset_graph, rules)

    # 汇总命中
    all_findings = []
    for result in scan_results:
        for finding in result.get("findings", []):
            finding["file_path"] = result["path"]
            all_findings.append(finding)

    # 统计分类
    category_counts = {}
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in all_findings:
        cat_id = f.get("rule_category", 8)
        category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
        sev = f.get("rule_severity", "medium")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # 计算风险等级
    risk_level, risk_score = _calculate_risk_level(all_findings)

    # 生成证据
    evidence = _generate_evidence(all_findings, risk_level)

    # 计算扫描文件数
    scanned_files = len([r for r in scan_results if not r.get("error")])
    total_files = (
        len(asset_graph.get("scripts", []))
        + len(asset_graph.get("configs", []))
        + len(asset_graph.get("docs", []))
        + len(asset_graph.get("templates", []))
        + len(asset_graph.get("other", []))
        + 1  # entry file
    )

    return {
        "skill_name": asset_graph.get("metadata", {}).get("name", "unknown"),
        "skill_path": asset_graph.get("skill_root", ""),
        "scan_time": datetime.now().isoformat(),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "summary": {
            "total_files": total_files,
            "scanned_files": scanned_files,
            "total_findings": len(all_findings),
            "categories": category_counts,
            "severity_counts": severity_counts,
        },
        "findings": _simplify_findings(all_findings),
        "evidence": evidence,
        "asset_graph_summary": {
            "entry_file": asset_graph.get("entry_file", ""),
            "scripts_count": len(asset_graph.get("scripts", [])),
            "configs_count": len(asset_graph.get("configs", [])),
            "archives_count": len(asset_graph.get("archives", [])),
            "indirect_deps_count": len(asset_graph.get("indirect_deps", [])),
        },
    }


def _calculate_risk_level(findings: List[dict]) -> tuple:
    """综合评估风险等级。

    评分规则:
    - critical 命中: 每个 +25 分
    - high 命中: 每个 +10 分
    - medium 命中: 每个 +3 分
    - low 命中: 每个 +1 分

    文档文件（.md/.txt）中的命中权重减半，因为审计/安全工具的文档
    包含攻击示例是合法的。

    等级阈值:
    - 0-5 分: allow (低风险)
    - 6-25 分: review (中风险，需人工确认)
    - 26+ 分: block (高风险，禁止自动启用)
    """
    score = 0
    for f in findings:
        file_path = f.get("file_path", "")
        weight = 0.5 if _is_doc_file(file_path) else 1.0
        sev = f.get("rule_severity", "medium")
        if sev == "critical":
            score += 25 * weight
        elif sev == "high":
            score += 10 * weight
        elif sev == "medium":
            score += 3 * weight
        else:
            score += 1 * weight

    score = int(score)

    if score >= 26:
        level = "block"
    elif score >= 6:
        level = "review"
    else:
        level = "allow"

    return level, score


def _is_doc_file(file_path: str) -> bool:
    """判断是否为文档文件（.md/.txt/.rst）"""
    return file_path.endswith((".md", ".txt", ".rst", ".markdown"))


def _generate_evidence(findings: List[dict], risk_level: str) -> List[dict]:
    """为每个命中生成可解释的证据记录。

    每个证据包含:
    - file: 文件路径
    - line: 行号
    - rule: 规则描述
    - category: 风险分类名称
    - severity: 严重程度
    - reason: 风险原因
    - suggestion: 处理建议
    """
    evidence = []
    for f in findings:
        cat_name = RISK_CATEGORIES.get(f.get("rule_category", 8), "未知")
        sev = f.get("rule_severity", "medium")

        # 根据风险分类生成建议
        suggestions = {
            1: "检查指令是否试图覆盖或绕过 AI 安全策略，建议移除或重写",
            2: "检查数据外发目标，确认是否为合法遥测或日志上报",
            3: "确认是否需要提权操作，优先使用最小权限原则",
            4: "检查持久化机制是否必要，移除不必要的自启动逻辑",
            5: "确认文件操作的目标路径，避免破坏系统关键文件",
            6: "验证依赖来源的可信度，优先使用官方源和锁定版本",
            7: "检测到反弹Shell或后门特征，建议立即禁用该 Skill",
            8: "检查命令执行上下文，确认输入来源是否可信",
            9: "确认敏感信息访问是否必要，避免硬编码凭证",
            10: "检查混淆代码的目的，合法的混淆应有明确的技术理由",
        }

        evidence.append({
            "file": f.get("file_path", "unknown"),
            "line": f.get("line_no", 0),
            "rule": f.get("rule_description", ""),
            "category": cat_name,
            "severity": sev,
            "reason": f"第 {f.get('line_no', '?')} 行匹配到规则: {f.get('rule_description', '')}",
            "suggestion": suggestions.get(f.get("rule_category", 8), "请人工审查"),
            "match": f.get("match", ""),
            "line_content": f.get("line_content", "")[:200],
        })

    return evidence


def _simplify_findings(findings: List[dict]) -> List[dict]:
    """精简命中记录，仅保留关键字段"""
    simplified = []
    for f in findings:
        simplified.append({
            "file": f.get("file_path", ""),
            "line": f.get("line_no", 0),
            "rule": f.get("rule_description", ""),
            "severity": f.get("rule_severity", ""),
            "category": f.get("rule_category", 0),
            "match": f.get("match", ""),
        })
    return simplified