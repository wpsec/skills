#!/usr/bin/env python3
"""Profile an Alibaba Cloud Resource Center CSV for topology work."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


HEADER_ALIASES = {
    "resource_id": ("资源id", "resourceid", "id"),
    "resource_name": ("资源名称", "resourcename", "name"),
    "region": ("地域名称", "regionname", "region"),
    "zone": ("可用区", "availabilityzone", "zone"),
    "resource_type": ("资源类型", "resourcetype", "type"),
    "resource_type_code": ("资源类型code", "resourcetypecode", "typecode"),
    "resource_group": ("资源组名称", "resourcegroupname", "resourcegroup"),
    "tags": ("标签", "tags", "tag"),
}

ENV_TAG_KEYS = {
    "env",
    "environment",
    "stage",
    "tier",
    "环境",
    "环境名称",
    "部署环境",
}
RELATION_KEY_PARTS = (
    "ack",
    "cluster",
    "vpc",
    "vswitch",
    "subnet",
    "network",
    "nodepool",
    "eni",
    "securitygroup",
    "loadbalancer",
    "instanceid",
    "resourceid",
)
TOPOLOGY_HINTS = (
    "vpc",
    "专有网络",
    "交换机",
    "subnet",
    "路由表",
    "route table",
    "安全组",
    "security group",
    "云服务器",
    "ecs",
    "kubernetes",
    "容器服务",
    "ack",
    "负载均衡",
    "load balancer",
    "clb",
    "alb",
    "弹性网卡",
    "eni",
    "nat",
    "弹性公网",
    "eip",
    "数据库",
    "database",
    "rds",
    "tair",
    "redis",
    "mysql",
    "postgres",
    "对象存储",
    "oss",
    "文件存储",
    "nas",
    "容器镜像",
    "registry",
    "acr",
    "vpn",
    "防火墙",
    "firewall",
    "waf",
    "api网关",
    "api gateway",
    "域名",
    "dns",
)
AGGREGATE_HINTS = ("仓库", "repository", "虚拟服务器组", "server group")
NON_TOPOLOGY_HINTS = ("快照", "snapshot", "密钥对", "keypair", "权限策略", "磁盘", "disk")
SECRET_RE = re.compile(
    r"(?i)\b(?:LTAI|AKIA|ASIA)[A-Z0-9]{12,}\b|"
    r"\b(?:access.?key|secret|token|password)[\s:=_-]+[A-Za-z0-9/+=._-]{12,}"
)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{24,}\b")


def normalize_header(value: str) -> str:
    return "".join(char.casefold() for char in value.strip().lstrip("\ufeff") if char.isalnum())


def parse_tags(value: str) -> list[tuple[str, str]]:
    result = []
    for item in value.split(";"):
        key, separator, tag_value = item.partition(":")
        if separator and key.strip():
            result.append((key.strip(), tag_value.strip()))
    return result


def resolve_columns(headers: list[str | None]) -> dict[str, str]:
    normalized = {
        normalize_header(header or ""): header
        for header in headers
        if header is not None
    }
    columns = {}
    for field, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            column = normalized.get(normalize_header(alias))
            if column:
                columns[field] = column
                break

    if "resource_type" not in columns:
        columns["resource_type"] = columns.get("resource_type_code", "")
    if not columns.get("resource_type"):
        accepted = "、".join(HEADER_ALIASES["resource_type"])
        raise ValueError(f"缺少资源类型列，支持的列名包括：{accepted}")
    return columns


def read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError("CSV 没有表头")
        columns = resolve_columns(reader.fieldnames)
        rows = []
        for line_number, raw in enumerate(reader, start=2):
            if None in raw:
                raise ValueError(f"第 {line_number} 行字段数与表头不一致")
            row = {
                field: (raw.get(column) or "").strip() if column else ""
                for field, column in columns.items()
            }
            row["tags_parsed"] = parse_tags(row.get("tags", ""))
            row["line_number"] = line_number
            rows.append(row)
    return rows


def environment_match(value: str, environment: str) -> bool:
    value = value.casefold()
    environment = environment.strip().casefold()
    if not value or not environment:
        return False
    if environment.isascii() and environment.replace("-", "").isalnum():
        pattern = rf"(?<![a-z0-9]){re.escape(environment)}(?![a-z0-9])"
        return re.search(pattern, value) is not None
    return environment in value


def matches_environment(row: dict[str, Any], environment: str) -> bool:
    if environment_match(row.get("resource_name", ""), environment):
        return True
    if environment_match(row.get("resource_group", ""), environment):
        return True
    for key, value in row["tags_parsed"]:
        if normalize_header(key) in ENV_TAG_KEYS and environment_match(value, environment):
            return True
    return False


def relation_tag(key: str) -> bool:
    normalized = normalize_header(key)
    return any(part in normalized for part in RELATION_KEY_PARTS)


def relation_pairs(row: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (normalize_header(key), value.casefold())
        for key, value in row["tags_parsed"]
        if value and relation_tag(key)
    }


def linked_by_anchor(row: dict[str, Any], anchors: set[tuple[str, str]]) -> bool:
    own_pairs = relation_pairs(row)
    if own_pairs.intersection(anchors):
        return True

    searchable = row.get("resource_name", "").casefold()
    for key, value in anchors:
        if len(value) >= 10 and any(
            part in key for part in ("cluster", "ack", "vpc", "resourceid")
        ):
            if value in searchable:
                return True
    return False


def topology_relevant(resource_type: str) -> bool:
    normalized = resource_type.casefold()
    if any(hint in normalized for hint in NON_TOPOLOGY_HINTS):
        return False
    return any(hint in normalized for hint in TOPOLOGY_HINTS)


def safe_label(value: str) -> str:
    value = SECRET_RE.sub("[已脱敏]", value)
    value = IP_RE.sub("[IP]", value)
    return LONG_TOKEN_RE.sub("[资源标识]", value).strip() or "未命名"


def select_candidates(
    rows: list[dict[str, Any]],
    environment: str,
    resource_group: str | None,
) -> tuple[set[int], set[int], set[int]]:
    direct_group = set()
    direct_environment = set()
    for index, row in enumerate(rows):
        if resource_group and row.get("resource_group", "").casefold() == resource_group.casefold():
            direct_group.add(index)
        if matches_environment(row, environment):
            direct_environment.add(index)

    seeds = direct_group | direct_environment
    anchors = set()
    for index in seeds:
        anchors.update(relation_pairs(rows[index]))

    linked = {
        index
        for index, row in enumerate(rows)
        if index not in seeds and linked_by_anchor(row, anchors)
    }
    return seeds, linked, direct_group


def cluster_relationships(rows: list[dict[str, Any]]) -> list[tuple[str, Counter[str]]]:
    reports = []
    for cluster in rows:
        resource_type = cluster.get("resource_type", "").casefold()
        if "集群" not in resource_type and "cluster" not in resource_type:
            continue
        anchors = relation_pairs(cluster)
        if not anchors:
            continue
        counts = Counter()
        for row in rows:
            if row is cluster or linked_by_anchor(row, anchors):
                counts[row.get("resource_type") or "未分类"] += 1
        if sum(counts.values()) > 1:
            reports.append((safe_label(cluster.get("resource_name", "")), counts))
    return reports


def format_candidates(rows: list[dict[str, Any]], selected: set[int]) -> list[str]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for index in sorted(selected):
        row = rows[index]
        resource_type = row.get("resource_type") or "未分类"
        if topology_relevant(resource_type):
            key = (
                resource_type,
                row.get("resource_group") or "未分组",
                row.get("region") or "地域未知",
            )
            grouped[key].append(row)

    output = []
    for (resource_type, resource_group, region), items in sorted(grouped.items()):
        names = sorted({safe_label(item.get("resource_name", "")) for item in items})
        summary = f"{len(items)} 项"
        if any(hint in resource_type.casefold() for hint in AGGREGATE_HINTS):
            details = "聚合展示"
        elif names:
            samples = names[:5]
            details = "、".join(samples)
            if len(names) > len(samples):
                details += f" 等 {len(names)} 个名称"
        else:
            details = "名称缺失"
        output.append(
            f"- {resource_type}：{summary}；资源组={resource_group}；"
            f"地域={region}；{details}"
        )
    return output


def print_report(
    rows: list[dict[str, Any]],
    environment: str,
    resource_group: str | None,
    seeds: set[int],
    linked: set[int],
    direct_group: set[int],
) -> None:
    selected = seeds | linked
    print(f"环境筛选：{environment}")
    print(f"资源总数：{len(rows)}")
    print(f"环境名/标签匹配：{len(seeds - direct_group)}")
    if resource_group:
        print(f"指定资源组匹配（{resource_group}）：{len(direct_group)}")
    print(f"通过共享关联标识找到的跨组候选：{len(linked)}")
    print(f"候选总数：{len(selected)}")

    group_counts = Counter(rows[index].get("resource_group") or "未分组" for index in selected)
    if group_counts:
        print("\n候选资源组：")
        for group, count in group_counts.most_common():
            print(f"- {safe_label(group)}：{count}")

    type_counts = Counter(
        rows[index].get("resource_type") or "未分类"
        for index in selected
        if topology_relevant(rows[index].get("resource_type", ""))
    )
    print("\n候选拓扑资源类型 Top 20：")
    for resource_type, count in type_counts.most_common(20):
        print(f"- {safe_label(resource_type)}：{count}")

    candidates = format_candidates(rows, selected)
    print("\n拓扑资源候选：")
    if candidates:
        for item in candidates:
            print(item)
    else:
        print("- 未找到符合当前筛选条件的拓扑资源。")

    relationships = cluster_relationships(rows)
    if relationships:
        print("\nACK/Kubernetes 集群关联摘要（共享关系标识，不代表流量方向）：")
        for name, counts in relationships:
            related = [
                f"{safe_label(resource_type)} {count}"
                for resource_type, count in counts.most_common(8)
            ]
            print(f"- {name}：{'；'.join(related)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="统计阿里云资源清单并提取拓扑候选；不会输出资源 ID、IP 或标签值。"
    )
    parser.add_argument("csv_path", type=Path, help="Resource Center 导出的 CSV")
    parser.add_argument("--environment", required=True, help="环境名称，例如 DEV、PROD")
    parser.add_argument("--resource-group", help="可选的资源组名称")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        rows = read_rows(args.csv_path)
        print_report(
            rows,
            args.environment,
            args.resource_group,
            *select_candidates(rows, args.environment, args.resource_group),
        )
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
