#!/usr/bin/env python3
"""Generate readable Markdown reports from an AISC JSON report.

The script does not contact any translation service unless a translator is
selected explicitly. Translation input contains finding descriptions only;
matched source snippets and sensitive detection results are never sent to a
model API.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit


ITEM_CN = {
    "Hardcoded API Keys": "硬编码 API 密钥",
    "Hardcoded Access Keys": "硬编码访问密钥",
    "Hardcoded Secret Keys": "硬编码密钥",
    "Hardcoded Passwords": "硬编码密码",
    "Hardcoded Database Credentials": "硬编码数据库凭证",
    "Unsafe Code Injection": "不安全代码注入",
    "SQL Injection": "SQL 注入",
    "Security Feature Bypass": "安全功能绕过",
    "Outbound Data Transmission": "外发数据传输",
    "Unsafe Default Behavior": "不安全的默认行为",
    "Credential File Access": "凭证文件访问",
    "Permission Relaxation": "权限放宽",
    "Overly Permissive Permissions": "过度宽松权限",
    "Encoded Data Exfiltration": "编码数据外泄",
    "Insecure Tool Configuration": "不安全工具配置",
}

SENSITIVE_CN = {
    "aws_access_key": "AWS 访问密钥",
    "stripe_skpk": "Stripe 密钥对",
}

STATUS_CN = {
    "success": "已完成",
    "completed": "已完成",
    "failed": "失败",
    "init": "排队中",
    "running": "检测中",
    "timeout": "超时",
    "error": "异常",
}

SEVERITY_CN = {
    "critical": "严重",
    "high": "高危",
    "medium": "中危",
    "low": "低危",
}

CONFIG_SEVERITY = {
    "Hardcoded API Keys": "critical",
    "Hardcoded Access Keys": "critical",
    "Hardcoded Secret Keys": "critical",
    "Hardcoded Passwords": "critical",
    "Hardcoded Database Credentials": "critical",
    "Unsafe Code Injection": "critical",
    "SQL Injection": "critical",
    "Outbound Data Transmission": "critical",
    "Encoded Data Exfiltration": "critical",
    "Security Feature Bypass": "high",
    "Credential File Access": "high",
    "Unsafe Default Behavior": "high",
    "Permission Relaxation": "medium",
    "Overly Permissive Permissions": "medium",
    "Insecure Tool Configuration": "medium",
}

TRANSLATION_SYSTEM_PROMPT = """你是安全审计报告翻译器。将输入的安全风险描述翻译为简体中文。
只翻译描述，不要补充事实，不要改变技术名词、函数名、变量名、路径、数字或占位符。
必须返回 JSON 对象，格式为 {\"translations\": [\"...\"]}，数组长度必须与输入完全一致。"""

SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)((?:\$?[A-Za-z_][A-Za-z0-9_$.-]*?"
    r"(?:password|passwd|pwd|pass|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)"
    r"[A-Za-z0-9_$.-]*)\s*[:=]\s*)([\"']?)([^\"'\s,;]+)(\2)"
)
SECRET_JSON_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)([\"'](?:[A-Za-z_][A-Za-z0-9_$.-]*?"
    r"(?:password|passwd|pwd|pass|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)"
    r"[A-Za-z0-9_$.-]*)[\"']\s*:\s*)([\"'])([^\"']+)(\2)"
)
SECRET_QUOTED_PATTERN = re.compile(
    r"(?i)((?<![A-Za-z0-9_])(?:password|passwd|pwd|pass|secret|token|api[ _-]?key|access[ _-]?key)"
    r"[^\"'\n]{0,50}[\"'])([^\"']+)([\"'])"
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)\b(?:AKIA|ASIA)[0-9A-Z]{12,}\b"),
    re.compile(r"(?i)\b(?:ghp_|github_pat_|sk-|xox[baprs]-)[A-Za-z0-9_./+-]{8,}\b"),
    re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]{12,}"),
)


class ReportError(Exception):
    """Raised for invalid report input or an unusable translation response."""


class TranslationError(ReportError):
    """Raised when a model translation request cannot be completed."""


