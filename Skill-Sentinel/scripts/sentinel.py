#!/usr/bin/env python3
# SkillSentinel CLI 入口
# 用法:
#   python3 -m skill_sentinel /path/to/skill         扫描单个 Skill
#   python3 -m skill_sentinel --scan-all              扫描所有已安装 Skill
#   python3 -m skill_sentinel --init                  同 --scan-all，初始化安全基线
#   python3 -m skill_sentinel /path/to/skill --json   输出 JSON 格式

import argparse
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill_sentinel import scan_skill
from skill_sentinel.reporter import format_result_json, format_result_terminal, export_report
from skill_sentinel.discovery import find_common_tool_skills, find_skill_root


def scan_all_skills():
    """扫描所有已安装的 Skill，返回汇总结果"""
    skills = find_common_tool_skills()
    return _scan_skill_list(skills)


def scan_dir(dir_path: str):
    """扫描指定目录下的所有 Skill（递归查找 SKILL.md）"""
    skills = []
    for root, dirs, _ in os.walk(dir_path):
        # 跳过隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if "SKILL.md" in os.listdir(root):
            skills.append(root)
            # 找到 SKILL.md 后不再深入该目录
            dirs.clear()
    return _scan_skill_list(skills)


def _scan_skill_list(skills: list):
    """扫描 Skill 列表，返回汇总结果"""
    results = []
    for i, skill_path in enumerate(skills):
        result = scan_skill(skill_path)
        results.append(result)
        if result.get("risk_level") == "block":
            print(f"  [{i+1}/{len(skills)}] BLOCK  {result.get('skill_name', '?')}", file=sys.stderr)
    return results


