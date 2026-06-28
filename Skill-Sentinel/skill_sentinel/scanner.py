# skill_sentinel/scanner.py
# 正则扫描引擎与归档扫描

import os
import tarfile
import zipfile
from typing import Dict, List, Optional

from skill_sentinel.rules import Rule, select_rules_for_target


MAX_SCAN_BYTES = 1024 * 1024
TEXT_SAMPLE_BYTES = 2048
ARCHIVE_SOURCE_KIND = {
    "zip": "zip_archive",
    "tar": "tar_archive",
}
DOC_SCAN_HINTS = (
    "ignore previous",
    "ignore all",
    "system prompt",
    "pretend",
    "curl",
    "wget",
    "http://",
    "https://",
    "os.system",
    "subprocess",
    "eval",
    "exec",
    "base64",
    "sudo",
    "token",
    "secret",
    "rm -rf",
    "cron",
    "systemctl",
    "launchctl",
    "scp",
    "rsync",
    "socket",
    "__import__",
    "importlib",
)

FAST_LINE_HINTS = DOC_SCAN_HINTS + (
    "post(",
    "requests",
    "urllib",
    "ftp",
    "webhook",
    "telegram",
    "discord",
    "sudo",
    "setuid",
    "setgid",
    "cap_set",
    "cron",
    "launchagent",
    "launchdaemon",
    "schtasks",
    "systemctl",
    "launchctl",
    "bashrc",
    "zshrc",
    "rc.local",
    "startup",
    "delete",
    "remove",
    "unlink",
    "truncate",
    "shred",
    "dd if=",
    "pip install",
    "npm install",
    "curl|",
    "wget|",
    "popen",
    "shell=true",
    "token",
    "secret",
    "password",
    "api_key",
    "credential",
    "private key",
    "id_rsa",
    "nohup",
    "tmux",
    "screen",
    "chattr",
    "ngrok",
    "frp",
    "nc ",
    "netcat",
    "powershell",
    "certutil",
    "regsvr32",
    "regsvr",
    "mshta",
    "psexec",
    "impacket",
)


def scan_text_by_line(
    content_lines: List[str],
    rules: Dict[str, Rule],
    line_filter=None,
) -> List[dict]:
    """逐行扫描文本内容，返回命中列表。"""
    findings = []
    for line_no, line in enumerate(content_lines, start=1):
        line_stripped = line.rstrip("\n\r")
        if line_filter and not line_filter(line_stripped, line_no):
            continue
        if not _has_fast_line_hint(line_stripped):
            continue
        for pattern_str, rule in rules.items():
            matches = rule.compiled.findall(line_stripped)
            for match in matches:
                findings.append({
                    "line_no": line_no,
                    "line_content": line_stripped,
                    "match": str(match),
                    "rule_description": rule.description,
                    "rule_category": rule.category_id,
                    "rule_severity": rule.severity,
                    "rule_pattern": pattern_str,
                })
    return findings


def _make_result(
    path: str,
    node_kind: str,
    source_kind: str = "filesystem",
    origin_path: Optional[str] = None,
    archive_path: Optional[str] = None,
    archive_member: Optional[str] = None,
) -> dict:
    """构造统一的扫描结果对象。"""
    return {
        "path": path,
        "origin_path": origin_path or path,
        "node_kind": node_kind,
        "source_kind": source_kind,
        "archive_path": archive_path,
        "archive_member": archive_member,
        "malicious": False,
        "findings": [],
        "error": None,
        "skipped": False,
        "skip_reason": None,
        "unsupported_archive": False,
    }


def _should_skip(file_path: str, target_kind: Optional[str] = None) -> tuple:
    """检查目标是否应跳过扫描。"""
    normalized = os.path.normpath(file_path)
    basename = os.path.basename(normalized)
    parts = set(normalized.split(os.sep))
    example_dirs = {"examples", "example", "samples", "fixtures", "skill_sandbox", "sample_codebase"}

    if basename in ("total_rules.py", "precise_rules.py", "apt_rules.py"):
        return True, "rule_file"
    if basename.endswith("_rules.py"):
        return True, "rule_file"
    if "tests" in parts or (basename.startswith("test_") and basename.endswith(".py")):
        return True, "test_fixture"
    if parts & example_dirs or basename.startswith(("example_", "sample_")):
        return True, "example_asset"
    if target_kind == "other":
        return True, "unsupported_target_kind"
    return False, None


def _is_doc_target(file_path: str, target_kind: Optional[str]) -> bool:
    """判断是否为文档类目标。"""
    ext = os.path.splitext(file_path)[1].lower()
    return target_kind in {"entry", "reference", "doc"} or ext in {".md", ".txt", ".rst", ".markdown"}