def _load_local_env() -> None:
    """Load literal KEY=VALUE pairs from the skill-local .env file.

    Existing shell variables win so CI and explicit shell configuration remain
    authoritative. This parser intentionally does not execute shell syntax.
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, encoding="utf-8") as env_file:
            lines = env_file.readlines()
    except OSError as exc:
        raise ReportError(f"读取本地 .env 失败：{exc}") from exc

    for line_number, line in enumerate(lines, 1):
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if value.startswith("export "):
            value = value[7:].lstrip()
        key, separator, raw_value = value.partition("=")
        key = key.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ReportError(f".env 第 {line_number} 行格式无效")
        raw_value = raw_value.strip()
        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in "\"'":
            raw_value = raw_value[1:-1]
        os.environ.setdefault(key, raw_value)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _config_value(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _object_list(value: Any) -> list[dict]:
    if isinstance(value, dict):
        return [value]
    return [item for item in _as_list(value) if isinstance(item, dict)]


def _extension_details(ext: dict, key: str) -> list[dict]:
    value = ext.get(key)
    if isinstance(value, dict):
        return _object_list(value.get("detail"))
    if isinstance(value, list):
        return _object_list(value)
    return []


def _first(mapping: dict, *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def _normalize_category(value: Any) -> str:
    raw = _as_text(value).strip()
    aliases = {
        "virus": "Virus",
        "病毒": "Virus",
        "sensitive": "Sensitive",
        "敏感": "Sensitive",
        "guardrail": "Guardrail",
        "防护": "Guardrail",
        "config": "Config",
        "configuration": "Config",
        "配置": "Config",
    }
    return aliases.get(raw.lower(), aliases.get(raw, raw or "Other"))


def _severity_for_guardrail(level: Any) -> str:
    level = _as_text(level).lower()
    return {
        "critical": "critical",
        "严重": "critical",
        "high": "high",
        "高": "high",
        "medium": "medium",
        "中": "medium",
        "low": "low",
        "低": "low",
    }.get(level, "medium")


def _finding(
    category: str,
    path: Any,
    item_name: Any = "",
    description: Any = "",
    content: Any = "",
    line: Any = "—",
    severity: str | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "category": category,
        "path": _as_text(path) or "未知文件",
        "line": _as_text(line) or "—",
        "item_name": _as_text(item_name) or category,
        "description": _as_text(description),
        "content": _as_text(content),
        "severity": severity or "low",
        "metadata": metadata or {},
    }


def _parse_virus_findings(path: Any, value: Any) -> list[dict]:
    details = value if isinstance(value, list) else [value]
    findings = []
    for detail in details:
        detail = detail if isinstance(detail, dict) else {"type": detail}
        virus_type = _first(detail, "type", "name", default="病毒风险")
        score = _first(detail, "score", "risk_score", default="")
        score_text = f"，风险评分 {score}" if score != "" else ""
        findings.append(
            _finding(
                "Virus",
                path,
                item_name=virus_type,
                description=f"检测引擎报告病毒或恶意行为：{virus_type}{score_text}。",
                content=_first(detail, "ext", "content", default=""),
                severity=(
                    "critical"
                    if isinstance(score, (int, float)) and score >= 80
                    else "high"
                ),
                metadata={"score": score},
            )
        )
    return findings


def _parse_guardrail_findings(path: Any, value: Any) -> list[dict]:
    guardrail = value if isinstance(value, dict) else {}
    details = _object_list(guardrail.get("detail"))
    findings = []
    for detail in details:
        if not isinstance(detail, dict):
            detail = {"result": detail}
        detail_type = _first(detail, "type", "label", default="Guardrail 风险")
        detail_level = _first(detail, "level", default="medium")
        suggestion = _first(detail, "suggestion", default=guardrail.get("suggestion", ""))
        results = _object_list(detail.get("result"))
        if not results:
            results = [detail]
        for result in results:
            result = result if isinstance(result, dict) else {"description": result}
            description = _first(result, "description", "desc", default="")
            if not description:
                description = f"检测到 {detail_type} 风险。"
            findings.append(
                _finding(
                    "Guardrail",
                    path,
                    item_name=_first(result, "label", default=detail_type),
                    description=description,
                    content="",
                    severity=_severity_for_guardrail(
                        _first(result, "level", default=detail_level)
                    ),
                    metadata={
                        "level": _first(result, "level", default=detail_level),
                        "suggestion": suggestion,
                        "confidence": result.get("confidence", ""),
                    },
                )
            )
    if not findings and guardrail:
        findings.append(
            _finding(
                "Guardrail",
                path,
                item_name="Guardrail 风险",
                description=f"检测引擎返回 Guardrail 风险，处置建议：{guardrail.get('suggestion', '人工复核')}。",
                severity="high",
            )
        )
    return findings


def parse_task(task: dict) -> list[dict]:
    """Parse all known AISC risk extensions from one sub-task."""
    findings = []
    for risk_info in _as_list(task.get("risk_info")):
        if not isinstance(risk_info, dict):
            continue
        path = _first(risk_info, "path", "file_path", default="未知文件")
        ext = risk_info.get("ext") if isinstance(risk_info.get("ext"), dict) else {}
        finding_count = len(findings)

        for detail in _extension_details(ext, "config"):
            raw_item = _first(detail, "item_name", "name", default="配置风险")
            findings.append(
                _finding(
                    "Config",
                    path,
                    item_name=ITEM_CN.get(_as_text(raw_item), _as_text(raw_item)),
                    description=_first(detail, "description", "desc", default=""),
                    content=_first(detail, "content", "match", default=""),
                    line=_first(detail, "line", "line_number", default="—"),
                    severity=CONFIG_SEVERITY.get(_as_text(raw_item), "low"),
                )
            )

        for detail in _extension_details(ext, "sensitive"):
            raw_desc = _first(detail, "desc", "name", default="敏感信息")
            findings.append(
                _finding(
                    "Sensitive",
                    path,
                    item_name="敏感信息",
                    description=SENSITIVE_CN.get(_as_text(raw_desc), _as_text(raw_desc)),
                    content="[已脱敏]",
                    severity="critical",
                    metadata={"sensitive_type": _as_text(raw_desc)},
                )
            )

        if ext.get("virus"):
            findings.extend(_parse_virus_findings(path, ext.get("virus")))
        if ext.get("guardrail"):
            findings.extend(_parse_guardrail_findings(path, ext.get("guardrail")))

        if len(findings) == finding_count:
            category = _normalize_category(risk_info.get("result_type"))
            findings.append(
                _finding(
                    category,
                    path,
                    description=f"检测引擎返回 {category} 风险，但未提供可展开的明细字段。",
                    severity="high" if category in ("Virus", "Guardrail") else "low",
                )
            )
    return findings


def _extract_tasks(data: dict) -> list[dict]:
    """Accept single-batch, run, and multi-batch wrapper report shapes."""
    candidates = []
    if isinstance(data.get("tasks"), list):
        candidates.append(data["tasks"])
    poll = data.get("poll")
    if isinstance(poll, dict) and isinstance(poll.get("tasks"), list):
        candidates.append(poll["tasks"])
    for batch in _as_list(data.get("batches")):
        if not isinstance(batch, dict):
            continue
        batch_poll = batch.get("poll")
        if isinstance(batch_poll, dict) and isinstance(batch_poll.get("tasks"), list):
            candidates.append(batch_poll["tasks"])

    seen = set()
    result = []
    for candidate in candidates:
        for task in candidate:
            if not isinstance(task, dict):
                continue
            identity = (
                _as_text(task.get("id")),
                _as_text(task.get("file_hash")),
                _as_text(task.get("target")),
            )
            if not any(identity):
                identity = ("anonymous", len(result))
            if identity in seen:
                continue
            seen.add(identity)
            result.append(task)
    return result


def _iter_submit_results(data: dict) -> Iterable[dict]:
    submit = data.get("submit")
    if isinstance(submit, dict):
        yield from _as_list(submit.get("upload_results"))
        for batch in _as_list(submit.get("batches")):
            if isinstance(batch, dict):
                yield from _as_list(batch.get("upload_results"))
    for batch in _as_list(data.get("batches")):
        if isinstance(batch, dict):
            batch_submit = batch.get("submit")
            if isinstance(batch_submit, dict):
                yield from _as_list(batch_submit.get("upload_results"))


def _upload_map(data: dict) -> dict[str, str]:
    result = {}
    for upload in _iter_submit_results(data):
        if not isinstance(upload, dict):
            continue
        file_hash = _as_text(upload.get("file_hash"))
        file_name = _as_text(upload.get("file_name"))
        if file_hash and file_name:
            result[file_hash] = file_name
    return result


def _root_task_id(data: dict) -> str:
    value = _first(data, "root_task_id", "rootTaskId", default="")
    if value:
        return _as_text(value)
    root_ids = _as_list(data.get("root_task_ids"))
    return ", ".join(_as_text(item) for item in root_ids if item)


def _redact_text(value: Any) -> str:
    text = _as_text(value)
    text = SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[已脱敏]{match.group(4)}",
        text,
    )
    text = SECRET_JSON_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[已脱敏]{match.group(4)}",
        text,
    )
    text = SECRET_QUOTED_PATTERN.sub(
        lambda match: f"{match.group(1)}[已脱敏]{match.group(3)}",
        text,
    )
    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.groups:
            text = pattern.sub(lambda match: f"{match.group(1)}[已脱敏]", text)
        else:
            text = pattern.sub("[已脱敏]", text)
    return text


def _md_cell(value: Any, limit: int = 180) -> str:
    text = _redact_text(value).replace("|", r"\|").replace("\r", " ").replace("\n", " ")
    return text[:limit] if text else "—"


def _code_cell(value: Any, show_content: bool) -> str:
    if not show_content:
        return "[已隐藏]"
    text = _redact_text(value).replace("`", "\\`").replace("\r", " ").replace("\n", " ")
    return text[:180] if text else "—"


def _severity_text(severity: str) -> str:
    return SEVERITY_CN.get(severity, "低危")


def _recommendations(findings: list[dict]) -> list[str]:
    categories = {finding["category"] for finding in findings}
    recommendations = []
    if "Virus" in categories:
        recommendations.append("立即阻断并隔离命中文件，确认来源和完整性后再决定是否替换。")
    if "Sensitive" in categories:
        recommendations.append("删除报告涉及的敏感信息，并立即轮换已经暴露的凭据或 Token，清理后重新检测。")
    if "Guardrail" in categories:
        recommendations.append("检查相关 prompt 和执行边界，删除 prompt injection、越权操作或不必要的外部 URL 处理。")
    if "Config" in categories:
        recommendations.append("按命中的配置项收紧权限、移除危险执行方式，并根据报告中的行号逐项整改。")
    return recommendations


def _build_issues(findings: list[dict]) -> str:
    if not findings:
        return ""
    lines = ["## 整改建议", ""]
    for index, recommendation in enumerate(_recommendations(findings), 1):
        lines.append(f"{index}. {recommendation}")
    if len(lines) == 2:
        lines.append("1. 请安全工程师结合原始报告人工复核该风险。")
    return "\n".join(lines) + "\n"


def _task_file_name(
    task: dict,
    upload_map: dict[str, str],
    index: int,
    file_names: dict[str, str],
) -> tuple[str, bool]:
    file_hash = _as_text(task.get("file_hash"))
    task_id = _as_text(task.get("id"))
    target = _as_text(task.get("target"))
    mapped_name = next(
        (
            file_names[key]
            for key in (task_id, file_hash, target, str(index))
            if key and key in file_names
        ),
        "",
    )
    name = (
        _as_text(task.get("file_name"))
        or upload_map.get(file_hash)
        or mapped_name
    )
    inferred = False
    if not name:
        name = f"skill-task-{task_id}" if task_id else f"skill-{index:02d}"
        inferred = True
    name = os.path.basename(name.rstrip("/")) or "skill-file"
    if name.endswith(".zip"):
        name = name[:-4]
    return name, inferred


def _parse_file_names(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ReportError("--file-names 必须是 JSON 数组或 JSON 对象") from exc
    if isinstance(parsed, list):
        return {str(index): _as_text(name) for index, name in enumerate(parsed, 1) if name}
    if isinstance(parsed, dict):
        return {
            _as_text(key): _as_text(name)
            for key, name in parsed.items()
            if _as_text(key) and name
        }
    raise ReportError("--file-names 必须是 JSON 数组或 JSON 对象")


def build_one_report(
    task: dict,
    file_name: str,
    findings: list[dict],
    root_id: str,
    report_status: str,
    show_content: bool,
) -> str:
    task_status = _as_text(task.get("task_status")) or "unknown"
    file_hash = _as_text(task.get("file_hash")) or "—"
    task_id = _as_text(task.get("id")) or "—"
    risk_total = len(findings)
    level_count = Counter(finding["severity"] for finding in findings)
    category_count = Counter(finding["category"] for finding in findings)
    risk_files = len({finding["path"] for finding in findings})
    status_text = STATUS_CN.get(task_status.lower(), task_status)
    poll_text = STATUS_CN.get(report_status.lower(), report_status or "—")

    if task_status.lower() in {"failed", "error", "timeout"}:
        verdict = "检测失败"
        verdict_desc = "AISC 子任务未成功完成，当前报告不包含有效的安全结论。"
    elif not findings:
        verdict = "未发现风险"
        verdict_desc = "AISC 未返回风险发现；这不等于对 Skill 绝对安全的保证。"
    elif level_count["critical"] or level_count["high"]:
        verdict = "不通过"
        verdict_desc = "发现严重或高危风险，整改并重新检测前不建议准入。"
    else:
        verdict = "有条件通过"
        verdict_desc = "发现中低危风险，需完成安全复核或整改后再准入。"

    category_rows = "\n".join(
        f"| {category} | {count} | {count / risk_total * 100:.1f}% |"
        for category, count in category_count.most_common()
    ) or "| — | 0 | 0.0% |"

    detail_blocks = []
    by_path: dict[str, list[dict]] = {}
    for finding in findings:
        by_path.setdefault(finding["path"], []).append(finding)
    for path, path_findings in by_path.items():
        detail_blocks.extend(
            [
                f"### `{_md_cell(path, 240)}`",
                "",
                "| 行号 | 类别 | 风险类型 | 等级 | 风险描述 | 代码片段 |",
                "|---:|---|---|---|---|---|",
            ]
        )
        for finding in path_findings:
            detail_blocks.append(
                "| {} | {} | {} | {} | {} | `{}` |".format(
                    _md_cell(finding["line"], 24),
                    _md_cell(finding["category"], 30),
                    _md_cell(finding["item_name"], 50),
                    _severity_text(finding["severity"]),
                    _md_cell(finding["description"], 180),
                    _code_cell(finding["content"], show_content),
                )
            )
        detail_blocks.append("")
    detail_text = "\n".join(detail_blocks) or "> 未返回逐文件风险明细。"

    issues = _build_issues(findings)
    return f"""# 阿里云 AISC Skill 安全检测报告

