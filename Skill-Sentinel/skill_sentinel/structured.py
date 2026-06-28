# skill_sentinel/structured.py
# Phase 2 结构化扫描与证据聚合

import os
import re
from collections import defaultdict
from typing import Dict, List, Optional

from skill_sentinel.graph import find_path_to_target
from skill_sentinel.rules import RISK_CATEGORIES, SEVERITY_LEVELS


SUGGESTIONS = {
    1: "检查提示词是否试图覆盖或绕过安全边界，必要时拆分为只读说明和执行步骤",
    2: "确认外发目标和数据范围，避免把本地上下文或凭据发送到远端",
    3: "核实是否真的需要提权，优先改为最小权限执行",
    4: "检查持久化或自启动逻辑是否必要，默认禁止静默常驻",
    5: "复核破坏性文件操作的目标路径和触发条件，避免误删关键数据",
    6: "确认依赖来源可信且版本锁定，避免安装链路被注入",
    7: "检测到后门或反连特征，默认应禁用并人工审查",
    8: "检查命令执行、下载执行或动态解释的输入来源，确认是否受控",
    9: "确认敏感信息访问是否最小化，避免读取或传播凭据",
    10: "检查混淆或隐藏行为是否有明确合法用途，默认按高风险处理",
}

COMMAND_HINTS = (
    "os.system",
    "subprocess",
    "eval(",
    "exec(",
    "popen",
    "bash -c",
    "sh -c",
    "shell=True",
    "curl ",
    "wget ",
    "base64",
    "source ",
    " . ",
)

COMMENT_PREFIXES = ("#", "//", "*", "<!--")


def build_structured_findings(asset_graph: dict, scan_results: List[dict]) -> dict:
    """把底层逐行命中聚合为结构化发现。"""
    content_cache: Dict[str, List[str]] = {}
    raw_findings = _collect_raw_findings(scan_results, content_cache)
    clustered = _cluster_findings(raw_findings)

    structured = [
        _build_structured_finding(asset_graph, cluster, content_cache)
        for cluster in clustered
    ]
    structured = [item for item in structured if item is not None]

    return {
        "raw_findings": raw_findings,
        "structured_findings": structured,
    }


def _collect_raw_findings(scan_results: List[dict], content_cache: Dict[str, List[str]]) -> List[dict]:
    """把扫描结果扁平化成带上下文的原始命中。"""
    raw_findings = []
    for result in scan_results:
        file_path = result.get("path", "")
        origin_path = result.get("origin_path") or file_path
        for finding in result.get("findings", []):
            context_flags = _detect_context_flags(result, finding, content_cache)
            enriched = dict(finding)
            enriched.update({
                "file_path": file_path,
                "origin_path": origin_path,
                "node_kind": result.get("node_kind", "script"),
                "source_kind": result.get("source_kind", "filesystem"),
                "archive_path": result.get("archive_path"),
                "archive_member": result.get("archive_member"),
                "context_flags": context_flags,
            })
            raw_findings.append(enriched)

    return sorted(raw_findings, key=lambda item: (item["file_path"], item["line_no"], item["rule_description"]))


def _detect_context_flags(result: dict, finding: dict, content_cache: Dict[str, List[str]]) -> dict:
    """标注文件/行级上下文。"""
    file_path = result.get("path", "")
    origin_path = result.get("origin_path") or file_path
    normalized = os.path.normpath(origin_path)
    basename = os.path.basename(normalized)
    is_doc = file_path.endswith((".md", ".txt", ".rst", ".markdown")) or result.get("node_kind") in {"entry", "reference", "doc"}
    is_test = f"{os.sep}tests{os.sep}" in normalized or basename.startswith("test_")
    is_rule_file = basename.endswith("_rules.py")
    line_content = finding.get("line_content", "").strip()

    return {
        "is_doc": is_doc,
        "is_test": is_test,
        "is_rule_file": is_rule_file,
        "is_comment_line": line_content.startswith(COMMENT_PREFIXES),
        "is_code_example": is_doc and _is_line_in_fenced_code_block(origin_path, finding.get("line_no", 0), content_cache),
        "is_archive_member": bool(result.get("archive_member")),
    }


