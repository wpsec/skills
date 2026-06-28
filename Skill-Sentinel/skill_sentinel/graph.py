# skill_sentinel/graph.py
# Skill 资产图构建与遍历

import os
import re
from collections import deque
from typing import Callable, Dict, List, Optional

from skill_sentinel.discovery import collect_assets, parse_skill_md, resolve_references


def build_asset_graph(skill_root: str) -> dict:
    """构建 Skill 资产图。

    图结构中的 node 和 edge 使用稳定 schema：
    - node: {path, kind, exists}
    - edge: {from, to, type, meta}
    """
    skill_info = parse_skill_md(skill_root)
    assets = collect_assets(skill_root)
    refs = resolve_references(skill_info["body"], skill_root)

    entry_file = skill_info["path"]
    node_map: Dict[str, dict] = {}
    edges: List[dict] = []

    _register_node(node_map, entry_file, "entry")

    grouped_nodes = {
        "scripts": _register_paths(node_map, assets["scripts"], "script"),
        "configs": _register_paths(node_map, assets["configs"], "config"),
        "archives": _register_paths(node_map, assets["archives"], "archive"),
        "docs": _register_paths(node_map, assets["docs"], "doc"),
        "templates": _register_paths(node_map, assets["templates"], "template"),
        "other": _register_paths(node_map, assets["other"], "other"),
    }

    references = []
    for ref in refs:
        target_path = ref["path"]
        node = _register_node(node_map, target_path, _infer_node_kind(target_path))
        references.append({
            "path": target_path,
            "line": ref["line"],
            "type": ref["type"],
            "exists": node["exists"],
        })
        edges.append({
            "from": entry_file,
            "to": target_path,
            "type": "reference",
            "meta": {
                "reference_type": ref["type"],
                "line": ref["line"],
            },
        })

    indirect_deps = _find_script_dependencies(
        [node["path"] for node in grouped_nodes["scripts"]],
        skill_root,
        node_map,
    )

    for dep in indirect_deps:
        edges.append({
            "from": dep["source"],
            "to": dep["path"],
            "type": "dependency",
            "meta": {
                "dep_type": dep["dep_type"],
                "raw_name": dep["raw_name"],
            },
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
        "nodes": list(node_map.values()),
        "references": references,
        "scripts": grouped_nodes["scripts"],
        "configs": grouped_nodes["configs"],
        "archives": grouped_nodes["archives"],
        "docs": grouped_nodes["docs"],
        "templates": grouped_nodes["templates"],
        "other": grouped_nodes["other"],
        "indirect_deps": indirect_deps,
        "edges": edges,
    }


def _register_paths(node_map: Dict[str, dict], paths: List[str], kind: str) -> List[dict]:
    """按路径批量注册节点。"""
    return [_register_node(node_map, path, kind) for path in paths]


def _register_node(node_map: Dict[str, dict], path: str, kind: str) -> dict:
    """注册或更新单个节点。"""
    node = node_map.get(path)
    if node is None:
        node = {
            "path": path,
            "kind": kind,
            "exists": os.path.exists(path),
        }
        node_map[path] = node
        return node

    if node["kind"] == "other" and kind != "other":
        node["kind"] = kind
    if node["kind"] == "reference" and kind not in {"reference", "other"}:
        node["kind"] = kind
    node["exists"] = os.path.exists(path)
    return node


def _infer_node_kind(path: str) -> str:
    """根据扩展名推断节点类型。"""
    ext = os.path.splitext(path)[1].lower()
    if path.endswith(".tar.gz"):
        return "archive"
    if ext in {".py", ".sh", ".bash", ".js", ".ts", ".rb", ".pl", ".php", ".ps1", ".bat", ".cmd"}:
        return "script"
    if ext in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".xml"}:
        return "config"
    if ext in {".zip", ".tar", ".tgz", ".rar", ".7z"}:
        return "archive"
    if ext in {".md", ".txt", ".rst", ".pdf"}:
        return "doc"
    if ext in {".html", ".jinja", ".j2", ".tmpl", ".hbs", ".ejs"}:
        return "template"
    return "reference"


