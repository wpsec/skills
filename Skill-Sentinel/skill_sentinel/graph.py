# skill_sentinel/graph.py
# Skill 资产图构建与遍历

import os
import re
from typing import Dict, List, Optional, Callable

from skill_sentinel.discovery import parse_skill_md, collect_assets, resolve_references


def build_asset_graph(skill_root: str) -> dict:
    """构建 Skill 资产图。

    资产图包含以下节点：
    - entry_file: SKILL.md 路径
    - metadata: Skill 元信息
    - references: 引用文件列表
    - scripts: 脚本文件列表
    - configs: 配置文件列表
    - archives: 压缩包列表
    - docs: 文档文件列表
    - templates: 模板文件列表
    - other: 其他文件
    - indirect_deps: 脚本中引用的间接依赖
    - edges: 节点间引用关系

    Returns:
        {
            "skill_root": str,
            "entry_file": str,
            "metadata": {...},
            "references": [...],
            "scripts": [...],
            "configs": [...],
            "archives": [...],
            "docs": [...],
            "templates": [...],
            "other": [...],
            "indirect_deps": [...],
            "edges": [{from, to, type}],
        }
    """
    skill_info = parse_skill_md(skill_root)
    assets = collect_assets(skill_root)
    refs = resolve_references(skill_info["body"], skill_root)

    # 构建引用关系边
    edges = []
    entry_file = skill_info["path"]

    for ref in refs:
        edges.append({
            "from": entry_file,
            "to": ref["path"],
            "type": ref["type"],
        })

    # 分析脚本中的间接依赖（import/require/include）
    indirect_deps = _find_script_dependencies(
        assets["scripts"], skill_root
    )

    for dep in indirect_deps:
        edges.append({
            "from": dep.get("source", "unknown"),
            "to": dep,
            "type": dep.get("dep_type", "import"),
        })

    return {
        "skill_root": skill_root,
        "entry_file": entry_file,
        "metadata": {
            "name": skill_info["name"],
            "description": skill_info["description"],
            "agent_type": skill_info["agent_type"],
            "front_matter": skill_info["front_matter"],
        },
        "references": refs,
        "scripts": assets["scripts"],
        "configs": assets["configs"],
        "archives": assets["archives"],
        "docs": assets["docs"],
        "templates": assets["templates"],
        "other": assets["other"],
        "indirect_deps": [d.get("path", "") for d in indirect_deps if d.get("path")],
        "edges": edges,
    }


def _find_script_dependencies(scripts: List[str], skill_root: str) -> List[dict]:
    """分析脚本文件中的依赖引用（import/require/include）。

    识别 Python import、JavaScript require/import、Shell source 等。
    """
    deps = []

    import_patterns = {
        ".py": [
            (re.compile(r"^\s*(?:from|import)\s+(\S+)"), "python_import"),
            (re.compile(r"(?:importlib|__import__)\s*\(\s*['\"]([^'\"]+)['\"]"), "dynamic_import"),
        ],
        ".js": [
            (re.compile(r"(?:require|import)\s*\(?\s*['\"]([^'\"]+)['\"]"), "js_import"),
        ],
        ".ts": [
            (re.compile(r"(?:require|import)\s*\(?\s*['\"]([^'\"]+)['\"]"), "ts_import"),
        ],
        ".sh": [
            (re.compile(r"(?:source|\.)\s+(\S+)"), "shell_source"),
        ],
        ".bash": [
            (re.compile(r"(?:source|\.)\s+(\S+)"), "shell_source"),
        ],
    }

    for script in scripts:
        ext = os.path.splitext(script)[1].lower()
        patterns = import_patterns.get(ext, [])
        if not patterns:
            continue

        try:
            with open(script, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue

        for pattern, dep_type in patterns:
            for match in pattern.finditer(content):
                dep_name = match.group(1)
                # 跳过标准库和第三方包（仅追踪相对路径引用）
                if dep_name.startswith("."):
                    resolved = os.path.normpath(
                        os.path.join(os.path.dirname(script), dep_name)
                    )
                    deps.append({
                        "source": script,
                        "path": resolved,
                        "dep_type": dep_type,
                        "raw_name": dep_name,
                    })

    return deps


def traverse_graph(
    asset_graph: dict,
    visitor: Callable[[str, str], None],
    order: str = "breadth",
):
    """遍历资产图，对每个节点调用 visitor 函数。

    Args:
        asset_graph: 资产图字典
        visitor: 访问函数，签名为 visitor(node_type, node_path)
        order: 遍历顺序 "breadth"（广度优先）或 "depth"（深度优先）
    """
    # 定义遍历顺序
    node_groups = [
        ("entry", [asset_graph.get("entry_file", "")]),
        ("reference", [r.get("path", "") for r in asset_graph.get("references", [])]),
        ("script", asset_graph.get("scripts", [])),
        ("config", asset_graph.get("configs", [])),
        ("archive", asset_graph.get("archives", [])),
        ("doc", asset_graph.get("docs", [])),
        ("template", asset_graph.get("templates", [])),
        ("indirect_dep", asset_graph.get("indirect_deps", [])),
        ("other", asset_graph.get("other", [])),
    ]

    for node_type, paths in node_groups:
        for path in paths:
            if path and os.path.exists(path):
                visitor(node_type, path)