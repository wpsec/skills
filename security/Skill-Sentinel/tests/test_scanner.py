# tests/test_scanner.py
# 扫描引擎与归档安全测试

import os
import sys
import tarfile
import tempfile
import zipfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill_sentinel.rules import Rule, _load_rules_cached, load_rules
from skill_sentinel.scanner import scan_archive, scan_directory, scan_file, scan_text_by_line, scan_zip


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
        findings = scan_text_by_line([], get_test_rules())
        assert findings == []

    def test_single_match(self):
        findings = scan_text_by_line(["os.system('ls -la')"], get_test_rules())
        assert len(findings) == 1
        assert findings[0]["line_no"] == 1
        assert findings[0]["rule_category"] == 8

    def test_multiple_matches_same_line(self):
        findings = scan_text_by_line(["os.system('rm -rf /')"], get_test_rules())
        assert len(findings) >= 2


class TestScanFile:
    """测试文件扫描"""

    def test_scan_clean_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("print('hello')\n")
            file_path = f.name

        try:
            result = scan_file(file_path, get_test_rules(), target_kind="script")
            assert not result["malicious"]
            assert result["findings"] == []
            assert not result["skipped"]
        finally:
            os.unlink(file_path)

    def test_scan_nonexistent_file(self):
        result = scan_file("/nonexistent/path.py", get_test_rules(), target_kind="script")
        assert result["error"] is not None

    def test_skip_rule_test_and_example_files(self):
        tmpdir = tempfile.mkdtemp()
        rule_path = os.path.join(tmpdir, "sample_rules.py")
        test_path = os.path.join(tmpdir, "test_attack.py")
        example_dir = os.path.join(tmpdir, "examples")
        os.makedirs(example_dir, exist_ok=True)
        example_path = os.path.join(example_dir, "sample_attack.py")
        with open(rule_path, "w", encoding="utf-8") as f:
            f.write("os.system('rm -rf /')\n")
        with open(test_path, "w", encoding="utf-8") as f:
            f.write("os.system('rm -rf /')\n")
        with open(example_path, "w", encoding="utf-8") as f:
            f.write("os.system('rm -rf /')\n")

        try:
            rule_result = scan_file(rule_path, get_test_rules(), target_kind="script")
            test_result = scan_file(test_path, get_test_rules(), target_kind="script")
            example_result = scan_file(example_path, get_test_rules(), target_kind="script")
            assert rule_result["skipped"]
            assert rule_result["skip_reason"] == "rule_file"
            assert test_result["skipped"]
            assert test_result["skip_reason"] == "test_fixture"
            assert example_result["skipped"]
            assert example_result["skip_reason"] == "example_asset"
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestScanDirectory:
    """测试目录扫描"""

    def test_scan_directory(self):
        tmpdir = tempfile.mkdtemp()
        with open(os.path.join(tmpdir, "clean.py"), "w", encoding="utf-8") as f:
            f.write("print('hello')\n")
        with open(os.path.join(tmpdir, "bad.py"), "w", encoding="utf-8") as f:
            f.write("eval(input())\n")

        try:
            results = scan_directory(tmpdir, get_test_rules())
            assert len(results) == 2
            malicious = [item for item in results if item["malicious"]]
            assert len(malicious) == 1
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestArchives:
    """测试压缩包扫描和安全处理"""

    def test_scan_zip_archive(self):
        tmpdir = tempfile.mkdtemp()
        archive_path = os.path.join(tmpdir, "payload.zip")
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("evil.py", "import os\nos.system('rm -rf /')\n")

        try:
            results = scan_zip(archive_path, get_test_rules())
            assert any(result["malicious"] for result in results)
            assert any(result["archive_member"] == "evil.py" for result in results)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_zip_slip_member_is_rejected(self):
        tmpdir = tempfile.mkdtemp()
        archive_path = os.path.join(tmpdir, "payload.zip")
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("../escape.py", "os.system('rm -rf /')\n")

        try:
            results = scan_zip(archive_path, get_test_rules())
            assert any(result["error"] == "非法归档路径" for result in results)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_scan_tar_archive(self):
        tmpdir = tempfile.mkdtemp()
        archive_path = os.path.join(tmpdir, "payload.tar.gz")
        file_path = os.path.join(tmpdir, "evil.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("eval(user_input)\n")
        with tarfile.open(archive_path, "w:gz") as tf:
            tf.add(file_path, arcname="nested/evil.py")

        try:
            results = scan_archive(archive_path, get_test_rules())
            assert any(result["malicious"] for result in results)
            assert any(result["archive_member"] == os.path.normpath("nested/evil.py") for result in results)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_unsupported_archive_is_reported(self):
        results = scan_archive("/tmp/payload.rar", get_test_rules())
        assert len(results) == 1
        assert results[0]["unsupported_archive"]
        assert results[0]["error"] == "未支持的压缩包格式"


class TestLoadRules:
    """测试规则加载缓存"""

    def test_load_rules_cached(self, monkeypatch):
        calls = {"count": 0}
        _load_rules_cached.cache_clear()

        import skill_sentinel.rules as rules_module

        original = rules_module.load_rules_from_file

        def wrapped(filepath):
            calls["count"] += 1
            return original(filepath)

        monkeypatch.setattr(rules_module, "load_rules_from_file", wrapped)

        rules_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "rules",
        )
        rule_files = [
            os.path.join(rules_dir, "total_rules.py"),
            os.path.join(rules_dir, "precise_rules.py"),
        ]

        first = load_rules(rule_files)
        second = load_rules(rule_files)

        assert len(first) > 0
        assert len(second) == len(first)
        assert calls["count"] == len(rule_files)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
