# skill_sentinel/analyzer.py
# 风险分析与评分

from datetime import datetime
from typing import Dict, List

from skill_sentinel.rules import RISK_CATEGORIES, Rule
from skill_sentinel.scanner import scan_skill_assets
from skill_sentinel.structured import build_structured_findings


SEVERITY_WEIGHTS = {
    "critical": 25,
    "high": 10,
    "medium": 3,
    "low": 1,
}

CONFIDENCE_WEIGHTS = {
    "high": 1.35,
    "medium": 1.0,
    "low": 0.35,
}

IMPACT_SCOPE_WEIGHTS = {
    "single_file": 1.0,
    "multi_file_local": 1.25,
    "archive_embedded": 1.4,
}


def analyze_skill(asset_graph: dict, rules: Dict[str, Rule]) -> dict:
    """对 Skill 执行完整的安全分析。"""
    scan_results = scan_skill_assets(asset_graph, rules)
    structured_payload = build_structured_findings(asset_graph, scan_results)
    raw_findings = structured_payload["raw_findings"]
    structured_findings = structured_payload["structured_findings"]

    risk_level, risk_score, decision_factors = _calculate_risk_level(
        structured_findings,
        raw_findings=raw_findings,
        include_factors=True,
    )

    category_counts = {}
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    impact_scope_counts = {
        "single_file": 0,
        "multi_file_local": 0,
        "archive_embedded": 0,
    }

    for finding in structured_findings:
        category = finding.get("category", 8)
        category_counts[category] = category_counts.get(category, 0) + 1
        severity_counts[finding.get("severity", "medium")] += 1
        confidence_counts[finding.get("confidence", "medium")] += 1
        impact_scope_counts[finding.get("impact_scope", "single_file")] += 1

    discovered_files = len(asset_graph.get("nodes", []))
    scanned_targets = len([
        result for result in scan_results
        if not result.get("skipped") and not result.get("error") and not result.get("unsupported_archive")
    ])
    skipped_targets = len([result for result in scan_results if result.get("skipped")])
    errored_targets = len([
        result for result in scan_results
        if result.get("error") or result.get("unsupported_archive")
    ])

    return {
        "skill_name": asset_graph.get("metadata", {}).get("name", "unknown"),
        "skill_path": asset_graph.get("skill_root", ""),
        "scan_time": datetime.now().isoformat(),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "summary": {
            "discovered_files": discovered_files,
            "scanned_targets": scanned_targets,
            "skipped_targets": skipped_targets,
            "errored_targets": errored_targets,
            "total_findings": len(structured_findings),
            "raw_findings_count": len(raw_findings),
            "categories": category_counts,
            "severity_counts": severity_counts,
            "confidence_counts": confidence_counts,
            "impact_scope_counts": impact_scope_counts,
        },
        "findings": _simplify_structured_findings(structured_findings),
        "raw_findings": _simplify_raw_findings(raw_findings),
        "structured_findings": structured_findings,
        "evidence": _build_evidence(structured_findings),
        "decision_factors": decision_factors,
        "asset_graph_summary": {
            "entry_file": asset_graph.get("entry_file", ""),
            "nodes_count": len(asset_graph.get("nodes", [])),
            "edges_count": len(asset_graph.get("edges", [])),
            "scripts_count": len(asset_graph.get("scripts", [])),
            "configs_count": len(asset_graph.get("configs", [])),
            "archives_count": len(asset_graph.get("archives", [])),
            "indirect_deps_count": len(asset_graph.get("indirect_deps", [])),
        },
    }


