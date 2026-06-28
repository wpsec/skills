# tests/test_reporter.py
# 报告输出测试

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill_sentinel.reporter import format_result_terminal


def test_terminal_report_prefers_structured_evidence():
    result = {
        "skill_name": "demo",
        "skill_path": "/tmp/demo",
        "scan_time": "2026-06-28T10:00:00",
        "risk_level": "review",
        "risk_score": 12,
        "summary": {
            "discovered_files": 4,
            "scanned_targets": 3,
            "skipped_targets": 1,
            "errored_targets": 0,
            "total_findings": 1,
            "raw_findings_count": 3,
            "severity_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
            "confidence_counts": {"high": 1, "medium": 0, "low": 0},
            "impact_scope_counts": {"single_file": 0, "multi_file_local": 1, "archive_embedded": 0},
        },
        "asset_graph_summary": {
            "entry_file": "SKILL.md",
            "nodes_count": 4,
            "edges_count": 2,
            "scripts_count": 2,
            "configs_count": 0,
            "archives_count": 0,
            "indirect_deps_count": 1,
        },
        "evidence": [
            {
                "file": "/tmp/demo/helper.py",
                "line": 12,
                "rule": "执行系统命令",
                "category": "隐蔽下载与远程执行",
                "severity": "high",
                "confidence": "high",
                "impact_scope": "multi_file_local",
                "reason": "第 12 行命中执行系统命令",
                "suggestion": "检查命令执行、下载执行或动态解释的输入来源，确认是否受控",
                "chain": [
                    {"type": "reference", "path": "scripts/run.py", "line": 5, "detail": "markdown_link"},
                    {"type": "dependency", "path": "helper.py", "line": None, "detail": "python_import"},
                ],
                "related_files": ["scripts/run.py", "helper.py"],
            }
        ],
        "decision_factors": {
            "top_contributors": [
                {
                    "score": 12.5,
                    "severity": "high",
                    "confidence": "high",
                    "impact_scope": "multi_file_local",
                    "file": "/tmp/demo/helper.py",
                    "line": 12,
                }
            ]
        },
    }

    output = format_result_terminal(result)
    assert "结构化证据" in output
    assert "confidence=high" in output
    assert "评分贡献 Top 5" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