def _is_line_in_fenced_code_block(file_path: str, line_no: int, content_cache: Dict[str, List[str]]) -> bool:
    """判断某一行是否位于 Markdown 代码块中。"""
    if not file_path or not os.path.isfile(file_path):
        return False
    lines = _read_lines(file_path, content_cache)
    in_code = False
    for index, line in enumerate(lines, start=1):
        if line.strip().startswith("```"):
            in_code = not in_code
        if index == line_no:
            return in_code
    return False


def _read_lines(file_path: str, content_cache: Dict[str, List[str]]) -> List[str]:
    """带缓存读取文件。"""
    if file_path in content_cache:
        return content_cache[file_path]
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        lines = []
    content_cache[file_path] = lines
    return lines


def _cluster_findings(raw_findings: List[dict]) -> List[List[dict]]:
    """按文件和局部上下文聚合命中，减少重复报警。"""
    grouped: Dict[str, List[dict]] = defaultdict(list)
    for finding in raw_findings:
        grouped[finding["file_path"]].append(finding)

    clusters = []
    for file_findings in grouped.values():
        current = []
        for finding in sorted(file_findings, key=lambda item: (item["line_no"], item["rule_description"])):
            if not current:
                current = [finding]
                continue

            previous = current[-1]
            line_gap = finding["line_no"] - previous["line_no"]
            same_category = finding["rule_category"] == previous["rule_category"]
            execution_context = _is_execution_like(finding) or any(_is_execution_like(item) for item in current)
            if line_gap <= 2 and (same_category or execution_context):
                current.append(finding)
            else:
                clusters.append(current)
                current = [finding]

        if current:
            clusters.append(current)

    return clusters


def _build_structured_finding(asset_graph: dict, cluster: List[dict], content_cache: Dict[str, List[str]]) -> Optional[dict]:
    """把一个 cluster 转成结构化结果。"""
    if not cluster:
        return None

    primary = _select_primary_finding(cluster)
    graph_chain = _build_graph_chain(asset_graph, primary)
    command_chain = _build_command_chain(primary, content_cache)
    related_files = _collect_related_files(graph_chain, primary)
    confidence = _classify_confidence(primary, cluster, graph_chain, command_chain)
    impact_scope = _classify_impact_scope(primary, related_files)
    category_id = primary["rule_category"]
    category_name = RISK_CATEGORIES.get(category_id, f"未知({category_id})")

    chain = graph_chain + command_chain
    reason = _build_reason(primary, cluster, confidence, impact_scope, chain)

    return {
        "file": primary["file_path"],
        "line": primary["line_no"],
        "rule": primary["rule_description"],
        "severity": primary["rule_severity"],
        "category": category_id,
        "category_name": category_name,
        "match": primary.get("match", ""),
        "confidence": confidence,
        "impact_scope": impact_scope,
        "related_files": related_files,
        "chain": chain,
        "reason": reason,
        "suggestion": SUGGESTIONS.get(category_id, "请人工审查"),
        "raw_finding_count": len(cluster),
        "line_content": primary.get("line_content", "")[:200],
    }


def _select_primary_finding(cluster: List[dict]) -> dict:
    """选择一个 cluster 中最能代表风险的命中。"""
    return max(
        cluster,
        key=lambda item: (
            SEVERITY_LEVELS.get(item["rule_severity"], 0),
            1 if _is_execution_like(item) else 0,
            -item["line_no"],
        ),
    )


def _build_graph_chain(asset_graph: dict, finding: dict) -> List[dict]:
    """生成入口到目标文件的引用/依赖链。"""
    if finding.get("archive_path"):
        chain = find_path_to_target(asset_graph, finding["archive_path"])
        if chain:
            chain.append({
                "type": "archive_member",
                "path": finding["file_path"],
                "line": finding["line_no"],
                "detail": finding.get("archive_member", ""),
            })
        return _normalize_chain_steps(chain)

    chain = find_path_to_target(asset_graph, finding["origin_path"])
    return _normalize_chain_steps(chain)


def _normalize_chain_steps(chain: List[dict]) -> List[dict]:
    """规范化链路步骤格式。"""
    normalized = []
    for step in chain:
        normalized.append({
            "type": step.get("edge_type", step.get("type", step.get("kind", "entry"))),
            "path": step.get("path", ""),
            "line": step.get("meta", {}).get("line", step.get("line")),
            "detail": step.get("meta", {}).get("reference_type", step.get("detail", "")),
        })
    return normalized