---

| 项目 | 内容 |
|---|---|
| 根任务 ID | `{_md_cell(root_id, 120)}` |
| 子任务 ID | `{_md_cell(task_id, 120)}` |
| 生成时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| 轮询状态 | {poll_text} |

## 一、基本信息

| 项目 | 内容 |
|---|---|
| Skill 文件 | `{_md_cell(file_name, 240)}` |
| SHA256 | `{_md_cell(file_hash, 120)}` |
| 子任务状态 | {status_text} |

## 二、检测结论

| 项目 | 内容 |
|---|---|
| 判定结果 | **{verdict}** |
| 判定说明 | {verdict_desc} |

## 三、检测统计

| 指标 | 数值 |
|---|---:|
| 风险文件数 | {risk_files} |
| 风险项总数 | {risk_total} |
| 严重 | {level_count['critical']} |
| 高危 | {level_count['high']} |
| 中危 | {level_count['medium']} |
| 低危 | {level_count['low']} |

## 四、风险类型分布

| 风险类别 | 检出次数 | 占比 |
|---|---:|---:|
{category_rows}

## 五、逐文件风险详情

{detail_text}

{issues}
---

*本报告由本地 `generate_report.py` 基于阿里云 AISC 原始 JSON 生成；原始报告中的敏感检测值默认不写入本报告。*
"""


def _load_report(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as report_file:
            data = json.load(report_file)
    except FileNotFoundError as exc:
        raise ReportError(f"找不到 JSON 报告：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ReportError(f"JSON 报告格式无效：第 {exc.lineno} 行，第 {exc.colno} 列") from exc
    if not isinstance(data, dict):
        raise ReportError("JSON 报告顶层必须是对象")
    return data


def _json_from_text(text: str) -> Any:
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        cleaned = match.group(1)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise TranslationError("模型返回的翻译结果不是有效 JSON") from exc


def _translation_list(content: Any, expected: int) -> list[str]:
    if isinstance(content, str):
        content = _json_from_text(content)
    if isinstance(content, dict):
        content = content.get("translations", content.get("translation"))
    if not isinstance(content, list) or len(content) != expected:
        raise TranslationError(
            f"模型返回的 translations 数量不正确，期望 {expected} 条"
        )
    if not all(isinstance(item, str) for item in content):
        raise TranslationError("模型返回的 translations 必须全部是字符串")
    return content


def _post_json(url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body)
            message = detail.get("error", detail) if isinstance(detail, dict) else detail
        except json.JSONDecodeError:
            message = body[:300]
        raise TranslationError(f"翻译 API 返回 HTTP {exc.code}: {_as_text(message)}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TranslationError(f"翻译 API 请求失败：{exc}") from exc
    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise TranslationError("翻译 API 返回的内容不是有效 JSON") from exc
    if not isinstance(result, dict):
        raise TranslationError("翻译 API 返回的顶层 JSON 必须是对象")
    return result


def _normalize_api_url(provider: str, url: str) -> str:
    """Accept either a provider base URL or its full HTTP endpoint."""
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ReportError("翻译 API 地址必须是完整的 http(s) URL")
    path = parts.path.rstrip("/")
    endpoint = "/messages" if provider == "anthropic" else "/chat/completions"
    if not path.endswith(endpoint):
        path = f"{path}{endpoint}"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def _infer_provider(url: str | None) -> str:
    if url:
        parts = urlsplit(url.strip())
        if parts.path.rstrip("/").endswith("/messages") or "anthropic" in parts.netloc.lower():
            return "anthropic"
    return "openai"


class ModelTranslator:
    """Translate descriptions through an OpenAI or Anthropic style API."""

    def __init__(
        self,
        provider: str,
        url: str,
        api_key: str,
        model: str,
        api_key_header: str | None,
        api_key_prefix: str,
        timeout: float,
        batch_size: int,
    ):
        self.provider = provider
        self.url = url
        self.api_key = api_key
        self.model = model
        self.api_key_header = api_key_header
        self.api_key_prefix = api_key_prefix
        self.timeout = timeout
        self.batch_size = batch_size
        self.cache: dict[str, str] = {}

    def _headers(self) -> dict[str, str]:
        if self.provider == "anthropic":
            header = self.api_key_header or "x-api-key"
            value = self.api_key if not self.api_key_prefix else f"{self.api_key_prefix} {self.api_key}"
            return {header: value, "anthropic-version": "2023-06-01"}
        header = self.api_key_header or "Authorization"
        value = self.api_key if not self.api_key_prefix else f"{self.api_key_prefix} {self.api_key}"
        return {header: value}

    def _payload(self, texts: list[str]) -> dict:
        user_prompt = json.dumps(
            {"source_language": "English", "target_language": "Simplified Chinese", "texts": texts},
            ensure_ascii=False,
        )
        if self.provider == "anthropic":
            return {
                "model": self.model,
                "max_tokens": max(512, len(texts) * 160),
                "system": TRANSLATION_SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}],
            }
        return {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }

    def _response_content(self, response: dict) -> Any:
        if self.provider == "anthropic":
            blocks = _as_list(response.get("content"))
            return "\n".join(_as_text(block.get("text")) for block in blocks if isinstance(block, dict))
        choices = _as_list(response.get("choices"))
        if not choices or not isinstance(choices[0], dict):
            raise TranslationError("OpenAI-compatible API 未返回 choices")
        message = choices[0].get("message") or {}
        content = message.get("content", "") if isinstance(message, dict) else ""
        if isinstance(content, list):
            return "\n".join(
                _as_text(block.get("text"))
                for block in content
                if isinstance(block, dict) and block.get("text") is not None
            )
        return content

    def translate_many(self, texts: list[str]) -> dict[str, str]:
        missing = [text for text in texts if text not in self.cache]
        for offset in range(0, len(missing), self.batch_size):
            batch = missing[offset:offset + self.batch_size]
            response = _post_json(self.url, self._headers(), self._payload(batch), self.timeout)
            translated = _translation_list(self._response_content(response), len(batch))
            self.cache.update(zip(batch, translated))
        return {text: self.cache.get(text, text) for text in texts}


def _build_translator(args: argparse.Namespace) -> ModelTranslator | None:
    if args.translator == "none":
        return None
    if not args.model:
        raise ReportError("选择模型翻译时必须提供 --model")

    defaults = {
        "openai": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY", "openai"),
        "anthropic": ("https://api.anthropic.com/v1/messages", "ANTHROPIC_API_KEY", "anthropic"),
    }
    if args.translator == "auto":
        provider = _infer_provider(args.api_url)
        default_url, default_env, _ = defaults[provider]
        url = args.api_url or default_url
        api_key_env = args.api_key_env or default_env
    elif args.translator in defaults:
        default_url, default_env, provider = defaults[args.translator]
        url = args.api_url or default_url
        api_key_env = args.api_key_env or default_env
    else:
        if not args.api_url:
            raise ReportError("custom 翻译器必须提供 --api-url")
        url = args.api_url
        api_key_env = args.api_key_env or "MODEL_API_KEY"
        provider = args.api_format or _infer_provider(url)

    api_key = _config_value("API_KEY") or os.environ.get(api_key_env)
    if not api_key:
        raise ReportError(
            f"未找到翻译 API 密钥，请在运行环境配置环境变量 {api_key_env}；不要把密钥写入命令行或报告。"
        )
    return ModelTranslator(
        provider=provider,
        url=_normalize_api_url(provider, url),
        api_key=api_key,
        model=args.model,
        api_key_header=args.api_key_header,
        api_key_prefix=(
            args.api_key_prefix
            if args.api_key_prefix is not None
            else ("Bearer" if provider == "openai" else "")
        ),
        timeout=args.api_timeout,
        batch_size=args.translation_batch_size,
    )


def _translate_findings(findings: list[dict], translator: ModelTranslator | None) -> None:
    if translator is None:
        return
    description_map = {
        finding["description"]: _redact_text(finding["description"])
        for finding in findings
        if finding.get("description") and re.search(r"[A-Za-z]", finding["description"])
    }
    descriptions = sorted(set(description_map.values()))
    if not descriptions:
        return
    translations = translator.translate_many(descriptions)
    for finding in findings:
        description = finding.get("description", "")
        safe_description = description_map.get(description)
        if safe_description in translations:
            finding["description"] = translations[safe_description]


def _safe_output_path(out_dir: str, file_name: str, task: dict, used: set[str]) -> str:
    safe_name = re.sub(r"[^0-9A-Za-z_.\u4e00-\u9fff-]+", "_", file_name).strip("._") or "skill-file"
    candidate = os.path.join(out_dir, f"{safe_name}_阿里云AISC检测报告.md")
    if candidate in used:
        suffix = _as_text(task.get("id")) or _as_text(task.get("file_hash"))[:12] or "duplicate"
        candidate = os.path.join(out_dir, f"{safe_name}_{suffix}_阿里云AISC检测报告.md")
    used.add(candidate)
    return candidate


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="读取 AISC check-report.json，生成可读的 Markdown 安全检测报告。"
    )
    parser.add_argument("json_path", help="AISC 原始 JSON 报告路径")
    parser.add_argument("-o", "--output-dir", default=None, help="报告输出目录，默认与 JSON 同目录")
    parser.add_argument(
        "--file-names",
        help="补充原始报告缺失的文件名，传 JSON 数组（按任务顺序）或 JSON 对象（按 task id/file_hash/target 映射）",
    )
    simple_configured = bool(_config_value("MODEL", "API_URL", "API_KEY"))
    configured_translator = os.getenv("AISCC_REPORT_TRANSLATOR")
    parser.add_argument(
        "--translator",
        choices=("none", "auto", "openai", "anthropic", "custom"),
        default=("auto" if simple_configured else (configured_translator or "none")),
        help="描述翻译方式，默认读取 .env 中的 AISCC_REPORT_TRANSLATOR",
    )
    parser.add_argument(
        "--model",
        default=_config_value("MODEL", "AISCC_REPORT_MODEL"),
        help="模型名称，例如 gpt-4o-mini 或 claude-3-5-haiku-latest",
    )
    parser.add_argument(
        "--api-url",
        default=_config_value("API_URL", "AISCC_REPORT_API_URL"),
        help="自定义翻译 API 地址；custom 必填",
    )
    parser.add_argument(
        "--api-key-env",
        default=os.getenv("AISCC_REPORT_API_KEY_ENV") or None,
        help="API 密钥所在环境变量名",
    )
    parser.add_argument(
        "--api-format",
        choices=("openai", "anthropic"),
        default=_config_value("API_FORMAT", "AISCC_REPORT_API_FORMAT"),
        help="custom API 的请求/响应格式，默认 OpenAI-compatible",
    )
    parser.add_argument(
        "--api-key-header",
        default=os.getenv("AISCC_REPORT_API_KEY_HEADER") or None,
        help="自定义鉴权 Header，默认按接口类型选择",
    )
    parser.add_argument(
        "--api-key-prefix",
        default=os.getenv("AISCC_REPORT_API_KEY_PREFIX"),
        help="鉴权值前缀；传空字符串表示不加前缀",
    )
    parser.add_argument("--api-timeout", type=float, default=45, help="翻译 API 超时时间（秒）")
    parser.add_argument("--translation-batch-size", type=int, default=20, help="单次翻译的描述数量")
    parser.add_argument(
        "--translation-error",
        choices=("keep-original", "fail"),
        default="keep-original",
        help="翻译失败时保留英文原文或终止生成，默认保留原文",
    )
    parser.add_argument(
        "--hide-content",
        action="store_true",
        help="隐藏风险代码片段；敏感信息检测结果始终脱敏",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        _load_local_env()
    except ReportError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    args = _build_parser().parse_args(argv)
    if args.translation_batch_size < 1:
        print("错误：--translation-batch-size 必须大于 0", file=sys.stderr)
        return 2

    try:
        data = _load_report(args.json_path)
        translator = _build_translator(args)
        tasks = _extract_tasks(data)
        if not tasks:
            raise ReportError("报告中没有找到 tasks；请确认输入的是 AISC submit/poll/run JSON 报告")

        report_status = _as_text((data.get("poll") or {}).get("status")) if isinstance(data.get("poll"), dict) else ""
        report_status = report_status or _as_text(data.get("status")) or "unknown"
        root_id = _root_task_id(data)
        upload_map = _upload_map(data)
        file_names = _parse_file_names(args.file_names)
        parsed = []
        all_findings = []
        inferred_names = 0
        for index, task in enumerate(tasks, 1):
            findings = parse_task(task)
            file_name, inferred = _task_file_name(task, upload_map, index, file_names)
            inferred_names += int(inferred)
            parsed.append((task, file_name, findings))
            all_findings.extend(findings)

        if inferred_names:
            print(
                f"警告：{inferred_names} 个任务缺少原始 file_name，已使用任务 ID 生成文件名；"
                "如需恢复真实名称，请使用 --file-names 提供映射。",
                file=sys.stderr,
            )

        if translator:
            print(f"翻译中：{len({f['description'] for f in all_findings if f.get('description')})} 条描述", file=sys.stderr)
            try:
                _translate_findings(all_findings, translator)
            except TranslationError as exc:
                if args.translation_error == "fail":
                    raise
                print(f"警告：AI 翻译失败，保留原始描述：{exc}", file=sys.stderr)

        output_dir = args.output_dir or os.path.dirname(os.path.abspath(args.json_path)) or "."
        os.makedirs(output_dir, exist_ok=True)
        used_paths: set[str] = set()
        for task, file_name, findings in parsed:
            output_path = _safe_output_path(output_dir, file_name, task, used_paths)
            report = build_one_report(
                task,
                file_name,
                findings,
                root_id,
                report_status,
                show_content=not args.hide_content,
            )
            with open(output_path, "w", encoding="utf-8") as report_file:
                report_file.write(report)
            print(output_path)
        print(f"完成，共生成 {len(parsed)} 份报告。")
        return 0
    except ReportError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"错误：写入报告失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