def format_summary(results: list) -> str:
    """生成多 Skill 扫描汇总"""
    lines = []
    lines.append("=" * 60)
    lines.append("  SkillSentinel 初始化扫描报告")
    lines.append(f"  扫描时间: {datetime.now().isoformat()}")
    lines.append(f"  扫描 Skill 总数: {len(results)}")
    lines.append("=" * 60)
    lines.append("")

    blocked = [r for r in results if r.get("risk_level") == "block"]
    review = [r for r in results if r.get("risk_level") == "review"]
    allowed = [r for r in results if r.get("risk_level") == "allow"]

    lines.append(f"  BLOCK (高危): {len(blocked)} 个")
    lines.append(f"  REVIEW (中危): {len(review)} 个")
    lines.append(f"  ALLOW (低危): {len(allowed)} 个")
    lines.append("")

    # 列出 BLOCK 级别的 Skill 详情
    if blocked:
        lines.append("--- 高危 Skill (建议立即禁用) ---")
        for r in blocked:
            lines.append(f"  [BLOCK] {r.get('skill_name', '?')}")
            lines.append(f"          路径: {r.get('skill_path', '?')}")
            lines.append(f"          评分: {r.get('risk_score', 0)} | 命中: {r['summary']['total_findings']}")
            # 列出风险分类
            cats = r["summary"].get("categories", {})
            if cats:
                from skill_sentinel.rules import RISK_CATEGORIES
                cat_str = ", ".join(
                    f"{RISK_CATEGORIES.get(c, str(c))}({n})"
                    for c, n in sorted(cats.items(), key=lambda x: -x[1])[:3]
                )
                lines.append(f"          风险: {cat_str}")
            lines.append("")

    if review:
        lines.append("--- 中危 Skill (建议人工审查) ---")
        for r in review:
            lines.append(f"  [REVIEW] {r.get('skill_name', '?')} (评分: {r.get('risk_score', 0)})")
        lines.append("")

    if allowed:
        lines.append(f"--- 低危 Skill ({len(allowed)} 个，已放行) ---")

    lines.append("")
    lines.append("=" * 60)
    if blocked:
        lines.append("  建议: 立即禁用 {0} 个高危 Skill，审查 {1} 个中危 Skill".format(
            len(blocked), len(review)))
    elif review:
        lines.append("  建议: 审查 {0} 个中危 Skill 后决定是否启用".format(len(review)))
    else:
        lines.append("  所有 Skill 均已通过安全检查")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="SkillSentinel — Skill 安全扫描哨兵",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s /path/to/skill                   扫描单个 Skill（终端输出）
  %(prog)s /path/to/skill --json            输出 JSON 格式
  %(prog)s /path/to/skill -o report.json    导出报告到文件
  %(prog)s --scan-all                       扫描所有已安装 Skill
  %(prog)s --init                           初始化安全基线（同 --scan-all）
  %(prog)s /path/to/skill --rules custom.py 使用自定义规则文件
        """,
    )
    parser.add_argument("path", nargs="?", help="Skill 目录路径（不指定则使用 --scan-all）")
    parser.add_argument("--scan-all", action="store_true", help="扫描所有已安装的 Skill")
    parser.add_argument("--scan-dir", help="扫描指定目录下所有 Skill（递归查找 SKILL.md）")
    parser.add_argument("--init", action="store_true", help="初始化安全基线（同 --scan-all）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("-o", "--output", help="导出报告到指定文件")
    parser.add_argument("--rules", nargs="+", help="指定规则文件路径（可多个）")
    parser.add_argument("--format", choices=["json", "terminal"], default="json",
                        help="导出报告格式 (默认: json)")
    parser.add_argument("--quiet", action="store_true", help="静默模式，仅输出 JSON 结果")

    args = parser.parse_args()

    # --scan-dir 模式
    if args.scan_dir:
        if not os.path.isdir(args.scan_dir):
            print(f"错误: 目录不存在: {args.scan_dir}", file=sys.stderr)
            sys.exit(1)

        if not args.quiet:
            print(f"正在扫描目录: {args.scan_dir}", file=sys.stderr)

        results = scan_dir(args.scan_dir)

        if args.output:
            export_report({"scan_time": datetime.now().isoformat(), "results": results},
                          args.output, format=args.format)
            if not args.quiet:
                print(f"报告已导出: {args.output}", file=sys.stderr)
        elif args.json:
            print(format_result_json({"scan_time": datetime.now().isoformat(), "results": results}))
        else:
            print(format_summary(results))

        blocked = [r for r in results if r.get("risk_level") == "block"]
        sys.exit(2 if blocked else 0)
        return

    # --scan-all / --init 模式
    if args.scan_all or args.init:
        mode = "init" if args.init else "scan-all"
        if not args.quiet:
            print(f"正在扫描所有已安装 Skill ({mode})...", file=sys.stderr)

        results = scan_all_skills()

        if args.output:
            export_report({"scan_time": datetime.now().isoformat(), "results": results},
                          args.output, format=args.format)
            if not args.quiet:
                print(f"报告已导出: {args.output}", file=sys.stderr)
        elif args.json:
            print(format_result_json({"scan_time": datetime.now().isoformat(), "results": results}))
        else:
            print(format_summary(results))

        blocked = [r for r in results if r.get("risk_level") == "block"]
        sys.exit(2 if blocked else 0)
        return

    # 单 Skill 扫描模式
    if not args.path:
        parser.print_help()
        print("\n错误: 请指定 Skill 路径或使用 --scan-dir / --scan-all / --init", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.path):
        print(f"错误: 路径不存在: {args.path}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"正在扫描: {args.path}", file=sys.stderr)

    result = scan_skill(args.path, rule_files=args.rules)

    if args.output:
        out_path = export_report(result, args.output, format=args.format)
        if not args.quiet:
            print(f"报告已导出: {out_path}", file=sys.stderr)
    elif args.json:
        print(format_result_json(result))
    else:
        print(format_result_terminal(result))

    risk_level = result.get("risk_level", "block")
    if risk_level == "block":
        sys.exit(2)
    elif risk_level == "review":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()