def _build_command_chain(primary: dict, content_cache: Dict[str, List[str]]) -> List[dict]:
    """为危险执行点补一段同文件命令构造上下文。"""
    if primary["context_flags"].get("is_doc"):
        return []
    if primary["source_kind"] != "filesystem":
        return []

    lines = _read_lines(primary["origin_path"], content_cache)
    if not lines:
        return []

    line_no = primary["line_no"]
    current_line = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else primary.get("line_content", "")
    identifiers = _extract_identifiers(current_line)
    hints = []

    start = max(1, line_no - 4)
    for index in range(start, line_no):
        previous_line = lines[index - 1].strip()
        if not previous_line:
            continue
        if _looks_like_command_builder(previous_line) or _shares_symbol(previous_line, identifiers):
            hints.append({
                "type": "command_context",
                "path": primary["file_path"],
                "line": index,
                "detail": previous_line[:160],
            })

    if hints:
        hints.append({
            "type": "command_execution",
            "path": primary["file_path"],
            "line": line_no,
            "detail": current_line[:160],
        })

    return hints


def _extract_identifiers(line: str) -> set:
    """提取一行中的变量名。"""
    words = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", line))
    stopwords = {"if", "for", "while", "with", "return", "import", "from", "true", "false", "none"}
    return {word for word in words if word.lower() not in stopwords}


def _looks_like_command_builder(line: str) -> bool:
    """判断一行是否像命令/载荷构造。"""
    lower = line.lower()
    return any(token in lower for token in COMMAND_HINTS)


def _shares_symbol(line: str, identifiers: set) -> bool:
    """判断前置行和执行行是否共享变量。"""
    if not identifiers:
        return False
    return bool(_extract_identifiers(line) & identifiers)


def _is_execution_like(finding: dict) -> bool:
    """判断命中是否属于执行/下载/破坏链路。"""
    text = f"{finding.get('rule_description', '')} {finding.get('match', '')}".lower()
    if finding.get("rule_category") in {5, 7, 8}:
        return True
    return any(token in text for token in ("os.system", "subprocess", "eval", "exec", "popen", "rm -rf", "curl", "wget"))


def _collect_related_files(chain: List[dict], primary: dict) -> List[str]:
    """提取结构化发现涉及的文件列表。"""
    paths = []
    for step in chain:
        path = step.get("path")
        if path and path not in paths:
            paths.append(path)
    if primary["file_path"] not in paths:
        paths.append(primary["file_path"])
    return paths


def _classify_confidence(primary: dict, cluster: List[dict], graph_chain: List[dict], command_chain: List[dict]) -> str:
    """根据链路完整度和上下文给出置信度。"""
    flags = primary["context_flags"]
    if flags.get("is_rule_file") or flags.get("is_test"):
        return "low"
    if flags.get("is_doc") and (flags.get("is_code_example") or flags.get("is_comment_line")):
        return "low"

    severity = primary["rule_severity"]
    has_multi_file_path = len({step["path"] for step in graph_chain if step.get("path")}) > 2
    has_command_context = len(command_chain) >= 2
    cluster_depth = len(cluster) >= 2

    if primary.get("archive_path"):
        return "high"
    if severity in {"critical", "high"} and (has_command_context or has_multi_file_path or cluster_depth):
        return "high"
    if has_command_context or has_multi_file_path:
        return "high" if severity != "low" else "medium"
    if _is_execution_like(primary) or severity in {"critical", "high"}:
        return "medium"
    return "low"


def _classify_impact_scope(primary: dict, related_files: List[str]) -> str:
    """给出结构化发现影响范围。"""
    if primary.get("archive_path"):
        return "archive_embedded"
    unique_files = {path for path in related_files if path}
    if len(unique_files) > 1:
        return "multi_file_local"
    return "single_file"


def _build_reason(primary: dict, cluster: List[dict], confidence: str, impact_scope: str, chain: List[dict]) -> str:
    """生成人类可读的原因说明。"""
    parts = [f"第 {primary['line_no']} 行命中 {primary['rule_description']}"]
    if len(cluster) > 1:
        parts.append(f"同一上下文归并了 {len(cluster)} 条底层命中")
    if chain:
        chain_types = [step["type"] for step in chain if step.get("type")]
        if chain_types:
            parts.append(f"链路包含 {' -> '.join(chain_types[:4])}")
    parts.append(f"confidence={confidence}")
    parts.append(f"impact_scope={impact_scope}")
    return "；".join(parts)