def _doc_line_filter(line: str, _: int) -> bool:
    """文档类目标只扫描高信号行，减少示例噪声。"""
    lower = line.lower()
    return any(token in lower for token in DOC_SCAN_HINTS)


def _has_fast_line_hint(line: str) -> bool:
    """先过滤明显安全的普通代码行，降低正则扫描成本。"""
    lower = line.lower()
    return any(token in lower for token in FAST_LINE_HINTS)


def _is_binary_bytes(data: bytes) -> bool:
    """基于采样判断二进制内容。"""
    if not data:
        return False
    if b"\x00" in data:
        return True

    text_chars = bytes(range(32, 127)) + b"\n\r\t\b\f"
    sample = data[:TEXT_SAMPLE_BYTES]
    non_text = sum(byte not in text_chars for byte in sample)
    return non_text / max(1, len(sample)) > 0.3


def _load_file_bytes(file_path: str) -> tuple:
    """读取文件内容并做大小限制。"""
    file_size = os.path.getsize(file_path)
    if file_size > MAX_SCAN_BYTES:
        return None, "file_too_large"

    with open(file_path, "rb") as f:
        data = f.read(MAX_SCAN_BYTES + 1)

    if len(data) > MAX_SCAN_BYTES:
        return None, "file_too_large"
    if _is_binary_bytes(data):
        return None, "binary_file"
    return data, None


def _scan_content(
    display_path: str,
    content: bytes,
    rules: Dict[str, Rule],
    node_kind: str,
    source_kind: str,
    origin_path: Optional[str] = None,
    archive_path: Optional[str] = None,
    archive_member: Optional[str] = None,
) -> dict:
    """扫描内存中的文本内容。"""
    result = _make_result(
        path=display_path,
        node_kind=node_kind,
        source_kind=source_kind,
        origin_path=origin_path or display_path,
        archive_path=archive_path,
        archive_member=archive_member,
    )

    try:
        text = content.decode("utf-8", errors="ignore")
        active_rules = select_rules_for_target(display_path, rules, target_kind=node_kind)
        line_filter = _doc_line_filter if _is_doc_target(display_path, node_kind) else None
        findings = scan_text_by_line(text.splitlines(), active_rules, line_filter=line_filter)
        if findings:
            result["malicious"] = True
            result["findings"] = findings
    except Exception as exc:
        result["error"] = str(exc)
    return result


def scan_file(file_path: str, rules: Dict[str, Rule], target_kind: Optional[str] = None) -> dict:
    """扫描单个文件。"""
    node_kind = target_kind or "script"
    result = _make_result(file_path, node_kind=node_kind)
    should_skip, reason = _should_skip(file_path, target_kind=node_kind)
    if should_skip:
        result["skipped"] = True
        result["skip_reason"] = reason
        return result

    try:
        data, load_error = _load_file_bytes(file_path)
        if load_error:
            result["skipped"] = True
            result["skip_reason"] = load_error
            return result
        return _scan_content(
            display_path=file_path,
            content=data,
            rules=rules,
            node_kind=node_kind,
            source_kind="filesystem",
            origin_path=file_path,
        )
    except Exception as exc:
        result["error"] = str(exc)
        return result


def scan_directory(dir_path: str, rules: Dict[str, Rule]) -> List[dict]:
    """递归扫描目录中的所有文件。"""
    results = []
    for root, _, files in os.walk(dir_path):
        for filename in files:
            full = os.path.join(root, filename)
            results.append(scan_file(full, rules, target_kind="script"))
    return results


def scan_archive(archive_path: str, rules: Dict[str, Rule]) -> List[dict]:
    """按实际归档格式扫描压缩包。"""
    if archive_path.endswith(".zip"):
        return scan_zip(archive_path, rules)
    if archive_path.endswith((".tar", ".tar.gz", ".tgz")):
        return scan_tar(archive_path, rules)

    result = _make_result(archive_path, node_kind="archive")
    result["unsupported_archive"] = True
    result["error"] = "未支持的压缩包格式"
    return [result]


