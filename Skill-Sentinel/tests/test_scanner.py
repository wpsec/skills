# tests/test_scanner.py
# 扫描引擎测试

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill_sentinel.scanner import scan_text_by_line, scan_file, scan_directory
from skill_sentinel.rules import Rule, load_rules


def get_test_rules():
    """获取测试用规则集"""
    return {
        r"(?i)\bos\.system\s*\(": Rule(
            pattern=r"(?i)\bos\.system\s*\(",
            description="执行系统命令",
            category_id=8,
            severity="medium",
        ),
        r"(?i)\brm\s+-rf\s+/": Rule(
            pattern=r"(?i)\brm\s+-rf\s+/",
            description="删除根目录",
            category_id=5,
            severity="critical",
        ),
        r"(?i)\beval\s*\(": Rule(
            pattern=r"(?i)\beval\s*\(",
            description="动态执行代码",
            category_id=8,
            severity="medium",
        ),
    }


class TestScanTextByLine:
    """测试逐行文本扫描"""

    def test_empty_content(self):
        rules = get_test_rules()
        findings = scan_text_by_line([], rules)
        assert findings == []

    def test_no_match(self):
        rules = get_test_rules()
        lines = ["print('hello world')", "x = 1 + 2"]
        findings = scan_text_by_line(lines, rules)
        assert findings == []

    def test_single_match(self):
        rules = get_test_rules()
        lines = ["os.system('ls -la')", "print('done')"]
        findings = scan_text_by_line(lines, rules)
        assert len(findings) == 1
        assert findings[0]["line_no"] == 1
        assert "system" in findings[0]["match"]
        assert findings[0]["rule_category"] == 8

    def test_multiple_matches(self):
        rules = get_test_rules()
        lines = [
            "os.system('rm -rf /')",
            "eval(user_input)",
            "rm -rf /tmp/test",
        ]
        findings = scan_text_by_line(lines, rules)
        # os.system 匹配 1 次, eval 匹配 1 次, rm -rf / 匹配 1 次 (line 1 中的 rm -rf /)
        assert len(findings) >= 3

    def test_critical_severity(self):
        rules = get_test_rules()
        lines = ["rm -rf / --no-preserve-root"]
        findings = scan_text_by_line(lines, rules)
        assert len(findings) >= 1
        assert any(f["rule_severity"] == "critical" for f in findings)


class TestScanFile:
    """测试文件扫描"""

    def test_scan_clean_file(self):
        rules = get_test_rules()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("print('hello')\nx = 1\n")
            tmp_path = f.name

        try:
            result = scan_file(tmp_path, rules)
            assert not result["malicious"]
            assert result["findings"] == []
        finally:
            os.unlink(tmp_path)

    def test_scan_malicious_file(self):
        rules = get_test_rules()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import os\nos.system('rm -rf /')\n")
            tmp_path = f.name

        try:
            result = scan_file(tmp_path, rules)
            assert result["malicious"]
            assert len(result["findings"]) >= 1
        finally:
            os.unlink(tmp_path)

    def test_scan_nonexistent_file(self):
        rules = get_test_rules()
        result = scan_file("/nonexistent/path.py", rules)
        assert result["error"] is not None


class TestScanDirectory:
    """测试目录扫描"""

    def test_scan_directory(self):
        rules = get_test_rules()
        tmpdir = tempfile.mkdtemp()

        # 创建干净文件
        with open(os.path.join(tmpdir, "clean.py"), "w") as f:
            f.write("print('hello')\n")

        # 创建恶意文件
        with open(os.path.join(tmpdir, "bad.py"), "w") as f:
            f.write("eval(input())\n")

        results = scan_directory(tmpdir, rules)
        assert len(results) == 2
        malicious = [r for r in results if r["malicious"]]
        assert len(malicious) == 1

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestLoadRules:
    """测试规则加载"""

    def test_load_rules_from_files(self):
        rules_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "rules"
        )
        rule_files = [
            os.path.join(rules_dir, "total_rules.py"),
            os.path.join(rules_dir, "precise_rules.py"),
        ]

        rules = load_rules(rule_files)
        assert len(rules) > 0
        # 验证所有规则都是 Rule 对象
        for pattern, rule in rules.items():
            assert isinstance(rule, Rule)
            assert rule.compiled is not None
            assert 1 <= rule.category_id <= 10
            assert rule.severity in ("critical", "high", "medium", "low")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])