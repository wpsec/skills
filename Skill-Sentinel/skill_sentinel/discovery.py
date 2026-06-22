# skill_sentinel/discovery.py
# Skill 发现与结构识别

import os
import re
import yaml
from typing import Dict, List, Optional, Tuple


# 常见 AI 工具的 Skill 搜索路径
COMMON_SKILL_PATHS = [
    "~/.claude/skills",
    "~/.cursor/skills",
    "~/.codex/skills",
    "~/.codebuddy/skills",
    "~/.anthropic/skills",
    "~/.config/claude/skills",
]


def find_skill_root(path: str) -> Optional[str]:
    """从给定路径向上或向下查找 Skill 根目录（包含 SKILL.md 的目录）。

    优先检查给定路径本身，然后向下搜索子目录，最后向上搜索父目录。
    """
    path = os.path.abspath(os.path.expanduser(path))

    # 如果直接给定文件路径，使用其所在目录
    if os.path.isfile(path):
        path = os.path.dirname(path)

    # 检查当前目录
    if os.path.isfile(os.path.join(path, "SKILL.md")):
        return path

    # 向下搜索子目录（最多 2 层）
    if os.path.isdir(path):
        for root, dirs, _ in os.walk(path):
            depth = root[len(path):].count(os.sep)
            if depth > 2:
                dirs.clear()
                continue
            if "SKILL.md" in os.listdir(root):
                return root

    # 向上搜索父目录（最多 3 层）
    current = path
    for _ in range(3):
        parent = os.path.dirname(current)
        if parent == current:
            break
        if os.path.isfile(os.path.join(parent, "SKILL.md")):
            return parent
        current = parent

    return None


def parse_skill_md(skill_root: str) -> Dict:
    """解析 SKILL.md 文件，提取 YAML Front Matter 和正文内容。

    Returns:
        {
            "path": "/path/to/SKILL.md",
            "front_matter": {...},
            "body": "...",
            "name": "...",
            "description": "...",
            "agent_type": "...",
        }
    """
    md_path = os.path.join(skill_root, "SKILL.md")
    result = {
        "path": md_path,
        "front_matter": {},
        "body": "",
        "name": os.path.basename(skill_root),
        "description": "",
        "agent_type": "unknown",
    }

    if not os.path.isfile(md_path):
        return result

    with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # 解析 YAML Front Matter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if fm_match:
        try:
            front_matter = yaml.safe_load(fm_match.group(1))
            if isinstance(front_matter, dict):
                result["front_matter"] = front_matter
                result["name"] = front_matter.get("name", result["name"])
                result["description"] = front_matter.get("description", "")
                result["agent_type"] = front_matter.get("agent-type", front_matter.get("agent_type", "unknown"))
        except yaml.YAMLError:
            pass

        result["body"] = content[fm_match.end():]
    else:
        result["body"] = content

    return result


def collect_assets(skill_root: str) -> Dict[str, List[str]]:
    """收集 Skill 目录下的所有资源文件，按类型分类。

    Returns:
        {
            "scripts": [".py", ".sh", ".js", ".ts", ...],
            "configs": [".json", ".yaml", ".yml", ".toml", ...],
            "archives": [".zip", ".tar.gz", ...],
            "docs": [".md", ".txt", ...],
            "templates": [".html", ".jinja", ...],
            "other": [...],
        }
    """
    assets = {
        "scripts": [],
        "configs": [],
        "archives": [],
        "docs": [],
        "templates": [],
        "other": [],
    }

    script_exts = {".py", ".sh", ".bash", ".js", ".ts", ".rb", ".pl", ".php", ".ps1", ".bat", ".cmd"}
    config_exts = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".xml"}
    archive_exts = {".zip", ".tar.gz", ".tar", ".tgz", ".gz", ".rar", ".7z"}
    doc_exts = {".md", ".txt", ".rst", ".pdf"}
    template_exts = {".html", ".jinja", ".j2", ".tmpl", ".hbs", ".ejs"}
    # 排除常见的非代码文件
    exclude_exts = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".ttf", ".eot", ".map"}

    for root, _, files in os.walk(skill_root):
        for file in files:
            if file.startswith(".") and file != ".env":
                continue
            full = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            # 检查双扩展名 (如 .tar.gz)
            if file.endswith(".tar.gz"):
                ext = ".tar.gz"
            elif file.endswith(".tar.xz"):
                ext = ".tar.xz"

            if ext in exclude_exts:
                continue
            elif ext in script_exts:
                assets["scripts"].append(full)
            elif ext in config_exts:
                assets["configs"].append(full)
            elif ext in archive_exts:
                assets["archives"].append(full)
            elif ext in doc_exts:
                assets["docs"].append(full)
            elif ext in template_exts:
                assets["templates"].append(full)
            else:
                assets["other"].append(full)

    return assets


def resolve_references(skill_md_body: str, skill_root: str) -> List[Dict[str, str]]:
    """解析 SKILL.md 正文中的引用路径。

    识别 Markdown 链接、文件路径引用、代码块中的文件路径等。

    Returns:
        [{type, path, line}]
    """
    references = []

    # 1. Markdown 链接: [text](path)
    md_link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
    for line_no, line in enumerate(skill_md_body.split("\n"), start=1):
        for match in md_link_pattern.finditer(line):
            ref_path = match.group(2)
            if ref_path and not ref_path.startswith(("http://", "https://", "#")):
                full_path = os.path.normpath(os.path.join(skill_root, ref_path))
                references.append({
                    "type": "markdown_link",
                    "path": full_path,
                    "line": line_no,
                })

    # 2. 反引号中的文件路径: `path/to/file`
    backtick_pattern = re.compile(r"`([^`]+\.(?:py|sh|js|ts|json|yaml|yml|toml|md|txt|cfg|conf))`")
    for line_no, line in enumerate(skill_md_body.split("\n"), start=1):
        for match in backtick_pattern.finditer(line):
            ref_path = match.group(1)
            if not ref_path.startswith(("http://", "https://", "/")):
                full_path = os.path.normpath(os.path.join(skill_root, ref_path))
                references.append({
                    "type": "inline_path",
                    "path": full_path,
                    "line": line_no,
                })

    # 3. 代码块中的文件路径引用
    # 匹配类似 "file: path/to/file.py" 或 "see path/to/file.sh"
    file_ref_pattern = re.compile(
        r"(?:file|script|config|参考|引用|参见|see|refer|source)[:：]\s*([^\s\n]+\.(?:py|sh|js|ts|json|yaml|yml|toml|md))",
        re.IGNORECASE
    )
    for line_no, line in enumerate(skill_md_body.split("\n"), start=1):
        for match in file_ref_pattern.finditer(line):
            ref_path = match.group(1)
            if not ref_path.startswith(("http://", "https://", "/")):
                full_path = os.path.normpath(os.path.join(skill_root, ref_path))
                references.append({
                    "type": "explicit_ref",
                    "path": full_path,
                    "line": line_no,
                })

    return references


def find_common_tool_skills() -> List[str]:
    """查找系统中常见 AI 工具的 Skill 目录"""
    found = []
    for path in COMMON_SKILL_PATHS:
        expanded = os.path.expanduser(path)
        if os.path.isdir(expanded):
            for item in os.listdir(expanded):
                item_path = os.path.join(expanded, item)
                if os.path.isdir(item_path):
                    root = find_skill_root(item_path)
                    if root:
                        found.append(root)
        elif os.path.isdir(expanded):
            root = find_skill_root(expanded)
            if root:
                found.append(root)
    return found