def scan_zip(zip_path: str, rules: Dict[str, Rule]) -> List[dict]:
    """安全扫描 ZIP 压缩包内容。"""
    results = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                safe_name = _sanitize_archive_member(member.filename)
                if safe_name is None:
                    results.append(_archive_member_error(zip_path, member.filename, "非法归档路径"))
                    continue
                if member.file_size > MAX_SCAN_BYTES:
                    results.append(_archive_member_skip(zip_path, safe_name, "file_too_large"))
                    continue
                data = zf.read(member)
                if _is_binary_bytes(data):
                    results.append(_archive_member_skip(zip_path, safe_name, "binary_file"))
                    continue
                results.append(
                    _scan_content(
                        display_path=f"{zip_path}:{safe_name}",
                        content=data,
                        rules=rules,
                        node_kind="archive_member",
                        source_kind=ARCHIVE_SOURCE_KIND["zip"],
                        origin_path=zip_path,
                        archive_path=zip_path,
                        archive_member=safe_name,
                    )
                )
    except Exception as exc:
        result = _make_result(zip_path, node_kind="archive")
        result["error"] = f"ZIP 扫描失败: {exc}"
        results.append(result)
    return results


def scan_tar(archive_path: str, rules: Dict[str, Rule]) -> List[dict]:
    """安全扫描 tar/tar.gz/tgz 内容。"""
    results = []
    try:
        with tarfile.open(archive_path, "r:*") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                safe_name = _sanitize_archive_member(member.name)
                if safe_name is None:
                    results.append(_archive_member_error(archive_path, member.name, "非法归档路径"))
                    continue
                if member.size > MAX_SCAN_BYTES:
                    results.append(_archive_member_skip(archive_path, safe_name, "file_too_large"))
                    continue
                file_obj = tf.extractfile(member)
                if file_obj is None:
                    results.append(_archive_member_error(archive_path, safe_name, "归档成员读取失败"))
                    continue
                data = file_obj.read(MAX_SCAN_BYTES + 1)
                if len(data) > MAX_SCAN_BYTES:
                    results.append(_archive_member_skip(archive_path, safe_name, "file_too_large"))
                    continue
                if _is_binary_bytes(data):
                    results.append(_archive_member_skip(archive_path, safe_name, "binary_file"))
                    continue
                results.append(
                    _scan_content(
                        display_path=f"{archive_path}:{safe_name}",
                        content=data,
                        rules=rules,
                        node_kind="archive_member",
                        source_kind=ARCHIVE_SOURCE_KIND["tar"],
                        origin_path=archive_path,
                        archive_path=archive_path,
                        archive_member=safe_name,
                    )
                )
    except Exception as exc:
        result = _make_result(archive_path, node_kind="archive")
        result["error"] = f"TAR 扫描失败: {exc}"
        results.append(result)
    return results


def _archive_member_error(archive_path: str, member_name: str, message: str) -> dict:
    """构造归档成员错误结果。"""
    result = _make_result(
        path=f"{archive_path}:{member_name}",
        node_kind="archive_member",
        source_kind="archive",
        origin_path=archive_path,
        archive_path=archive_path,
        archive_member=member_name,
    )
    result["error"] = message
    return result


def _archive_member_skip(archive_path: str, member_name: str, reason: str) -> dict:
    """构造归档成员跳过结果。"""
    result = _make_result(
        path=f"{archive_path}:{member_name}",
        node_kind="archive_member",
        source_kind="archive",
        origin_path=archive_path,
        archive_path=archive_path,
        archive_member=member_name,
    )
    result["skipped"] = True
    result["skip_reason"] = reason
    return result


def _sanitize_archive_member(member_name: str) -> Optional[str]:
    """校验归档成员路径，阻止目录穿越。"""
    drive, _ = os.path.splitdrive(member_name)
    normalized = os.path.normpath(member_name)
    if drive:
        return None
    if os.path.isabs(normalized):
        return None
    if normalized.startswith("..") or f"..{os.sep}" in normalized:
        return None
    return normalized


def scan_skill_assets(asset_graph: dict, rules: Dict[str, Rule]) -> List[dict]:
    """基于资产图扫描 Skill 的所有有效目标。"""
    all_results = []
    seen_paths = set()
    node_kind = {node["path"]: node["kind"] for node in asset_graph.get("nodes", [])}

    def scan_once(path: str, kind: str):
        if not path or path in seen_paths:
            return
        seen_paths.add(path)
        if kind == "archive":
            all_results.extend(scan_archive(path, rules))
        else:
            all_results.append(scan_file(path, rules, target_kind=kind))

    entry_file = asset_graph.get("entry_file")
    if entry_file:
        scan_once(entry_file, "entry")

    for ref in asset_graph.get("references", []):
        scan_once(ref.get("path", ""), node_kind.get(ref.get("path", ""), "reference"))

    for group_name in ("scripts", "configs", "archives"):
        for node in asset_graph.get(group_name, []):
            scan_once(node["path"], node["kind"])

    for dep in asset_graph.get("indirect_deps", []):
        scan_once(dep.get("path", ""), node_kind.get(dep.get("path", ""), "indirect_dep"))

    return all_results
