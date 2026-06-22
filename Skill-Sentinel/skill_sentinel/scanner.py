# skill_sentinel/scanner.py
# 正则扫描引擎 — 从 Safety and Management Tools for Skill.py 提取并重构

import os
import re
import zipfile
import tempfile
from typing import Dict, List, Optional

from skill_sentinel.rules import Rule


def scan_text_by_line(content_lines: List[str], rules: Dict[str, Rule]) -> List[dict]:
    """逐行扫描文本内容，返回命中列表。

    Args:
        content_lines: 文本行列表
        rules: {pattern_str: Rule} 映射

    Returns:
        [{line_no, line_content, match, rule_description, rule_category, rule_severity}]
    """
    findings = []
    for line_no, line in enumerate(content_lines, start=1):
        line_stripped = line.rstrip("\n\r")
        for pattern_str, rule in rules.items():
            matches = rule.compiled.findall(line_stripped)
            for m in matches:
                findings.append({
                    "line_no": line_no,
                    "line_content": line_stripped,
                    "match": str(m),
                    "rule_description": rule.description,
                    "rule_category": rule.category_id,
                    "rule_severity": rule.severity,
                    "rule_pattern": pattern_str,
                })
    return findings


# 默认跳过的文件模式 — 安全扫描工具的规则文件会自匹配
SKIP_PATTERNS = [
    "**/rules/total_rules.py",
    "**/rules/precise_rules.py",
    "**/rules/apt_rules.py",
    "**/rules/*_rules.py",
]


def _should_skip(file_path: str) -> bool:
    """检查文件是否应跳过扫描"""
    import fnmatch
    basename = os.path.basename(file_path)
    # 跳过规则文件（含检测模式字面字符串，100%自匹配误报）
    if basename in ("total_rules.py", "precise_rules.py", "apt_rules.py"):
        return True
    if basename.endswith("_rules.py"):
        return True
    return False


def scan_file(file_path: str, rules: Dict[str, Rule]) -> dict:
    """扫描单个文件。

    Returns:
        {path, malicious, findings, error}
    """
    result = {"path": file_path, "malicious": False, "findings": [], "error": None}
    if _should_skip(file_path):
        result["skipped"] = True
        return result
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        findings = scan_text_by_line(lines, rules)
        if findings:
            result["malicious"] = True
            result["findings"] = findings
    except Exception as e:
        result["error"] = str(e)
    return result


def scan_directory(dir_path: str, rules: Dict[str, Rule]) -> List[dict]:
    """递归扫描目录中的所有文件。

    Returns:
        [{path, malicious, findings, error}]
    """
    results = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            full = os.path.join(root, file)
            results.append(scan_file(full, rules))
    return results


def scan_zip(zip_path: str, rules: Dict[str, Rule]) -> List[dict]:
    """扫描 ZIP 压缩包内容。

    解压到临时目录，递归扫描，完成后清理临时目录。

    Returns:
        [{path, malicious, findings, error}]
    """
    results = []
    tmpdir = tempfile.mkdtemp(prefix="skill_sentinel_")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmpdir)
        for root, _, files in os.walk(tmpdir):
            for file in files:
                full = os.path.join(root, file)
                results.append(scan_file(full, rules))
    except Exception as e:
        results.append({
            "path": zip_path, "malicious": False, "findings": [],
            "error": f"ZIP 解压失败: {e}"
        })
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    return results


def scan_skill_assets(asset_graph: dict, rules: Dict[str, Rule]) -> List[dict]:
    """基于资产图扫描 Skill 的所有资源。

    按资产图顺序依次扫描：入口文件 → 引用文件 → 脚本 → 配置 → 压缩包。

    Args:
        asset_graph: 由 graph.build_asset_graph() 返回的资产图
        rules: 规则字典

    Returns:
        [{path, malicious, findings, error}]
    """
    all_results = []

    # 1. 扫描入口文件
    entry_file = asset_graph.get("entry_file")
    if entry_file and os.path.isfile(entry_file):
        all_results.append(scan_file(entry_file, rules))

    # 2. 扫描引用文件
    for ref in asset_graph.get("references", []):
        path = ref.get("path", "")
        if path and os.path.isfile(path):
            all_results.append(scan_file(path, rules))

    # 3. 扫描脚本文件
    for script in asset_graph.get("scripts", []):
        all_results.append(scan_file(script, rules))

    # 4. 扫描配置文件
    for config in asset_graph.get("configs", []):
        all_results.append(scan_file(config, rules))

    # 5. 扫描压缩包
    for archive in asset_graph.get("archives", []):
        all_results.extend(scan_zip(archive, rules))

    # 6. 扫描间接依赖
    for dep in asset_graph.get("indirect_deps", []):
        if os.path.isfile(dep):
            all_results.append(scan_file(dep, rules))

    return all_results