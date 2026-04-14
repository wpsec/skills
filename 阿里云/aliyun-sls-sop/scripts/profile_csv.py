#!/usr/bin/env python3
"""分析 CSV/CSV.GZ 日志样本，并输出可用于生成文档的关键信号。"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import ipaddress
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, TextIO


TIME_NAME_RE = re.compile(r"(?:^|[_-])(time|date|timestamp|start|end)(?:$|[_-])", re.I)
IP_NAME_RE = re.compile(r"(?:ip|addr|host)$", re.I)
PORT_NAME_RE = re.compile(r"port", re.I)
STATUS_NAME_RE = re.compile(r"(status|error|result|fail|code)", re.I)
ACTION_NAME_RE = re.compile(r"(action|operation|method|event|op)", re.I)
ID_NAME_RE = re.compile(
    r"(?:^|[_-])(id|uid|guid|requestid|request_id|instance|vm|eni|vpc|vswitch)(?:$|[_-])",
    re.I,
)
VOLUME_NAME_RE = re.compile(r"(bytes|packets|size|length|latency|duration|cost|rows)", re.I)
OBJECT_HINT_RE = re.compile(r"(bucket|object|request_uri|host|domain|device|policy|sql|db|user)", re.I)

MAX_TRACKED_UNIQUES = 2000

ENV_ALIASES = {
    "prod": ("prod", "prd", "production", "online"),
    "pre": ("pre", "staging", "stage", "gray"),
    "uat": ("uat",),
    "sit": ("sit",),
    "test": ("test", "qa"),
    "dev": ("dev", "daily", "local"),
}

ENV_DISPLAY = {
    "prod": "PROD",
    "pre": "PRE",
    "uat": "UAT",
    "sit": "SIT",
    "test": "TEST",
    "dev": "DEV",
    "common": "COMMON",
}

FAMILY_SPECS = {
    "network_flow": {
        "label": "网络流日志",
        "module_id": "network_flow",
        "portable_naming": {
            "module_dir": "network_flow_log",
            "datasource_prefix": "network_flow",
            "analysis_file": "network_flow_analysis_sop.yaml",
            "report_file": "network_flow_report_template.md",
        },
        "reference_naming": {
            "module_dir": "vpc_log",
            "datasource_prefix": "vpc",
            "analysis_file": "vpc_flow_analysis_sop.yaml",
            "report_file": "vpc_flow_report_template.md",
        },
        "source_alias_suffix": "NETWORK-FLOW",
        "dimensions": [
            "安全类：暴露面、异常来源、敏感端口、横向移动",
            "运维类：REJECT 比率、流量波动、连通性异常",
            "治理类：拓扑、访问关系、白名单沉淀",
        ],
        "prompts": [
            "分析最近24小时的网络流日志",
            "排查敏感端口访问和异常来源",
            "生成网络流日志的标准 SOP",
        ],
        "lead": "基线 -> 异常流量 -> 分级响应 -> 根因排查 -> 闭环",
    },
    "object_storage_access": {
        "label": "对象存储访问日志",
        "module_id": "object_storage_access",
        "portable_naming": {
            "module_dir": "object_storage_access_log",
            "datasource_prefix": "object_storage_access",
            "analysis_file": "object_storage_access_analysis_sop.yaml",
            "report_file": "object_storage_access_report_template.md",
        },
        "reference_naming": {
            "module_dir": "oss_log",
            "datasource_prefix": "oss",
            "analysis_file": "oss_access_analysis_sop.yaml",
            "report_file": "oss_access_report_template.md",
        },
        "source_alias_suffix": "OBJECT-STORAGE-ACCESS",
        "dimensions": [
            "安全类：异常下载、越权访问、可疑导出、配置变更",
            "运维类：失败高峰、链路抖动、延迟异常",
            "业务类：对象覆盖、目录错写、上传异常",
        ],
        "prompts": [
            "分析最近24小时的 OSS 访问日志",
            "排查异常下载或对象覆盖",
            "生成 OSS 访问日志的标准 SOP",
        ],
        "lead": "基线访问 -> 异常读写 -> 分级响应 -> 归因 -> 闭环",
    },
    "database_audit": {
        "label": "数据库审计日志",
        "module_id": "database_audit",
        "portable_naming": {
            "module_dir": "database_audit_log",
            "datasource_prefix": "database_audit",
            "analysis_file": "database_audit_analysis_sop.yaml",
            "report_file": "database_audit_report_template.md",
        },
        "reference_naming": {
            "module_dir": "rds_log",
            "datasource_prefix": "rds",
            "analysis_file": "rds_audit_analysis_sop.yaml",
            "report_file": "rds_audit_report_template.md",
        },
        "source_alias_suffix": "DATABASE-AUDIT",
        "dimensions": [
            "安全类：越权、脱库、敏感 SQL、破坏性操作",
            "运维类：慢 SQL、失败重试、发布回归",
            "业务类：事务异常、批量写入异常、链路回溯",
        ],
        "prompts": [
            "分析最近24小时的数据库审计日志",
            "排查异常 SQL 或失败高峰",
            "生成数据库审计日志的标准 SOP",
        ],
        "lead": "基线 SQL -> 异常操作 -> 分级响应 -> 根因排查 -> 闭环",
    },
    "waf_or_edge_security": {
        "label": "WAF 或边界安全日志",
        "module_id": "waf_or_edge_security",
        "portable_naming": {
            "module_dir": "waf_security_log",
            "datasource_prefix": "waf_security",
            "analysis_file": "waf_security_analysis_sop.yaml",
            "report_file": "waf_security_report_template.md",
        },
        "reference_naming": {
            "module_dir": "waf_log",
            "datasource_prefix": "waf",
            "analysis_file": "waf_attack_analysis_sop.yaml",
            "report_file": "waf_attack_report_template.md",
        },
        "source_alias_suffix": "WAF-ACCESS",
        "dimensions": [
            "安全类：攻击趋势、高危命中、误报与真实拦截",
            "运维类：规则漂移、拦截激增、日志完整性",
            "业务类：误拦截和入口影响",
        ],
        "prompts": [
            "分析最近24小时的 WAF 日志",
            "排查攻击类型和高危来源",
            "生成 WAF 日志的标准 SOP",
        ],
        "lead": "攻击趋势 -> 高危命中 -> 处置 -> 溯源 -> 规则优化",
    },
    "network_device_or_firewall": {
        "label": "网络设备或防火墙日志",
        "module_id": "network_device_or_firewall",
        "portable_naming": {
            "module_dir": "network_device_log",
            "datasource_prefix": "network_device",
            "analysis_file": "network_device_analysis_sop.yaml",
            "report_file": "network_device_report_template.md",
        },
        "reference_naming": {
            "module_dir": "net_log",
            "datasource_prefix": "net",
            "analysis_file": "net_device_analysis_sop.yaml",
            "report_file": "net_device_report_template.md",
        },
        "source_alias_suffix": "NETWORK-DEVICE",
        "dimensions": [
            "安全类：策略命中、异常访问、暴露面",
            "运维类：设备抖动、策略漂移、链路异常",
            "治理类：策略优化、白名单和例外梳理",
        ],
        "prompts": [
            "分析最近24小时的网络设备日志",
            "排查策略命中和异常访问",
            "生成网络设备日志的标准 SOP",
        ],
        "lead": "访问策略 -> 异常命中 -> 处置 -> 策略核查 -> 闭环",
    },
    "generic_structured_log": {
        "label": "通用结构化日志",
        "module_id": "generic_structured_log",
        "portable_naming": {
            "module_dir": "structured_log",
            "datasource_prefix": "structured",
            "analysis_file": "structured_analysis_sop.yaml",
            "report_file": "structured_report_template.md",
        },
        "reference_naming": {
            "module_dir": "sls_log",
            "datasource_prefix": "sls",
            "analysis_file": "sls_generic_analysis_sop.yaml",
            "report_file": "sls_generic_report_template.md",
        },
        "source_alias_suffix": "SLS-GENERIC",
        "dimensions": [
            "通用：字段建模、异常识别、运行时解析",
            "运维：失败、高频、体量、稳定性",
            "安全：来源、结果、敏感对象和升级建议",
        ],
        "prompts": [
            "根据这份结构化日志生成一套通用 SOP",
            "补齐 README、overview、datasource、analysis_sop、report_template",
        ],
        "lead": "字段建模 -> 异常识别 -> 处置建议 -> 后续补充",
    },
}

NAMING_STYLE_LABELS = {
    "portable": "便携默认命名",
    "repo_reference": "仓库参考命名",
}

TYPE_LABELS = {
    "time": "时间",
    "ip": "IP",
    "port": "端口",
    "integer": "整数",
    "number": "数值",
    "status": "状态",
    "action": "动作",
    "identifier": "标识",
    "metric": "指标",
    "string": "文本",
}

CATEGORY_LABELS = {
    "time_fields": "时间字段",
    "ip_fields": "IP 字段",
    "port_fields": "端口字段",
    "status_fields": "状态字段",
    "action_fields": "动作字段",
    "identifier_fields": "标识字段",
    "metric_fields": "指标字段",
}


def open_text(path: Path) -> TextIO:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("r", encoding="utf-8-sig", newline="")


def normalize_value(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^A-Za-z0-9]+", text.lower()) if token]


def normalize_environment(raw: str | None) -> str | None:
    if not raw:
        return None
    lowered = raw.lower()
    tokens = tokenize(lowered) or [lowered]
    for token in tokens:
        for canonical, aliases in ENV_ALIASES.items():
            if token in aliases:
                return canonical
    for canonical, aliases in ENV_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return canonical
    return None


def infer_environment_from_path(path: Path) -> tuple[str | None, str]:
    for part in [path.name, path.stem, *path.parts]:
        env = normalize_environment(part)
        if env:
            return env, "path"
    return None, "unknown"


def parse_timestamp(value: str) -> dt.datetime | None:
    value = value.strip()
    if not value:
        return None

    epoch_match = re.fullmatch(r"\d{10,13}", value)
    if epoch_match:
        scale = 1000 if len(value) == 13 else 1
        try:
            return dt.datetime.utcfromtimestamp(int(value) / scale)
        except (OverflowError, ValueError):
            return None

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
    )
    for fmt in formats:
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def looks_like_ip(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def looks_like_int(value: str) -> bool:
    return bool(re.fullmatch(r"-?\d+", value.strip()))


def looks_like_float(value: str) -> bool:
    return bool(re.fullmatch(r"-?(?:\d+\.\d+|\d+)", value.strip()))


def sniff_dialect(path: Path) -> csv.Dialect:
    with open_text(path) as handle:
        sample = handle.read(8192)
    try:
        return csv.Sniffer().sniff(sample)
    except csv.Error:
        return csv.excel


@dataclass
class FieldStats:
    name: str
    non_empty: int = 0
    parsed_time: int = 0
    parsed_ip: int = 0
    parsed_int: int = 0
    parsed_float: int = 0
    counter: Counter = field(default_factory=Counter)
    tracking_values: bool = True
    min_time: dt.datetime | None = None
    max_time: dt.datetime | None = None

    def observe(self, raw_value: str | None) -> None:
        value = normalize_value(raw_value)
        if not value:
            return

        self.non_empty += 1
        parsed_ts = parse_timestamp(value)
        if parsed_ts is not None:
            self.parsed_time += 1
            if self.min_time is None or parsed_ts < self.min_time:
                self.min_time = parsed_ts
            if self.max_time is None or parsed_ts > self.max_time:
                self.max_time = parsed_ts

        if looks_like_ip(value):
            self.parsed_ip += 1
        if looks_like_int(value):
            self.parsed_int += 1
            self.parsed_float += 1
        elif looks_like_float(value):
            self.parsed_float += 1

        if self.tracking_values:
            self.counter[value] += 1
            if len(self.counter) > MAX_TRACKED_UNIQUES:
                self.tracking_values = False
                self.counter.clear()

    def inferred_type(self) -> str:
        base = self.non_empty or 1
        time_ratio = self.parsed_time / base
        ip_ratio = self.parsed_ip / base
        int_ratio = self.parsed_int / base
        float_ratio = self.parsed_float / base

        if TIME_NAME_RE.search(self.name) or time_ratio >= 0.8:
            return "time"
        if IP_NAME_RE.search(self.name) or ip_ratio >= 0.8:
            return "ip"
        if PORT_NAME_RE.search(self.name):
            return "port"
        if int_ratio >= 0.95:
            return "integer"
        if float_ratio >= 0.95:
            return "number"
        if STATUS_NAME_RE.search(self.name):
            return "status"
        if ACTION_NAME_RE.search(self.name):
            return "action"
        if ID_NAME_RE.search(self.name):
            return "identifier"
        if VOLUME_NAME_RE.search(self.name):
            return "metric"
        return "string"


def detect_log_family(headers: Iterable[str]) -> str:
    lowered = {header.lower() for header in headers}
    if {"domain", "rule_id"} <= lowered or {"attack_type", "client_ip"} <= lowered:
        return "waf_or_edge_security"
    if {"srcip", "dstip"} <= lowered and (
        {"device_name", "policy_name"} & lowered or {"devicename", "policyname"} & lowered
    ):
        return "network_device_or_firewall"
    if {"srcaddr", "dstaddr"} <= lowered:
        return "network_flow"
    if {"bucket", "object"} <= lowered or {"host", "request_uri"} <= lowered:
        return "object_storage_access"
    if {"sql", "db", "user"} <= lowered:
        return "database_audit"
    return "generic_structured_log"


def suggest_focuses(headers: Iterable[str]) -> list[str]:
    lowered = {header.lower() for header in headers}
    focuses: list[str] = []
    if {"srcaddr", "dstaddr", "action"} <= lowered or {"client_ip", "http_status"} <= lowered:
        focuses.append("安全")
    if {"latency", "response_time"} & lowered or {"fail", "error_code", "log-status"} & lowered:
        focuses.append("运维")
    if {"object", "bucket"} <= lowered or {"db", "sql"} <= lowered or {"vm-id", "vpc-id"} <= lowered:
        focuses.append("业务")
    if {"device_name", "policy_name"} & lowered or {"devicename", "policyname"} & lowered:
        if "治理" not in focuses:
            focuses.append("治理")
    if not focuses:
        focuses.append("通用")
    return focuses


def build_recommended_doc_set(
    family_key: str,
    environment: str | None,
    naming_style: str = "portable",
) -> dict[str, str]:
    spec = FAMILY_SPECS[family_key]
    naming = spec["portable_naming"] if naming_style == "portable" else spec["reference_naming"]
    env_code = environment or "common"
    datasource_file = f"{naming['datasource_prefix']}_{env_code}_datasources.yaml"
    return {
        "module_dir": naming["module_dir"],
        "readme": "README.md",
        "overview": "overview.yaml",
        "datasource": datasource_file,
        "analysis_sop": naming["analysis_file"],
        "report_template": naming["report_file"],
    }


def infer_fact_candidates(
    fields: list[dict],
    environment: str | None,
) -> tuple[list[str], list[str]]:
    stable = []
    dynamic = []
    for field in fields:
        name = field["name"]
        lowered = name.lower()
        field_type = field["inferred_type"]
        if lowered in {"region", "account-id", "account_id", "__topic__", "topic", "version"}:
            stable.append(name)
            continue
        if field_type in {"ip", "port", "identifier"}:
            dynamic.append(name)
            continue
        if OBJECT_HINT_RE.search(lowered):
            dynamic.append(name)
            continue
        if field_type in {"action", "status"}:
            dynamic.append(name)
    if environment:
        stable.append(f"environment:{environment}")
    return sorted(dict.fromkeys(stable)), sorted(dict.fromkeys(dynamic))


def build_warning_messages(summary: dict) -> list[str]:
    warnings = []
    if summary["row_count"] < 20:
        warnings.append("样本行数较少，热点值和趋势只适合作为字段建模参考。")
    if not summary["categories"]["time_fields"]:
        warnings.append("未识别到稳定时间字段，后续 SOP 里的时间窗口规则需要人工补充。")
    if not summary["categories"]["action_fields"] and not summary["categories"]["status_fields"]:
        warnings.append("缺少动作或状态字段，异常判断更依赖业务语义和上下文。")
    if summary["family_key"] == "generic_structured_log":
        warnings.append("当前样本未稳定命中已知日志家族，建议先生成通用骨架再逐步细化。")
    return warnings


def format_dt(value: dt.datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(sep=" ", timespec="seconds")


def profile_csv_file(
    csv_path: Path,
    max_rows: int = 0,
    top_n: int = 8,
    family_override: str | None = None,
    environment_override: str | None = None,
    naming_style: str = "portable",
) -> dict:
    dialect = sniff_dialect(csv_path)
    with open_text(csv_path) as handle:
        reader = csv.DictReader(handle, dialect=dialect)
        if not reader.fieldnames:
            raise ValueError("CSV 表头为空，无法分析。")

        stats = {name: FieldStats(name=name) for name in reader.fieldnames}
        row_count = 0
        for row in reader:
            row_count += 1
            for field_name, field_stats in stats.items():
                field_stats.observe(row.get(field_name))
            if max_rows and row_count >= max_rows:
                break

    fields = []
    categories = {
        "time_fields": [],
        "ip_fields": [],
        "port_fields": [],
        "status_fields": [],
        "action_fields": [],
        "identifier_fields": [],
        "metric_fields": [],
    }
    for field_name, field_stats in stats.items():
        inferred = field_stats.inferred_type()
        record = {
            "name": field_name,
            "inferred_type": inferred,
            "non_empty_ratio": round(field_stats.non_empty / row_count, 4) if row_count else 0.0,
            "top_values": field_stats.counter.most_common(top_n) if field_stats.tracking_values else [],
            "value_tracking_truncated": not field_stats.tracking_values,
        }
        if inferred == "time" or field_stats.parsed_time:
            record["time_range"] = {
                "min": format_dt(field_stats.min_time),
                "max": format_dt(field_stats.max_time),
            }
        fields.append(record)

        if inferred == "time":
            categories["time_fields"].append(field_name)
        if inferred == "ip":
            categories["ip_fields"].append(field_name)
        if inferred == "port":
            categories["port_fields"].append(field_name)
        if inferred == "status":
            categories["status_fields"].append(field_name)
        if inferred == "action":
            categories["action_fields"].append(field_name)
        if inferred == "identifier":
            categories["identifier_fields"].append(field_name)
        if inferred in {"metric", "integer", "number"} and (
            VOLUME_NAME_RE.search(field_name) or inferred == "metric"
        ):
            categories["metric_fields"].append(field_name)

    inferred_family = family_override or detect_log_family(reader.fieldnames)
    environment = normalize_environment(environment_override)
    source = "override" if environment else "unknown"
    if not environment:
        environment, source = infer_environment_from_path(csv_path)
    recommended_doc_set = build_recommended_doc_set(
        inferred_family,
        environment,
        naming_style=naming_style,
    )
    reference_doc_set_example = build_recommended_doc_set(
        inferred_family,
        environment,
        naming_style="repo_reference",
    )
    stable_facts, dynamic_facts = infer_fact_candidates(fields, environment)

    summary = {
        "path": str(csv_path),
        "compression": "gzip" if csv_path.suffix.lower() == ".gz" else "plain",
        "delimiter": dialect.delimiter,
        "row_count": row_count,
        "field_count": len(fields),
        "headers": list(stats.keys()),
        "family_key": inferred_family,
        "candidate_log_family": FAMILY_SPECS[inferred_family]["label"],
        "family_lead": FAMILY_SPECS[inferred_family]["lead"],
        "suggested_lenses": suggest_focuses(stats.keys()),
        "naming_style": naming_style,
        "environment_hint": {
            "code": environment,
            "display": ENV_DISPLAY.get(environment, environment.upper()) if environment else None,
            "source": source,
        },
        "module_name_suggestion": recommended_doc_set["module_dir"],
        "recommended_doc_set": recommended_doc_set,
        "reference_doc_set_example": reference_doc_set_example,
        "categories": categories,
        "stable_fact_candidates": stable_facts,
        "dynamic_fact_candidates": dynamic_facts,
        "warnings": [],
        "fields": fields,
    }
    summary["warnings"] = build_warning_messages(summary)
    return summary


def render_text(summary: dict) -> str:
    lines = []
    lines.append(f"文件: {summary['path']}")
    lines.append(f"压缩格式: {summary['compression']}")
    lines.append(f"分隔符: {summary['delimiter']!r}")
    lines.append(f"记录数: {summary['row_count']}")
    lines.append(f"字段数: {summary['field_count']}")
    lines.append(f"候选日志家族: {summary['candidate_log_family']} ({summary['family_key']})")
    lines.append(f"推荐主线: {summary['family_lead']}")
    env_hint = summary["environment_hint"]
    if env_hint["code"]:
        lines.append(f"环境提示: {env_hint['display']} (来源: {env_hint['source']})")
    else:
        lines.append("环境提示: 未识别，建议按通用骨架生成")
    lines.append(f"建议分析方向: {', '.join(summary['suggested_lenses'])}")
    lines.append(f"命名策略: {NAMING_STYLE_LABELS.get(summary['naming_style'], summary['naming_style'])}")
    lines.append(f"建议模块目录: {summary['module_name_suggestion']}")
    lines.append("")
    lines.append("建议文档集合:")
    for key, value in summary["recommended_doc_set"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("仓库对齐时可参考的命名示例:")
    for key, value in summary["reference_doc_set_example"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("稳定事实候选:")
    lines.append(f"- {', '.join(summary['stable_fact_candidates']) or '-'}")
    lines.append("动态事实候选:")
    lines.append(f"- {', '.join(summary['dynamic_fact_candidates']) or '-'}")
    if summary["warnings"]:
        lines.append("")
        lines.append("注意事项:")
        for warning in summary["warnings"]:
            lines.append(f"- {warning}")
    lines.append("")
    lines.append("字段分组:")
    for key, values in summary["categories"].items():
        joined = ", ".join(values) if values else "-"
        lines.append(f"- {CATEGORY_LABELS.get(key, key)}: {joined}")
    lines.append("")
    lines.append("字段摘要:")
    for field in summary["fields"]:
        ratio = f"{field['non_empty_ratio'] * 100:.1f}%"
        field_type = TYPE_LABELS.get(field["inferred_type"], field["inferred_type"])
        lines.append(f"- {field['name']} [{field_type}] 非空占比: {ratio}")
        time_range = field.get("time_range")
        if time_range and (time_range.get("min") or time_range.get("max")):
            lines.append(
                f"  时间范围: {time_range.get('min') or '-'} -> {time_range.get('max') or '-'}"
            )
        if field["top_values"]:
            rendered = ", ".join(f"{value}({count})" for value, count in field["top_values"])
            lines.append(f"  热点值: {rendered}")
        elif field["value_tracking_truncated"]:
            lines.append("  热点值: 唯一值过多，已停止跟踪")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="分析 CSV/CSV.GZ 日志样本，为生成 SOP 或配套文档提供字段画像。")
    parser.add_argument("csv_path", help="CSV 或 CSV.GZ 文件路径")
    parser.add_argument("--max-rows", type=int, default=0, help="最多扫描多少行；0 表示扫描全部")
    parser.add_argument("--top", type=int, default=8, help="每个字段最多展示多少个热点值")
    parser.add_argument(
        "--family",
        choices=sorted(FAMILY_SPECS.keys()),
        help="手工指定日志家族，覆盖自动识别",
    )
    parser.add_argument("--environment", help="手工指定环境，如 uat/prod/sit/pre/test/dev")
    parser.add_argument(
        "--naming-style",
        choices=sorted(NAMING_STYLE_LABELS.keys()),
        default="portable",
        help="生成建议时采用的命名策略，默认使用可独立迁移的便携命名",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON，而不是纯文本")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.csv_path)
    if not path.is_file():
        print(f"CSV 文件不存在: {path}", file=sys.stderr)
        return 1
    try:
        summary = profile_csv_file(
            path,
            max_rows=args.max_rows,
            top_n=args.top,
            family_override=args.family,
            environment_override=args.environment,
            naming_style=args.naming_style,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