def _calculate_risk_level(
    findings: List[dict],
    raw_findings: List[dict] = None,
    include_factors: bool = False,
):
    """综合评估风险等级。"""
    raw_findings = raw_findings or []
    total_score = 0.0
    contributing = []

    for finding in findings:
        severity = finding.get("severity") or finding.get("rule_severity", "medium")
        base_score = SEVERITY_WEIGHTS.get(severity, 3)

        if "confidence" not in finding and "impact_scope" not in finding:
            modifier = 0.5 if _is_doc_file(finding.get("file") or finding.get("file_path", "")) else 1.0
            total_score += base_score * modifier
            continue

        confidence = finding.get("confidence", "medium")
        impact_scope = finding.get("impact_scope", "single_file")
        weighted = (
            base_score
            * CONFIDENCE_WEIGHTS.get(confidence, 1.0)
            * IMPACT_SCOPE_WEIGHTS.get(impact_scope, 1.0)
        )
        total_score += weighted
        contributing.append({
            "file": finding.get("file") or finding.get("file_path", ""),
            "line": finding.get("line", finding.get("line_no", 0)),
            "rule": finding.get("rule", finding.get("rule_description", "")),
            "severity": severity,
            "confidence": confidence,
            "impact_scope": impact_scope,
            "score": round(weighted, 2),
        })

    score = int(total_score)
    if score >= 26:
        level = "block"
    elif score >= 6:
        level = "review"
    else:
        level = "allow"

    if not include_factors:
        return level, score

    decision_factors = {
        "severity_weights": SEVERITY_WEIGHTS,
        "confidence_weights": CONFIDENCE_WEIGHTS,
        "impact_scope_weights": IMPACT_SCOPE_WEIGHTS,
        "raw_findings_count": len(raw_findings),
        "structured_findings_count": len(findings),
        "top_contributors": sorted(contributing, key=lambda item: item["score"], reverse=True)[:10],
    }
    return level, score, decision_factors


def _is_doc_file(file_path: str) -> bool:
    """判断是否为文档文件。"""
    return file_path.endswith((".md", ".txt", ".rst", ".markdown"))


def _simplify_structured_findings(findings: List[dict]) -> List[dict]:
    """精简结构化命中，保留兼容字段和 Phase 2 扩展字段。"""
    simplified = []
    for finding in findings:
        simplified.append({
            "file": finding.get("file", ""),
            "line": finding.get("line", 0),
            "rule": finding.get("rule", ""),
            "severity": finding.get("severity", ""),
            "category": finding.get("category", 0),
            "match": finding.get("match", ""),
            "confidence": finding.get("confidence", "medium"),
            "impact_scope": finding.get("impact_scope", "single_file"),
            "chain": finding.get("chain", []),
            "related_files": finding.get("related_files", []),
        })
    return simplified


def _simplify_raw_findings(findings: List[dict]) -> List[dict]:
    """输出逐行原始命中。"""
    simplified = []
    for finding in findings:
        simplified.append({
            "file": finding.get("file_path", ""),
            "line": finding.get("line_no", 0),
            "rule": finding.get("rule_description", ""),
            "severity": finding.get("rule_severity", ""),
            "category": finding.get("rule_category", 0),
            "match": finding.get("match", ""),
            "line_content": finding.get("line_content", "")[:200],
        })
    return simplified


def _build_evidence(findings: List[dict]) -> List[dict]:
    """生成终端和 JSON 共用的结构化证据。"""
    evidence = []
    for finding in findings:
        category_id = finding.get("category", 8)
        evidence.append({
            "file": finding.get("file", "unknown"),
            "line": finding.get("line", 0),
            "rule": finding.get("rule", ""),
            "category": finding.get("category_name", RISK_CATEGORIES.get(category_id, "未知")),
            "severity": finding.get("severity", "medium"),
            "confidence": finding.get("confidence", "medium"),
            "impact_scope": finding.get("impact_scope", "single_file"),
            "reason": finding.get("reason", ""),
            "suggestion": finding.get("suggestion", "请人工审查"),
            "match": finding.get("match", ""),
            "line_content": finding.get("line_content", ""),
            "chain": finding.get("chain", []),
            "related_files": finding.get("related_files", []),
        })
    return evidence
