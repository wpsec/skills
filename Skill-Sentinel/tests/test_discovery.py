# tests/test_discovery.py
# Skill 发现与结构识别测试

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill_sentinel.discovery import (
    find_skill_root,
    parse_skill_md,
    collect_assets,
    resolve_references,
)


class TestFindSkillRoot:
    """测试 Skill 根目录查找"""

    def test_find_skill_root_in_current_dir(self):
        tmpdir = tempfile.mkdtemp()
        # 创建 SKILL.md
        with open(os.path.join(tmpdir, "SKILL.md"), "w") as f:
            f.write("---\nname: test\n---\n# Test Skill\n")

        root = find_skill_root(tmpdir)
        assert root == tmpdir

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_find_skill_root_in_subdir(self):
        tmpdir = tempfile.mkdtemp()
        subdir = os.path.join(tmpdir, "subdir", "skill")
        os.makedirs(subdir)
        with open(os.path.join(subdir, "SKILL.md"), "w") as f:
            f.write("---\nname: test\n---\n")

        root = find_skill_root(tmpdir)
        assert root == subdir

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_no_skill_md(self):
        tmpdir = tempfile.mkdtemp()
        root = find_skill_root(tmpdir)
        assert root is None

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestParseSkillMd:
    """测试 SKILL.md 解析"""

    def test_parse_with_front_matter(self):
        tmpdir = tempfile.mkdtemp()
        content = """---
name: test-skill
description: A test skill for scanning
agent-type: test
---

# Test Skill

This is the body content.
"""
        with open(os.path.join(tmpdir, "SKILL.md"), "w") as f:
            f.write(content)

        result = parse_skill_md(tmpdir)
        assert result["name"] == "test-skill"
        assert result["description"] == "A test skill for scanning"
        assert result["agent_type"] == "test"
        assert "This is the body content" in result["body"]

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_parse_without_front_matter(self):
        tmpdir = tempfile.mkdtemp()
        content = "# Test Skill\n\nJust a simple skill."
        with open(os.path.join(tmpdir, "SKILL.md"), "w") as f:
            f.write(content)

        result = parse_skill_md(tmpdir)
        assert result["front_matter"] == {}
        assert "Just a simple skill" in result["body"]

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestCollectAssets:
    """测试资源收集"""

    def test_collect_assets(self):
        tmpdir = tempfile.mkdtemp()
        # 创建各类文件
        with open(os.path.join(tmpdir, "SKILL.md"), "w") as f:
            f.write("# Test\n")
        with open(os.path.join(tmpdir, "script.py"), "w") as f:
            f.write("print('hello')\n")
        with open(os.path.join(tmpdir, "config.json"), "w") as f:
            f.write('{"key": "value"}\n')
        with open(os.path.join(tmpdir, "setup.sh"), "w") as f:
            f.write("#!/bin/bash\necho hi\n")

        assets = collect_assets(tmpdir)
        assert "scripts" in assets
        assert "configs" in assets
        # 验证分类
        assert any("script.py" in s for s in assets["scripts"])
        assert any("setup.sh" in s for s in assets["scripts"])
        assert any("config.json" in c for c in assets["configs"])

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestResolveReferences:
    """测试引用解析"""

    def test_markdown_links(self):
        body = "See [script](scripts/run.py) for details."
        refs = resolve_references(body, "/tmp/test-skill")
        assert len(refs) >= 1
        assert any("scripts/run.py" in r["path"] for r in refs)

    def test_skip_http_links(self):
        body = "See [docs](https://example.com/doc) for more."
        refs = resolve_references(body, "/tmp/test-skill")
        http_refs = [r for r in refs if "https://" in r["path"]]
        assert len(http_refs) == 0

    def test_backtick_paths(self):
        body = "Run `scripts/setup.sh` first."
        refs = resolve_references(body, "/tmp/test-skill")
        assert any("scripts/setup.sh" in r["path"] for r in refs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])