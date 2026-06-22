# skill_sentinel/__init__.py
# SkillSentinel — Skill 安全扫描引擎
#
# 用法:
#   from skill_sentinel import scan_skill
#   result = scan_skill("/path/to/skill")
#
# 或作为模块运行:
#   python -m skill_sentinel /path/to/skill

from skill_sentinel.discovery import find_skill_root, parse_skill_md, collect_assets
from skill_sentinel.rules import load_rules, get_rules_by_category
from skill_sentinel.scanner import scan_file, scan_directory, scan_skill_assets
from skill_sentinel.graph import build_asset_graph
from skill_sentinel.analyzer import analyze_skill
from skill_sentinel.reporter import format_result_json, format_result_terminal


def scan_skill(skill_path: str, rule_files: list = None) -> dict:
    """扫描一个 Skill 的便捷入口函数。

    返回包含 risk_level、findings、evidence、asset_graph 的字典。
    """
    if rule_files is None:
        import os
        rules_dir = os.path.join(os.path.dirname(__file__), "..", "rules")
        rule_files = [
            os.path.join(rules_dir, "total_rules.py"),
            os.path.join(rules_dir, "precise_rules.py"),
            os.path.join(rules_dir, "apt_rules.py"),
        ]

    rules = load_rules(rule_files)
    skill_root = find_skill_root(skill_path)
    if not skill_root:
        return {"error": f"未找到 SKILL.md: {skill_path}", "risk_level": "block"}

    asset_graph = build_asset_graph(skill_root)
    result = analyze_skill(asset_graph, rules)
    return result