def _find_script_dependencies(
    scripts: List[str],
    skill_root: str,
    node_map: Optional[Dict[str, dict]] = None,
) -> List[dict]:
    """分析脚本文件中的本地依赖引用（import/require/include）。"""
    deps = []

    import_patterns = {
        ".py": [
            (re.compile(r"^\s*from\s+([A-Za-z_][\w\.]*)\s+import\b"), "python_import"),
            (re.compile(r"^\s*import\s+([A-Za-z_][\w\.]*)"), "python_import"),
            (re.compile(r"(?:importlib|__import__)\s*\(\s*['\"]([^'\"]+)['\"]"), "dynamic_import"),
        ],
        ".js": [
            (re.compile(r"(?:require|import)\s*\(?\s*['\"]([^'\"]+)['\"]"), "js_import"),
        ],
        ".ts": [
            (re.compile(r"(?:require|import)\s*\(?\s*['\"]([^'\"]+)['\"]"), "ts_import"),
        ],
        ".sh": [
            (re.compile(r"(?:source|\.)\s+([^\s]+)"), "shell_source"),
        ],
        ".bash": [
            (re.compile(r"(?:source|\.)\s+([^\s]+)"), "shell_source"),
        ],
    }

    seen = set()
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
                dep_name = match.group(1).strip()
                dep_path = _resolve_dependency_path(script, dep_name, dep_type, skill_root)
                if not dep_path:
                    continue

                item = (script, dep_path, dep_type)
                if item in seen:
                    continue
                seen.add(item)

                if node_map is not None:
                    _register_node(node_map, dep_path, _infer_node_kind(dep_path))

                deps.append({
                    "source": script,
                    "path": dep_path,
                    "dep_type": dep_type,
                    "raw_name": dep_name,
                    "exists": os.path.exists(dep_path),
                })

    return deps


def _resolve_dependency_path(
    script_path: str,
    dep_name: str,
    dep_type: str,
    skill_root: str,
) -> Optional[str]:
    """把 import/source 名称解析为 Skill 内部路径。"""
    script_dir = os.path.dirname(script_path)

    if dep_type == "shell_source":
        if dep_name.startswith(("http://", "https://")):
            return None
        return os.path.normpath(os.path.join(script_dir, dep_name))

    if dep_name.startswith("."):
        return _resolve_relative_module(script_dir, dep_name)

    if dep_type in {"python_import", "dynamic_import"}:
        candidate = os.path.join(skill_root, dep_name.replace(".", os.sep))
        for suffix in (".py", os.path.join("", "__init__.py")):
            full = candidate + suffix
            if os.path.exists(full):
                return os.path.normpath(full)

    if dep_type in {"js_import", "ts_import"}:
        if dep_name.startswith("/"):
            return None
        for base in (
            os.path.join(script_dir, dep_name),
            os.path.join(skill_root, dep_name),
        ):
            resolved = _resolve_script_candidate(base)
            if resolved:
                return resolved

    return None


def _resolve_relative_module(base_dir: str, dep_name: str) -> str:
    """解析相对 import 路径。"""
    normalized = dep_name.replace(".", os.sep).lstrip(os.sep)
    return _resolve_script_candidate(os.path.join(base_dir, normalized)) or os.path.normpath(
        os.path.join(base_dir, normalized)
    )


def _resolve_script_candidate(base_path: str) -> Optional[str]:
    """尝试解析常见脚本后缀。"""
    candidates = [
        base_path,
        f"{base_path}.py",
        f"{base_path}.sh",
        f"{base_path}.bash",
        f"{base_path}.js",
        f"{base_path}.ts",
        os.path.join(base_path, "__init__.py"),
        os.path.join(base_path, "index.js"),
        os.path.join(base_path, "index.ts"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return os.path.normpath(candidate)
    return None


def traverse_graph(
    asset_graph: dict,
    visitor: Callable[[str, str], None],
    order: str = "breadth",
):
    """遍历资产图中的节点。

    order 参数当前保留兼容，节点输出顺序始终是稳定的优先级顺序。
    """
    del order

    for node in asset_graph.get("nodes", []):
        if node["path"] and node["exists"]:
            visitor(node["kind"], node["path"])


def find_path_to_target(asset_graph: dict, target_path: str) -> List[dict]:
    """查找从入口文件到目标文件的一条链路。"""
    entry = asset_graph.get("entry_file", "")
    if not entry or not target_path:
        return []
    if entry == target_path:
        return [{"path": entry, "kind": "entry"}]

    adjacency: Dict[str, List[dict]] = {}
    for edge in asset_graph.get("edges", []):
        adjacency.setdefault(edge["from"], []).append(edge)

    queue = deque([(entry, [{"path": entry, "kind": "entry"}])])
    seen = {entry}
    node_kind = {node["path"]: node["kind"] for node in asset_graph.get("nodes", [])}

    while queue:
        current, path = queue.popleft()
        for edge in adjacency.get(current, []):
            nxt = edge["to"]
            if nxt in seen:
                continue
            next_step = {
                "path": nxt,
                "kind": node_kind.get(nxt, "reference"),
                "edge_type": edge["type"],
                "meta": edge.get("meta", {}),
            }
            if nxt == target_path:
                return path + [next_step]
            seen.add(nxt)
            queue.append((nxt, path + [next_step]))

    return []
